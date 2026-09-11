"""Sıra numarasından paket kaybı/tekrar/sıra dışılık hesabı — `F5-012`.

`docs/live/protocol-contract.md` §4: `sequence_no` bir `uint32`'dir ve
`2**32`'de sarar. Sarma kuralı ADR-003 §2.4'teki `device_ticks` sarma
kontrolüyle **aynı desenle** ele alınır: ardışık iki değer arasında fark
azaldıysa ve makul bir sarma farkına (nominal periyodun birkaç katı)
uyuyorsa sarma kabul edilir; uymuyorsa "sayaç geri gitti" (reset) olarak
işaretlenir.

Dört sınıf ayrı sayılır — hiçbiri diğerine sessizce karışmaz:

- **`in_order`** — beklenen bir sonraki değer (sarma dahil).
- **`gap`** — ileri bir atlama; kaç paketin atlandığı (`gap_size`) ayrıca
  toplanır (`missing_total`).
- **`duplicate`** — daha önce görülmüş bir değerin tekrarı.
- **`out_of_order`** — son görülenden geride ama makul sınırlar içinde,
  daha önce görülmemiş bir değer (geç gelen paket).
- **`reset`** — makul hiçbir açıklamaya uymayan büyük bir geri sıçrama;
  yeni bir oturum başladığı varsayılır (`F5-002`'nin yeniden bağlanma
  sonrası sıfırdan başlayan `sequence_no`'suyla tutarlı).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

#: `sequence_no` bir uint32'dir (`docs/live/protocol-contract.md` §2).
SEQUENCE_BITS = 32
SEQUENCE_MODULUS = 1 << SEQUENCE_BITS

#: Sarma/geç-gelme için "makul" kabul edilen en büyük fark; bunun üstü reset sayılır.
DEFAULT_MAX_PLAUSIBLE_GAP = 1000

#: Tekrar tespiti için tutulan pencere — sınırsız büyümesin diye (`F5-014`/`F5-016`
#: ile aynı "bellek sınırlı kal" ilkesi, burada basit bir sabit pencere olarak).
DEFAULT_DUPLICATE_WINDOW = 256


@dataclass(frozen=True)
class SequenceObservation:
    """Tek bir `sequence_no` gözleminin sınıflandırması."""

    sequence_no: int
    kind: str  # "in_order" | "gap" | "duplicate" | "out_of_order" | "reset"
    gap_size: int = 0


@dataclass
class SequenceStats:
    """Oturum boyunca biriken sayaçlar — bağlantı sağlığı göstergesi."""

    in_order: int = 0
    gaps: int = 0
    missing_total: int = 0
    duplicates: int = 0
    out_of_order: int = 0
    resets: int = 0

    @property
    def total_observed(self) -> int:
        return self.in_order + self.gaps + self.duplicates + self.out_of_order + self.resets


class SequenceTracker:
    """Ardışık `sequence_no` gözlemlerini sınıflandırıp ayrı sayaçlara işler."""

    def __init__(
        self,
        *,
        max_plausible_gap: int = DEFAULT_MAX_PLAUSIBLE_GAP,
        duplicate_window: int = DEFAULT_DUPLICATE_WINDOW,
    ) -> None:
        if max_plausible_gap < 1:
            raise ValueError(f"max_plausible_gap pozitif olmali: {max_plausible_gap}")
        if duplicate_window < 1:
            raise ValueError(f"duplicate_window pozitif olmali: {duplicate_window}")
        self._max_plausible_gap = max_plausible_gap
        self._last: int | None = None
        self._recent: deque[int] = deque(maxlen=duplicate_window)
        self._recent_set: set[int] = set()
        self.stats = SequenceStats()

    def observe(self, sequence_no: int) -> SequenceObservation:
        """`sequence_no`yu sınıflandırır ve ilgili sayacı bir artırır."""
        if not 0 <= sequence_no < SEQUENCE_MODULUS:
            raise ValueError(f"sequence_no uint32 araliginda olmali: {sequence_no}")

        if self._last is None:
            self._advance(sequence_no)
            self.stats.in_order += 1
            return SequenceObservation(sequence_no, "in_order")

        if sequence_no in self._recent_set:
            self.stats.duplicates += 1
            return SequenceObservation(sequence_no, "duplicate")

        if sequence_no == (self._last + 1) % SEQUENCE_MODULUS:
            self._advance(sequence_no)
            self.stats.in_order += 1
            return SequenceObservation(sequence_no, "in_order")

        if sequence_no > self._last:
            gap = sequence_no - self._last - 1
            self._advance(sequence_no)
            self.stats.gaps += 1
            self.stats.missing_total += gap
            return SequenceObservation(sequence_no, "gap", gap_size=gap)

        wrapped_delta = (sequence_no + SEQUENCE_MODULUS) - self._last - 1
        if 0 <= wrapped_delta <= self._max_plausible_gap:
            self._advance(sequence_no)
            if wrapped_delta == 0:
                self.stats.in_order += 1
                return SequenceObservation(sequence_no, "in_order")
            self.stats.gaps += 1
            self.stats.missing_total += wrapped_delta
            return SequenceObservation(sequence_no, "gap", gap_size=wrapped_delta)

        if self._last - sequence_no <= self._max_plausible_gap:
            self._remember(sequence_no)
            self.stats.out_of_order += 1
            return SequenceObservation(sequence_no, "out_of_order")

        # Ne sarma ne makul bir geç geliş: yeni bir oturum baslamis kabul edilir.
        self._recent.clear()
        self._recent_set.clear()
        self._advance(sequence_no)
        self.stats.resets += 1
        return SequenceObservation(sequence_no, "reset")

    def _advance(self, sequence_no: int) -> None:
        self._last = sequence_no
        self._remember(sequence_no)

    def _remember(self, sequence_no: int) -> None:
        if len(self._recent) == (self._recent.maxlen or 0):
            self._recent_set.discard(self._recent[0])
        self._recent.append(sequence_no)
        self._recent_set.add(sequence_no)

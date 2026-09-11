"""Canlı cihaz zamanını kanonik zamana bağlama — `F5-013`.

`docs/adr/ADR-003-time-base.md` §2.3'ün `TimeBase` modeli ve
`ticks_to_utc_ns()` çekirdeği dosya tarafında `F2-025`
(`sonar_analyzer.io.decoders.tick_conversion.convert_tick`) tarafından
kullanılıyor. Bu modül **aynı** çekirdeği canlı tel protokolünün
`LiveWireHeader.device_ticks` alanına bağlıyor.

Kabul kriteri "Dosya ve canlı replay aynı zaman tabanında eşleşir" burada
mimari olarak sağlanır: iki ayrı dönüşüm yazılmadı, dosya ve canlı tarafı
**aynı** `ticks_to_utc_ns()` fonksiyonunu çağırır — sürüklenme riski
yapısal olarak yoktur (`tests/unit/test_live_time.py` bunu doğrudan
kanıtlar).
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_base import TimeBase, ticks_to_utc_ns
from sonar_analyzer.io.live.wire_header import LiveWireHeader

#: Hesaplanan pencere başlangıcı ile payload'ın kendi ilk örneğinin zamanı
#: arasında makul kabul edilen en büyük sapma — bunun üstü saat kayması
#: (`Quality.JITTER`in canlı akıştaki karşılığı) olarak işaretlenir.
JITTER_TOLERANCE_NS = 1_000_000  # 1 ms


def canonical_window_start_ns(header: LiveWireHeader, time_base: TimeBase, ticks0: int = 0) -> int:
    """`header.device_ticks`'i kanonik UTC ns'ye çevirir.

    Dosya tarafındaki `tick_conversion.convert_tick()` ile **aynı**
    `ticks_to_utc_ns()` çekirdeğini çağırır — bu fonksiyonun tek işi bu
    çekirdeği canlı başlığın alan adına bağlamaktır.
    """
    return ticks_to_utc_ns(time_base, header.device_ticks, ticks0)


@dataclass(frozen=True)
class TimedWindow:
    """Bir paketin cihaz sayacından bağımsız hesaplanan kanonik penceresi.

    `payload_first_sample_ns`, payload'un kendi baytlarına gömülü ilk
    örnek zamanıdır (`F5-006`'nın kodladığı) — ikisi **bağımsız** iki
    kaynaktan gelir: biri ham sayaçtan (`device_ticks` + `TimeBase`), biri
    payload'un kendi içeriğinden. Anlaşmazlık gerçek bir saat kaymasının
    işaretidir, kodlama hatası değil.
    """

    canonical_window_start_ns: int
    payload_first_sample_ns: int | None

    @property
    def agrees_with_payload(self) -> bool:
        """Payload'la karşılaştırılacak bir şey yoksa (boş pencere) `True`."""
        if self.payload_first_sample_ns is None:
            return True
        deviation = abs(self.canonical_window_start_ns - self.payload_first_sample_ns)
        return deviation <= JITTER_TOLERANCE_NS

    @property
    def deviation_ns(self) -> int | None:
        if self.payload_first_sample_ns is None:
            return None
        return self.canonical_window_start_ns - self.payload_first_sample_ns


def timed_window(
    header: LiveWireHeader,
    time_base: TimeBase,
    ticks0: int,
    payload_first_sample_ns: int | None,
) -> TimedWindow:
    """Bir paket için `TimedWindow`'u tek adımda kurar."""
    return TimedWindow(
        canonical_window_start_ns=canonical_window_start_ns(header, time_base, ticks0),
        payload_first_sample_ns=payload_first_sample_ns,
    )


def _first_sample_ns(chunks: list[DataChunk]) -> int | None:
    """Payload'daki kanalların en erken örnek zamanı; hiç örnek yoksa `None`."""
    starts = [int(chunk.timestamps_ns[0]) for chunk in chunks if len(chunk)]
    return min(starts) if starts else None


def timed_window_from_packet(
    header: LiveWireHeader,
    chunks: list[DataChunk],
    time_base: TimeBase,
    ticks0: int,
) -> TimedWindow:
    """`timed_window`'un kolaylığı: `payload_first_sample_ns`'i çözülmüş `chunks`'tan
    kendisi çıkarır — üç adaptörün (UDP/TCP/Serial) tekrar yazmaması için.
    """
    return timed_window(header, time_base, ticks0, _first_sample_ns(chunks))

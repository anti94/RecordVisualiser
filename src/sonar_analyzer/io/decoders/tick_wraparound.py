"""Sayaç sarması (wraparound) ve saat resetini ayırt etme — `F2-026`.

`docs/adr/ADR-003-time-base.md` §2.4/§2.5: ardışık iki kayıtta `ticks`
azaldığında, **sarma** (sayaç genişliğine göre beklenen, unwrap
edilebilir) ile **reset** (açıklanamayan geri gidiş, yeni bir time-base
segmenti başlatır) ayırt edilir. Sarma varsayımıyla hesaplanan fark
makul aralıktaysa (nominal periyodun birkaç katı) sarma kabul edilir;
değilse cihaz sayacının sıfırlandığı işaretlenir — sıralama düzeltmesiyle
gizlenmez (ADR-003 §2.7 ile aynı ilke, `F2-011`'deki geri giden
`sequence_no` teşhisiyle paralel).

Bu iki durum farklı **zaman kalitesi** (`sync_quality`, ADR-003 §2.8)
üretir: sarma sonrası eksen doğrusal kalır (`iyi`), reset sonrası
segmentler arası ilişki bilinmez (`şüpheli`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TickAnomalyKind(str, Enum):
    """Bir geri gidişin sınıflandırması."""

    WRAPAROUND = "wraparound"
    RESET = "reset"


class SyncQuality(str, Enum):
    """ADR-003 §2.8: kayıt için hesaplanan senkron kalitesi."""

    GOOD = "iyi"
    SUSPECT = "supheli"
    UNKNOWN = "bilinmiyor"


@dataclass(frozen=True)
class TickAnomaly:
    """Ardışık iki tick örneği arasında tespit edilen geri gidiş."""

    index: int
    kind: TickAnomalyKind
    previous_ticks: int
    observed_ticks: int
    #: Yalnız `WRAPAROUND` için dolu; `RESET`'te sarma varsayımı reddedildi.
    unwrapped_ticks: int | None

    def __str__(self) -> str:
        if self.kind is TickAnomalyKind.WRAPAROUND:
            return (
                f"Sayac sarmasi: index {self.index}, {self.previous_ticks} -> "
                f"{self.observed_ticks} (unwrap: {self.unwrapped_ticks})"
            )
        return (
            f"Cihaz sayaci sifirlandi: index {self.index}, "
            f"{self.previous_ticks} -> {self.observed_ticks}"
        )


def detect_tick_anomaly(
    previous_ticks: int,
    observed_ticks: int,
    counter_bits: int,
    max_plausible_delta: int,
    index: int,
) -> TickAnomaly | None:
    """ADR-003 §2.4 algoritmasının birebir uygulaması.

    `ticks` azalmadıysa `None` döner (anomali yok). Azaldıysa: sarma
    varsayımıyla hesaplanan `delta` makul aralıktaysa (`0 < delta <=
    max_plausible_delta`) `WRAPAROUND`, değilse `RESET` sayılır.
    """
    if observed_ticks >= previous_ticks:
        return None

    counter_range = 1 << counter_bits
    delta = (observed_ticks + counter_range) - previous_ticks

    if 0 < delta <= max_plausible_delta:
        return TickAnomaly(
            index=index,
            kind=TickAnomalyKind.WRAPAROUND,
            previous_ticks=previous_ticks,
            observed_ticks=observed_ticks,
            unwrapped_ticks=previous_ticks + delta,
        )
    return TickAnomaly(
        index=index,
        kind=TickAnomalyKind.RESET,
        previous_ticks=previous_ticks,
        observed_ticks=observed_ticks,
        unwrapped_ticks=None,
    )


def sync_quality_for_anomaly(anomaly: TickAnomaly | None) -> SyncQuality:
    """ADR-003 §2.8: anomali türünden senkron kalitesini türetir.

    Sarma sonrası eksen doğrusal kalır (unwrap yeterli) — `iyi`. Reset
    sonrası segmentler arası zaman ilişkisi bilinmez, uygulama iki
    segmenti tek sürekli eksen gibi çizmez — `şüpheli`. Anomali yoksa
    `iyi`.
    """
    if anomaly is None or anomaly.kind is TickAnomalyKind.WRAPAROUND:
        return SyncQuality.GOOD
    return SyncQuality.SUSPECT

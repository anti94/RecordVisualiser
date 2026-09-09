"""Time-base modeli — `docs/adr/ADR-003-time-base.md` §2.3.

Ham cihaz sayacını (`device_ticks`) kanonik UTC ns'ye çevirmenin temelidir.
Profil A'da sayaç **yoktur** (`tick_hz = 0`); Profil B `device_ticks` ve
`device_tick_hz` taşır. Her kanal bir `time_base_id` taşır
(`ChannelMetadata.time_base_id`); farklı `TimeBase`'lerdeki kanallar
karşılaştırıldığında senkron kalitesi kullanıcıya gösterilir (ADR-003 §2.8).
"""

from __future__ import annotations

from dataclasses import dataclass

#: 1 saniye = 1e9 nanosaniye — tick->ns dönüşümünde ortak çarpan.
_NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class TimeBase:
    """Bir cihaz saat kaynağının tanımı (ADR-003 §2.3)."""

    id: str
    #: `ticks = ticks0` anındaki UTC karşılığı.
    epoch_utc_ns: int
    #: Tick frekansı (Hz); `0` sayaç yok demektir (Profil A).
    tick_hz: int
    source: str = "unknown"
    #: Ölçülmüş/bildirilmiş sapma; `0.0` => düzeltme yok (ADR-003 §2.6).
    drift_ppm: float = 0.0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("time_base id bos olamaz")
        if self.tick_hz < 0:
            raise ValueError(f"{self.id}: tick_hz negatif olamaz: {self.tick_hz}")

    @property
    def has_counter(self) -> bool:
        """`tick_hz == 0` ise ham sayaç yoktur (Profil A) — ADR-003 §2.3/§2.8."""
        return self.tick_hz > 0


def ticks_to_utc_ns(time_base: TimeBase, ticks: int, ticks0: int) -> int:
    """ADR-003 §2.3: `ticks`'i tamsayı aritmetiğiyle UTC ns'ye çevirir.

    Yuvarlama hatası birikmez (tamsayı bölme kullanılır); `time_base.tick_hz
    == 0` sayaç olmadığı anlamına gelir (Profil A) — bu fonksiyon çağrılmamalıdır.
    """
    if time_base.tick_hz == 0:
        raise ValueError(
            f"{time_base.id}: tick_hz=0 (sayac yok, Profil A) - ticks_to_utc_ns cagrilmamali"
        )
    return time_base.epoch_utc_ns + (ticks - ticks0) * _NS_PER_SECOND // time_base.tick_hz

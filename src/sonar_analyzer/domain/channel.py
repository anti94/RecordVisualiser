"""Kanal tanımı — `F1-011`.

`ChannelMetadata`, bir veri kanalının kimliğini ve ölçüm özelliklerini taşır.
Ham `.bin` düzeninden bağımsızdır: parser bu modeli üretir, GUI yalnız bunu görür
(plan Bölüm 7.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

#: Desteklenen ornek veri tipleri (docs/format/profile-a.md dtype tablosu).
#: Gercek degerli tipler — Profil A ve B kanallari.
REAL_DTYPES = frozenset({"int16", "int32", "float32", "float64", "uint8"})

#: Complex (I/Q) tipler — Profil C sensor kanallari (`D-28`).
#:
#: Ayri tutulmalari bilincli: complex bir kanala gercek degerli bir
#: analiz uygulamak sessizce yanlis sonuc vermez, **hata verir**. NumPy
#: 2.0'da `np.fft.rfft` complex girdide `TypeError` firlatiyor; sanal
#: kismi sessizce atmiyor. Hangi kanalin hangi kumeden oldugunu bilmek,
#: o hatanin kullaniciya anlamli bir mesaj olarak tasinmasini saglar.
COMPLEX_DTYPES = frozenset({"complex64", "complex128"})

SUPPORTED_DTYPES = REAL_DTYPES | COMPLEX_DTYPES


class ChannelSource(str, Enum):
    """Kanalın hangi kaynaktan geldiği — Data Explorer grupları (plan Bölüm 5.2)."""

    SONAR = "sonar"
    ACOUSTIC = "acoustic"
    SENSORS = "sensors"
    NAVIGATION = "navigation"
    TRANSMISSION = "transmission"
    BIT = "bit"
    DERIVED = "derived"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ChannelMetadata:
    """Tek bir kanalın değişmeyen tanımı."""

    id: str
    path: str
    name: str
    dtype: str
    source: ChannelSource = ChannelSource.UNKNOWN
    unit: str | None = None
    sample_rate_hz: float | None = None
    time_base_id: str = "device0"
    calibration_id: str | None = None
    gain: float = 1.0
    offset: float = 0.0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Kanal kimligi bos olamaz")
        if not self.path.strip():
            raise ValueError(f"{self.id}: kanal yolu bos olamaz")
        if self.dtype not in SUPPORTED_DTYPES:
            supported = ", ".join(sorted(SUPPORTED_DTYPES))
            raise ValueError(
                f"{self.id}: desteklenmeyen dtype {self.dtype!r}. Desteklenen: {supported}"
            )
        if self.sample_rate_hz is not None and self.sample_rate_hz <= 0:
            raise ValueError(
                f"{self.id}: sample rate pozitif olmali, verilen: {self.sample_rate_hz}"
            )
        if not self.time_base_id.strip():
            raise ValueError(f"{self.id}: time_base_id bos olamaz")

    @property
    def display_unit(self) -> str:
        """Grafik ekseninde gösterilecek birim; tanımsızsa boş metin."""
        return self.unit or ""

    @property
    def display_label(self) -> str:
        """Grafik başlığı: ad ve varsa birim."""
        return f"{self.name} [{self.unit}]" if self.unit else self.name

    @property
    def sample_period_ns(self) -> int | None:
        """Örnekler arası nominal süre; sample rate bilinmiyorsa `None`."""
        if self.sample_rate_hz is None:
            return None
        return round(1_000_000_000 / self.sample_rate_hz)

    def to_physical(self, raw: float) -> float:
        """Ham değeri fiziksel birime çevirir: `raw * gain + offset`."""
        return raw * self.gain + self.offset

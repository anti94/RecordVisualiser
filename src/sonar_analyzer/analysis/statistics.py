"""Örnek dizisi temel istatistikleri — `F3-037`, `F3-038`.

Saf sayısal katman: bir `float64` dizisi girer, `SampleStatistics` çıkar.
Qt/pyqtgraph bağımlılığı yoktur; UI (`F3-039` dashboard kartı) bu
sonuçları yalnız biçimlendirir.

`std` **popülasyon** standart sapmasıdır (`ddof = 0`, NumPy varsayılanı).
`rms = sqrt(mean(x²))`. `peak_to_peak = max − min`.

Boş dizi bir hata değildir: `count = 0`, sayısal alanların hepsi `NaN`
(tanımlı ve gösterilebilir — `F3-038` "boş aralık tanımlı gösterilir").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

#: `F3-037` temel alanlar.
BASIC_STAT_FIELDS: tuple[str, ...] = ("count", "minimum", "maximum", "mean")
#: `F3-038` ile eklenen alanlar.
EXTENDED_STAT_FIELDS: tuple[str, ...] = ("median", "rms", "std", "peak_to_peak")


@dataclass(frozen=True)
class SampleStatistics:
    """Bir örnek dizisinin özeti.

    `count` örnek sayısı; diğer tüm alanlar dizi boşsa `NaN`.
    """

    count: int
    minimum: float
    maximum: float
    mean: float
    median: float
    rms: float
    std: float
    peak_to_peak: float

    @property
    def is_empty(self) -> bool:
        return self.count == 0


def summarize(values: NDArray[np.float64]) -> SampleStatistics:
    """`values` dizisinin tam istatistik özetini döndürür — `F3-037`/`F3-038`.

    Kabul kriteri: bilinen/referans dizi beklenen sonuçları üretir;
    boş aralık tanımlı (`NaN`) gösterilir.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.size == 0:
        nan = float("nan")
        return SampleStatistics(0, nan, nan, nan, nan, nan, nan, nan)
    minimum = float(data.min())
    maximum = float(data.max())
    return SampleStatistics(
        count=int(data.size),
        minimum=minimum,
        maximum=maximum,
        mean=float(data.mean()),
        median=float(np.median(data)),
        rms=float(np.sqrt(np.mean(np.square(data)))),
        std=float(data.std()),
        peak_to_peak=maximum - minimum,
    )

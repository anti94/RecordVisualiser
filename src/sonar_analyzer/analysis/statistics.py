"""Örnek dizisi temel istatistikleri — `F3-037`.

Saf sayısal katman: bir `float64` dizisi girer, `SampleStatistics` çıkar.
Qt/pyqtgraph bağımlılığı yoktur; UI (`F3-039` dashboard kartı) bu
sonuçları yalnız biçimlendirir.

Boş dizi bir hata değildir: `count = 0`, kalan alanlar `NaN`
(tanımlı ve gösterilebilir — `F3-038` "boş aralık tanımlı gösterilir").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

#: `F3-037` bu iş yalnız şu alanları hesaplar; medyan/RMS/std/tepe-tepe `F3-038`.
BASIC_STAT_FIELDS: tuple[str, ...] = ("count", "minimum", "maximum", "mean")


@dataclass(frozen=True)
class SampleStatistics:
    """Bir örnek dizisinin özeti.

    `count` örnek sayısı; `minimum`/`maximum`/`mean` dizi boşsa `NaN`.
    """

    count: int
    minimum: float
    maximum: float
    mean: float

    @property
    def is_empty(self) -> bool:
        return self.count == 0


def summarize(values: NDArray[np.float64]) -> SampleStatistics:
    """`values` dizisinin count/min/max/mean özetini döndürür — `F3-037`.

    Kabul kriteri: bilinen kısa dizi beklenen istatistikleri üretir.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.size == 0:
        nan = float("nan")
        return SampleStatistics(count=0, minimum=nan, maximum=nan, mean=nan)
    return SampleStatistics(
        count=int(data.size),
        minimum=float(data.min()),
        maximum=float(data.max()),
        mean=float(data.mean()),
    )

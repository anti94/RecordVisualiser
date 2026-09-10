"""İstatistik kartı — `F1-039`, `F3-039`.

Mockup satır 3 sağ hücresi (`docs/ui/layout-map.md` §3): `Statistics (kanal)`
başlığı altında Mean, Std, RMS, Min, Max, Peak-Peak — altı satır, birimli.

Sayısal hesap `analysis.statistics.summarize` tek kaynağından gelir
(`F3-037`/`F3-038`); bu panel yalnız biçimlendirir. `F3-039`: kart bir
zaman bölgesi (ROI) seçilince yalnız o pencerenin değerlerini gösterir.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QWidget

from sonar_analyzer.analysis.statistics import summarize
from sonar_analyzer.domain.channel import ChannelMetadata

EMPTY_VALUE = "—"
EMPTY_TITLE = "Statistics"

#: Mockup sirasi -> `SampleStatistics` alani.
STAT_FIELDS: tuple[str, ...] = ("Mean", "Std", "RMS", "Min", "Max", "Peak-Peak")
_FIELD_TO_ATTR: dict[str, str] = {
    "Mean": "mean",
    "Std": "std",
    "RMS": "rms",
    "Min": "minimum",
    "Max": "maximum",
    "Peak-Peak": "peak_to_peak",
}


def compute_statistics(values: NDArray[np.float64]) -> dict[str, float]:
    """Kartın altı alanını `summarize()`'dan biçimlenmemiş `float` olarak verir."""
    stats = summarize(np.asarray(values, dtype=np.float64))
    return {field: float(getattr(stats, attr)) for field, attr in _FIELD_TO_ATTR.items()}


class StatisticsPanel(QGroupBox):
    """Seçili kanalın altı temel istatistiğini gösteren kart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EMPTY_TITLE, parent)
        self.setObjectName("panel_statistics")

        form = QFormLayout(self)
        form.setContentsMargins(6, 6, 6, 6)

        self._fields: dict[str, QLabel] = {}
        for name in STAT_FIELDS:
            value = QLabel(EMPTY_VALUE, self)
            value.setObjectName(f"label_stat_{name.lower().replace('-', '_')}")
            value.setWordWrap(True)
            value.setMinimumWidth(1)
            self._fields[name] = value
            form.addRow(f"{name}:", value)

    # -- veri --------------------------------------------------------------

    def set_channel_data(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """Kanalın değerlerinden istatistikleri hesaplar ve gösterir.

        `region_seconds` verilirse (ROI, `F3-039`) başlığa aralık yazılır
        ve `values` yalnız o pencerenin örnekleri olmalıdır.
        """
        if region_seconds is None:
            self.setTitle(f"Statistics ({channel.name})")
        else:
            lo, hi = region_seconds
            self.setTitle(f"Statistics ({channel.name} · {lo:.3g}–{hi:.3g} s)")
        stats = compute_statistics(values)
        unit = f" {channel.unit}" if channel.unit else ""
        for name in STAT_FIELDS:
            self._fields[name].setText(f"{stats[name]:.4g}{unit}")

    def clear(self) -> None:
        self.setTitle(EMPTY_TITLE)
        for label in self._fields.values():
            label.setText(EMPTY_VALUE)

    def field_value(self, name: str) -> str:
        try:
            return self._fields[name].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz istatistik alani: {name}") from exc

"""İstatistik kartı — `F1-039`.

Mockup satır 3 sağ hücresi (`docs/ui/layout-map.md` §3): `Statistics (kanal)`
başlığı altında Mean, Std, RMS, Min, Max, Peak-Peak — altı satır, birimli.

Plan Bölüm 3.1: "Seçili kanal için temel istatistikler" MVP kapsamındadır; bu
panel gerçek hesap yapar, yer tutucu değildir.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QWidget

from sonar_analyzer.domain.channel import ChannelMetadata

EMPTY_VALUE = "—"
EMPTY_TITLE = "Statistics"

#: Mockup sirasi.
STAT_FIELDS: tuple[str, ...] = ("Mean", "Std", "RMS", "Min", "Max", "Peak-Peak")


def compute_statistics(values: NDArray[np.float64]) -> dict[str, float]:
    """Altı temel istatistiği hesaplar. Boş dizide `NaN` döner."""
    if values.size == 0:
        return {name: float("nan") for name in STAT_FIELDS}

    data = values.astype(np.float64)
    minimum = float(data.min())
    maximum = float(data.max())
    return {
        "Mean": float(data.mean()),
        "Std": float(data.std()),
        "RMS": float(np.sqrt(np.mean(np.square(data)))),
        "Min": minimum,
        "Max": maximum,
        "Peak-Peak": maximum - minimum,
    }


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

    def set_channel_data(self, channel: ChannelMetadata, values: NDArray[np.float64]) -> None:
        """Kanalın değerlerinden istatistikleri hesaplar ve gösterir."""
        self.setTitle(f"Statistics ({channel.name})")
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

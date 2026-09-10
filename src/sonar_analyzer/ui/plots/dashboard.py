"""Merkez dashboard grafik hücreleri — `F1-039`.

Mockup satır düzeni (`docs/ui/layout-map.md` §3, plan Bölüm 5.3):

    Satır 1  Zaman serisi
    Satır 2  Spektrogram
    Satır 3  Sol FFT · Sağ İstatistik kartı

Dört hücrenin dördü de gerçek veriyle çalışır: zaman serisi
(`PlotPanel`, `F1-031`), spektrogram (`SpectrogramPanel`, `F4-048`),
FFT (`SpectrumPanel`, `F4-042`) ve istatistik kartı (`StatisticsPanel`,
`F1-039`). Hiçbiri veri gelmeden sahte sonuç göstermez (plan Bölüm 3.1).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.spectrogram_panel import SpectrogramPanel
from sonar_analyzer.ui.plots.spectrum_panel import SpectrumPanel
from sonar_analyzer.ui.plots.statistics_panel import StatisticsPanel

SPECTROGRAM_TITLE = "Spectrogram"
FFT_TITLE = "FFT"


@dataclass(frozen=True)
class AnalysisSelection:
    """Analiz hücrelerinin **hepsinin** gösterdiği seçim — `F4-052`.

    Dört merkez bölgesinin tutarlılığı bu kayıtla denetlenir: aynı kanal,
    aynı örnek sayısı, aynı zaman aralığı.
    """

    channel_id: str
    channel_name: str
    sample_count: int
    region_seconds: tuple[float, float] | None = None


class DashboardPanel(QWidget):
    """Merkez alanın dört hücreli dashboard düzeni."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_dashboard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.rows = QSplitter(Qt.Orientation.Vertical, self)
        self.rows.setObjectName("splitter_dashboard_rows")

        self.time_series = PlotPanel(self.rows)
        self.rows.addWidget(self.time_series)

        # F4-048: spektrogram hücresi artık gerçek zaman-frekans haritasını çizer.
        self.spectrogram = SpectrogramPanel(self.rows)
        self.rows.addWidget(self.spectrogram)

        self.bottom = QSplitter(Qt.Orientation.Horizontal, self.rows)
        self.bottom.setObjectName("splitter_dashboard_bottom")

        # F4-042: FFT hücresi artık gerçek spektrumu çizer.
        self.fft = SpectrumPanel(self.bottom)
        self.bottom.addWidget(self.fft)

        self.statistics = StatisticsPanel(self.bottom)
        self.bottom.addWidget(self.statistics)

        self.rows.addWidget(self.bottom)
        # Mockup oranı: zaman serisi ~34%, spektrogram ~33%, alt satır ~33%.
        self.rows.setSizes([340, 330, 330])

        layout.addWidget(self.rows)

        self._selection: AnalysisSelection | None = None

    def row_titles(self) -> list[str]:
        """Kabul kontrolü için: üstten alta hücre başlıkları."""
        return [SPECTROGRAM_TITLE, FFT_TITLE]

    def spectrum(self) -> SpectrumPanel:
        """FFT hücresi — `F4-042`'den beri gerçek spektrum paneli."""
        return self.fft

    def set_channel_data(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """İstatistik, FFT ve spektrogram hücrelerini birlikte besler — `F4-048`.

        Üç hücre **tek çağrıda ve aynı veriyle** güncellenir; gösterilen
        seçim `selection()` ile dışarıya verilir (`F4-052`).
        """
        data = np.asarray(values, dtype=np.float64)
        self.statistics.set_channel_data(channel, data, region_seconds=region_seconds)
        self.fft.set_channel_data(channel, data, region_seconds=region_seconds)
        self.spectrogram.set_channel_data(channel, data, region_seconds=region_seconds)
        self._selection = AnalysisSelection(
            channel_id=channel.id,
            channel_name=channel.name,
            sample_count=int(data.size),
            region_seconds=region_seconds,
        )

    def clear_analysis(self) -> None:
        """İstatistik, FFT ve spektrogram hücrelerini boş duruma alır."""
        self.statistics.clear()
        self.fft.clear()
        self.spectrogram.clear()
        self._selection = None

    def selection(self) -> AnalysisSelection | None:
        """Analiz hücrelerinin gösterdiği seçim (yoksa `None`) — `F4-052`."""
        return self._selection

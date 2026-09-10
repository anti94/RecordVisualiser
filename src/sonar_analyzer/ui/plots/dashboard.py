"""Merkez dashboard grafik hücreleri — `F1-039`.

Mockup satır düzeni (`docs/ui/layout-map.md` §3, plan Bölüm 5.3):

    Satır 1  Zaman serisi
    Satır 2  Spektrogram
    Satır 3  Sol FFT · Sağ İstatistik kartı

Zaman serisi (`PlotPanel`, `F1-031`), istatistik kartı (`StatisticsPanel`,
`F1-039`) ve FFT hücresi (`SpectrumPanel`, `F4-042`) gerçek veriyle
çalışır. Spektrogram hücresi, hesaplama motoru gelene kadar (`F4-046`+)
açıkça pasif gösterilir — mockup'taki yeri hazırdır ama sahte sonuç
üretmez (plan Bölüm 3.1).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QSplitter, QVBoxLayout, QWidget

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.spectrum_panel import SpectrumPanel
from sonar_analyzer.ui.plots.statistics_panel import StatisticsPanel

SPECTROGRAM_TITLE = "Spectrogram"
FFT_TITLE = "FFT"


def _unavailable_cell(title: str, object_name: str) -> QGroupBox:
    """Henüz hesaplanmayan bir dashboard hücresinin gövdesi."""
    box = QGroupBox(title)
    box.setObjectName(object_name)
    layout = QVBoxLayout(box)
    note = QLabel(f"{title} — {NOT_YET_AVAILABLE}.", box)
    note.setObjectName(f"{object_name}_label")
    note.setAlignment(Qt.AlignmentFlag.AlignCenter)
    note.setWordWrap(True)
    note.setMinimumWidth(1)
    layout.addWidget(note)
    return box


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

        self.spectrogram = _unavailable_cell(SPECTROGRAM_TITLE, "cell_spectrogram")
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

    def row_titles(self) -> list[str]:
        """Kabul kontrolü için: üstten alta hücre başlıkları."""
        return [SPECTROGRAM_TITLE, FFT_TITLE]

    def spectrum(self) -> SpectrumPanel:
        """FFT hücresi — `F4-042`'den beri gerçek spektrum paneli."""
        return self.fft

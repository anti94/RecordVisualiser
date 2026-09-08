"""Ana pencere iskeleti — `F1-007`.

Yerleşimin tamamı `docs/ui/layout-map.md`'de tanımlıdır. Bu dosya şimdilik yalnız
pencerenin açılıp temiz kapandığını sağlayan en küçük gövdeyi içerir; dock'lar ve
grafik alanı sonraki işlerde eklenir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from sonar_analyzer import __version__

# docs/ui/layout-map.md §1: baslangic penceresi ~1520 x 840 mantiksal piksel.
DEFAULT_WINDOW_SIZE = (1520, 840)
WINDOW_TITLE = "SONAR Data Analyzer"


class MainWindow(QMainWindow):
    """Uygulamanın ana penceresi."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*DEFAULT_WINDOW_SIZE)
        self._build_placeholder()
        self.statusBar().showMessage("Ready")

    def _build_placeholder(self) -> None:
        """Dock'lar eklenene kadar duran geçici merkez alan."""
        central = QWidget(self)
        layout = QVBoxLayout(central)

        heading = QLabel(WINDOW_TITLE, central)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        detail = QLabel(
            f"surum {__version__}\n\nYerlesim henuz kurulmadi. Bkz. docs/ui/layout-map.md",
            central,
        )
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addStretch(1)

        self.setCentralWidget(central)

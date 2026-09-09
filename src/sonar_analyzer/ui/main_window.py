"""Ana pencere ve üç sütunlu düzen — `F1-007`, `F1-022`.

Yerleşim `docs/ui/layout-map.md` §1-2'ye göre kurulur:

    sol dock (~200 px) | merkez (esner) | sağ dock (~300 px)

Sütun genişlikleri sabit değil **öntanımlıdır**: kullanıcı ayırıcıyla
değiştirebilir ve düzen workspace ile kaydedilir. Pencere büyüdüğünde
yalnız merkez büyür; sağ sütundaki parametre alanları daralıp okunmaz
hâle gelmez.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer import __version__

# docs/ui/layout-map.md §1 ve §7
DEFAULT_WINDOW_SIZE = (1520, 840)
LEFT_COLUMN_WIDTH = 200
RIGHT_COLUMN_WIDTH = 300
LEFT_COLUMN_MIN_WIDTH = 160
RIGHT_COLUMN_MIN_WIDTH = 260

WINDOW_TITLE = "SONAR Data Analyzer"
LEFT_DOCK_TITLE = "Data Explorer"
RIGHT_DOCK_TITLE = "BIT / Analysis / Export"


def _placeholder(text: str, detail: str = "") -> QWidget:
    """İçeriği sonraki işlerde gelecek geçici panel gövdesi."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(8, 8, 8, 8)

    heading = QLabel(text, container)
    heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # Sarmalama olmadan etiketin sizeHint'i panelin asgari genisligini
    # belirler ve sutun mockup oranindan tasar.
    heading.setWordWrap(True)
    heading.setMinimumWidth(1)
    layout.addWidget(heading)

    if detail:
        note = QLabel(detail, container)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        note.setMinimumWidth(1)
        layout.addWidget(note)

    layout.addStretch(1)
    return container


class MainWindow(QMainWindow):
    """Uygulamanın ana penceresi: üç sütunlu mockup düzeni."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*DEFAULT_WINDOW_SIZE)

        self.left_dock = self._build_left_dock()
        self.right_dock = self._build_right_dock()
        self.center = self._build_center()

        self.setCentralWidget(self.center)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)
        self.apply_default_layout()

        self.statusBar().showMessage("Ready")

    # -- kurulum ---------------------------------------------------------

    def _build_left_dock(self) -> QDockWidget:
        dock = QDockWidget(LEFT_DOCK_TITLE, self)
        dock.setObjectName("dock_data_explorer")
        dock.setWidget(
            _placeholder(
                "Dosya ve Veri Yonetimi",
                "Open .bin File, dosya ozeti, Channels / Data Tree (docs/ui/layout-map.md bolge 1)",
            )
        )
        dock.setMinimumWidth(LEFT_COLUMN_MIN_WIDTH)
        return dock

    def _build_right_dock(self) -> QDockWidget:
        dock = QDockWidget(RIGHT_DOCK_TITLE, self)
        dock.setObjectName("dock_right_column")
        dock.setWidget(
            _placeholder(
                "BIT / Analysis Tools / Data Export",
                "Bolge 4, 5 ve 9 bu sutunda alt alta yer alir",
            )
        )
        dock.setMinimumWidth(RIGHT_COLUMN_MIN_WIDTH)
        return dock

    def _build_center(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("center_area")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        heading = QLabel(WINDOW_TITLE, container)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

        detail = QLabel(
            f"surum {__version__}\n\n"
            "Merkez alan: sekme cubugu, hizli araclar ve grafikler "
            "(bolge 2, 3, 6) sonraki islerde eklenecek.",
            container,
        )
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addStretch(1)
        return container

    # -- duzen -----------------------------------------------------------

    def apply_default_layout(self) -> None:
        """Sütun genişliklerini mockup öntanımlarına döndürür.

        `View -> Reset Layout` bunu çağırır (docs/ui/layout-map.md §7).
        """
        self.resizeDocks(
            [self.left_dock, self.right_dock],
            [LEFT_COLUMN_WIDTH, RIGHT_COLUMN_WIDTH],
            Qt.Orientation.Horizontal,
        )

    def column_widths(self) -> tuple[int, int, int]:
        """(sol, merkez, sağ) genişlikleri — görsel kabul kontrolü için."""
        return (
            self.left_dock.width(),
            self.center.width(),
            self.right_dock.width(),
        )

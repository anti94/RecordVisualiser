"""Ana pencere ve üç sütunlu düzen — `F1-007`, `F1-022`.

Yerleşim `docs/ui/layout-map.md` §1-2'ye göre kurulur:

    sol dock (~200 px) | merkez (esner) | sağ dock (~300 px)

Sütun genişlikleri sabit değil **öntanımlıdır**: kullanıcı ayırıcıyla
değiştirebilir ve düzen workspace ile kaydedilir. Pencere büyüdüğünde
yalnız merkez büyür; sağ sütundaki parametre alanları daralıp okunmaz
hâle gelmez.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QMenu,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer import __version__
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.ui.actions import (
    MENU_SPECS,
    TOOLBAR_ACTION_NAMES,
    build_action,
)
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock
from sonar_analyzer.ui.docks.playback import PlaybackDock
from sonar_analyzer.ui.docks.right_column import RightColumnDock

# docs/ui/layout-map.md §1 ve §7
DEFAULT_WINDOW_SIZE = (1520, 840)
LEFT_COLUMN_WIDTH = 200
RIGHT_COLUMN_WIDTH = 300
LEFT_COLUMN_MIN_WIDTH = 160
RIGHT_COLUMN_MIN_WIDTH = 260
BOTTOM_PANEL_HEIGHT = 152
BOTTOM_PANEL_MIN_HEIGHT = 96
PLAYBACK_HEIGHT = 56
PLAYBACK_MIN_HEIGHT = 44

WINDOW_TITLE = "SONAR Data Analyzer"
RIGHT_DOCK_TITLE = "BIT / Analysis / Export"


class MainWindow(QMainWindow):
    """Uygulamanın ana penceresi: üç sütunlu mockup düzeni."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*DEFAULT_WINDOW_SIZE)

        self._channels: tuple[ChannelMetadata, ...] = ()
        self.actions_by_name: dict[str, QAction] = {}
        # Menulere Python tarafinda referans tutulmazsa PySide nesneyi serbest
        # birakiyor ve sonraki erisimde "C++ object already deleted" hatasi
        # aliniyor.
        self.menus_by_name: dict[str, QMenu] = {}
        self._build_menus()
        self.toolbar = self._build_toolbar()

        # Paneller eylemlerden SONRA kurulur: sol panelin "Open .bin File"
        # dugmesi action_open eylemine baglaniyor.
        self.left_dock = self._build_left_dock()
        self.right_dock = self._build_right_dock()
        self.center = self._build_center()

        self.playback_dock = self._build_playback_dock()
        self.bottom_dock = self._build_bottom_dock()

        self.setCentralWidget(self.center)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)
        # Alt bolge merkezin ALTINDA durur; sol/sag sutunlar tepeden tabana
        # devam eder (docs/ui/layout-map.md §1). Sira: playback ustte, log altta.
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.playback_dock)
        self.splitDockWidget(self.playback_dock, self.bottom_dock, Qt.Orientation.Vertical)
        self.apply_default_layout()

        self._connect_layout_actions()
        self.left_dock.channel_activated.connect(self.show_channel_in_inspector)

        self.statusBar().showMessage("Ready")

    # -- eylemler --------------------------------------------------------

    def _build_menus(self) -> None:
        menubar = self.menuBar()
        for menu_spec in MENU_SPECS:
            menu = menubar.addMenu(menu_spec.title)
            menu.setObjectName(menu_spec.name)
            self.menus_by_name[menu_spec.name] = menu
            for action_spec in menu_spec.actions:
                action = build_action(self, action_spec)
                self.actions_by_name[action_spec.name] = action
                menu.addAction(action)

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Quick Tools", self)
        toolbar.setObjectName("toolbar_quick_tools")
        for name in TOOLBAR_ACTION_NAMES:
            action = self.actions_by_name.get(name)
            if action is not None:
                toolbar.addAction(action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        return toolbar

    def _connect_layout_actions(self) -> None:
        """Görünüm eylemlerini panellere bağlar."""
        self.action("action_exit").triggered.connect(self.close)
        self.action("action_reset_layout").triggered.connect(self.apply_default_layout)

        pairs = (
            ("action_toggle_data_explorer", self.left_dock),
            ("action_toggle_right_column", self.right_dock),
        )
        for name, dock in pairs:
            action = self.action(name)
            action.toggled.connect(dock.setVisible)
            dock.visibilityChanged.connect(action.setChecked)

    def menu(self, name: str) -> QMenu:
        """Adına göre menüyü döndürür; bulunamazsa hata verir."""
        try:
            return self.menus_by_name[name]
        except KeyError as exc:
            raise KeyError(f"Tanimsiz menu: {name}") from exc

    def show_channel_in_inspector(self, channel_id: str) -> None:
        """Seçilen kanalın ayrıntısını Inspector sekmesinde öne getirir."""
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None:
            return
        self.right_dock.show_channel(channel)

    def action(self, name: str) -> QAction:
        """Adına göre eylemi döndürür; bulunamazsa hata verir."""
        try:
            return self.actions_by_name[name]
        except KeyError as exc:
            raise KeyError(f"Tanimsiz eylem: {name}") from exc

    # -- kurulum ---------------------------------------------------------

    def _build_left_dock(self) -> DataExplorerDock:
        dock = DataExplorerDock(self)
        dock.setMinimumWidth(LEFT_COLUMN_MIN_WIDTH)
        dock.open_requested.connect(self.action("action_open").trigger)
        return dock

    def _build_right_dock(self) -> RightColumnDock:
        dock = RightColumnDock(self)
        dock.setMinimumWidth(RIGHT_COLUMN_MIN_WIDTH)
        return dock

    def _build_playback_dock(self) -> PlaybackDock:
        dock = PlaybackDock(self)
        dock.setMinimumHeight(PLAYBACK_MIN_HEIGHT)
        return dock

    def _build_bottom_dock(self) -> BottomPanelDock:
        dock = BottomPanelDock(self)
        dock.setMinimumHeight(BOTTOM_PANEL_MIN_HEIGHT)
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

    def set_recording(
        self,
        metadata: RecordingMetadata,
        channels: Sequence[ChannelMetadata],
    ) -> None:
        """Açılan kaydı panellere dağıtır."""
        self._channels = tuple(channels)
        self.left_dock.set_recording(metadata, channels)
        self.right_dock.close_inspector()
        self.playback_dock.set_recording_range(metadata.time_range)
        self.bottom_dock.append_log(f"Kayit acildi: {metadata.source_path}")
        self.bottom_dock.append_log(f"{len(channels)} kanal bulundu.")
        self.action("action_close").setEnabled(True)
        self.action("action_export").setEnabled(True)

    def apply_default_layout(self) -> None:
        """Sütun genişliklerini mockup öntanımlarına döndürür.

        `View -> Reset Layout` bunu çağırır (docs/ui/layout-map.md §7).
        """
        self.resizeDocks(
            [self.left_dock, self.right_dock],
            [LEFT_COLUMN_WIDTH, RIGHT_COLUMN_WIDTH],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks([self.bottom_dock], [BOTTOM_PANEL_HEIGHT], Qt.Orientation.Vertical)

    def column_widths(self) -> tuple[int, int, int]:
        """(sol, merkez, sağ) genişlikleri — görsel kabul kontrolü için."""
        return (
            self.left_dock.width(),
            self.center.width(),
            self.right_dock.width(),
        )

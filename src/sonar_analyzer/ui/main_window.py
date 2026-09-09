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
    QMainWindow,
    QMenu,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.repository.mock_repository import SIMULATION_LABEL, MockRecordingRepository
from sonar_analyzer.repository.protocol import RecordingRepository
from sonar_analyzer.ui.actions import (
    MENU_SPECS,
    TOOLBAR_ACTION_NAMES,
    build_action,
)
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock
from sonar_analyzer.ui.docks.playback import PlaybackDock
from sonar_analyzer.ui.docks.right_column import RightColumnDock
from sonar_analyzer.ui.empty_state import EmptyStatePanel
from sonar_analyzer.ui.plot_tool_bar import PlotToolBar
from sonar_analyzer.ui.plots.dashboard import DashboardPanel
from sonar_analyzer.ui.status_bar import AppStatusBar
from sonar_analyzer.ui.theme import apply_theme
from sonar_analyzer.ui.view_tab_bar import ViewTabBar

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
        # Tema pencere geneline uygulanir; tek renk bile widget icine yazilmaz.
        apply_theme(self)

        self._channels: tuple[ChannelMetadata, ...] = ()
        self._repository: RecordingRepository | None = None
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
        self.left_dock.channel_activated.connect(self.open_channel)
        self.right_dock.bit_status.analysis_requested.connect(self.refresh_bit_analysis)
        self.action("action_load_simulation").triggered.connect(self.load_simulation)

        self.status = AppStatusBar(self)
        self.setStatusBar(self.status)
        self.status.update_memory()

        self.playback_dock.position_changed.connect(self.status.set_cursor_time)

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

    def open_channel(self, channel_id: str) -> None:
        """Seçilen kanalı çizer ve ayrıntısını gösterir."""
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None or self._repository is None:
            return

        chunk = self._repository.query(channel_id, self._repository.metadata().time_range)
        self.plot_panel.set_channel(channel, chunk)
        self.dashboard.statistics.set_channel_data(channel, chunk.values)
        self.plot_tool_bar.set_current_channel(channel_id)
        self.show_plot()
        self.right_dock.show_channel(channel)
        self.bottom_dock.append_log(f"{channel.display_label} cizildi ({len(chunk)} ornek).")

    def refresh_bit_analysis(self) -> None:
        """Kayıtlı BIT verisini yeniden özetler; donanıma komut göndermez."""
        if self._repository is None:
            return
        span = self._repository.metadata().time_range
        self.right_dock.bit_status.set_results(self._repository.bit_results(span))
        self.bottom_dock.append_log("BIT ozeti yenilendi.")

    def load_simulation(self) -> None:
        """Sahte kaydı açar; veri kaynağı `Simülasyon` olarak görünür."""
        repository = MockRecordingRepository()
        self.set_repository(repository)

    def set_repository(self, repository: RecordingRepository) -> None:
        """Bir veri kaynağını açar ve panellere dağıtır."""
        self._repository = repository
        metadata = repository.metadata()
        channels = repository.channels()
        self.set_recording(metadata, channels)

        span = metadata.time_range
        self.bottom_dock.set_events(repository.events(span))
        self.right_dock.bit_status.set_results(repository.bit_results(span))

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
        """Merkez alan: kayıt yokken yönlendirme, varken grafik."""
        container = QFrame(self)
        container.setObjectName("center_area")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.view_tabs = ViewTabBar(container)
        layout.addWidget(self.view_tabs)

        self.plot_tool_bar = PlotToolBar(container)
        self.plot_tool_bar.channel_selected.connect(self.open_channel)
        layout.addWidget(self.plot_tool_bar)

        self.empty_state = EmptyStatePanel(container)
        self.empty_state.open_requested.connect(self.action("action_open").trigger)
        self.empty_state.simulation_requested.connect(self.action("action_load_simulation").trigger)

        self.dashboard = DashboardPanel(container)
        self.plot_panel = self.dashboard.time_series

        self.center_stack = QStackedWidget(container)
        self.center_stack.setObjectName("center_stack")
        self.center_stack.addWidget(self.empty_state)
        self.center_stack.addWidget(self.dashboard)
        self.center_stack.setCurrentWidget(self.empty_state)

        layout.addWidget(self.center_stack, 1)
        return container

    def show_empty_state(self) -> None:
        """Merkez alanı yönlendirme ekranına döndürür."""
        self.center_stack.setCurrentWidget(self.empty_state)

    def show_plot(self) -> None:
        self.center_stack.setCurrentWidget(self.dashboard)

    @property
    def center_shows_plot(self) -> bool:
        return self.center_stack.currentWidget() is self.dashboard

    # -- duzen -----------------------------------------------------------

    def set_recording(
        self,
        metadata: RecordingMetadata,
        channels: Sequence[ChannelMetadata],
    ) -> None:
        """Açılan kaydı panellere dağıtır."""
        self._channels = tuple(channels)
        self.left_dock.set_recording(metadata, channels)
        self.plot_tool_bar.set_channels(list(channels))
        self.right_dock.close_inspector()
        self.right_dock.bit_status.clear()
        self.plot_panel.clear()
        self.dashboard.statistics.clear()
        self.show_empty_state()
        self.playback_dock.set_recording_range(metadata.time_range)
        self.status.set_field("file", metadata.source_path)
        self.status.set_field(
            "connection",
            SIMULATION_LABEL if metadata.source_path == SIMULATION_LABEL else "Dosya",
        )
        self.status.set_status("Ready")
        self.status.update_memory()
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

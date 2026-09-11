"""Ana pencere ve üç sütunlu düzen — `F1-007`, `F1-022`.

Yerleşim `docs/ui/layout-map.md` §1-2'ye göre kurulur:

    sol dock (~200 px) | merkez (esner) | sağ dock (~300 px)

Sütun genişlikleri sabit değil **öntanımlıdır**: kullanıcı ayırıcıyla
değiştirebilir ve düzen workspace ile kaydedilir. Pencere büyüdüğünde
yalnız merkez büyür; sağ sütundaki parametre alanları daralıp okunmaz
hâle gelmez.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.application import favorite_groups, recent_files
from sonar_analyzer.application.export_controller import (
    KIND_FILE_FILTER,
    DataVariant,
    ExportKind,
    kind_for_format,
    resolve_target,
)
from sonar_analyzer.application.file_loader import (
    FileLoadResult,
    FileLoadService,
    LoaderCallable,
)
from sonar_analyzer.application.load_errors import describe_load_error
from sonar_analyzer.application.point_budget import points_for_width
from sonar_analyzer.application.scrub_debounce import ScrubDebouncer
from sonar_analyzer.application.view_history import ViewCommand, ViewHistory
from sonar_analyzer.domain.annotation import Annotation, AnnotationSet, new_annotation_id
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.export.csv_export import CsvExportResult, write_channel_csv
from sonar_analyzer.export.image_export import export_widget_png
from sonar_analyzer.logging.performance import measure
from sonar_analyzer.repository.derived_repository import (
    DerivedChannelError,
    DerivedChannelRepository,
)
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.repository.mock_repository import SIMULATION_LABEL, MockRecordingRepository
from sonar_analyzer.repository.protocol import RecordingRepository
from sonar_analyzer.settings.store import AppSettings, SettingsWriter, save_settings
from sonar_analyzer.ui import error_dialogs
from sonar_analyzer.ui.actions import (
    MENU_SPECS,
    TOOLBAR_ACTION_NAMES,
    build_action,
)
from sonar_analyzer.ui.cards.analysis_tools import FilterTabError
from sonar_analyzer.ui.cards.data_export import DataExportCard
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock, selected_channel_ids
from sonar_analyzer.ui.docks.event_table_model import related_channels
from sonar_analyzer.ui.docks.playback import PlaybackDock
from sonar_analyzer.ui.docks.right_column import RightColumnDock
from sonar_analyzer.ui.dsp_runner import DspRunner
from sonar_analyzer.ui.empty_state import EmptyStatePanel
from sonar_analyzer.ui.error_dialogs import LoadErrorNotifier
from sonar_analyzer.ui.export_runner import ExportRunner
from sonar_analyzer.ui.file_open import FileOpenController
from sonar_analyzer.ui.plot_tool_bar import PlotToolBar
from sonar_analyzer.ui.plots.dashboard import DashboardPanel
from sonar_analyzer.ui.plots.spectrum_panel import SpectrumPanel
from sonar_analyzer.ui.plots.transmission_panel import TransmissionPanel
from sonar_analyzer.ui.plots.waterfall_panel import WaterfallPanel
from sonar_analyzer.ui.shortcuts import install_shortcuts
from sonar_analyzer.ui.status_bar import CANCELLED_TEXT, READY_TEXT, AppStatusBar
from sonar_analyzer.ui.status_icons import severity_style
from sonar_analyzer.ui.theme import apply_theme
from sonar_analyzer.ui.view_tab_bar import ViewTabBar
from sonar_analyzer.workspace.model import (
    EventFilterState,
    PanelState,
    ViewState,
    WorkspaceError,
    WorkspaceModel,
)
from sonar_analyzer.workspace.resolve import resolve_sources
from sonar_analyzer.workspace.store import load_workspace, save_workspace

logger = logging.getLogger("sonar_analyzer")

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

    def __init__(
        self,
        *,
        loader: LoaderCallable | None = None,
        error_notifier: LoadErrorNotifier | None = None,
        settings: AppSettings | None = None,
        settings_writer: SettingsWriter | None = None,
    ) -> None:
        """`loader`: dosya açma çağrısını değiştirir (testler ve ileride
        farklı kaynak türleri için); verilmezse gerçek `.bin` okuyucu.
        `error_notifier`: yükleme hatasının kullanıcıya gösterimi;
        verilmezse Qt uyarı kutusu. `settings`: açılışta okunan kalıcı
        ayarlar (`F3-008` son dosyalar); `settings_writer`: kaydetme
        çağrısı — verilmezse gerçek ayar dosyasına yazılır."""
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*DEFAULT_WINDOW_SIZE)
        # Tema pencere geneline uygulanir; tek renk bile widget icine yazilmaz.
        apply_theme(self)

        self._channels: tuple[ChannelMetadata, ...] = ()
        self._repository: RecordingRepository | None = None
        #: `F4-074` kullanıcı işaretleri; `F4-076` çalışma alanına yazar.
        self._annotations = AnnotationSet()
        self._dsp_projection: tuple[int, NDArray[np.int64]] | None = None
        self._processed_values: NDArray[np.float64] | None = None
        #: `F3-041` görünüm ayarları (renk, eksen) undo/redo geçmişi.
        self._view_history = ViewHistory()
        #: `F3-065` dışa aktarma diyalog seam'leri (testler enjekte eder).
        self.export_save_dialog: Callable[[str, str], str] | None = None
        self.export_confirm_overwrite: Callable[[Path], bool] | None = None
        #: `F3-066` süren CSV dışa aktarma worker'ı (yoksa `None`).
        self._export_runner: ExportRunner | None = None
        #: `F3-070` son workspace geri yüklemesinde bulunamayan kaynak yolları.
        self.last_missing_sources: list[str] = []
        #: `F3-060` zaman bölgesi sürüklemesinde sorguları coalesce eder.
        self._scrub_debouncer: ScrubDebouncer[tuple[int, int]] = ScrubDebouncer(0.12)
        self._scrub_timer = QTimer(self)
        self._scrub_timer.setInterval(25)
        self._scrub_timer.timeout.connect(self._flush_scrub_region)
        self._plot_refresh_timer = QTimer(self)
        self._plot_refresh_timer.setSingleShot(True)
        self._plot_refresh_timer.setInterval(80)
        self._plot_refresh_timer.timeout.connect(self.refresh_plot_viewport)
        self._last_plot_request: tuple[float, float, int, tuple[str, ...]] | None = None
        self._analysis_data: (
            tuple[ChannelMetadata, NDArray[np.float64], tuple[float, float] | None] | None
        ) = None
        self._analysis_revision = 0
        self._analysis_rendered: dict[QWidget, int] = {}
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(50)
        self._analysis_timer.timeout.connect(self._flush_analysis_views)
        #: `F3-001` seçiminin sonucu; worker bu yolları açar.
        self.pending_load_paths: tuple[Path, ...] = ()
        #: Worker'dan dönen sonuçlar; ekrana bağlanması `F3-005`'in işi.
        self.loaded_results: tuple[FileLoadResult, ...] = ()
        self.failed_results: tuple[FileLoadResult, ...] = ()
        self.active_load_request_id = 0
        #: Ekrana uygulanmış, MainWindow'un sahibi olduğu snapshot'lar.
        self._owned_repositories: tuple[FileRecordingRepository, ...] = ()
        # None saklanir; ontanimli bildirim CAGRI aninda cozulur, boylece
        # modulu yamalayan test agi (tests/conftest.py) pencere kurulduktan
        # sonra da etkili olur (ayni tuzak: F3-001 dosya diyalogu).
        self._error_notifier: LoadErrorNotifier | None = error_notifier
        self._settings = settings if settings is not None else AppSettings()
        self._settings_writer: SettingsWriter = settings_writer or save_settings
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
        self.left_dock.channels_add_requested.connect(self._on_channels_add_requested)
        self.left_dock.channel_inspect_requested.connect(self.show_channel_in_inspector)
        self.left_dock.channel_path_copied.connect(self._on_channel_path_copied)
        self.right_dock.bit_status.analysis_requested.connect(self.refresh_bit_analysis)
        self.right_dock.inspector.axis_range_requested.connect(self._on_axis_range_requested)
        self.right_dock.data_export.export_requested.connect(self._on_export_requested)
        # F4-008: Analysis Tools -> işlem zincirini seçili kanala uygula.
        self._dsp_runner = DspRunner(self)
        self._dsp_runner.result_ready.connect(self._on_dsp_result)
        self._dsp_runner.failed.connect(self._on_dsp_failed)
        self.right_dock.analysis_tools.apply_requested.connect(self._on_apply_processing)
        self.right_dock.analysis_tools.show_filtered_toggled.connect(
            self.plot_panel.set_processed_overlay_visible
        )
        self.right_dock.analysis_tools.formula_editor.definition_requested.connect(
            self._on_derived_channel_requested
        )
        self.bottom_dock.bookmarks.add_requested.connect(self._on_bookmark_add)
        self.bottom_dock.bookmarks.edit_requested.connect(self._on_bookmark_edit)
        self.bottom_dock.bookmarks.remove_requested.connect(self._on_bookmark_remove)
        self.bottom_dock.bookmarks.selected.connect(self._on_bookmark_selected)
        self.bottom_dock.event_selected.connect(self._on_event_selected)
        self.bottom_dock.event_activated.connect(self._on_event_activated)
        self.action("action_load_simulation").triggered.connect(self.load_simulation)

        # Dosya secici yalniz talep uretir; okuma worker thread'inde yapilir.
        self.file_open = FileOpenController(self)
        self.file_open.set_last_directory(
            self._settings.last_directory
            or recent_files.default_directory(self._settings.recent_files)
        )
        self.file_loader = FileLoadService(self, loader=loader)
        self.action("action_open").triggered.connect(self.request_open_files)
        self.file_open.load_requested.connect(self._on_load_requested)
        self.file_loader.file_loaded.connect(self._on_file_loaded)
        self.file_loader.request_finished.connect(self._on_load_finished)
        self.file_loader.progress.connect(self._on_load_progress)

        self.status = AppStatusBar(self)
        self.setStatusBar(self.status)
        self.status.update_memory()
        self.status.cancel_requested.connect(self.cancel_active_load)

        self.playback_dock.position_changed.connect(self.status.set_cursor_time)
        self.playback_dock.timeline.viewport_changed.connect(self._on_timeline_viewport_changed)
        # F3-059: önceki/sonraki olaya atlayınca grafiği o zamana götür ve
        # olayı Inspector'da göster.
        self.playback_dock.event_navigated.connect(self._on_event_activated)
        self.playback_dock.event_navigated.connect(self._on_event_selected)

        # F3-072: Bölüm 16 klavye kısayolları.
        #: Testler enjekte eder; `str | ""` döndürür.
        self.workspace_save_dialog: Callable[[], str] | None = None
        self.shortcuts = install_shortcuts(self)
        # F3-073: yalnız klavyeyle tamamlanabilen ana akış için odak sırası.
        self._configure_keyboard_navigation()

    def _configure_keyboard_navigation(self) -> None:
        """Ana akışın Tab sırasını ve erişilebilir adları düzenler — `F3-073`.

        Akış: kayıt aç -> kanal ara -> kanal ağacı -> grafik -> oynatma ->
        olay filtresi. Tab bu sırayı izler; her durak ekran okuyucuya
        adıyla tanıtılır.
        """
        # Grafik Tab ile durulabilir olmalı: hem odak sırasında görünür,
        # hem de X/Y/B/C/R kısayolları için güvenilir odak taşır.
        self.plot_panel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.plot_panel.setAccessibleName("Zaman serisi grafiği")
        self.plot_panel.setAccessibleDescription(
            "X/Y/B: zoom modu. Home: görünümü sıfırla. C: cursor. R: bölge. "
            "F4 / Shift+F4: sonraki / önceki olay."
        )
        play_button = self.playback_dock.buttons["button_play"]
        play_button.setAccessibleName("Oynat / duraklat")
        self.bottom_dock.events.setAccessibleName("Olaylar tablosu")

        chain = [
            self.left_dock.open_button,
            self.left_dock.search,
            self.left_dock.tree,
            self.plot_panel,
            play_button,
            self.playback_dock.slider,
            self.bottom_dock.event_source_filter,
            self.bottom_dock.events,
        ]
        for earlier, later in zip(chain, chain[1:]):
            self.setTabOrder(earlier, later)

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
        self.action("action_close").triggered.connect(self.close_active_recording)
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

    def _on_channel_path_copied(self, path: str) -> None:
        """Sağ tık > Copy Path sonrası kullanıcıya geri bildirim — `F3-018`."""
        self.bottom_dock.append_log(f"Yol panoya kopyalandi: {path}")

    def _on_event_selected(self, event: object) -> None:
        """Events tablosunda seçilen olayın ayrıntısını Inspector'a bağlar — `F3-044`.

        Kaynak, kod ve olayla ilişkili kanallar gösterilir. Seçim
        kalkarsa (`event is None`) bir şey yapılmaz.
        """
        if not isinstance(event, Event):
            return
        self.right_dock.show_event(event, related_channels(event, self._channels))

    def _on_event_activated(self, event: object) -> None:
        """Olay satırına çift tıklama grafiği o zamana götürür — `F3-046`."""
        if isinstance(event, Event):
            self.go_to_time(event.timestamp_ns)

    # -- kullanici isaretleri (F4-075) -------------------------------------

    @property
    def annotations(self) -> AnnotationSet:
        """Açık kaydın kullanıcı işaretleri — `F4-074`."""
        return self._annotations

    def set_annotations(self, annotations: AnnotationSet) -> None:
        """İşaret kümesini değiştirir, listeyi ve timeline'ı tazeler."""
        self._annotations = annotations
        start_ns = 0
        if self._repository is not None:
            start_ns = self._repository.metadata().time_range.start_ns
        self.bottom_dock.bookmarks.set_annotations(annotations, start_ns)
        self.plot_panel.set_bookmarks(
            [(item.start_ns, item.end_ns, item.label) for item in annotations]
        )

    def bookmark_target(self) -> tuple[int, int | None]:
        """Yeni işaretin kapsayacağı zaman: seçili aralık varsa o, yoksa imleç.

        Grafikte bir zaman bölgesi seçiliyse işaret **aralık** olur;
        seçim yoksa oynatma imlecinin bulunduğu an **nokta** olur.
        """
        span = self.plot_panel.time_region_range()
        if span is not None and span.end_ns > span.start_ns:
            return span.start_ns, span.end_ns
        return self.playback_dock.current_time_ns(), None

    def _on_bookmark_add(self, label: object, text: object) -> None:
        if not isinstance(label, str) or not isinstance(text, str) or not label.strip():
            return
        start_ns, end_ns = self.bookmark_target()
        annotation = Annotation(
            id=new_annotation_id(),
            label=label.strip(),
            start_ns=start_ns,
            end_ns=end_ns,
            text=text,
        )
        self.set_annotations(self._annotations.added(annotation))
        self.bottom_dock.bookmarks.select(annotation.id)
        kind = "aralık" if end_ns is not None else "an"
        self.bottom_dock.append_log(f"İşaret eklendi ({kind}): {annotation.label}")

    def _on_bookmark_edit(self, annotation_id: object, label: object, text: object) -> None:
        if not (
            isinstance(annotation_id, str) and isinstance(label, str) and isinstance(text, str)
        ):
            return
        existing = self._annotations.get(annotation_id)
        if existing is None or not label.strip():
            return
        updated = existing.renamed(label.strip()).with_text(text)
        self.set_annotations(self._annotations.added(updated))
        self.bottom_dock.bookmarks.select(annotation_id)
        self.bottom_dock.append_log(f"İşaret güncellendi: {updated.label}")

    def _on_bookmark_remove(self, annotation_id: object) -> None:
        if not isinstance(annotation_id, str):
            return
        existing = self._annotations.get(annotation_id)
        if existing is None:
            return
        self.set_annotations(self._annotations.removed(annotation_id))
        self.bottom_dock.append_log(f"İşaret silindi: {existing.label}")

    def _on_bookmark_selected(self, annotation_id: object) -> None:
        """Seçilen işaretin zamanına gider — `F4-075` kabul kriteri."""
        if not isinstance(annotation_id, str) or not annotation_id:
            return
        annotation = self._annotations.get(annotation_id)
        if annotation is None:
            return
        self.playback_dock.goto_time_ns(annotation.start_ns)
        self.go_to_time(annotation.start_ns)

    def _set_event_markers_visible(self, visible: bool) -> None:
        """`F3-050` — olay işaretlerinin görünürlüğü (veri değişmez)."""
        self.plot_panel.set_event_markers_visible(visible)

    def _set_tx_regions_visible(self, visible: bool) -> None:
        """`F3-050` — TX bantlarının görünürlüğü (veri değişmez)."""
        self.plot_panel.set_tx_regions_visible(visible)

    def _sync_timeline_viewport(self, x_min_s: float, x_max_s: float) -> None:
        """`F3-055` — grafik X aralığını overview timeline viewport'una yansıtır."""
        try:
            start_ns = self.plot_panel.timestamp_ns_for_x(x_min_s)
            end_ns = self.plot_panel.timestamp_ns_for_x(x_max_s)
        except RuntimeError:
            return
        self.playback_dock.timeline.set_viewport_ns(start_ns, end_ns)
        self._plot_refresh_timer.start()

    def _on_timeline_viewport_changed(self, start_ns: object, end_ns: object) -> None:
        """`F3-055` — timeline viewport'u sürüklenince grafik(ler) o aralığa gider."""
        if not (isinstance(start_ns, int) and isinstance(end_ns, int)):
            return
        try:
            x0 = self.plot_panel.x_for_timestamp_ns(start_ns)
            x1 = self.plot_panel.x_for_timestamp_ns(end_ns)
        except RuntimeError:
            return
        self.plot_panel.set_x_range(x0, x1)

    def go_to_time(self, timestamp_ns: int) -> bool:
        """Grafiğin görünür X penceresini `timestamp_ns`'e **ortalar** — `F3-046`.

        Görünür süre korunur; yalnız merkez kayar. `set_x_range` üzerinden
        gittiği için X-senkronlu bağlı grafikler de aynı zamana gider
        (`F3-032`). Grafikte seri (zaman ankoru) yoksa `False` döner.
        """
        try:
            centre = self.plot_panel.x_for_timestamp_ns(timestamp_ns)
        except RuntimeError:
            return False
        x_min, x_max = self.plot_panel.visible_x_range()
        half = (x_max - x_min) / 2.0
        self.plot_panel.set_x_range(centre - half, centre + half)
        return True

    def export_plot_png(self, path: str | Path, *, scale: float = 1.0) -> Path:
        """Seçili (merkez) grafiği bir PNG dosyasına yazar — `F3-062`.

        Çıktı grafiğin o anki çizimidir: başlık, seriler ve eksen birimleri
        neyse dosyada odur. Grafikte çizili kanal yoksa `ValueError` verir;
        boş bir görüntü üretmez.
        """
        if not self.plot_panel.plotted_channel_ids():
            raise ValueError("Disa aktarilacak grafik yok: once bir kanal cizin")
        dest = export_widget_png(self.plot_panel, path, scale=scale)
        self.bottom_dock.append_log(f"Grafik PNG olarak yazildi: {dest}")
        return dest

    def export_plot_svg(self, path: str | Path) -> Path:
        """Seçili (merkez) grafiği **vektörel** SVG dosyasına yazar — `F3-063`.

        Seriler ve eksenler vektör olarak çıkar; çıktı kayıpsız ölçeklenir.
        Grafikte çizili kanal yoksa `ValueError` verir.
        """
        if not self.plot_panel.plotted_channel_ids():
            raise ValueError("Disa aktarilacak grafik yok: once bir kanal cizin")
        dest = self.plot_panel.export_svg(path)
        self.bottom_dock.append_log(f"Grafik SVG olarak yazildi: {dest}")
        return dest

    def export_channel_csv(
        self,
        path: str | Path,
        *,
        channel_id: str | None = None,
        selected_range_only: bool = False,
        include_metadata: bool = True,
        raw: bool = False,
    ) -> CsvExportResult:
        """Seçili kanal (ve isteğe bağlı seçili aralığı) CSV olarak yazar — `F3-064`.

        `channel_id` verilmezse grafiğin birincil kanalı kullanılır.
        `selected_range_only` ise ve grafikte bir zaman bölgesi seçiliyse
        yalnız o aralık; aksi hâlde kaydın tamamı yazılır. Metadata
        yorum satırları `include_metadata` ile açılıp kapanır. `raw` ise
        değerler kalibrasyonsuz (ham) yazılır — `F3-065`.

        Açık kayıt ya da hedef kanal yoksa `ValueError` verir.
        """
        job = self._build_csv_export_job(
            path,
            channel_id=channel_id,
            selected_range_only=selected_range_only,
            include_metadata=include_metadata,
            raw=raw,
        )
        result = job(lambda: False, None)
        self.bottom_dock.append_log(
            f"Kanal CSV olarak yazildi: {result.path} ({result.row_count} satir)"
        )
        return result

    def _build_csv_export_job(
        self,
        path: str | Path,
        *,
        channel_id: str | None,
        selected_range_only: bool,
        include_metadata: bool,
        raw: bool,
    ) -> Callable[[Callable[[], bool], Callable[[int, int], None] | None], CsvExportResult]:
        """Sorgu + doğrulamayı şimdi yapar; asıl yazma çağrıya bırakılır — `F3-066`.

        Döndürülen `job(should_cancel, on_progress)` hem senkron (GUI
        thread) hem de `ExportRunner` içinde (worker thread) çağrılabilir.
        """
        if self._repository is None:
            raise ValueError("Acik kayit yok: CSV disa aktarilamaz")
        primary = self.plot_panel.channel
        target_id = channel_id or (primary.id if primary is not None else None)
        if target_id is None:
            raise ValueError("Disa aktarilacak kanal yok: once bir kanal secin")
        channel = next((c for c in self._channels if c.id == target_id), None)
        if channel is None:
            raise ValueError(f"Bilinmeyen kanal: {target_id}")

        metadata = self._repository.metadata()
        exported_range = metadata.time_range
        if selected_range_only:
            region = self.plot_panel.time_region_range()
            if region is not None:
                exported_range = region

        chunk = self._repository.query(target_id, exported_range)

        def _job(
            should_cancel: Callable[[], bool],
            on_progress: Callable[[int, int], None] | None,
        ) -> CsvExportResult:
            return write_channel_csv(
                chunk,
                channel,
                path,
                recording=metadata,
                exported_range=exported_range,
                include_metadata=include_metadata,
                raw=raw,
                should_cancel=should_cancel,
                on_progress=on_progress,
            )

        return _job

    def start_channel_csv_export(
        self,
        path: str | Path,
        *,
        channel_id: str | None = None,
        selected_range_only: bool = False,
        include_metadata: bool = True,
        raw: bool = False,
    ) -> ExportRunner:
        """CSV dışa aktarımını worker thread'de başlatır — `F3-066`.

        GUI donmaz; ilerleme durum çubuğuna gider, `cancel_export()` işi
        durdurur ve yarım dosya bırakılmaz. Sorgu/doğrulama hatası
        (`ValueError`) hemen fırlatılır; yazma hataları `failed`
        sinyaliyle bildirilir.
        """
        job = self._build_csv_export_job(
            path,
            channel_id=channel_id,
            selected_range_only=selected_range_only,
            include_metadata=include_metadata,
            raw=raw,
        )
        runner = ExportRunner(job)
        self._export_runner = runner
        self.status.start_load_progress(1)
        self.right_dock.data_export.set_running(True)
        runner.progress.connect(self._on_export_progress)
        runner.export_finished.connect(self._on_export_finished)
        runner.cancelled.connect(self._on_export_cancelled)
        runner.failed.connect(self._on_export_failed)
        runner.start()
        return runner

    def cancel_export(self) -> None:
        """Süren CSV dışa aktarımını iptal eder — `F3-066`."""
        if self._export_runner is not None:
            self._export_runner.cancel()

    def _on_export_progress(self, written: int, total: int) -> None:
        self.status.set_load_progress(written, max(1, total))

    def _finish_export_ui(self) -> None:
        self.status.finish_load_progress()
        self.right_dock.data_export.set_running(False)
        self._export_runner = None

    def _on_export_finished(self, result: object) -> None:
        if isinstance(result, CsvExportResult):
            self.bottom_dock.append_log(
                f"Kanal CSV olarak yazildi: {result.path} ({result.row_count} satir)"
            )
        self._finish_export_ui()

    def _on_export_cancelled(self) -> None:
        self.bottom_dock.append_log("Disa aktarma iptal edildi: dosya yazilmadi.")
        self._finish_export_ui()

    def _on_export_failed(self, message: str) -> None:
        self.bottom_dock.append_log(f"Disa aktarma basarisiz: {message}")
        self._finish_export_ui()

    # -- dışa aktarma akışı (F3-065) ---------------------------------

    def _default_export_save_dialog(self, caption: str, name_filter: str) -> str:
        start_dir = self._settings.last_directory or str(Path.home())
        path, _selected = QFileDialog.getSaveFileName(self, caption, start_dir, name_filter)
        return path

    def _default_confirm_overwrite(self, path: Path) -> bool:
        answer = QMessageBox.question(
            self,
            "Üzerine yaz",
            f"{path.name} zaten var. Üzerine yazılsın mı?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _on_export_requested(self) -> None:
        """Data Export kartındaki `Export Data`'yı işler — `F3-065`, `F3-066`.

        Biçim ve ham/işlenmiş seçimi karttan okunur, hedef dosya adı
        sorulur, dosya varsa üzerine yazma onayı istenir. Onay yoksa
        **hiçbir şey yazılmaz** (var olan dosya dokunulmaz). Zaten bir
        CSV dışa aktarımı sürüyorsa buton iptal düğmesi gibi davranır.
        """
        if self._export_runner is not None:
            self.cancel_export()
            return

        card = self.right_dock.data_export
        try:
            kind = kind_for_format(card.selected_format())
        except KeyError:
            self.bottom_dock.append_log(
                f"{card.selected_format()} disa aktarimi henuz desteklenmiyor."
            )
            return

        dialog = self.export_save_dialog or self._default_export_save_dialog
        chosen = dialog(f"{kind.value.upper()} olarak disa aktar", KIND_FILE_FILTER[kind])
        if not chosen:
            return  # kullanıcı diyaloğu iptal etti

        confirm = self.export_confirm_overwrite or self._default_confirm_overwrite
        target = resolve_target(chosen, kind, exists=Path.exists, confirm_overwrite=confirm)
        if target is None:
            self.bottom_dock.append_log("Disa aktarma iptal edildi: dosyanin uzerine yazilmadi.")
            return

        try:
            self._dispatch_export(kind, target, card)
        except (ValueError, OSError) as exc:
            self.bottom_dock.append_log(f"Disa aktarma basarisiz: {exc}")

    def _dispatch_export(self, kind: ExportKind, target: Path, card: DataExportCard) -> None:
        if kind is ExportKind.PNG:
            self.export_plot_png(target)
        elif kind is ExportKind.SVG:
            self.export_plot_svg(target)
        else:
            # F3-066: CSV büyük olabilir; worker thread'de, iptal edilebilir.
            self.start_channel_csv_export(
                target,
                selected_range_only=card.wants_selected_range(),
                include_metadata=card.wants_metadata(),
                raw=card.selected_variant() is DataVariant.RAW,
            )

    # -- işlem zinciri uygulaması (F4-008) ------------------------

    def _on_apply_processing(self) -> None:
        """`Apply Filter` — aktif sekmeye göre Filter ya da Custom zincirini uygular."""
        channel = self.plot_panel.channel
        if channel is None:
            self.bottom_dock.append_log("Önce bir kanal çizin.")
            return

        tools = self.right_dock.analysis_tools
        if tools.active_tab_title() == "Filter":
            try:
                chain = tools.build_filter_chain(channel.id, channel.sample_rate_hz or 0.0)
            except FilterTabError as exc:
                self.bottom_dock.append_log(f"Filtre parametresi geçersiz: {exc}")
                return
        else:
            chain = tools.step_editor.chain()

        if not chain.enabled_steps:
            self.bottom_dock.append_log("Uygulanacak işlem adımı yok (Custom sekmesi).")
            return
        if self._repository is None:
            return
        chunk = self._repository.query(channel.id, self._repository.metadata().time_range)
        if len(chunk) == 0:
            return
        self._dsp_projection = (len(chunk), chunk.timestamps_ns)
        self._processed_values = None
        self._dsp_runner.set_selection(channel.id)
        self._dsp_runner.submit(chain, chunk.values, channel.id)
        self.bottom_dock.append_log(
            f"{channel.display_label}: {len(chain.enabled_steps)} adımlı işlem çalıştırıldı."
        )
        derived = self.right_dock.analysis_tools.step_editor.derived_channel_metadata(channel)
        if derived.id != channel.id and derived.sample_rate_hz is not None:
            self.bottom_dock.append_log(
                f"Türetilmiş kanal: {derived.name} @ {derived.sample_rate_hz:g} Hz "
                f"(kaynak {channel.sample_rate_hz or 0:g} Hz)."
            )

    def _on_derived_channel_requested(self, definition: object) -> None:
        """Formül editöründen gelen tanımı `Derived/` ağacına ekler — `F4-073`."""
        if not isinstance(definition, DerivedChannelDefinition):
            return
        repository = self._repository
        if not isinstance(repository, DerivedChannelRepository):
            self.bottom_dock.append_log("Türetilmiş kanal için önce bir kayıt açın.")
            return
        try:
            channel = repository.add(definition)
        except DerivedChannelError as exc:
            self.bottom_dock.append_log(f"Türetilmiş kanal eklenemedi: {exc}")
            return
        # Kanal ağacı ve seçiciler yeni kanalı görsün.
        self.set_recording(repository.metadata(), repository.channels())
        self.bottom_dock.append_log(
            f"Türetilmiş kanal eklendi: {channel.path} = {definition.expression}"
        )

    def _on_dsp_result(self, _job_id: int, channel_id: str, result: object) -> None:
        from sonar_analyzer.processing.chain import ChainResult

        primary = self.plot_panel.channel
        if not isinstance(result, ChainResult) or primary is None or primary.id != channel_id:
            return
        self._processed_values = result.values
        self._refresh_processed_overlay()
        if result.invalid_count:
            self.bottom_dock.append_log(
                f"İşlenmiş veride {result.invalid_count} geçersiz örnek işaretli."
            )

    def _refresh_processed_overlay(self) -> None:
        projection = self._dsp_projection
        values = self._processed_values
        if projection is None or values is None or values.size == 0:
            return
        source_count, source_times = projection
        x, _raw = self.plot_panel.curve_data()
        times = np.array([self.plot_panel.timestamp_ns_for_x(float(t)) for t in x], dtype=np.int64)
        indices = np.searchsorted(source_times, times)
        # Hesap tam çözünürlükte kalır; viewport değişince sonuç yeniden çizilir.
        positions = np.arange(values.size) * (source_count / values.size)
        plotted_values = np.interp(indices, positions, values)
        try:
            self.plot_panel.set_processed_overlay(
                plotted_values,
                visible=self.right_dock.analysis_tools.show_filtered_data.isChecked(),
            )
        except (ValueError, RuntimeError) as exc:
            self.bottom_dock.append_log(f"İşlenmiş veri gösterilemedi: {exc}")
            return

    def _on_dsp_failed(self, _job_id: int, message: str) -> None:
        self.bottom_dock.append_log(f"İşlem başarısız: {message}")

    @property
    def dsp_runner(self) -> DspRunner:
        """Analiz işlem worker'ı — testler ve dış gözlem için."""
        return self._dsp_runner

    # -- workspace (F3-068) ----------------------------------------

    def capture_workspace(self) -> WorkspaceModel:
        """Şu anki oturumu bir `WorkspaceModel`'e dökümler — `F3-068`.

        Açık kayıt dosyaları, grafik paneli (kanallar + eksen aralıkları +
        zoom kipi), açık görünüm sekmesi, X-senkronizasyon grubu, marker/TX
        görünürlüğü, imleç zamanı kipi ve olay filtresi yakalanır. Dock
        yerleşimi Qt `saveState()` ile opak biçimde saklanır.
        """
        source_paths = [repo.metadata().source_path for repo in self._owned_repositories]

        channel_ids = self.plot_panel.plotted_channel_ids()
        x0, x1, y0, y1 = self.plot_panel.visible_range()
        panel = PanelState(
            channel_ids=list(channel_ids),
            x_range=(x0, x1) if channel_ids else None,
            y_range=(y0, y1) if channel_ids else None,
            zoom_mode=self.plot_panel.zoom_mode,
        )

        sync_on = self.plot_tool_bar.sync_checkbox.isChecked()
        sync_groups = [[0]] if sync_on else []

        view = ViewState(
            time_display_mode=self.status.cursor_time_mode.value,
            markers_visible=self.plot_tool_bar.markers_checkbox.isChecked(),
            tx_visible=self.plot_tool_bar.tx_checkbox.isChecked(),
            sync_x=sync_on,
        )

        filter_state = self.bottom_dock.event_filter_state()
        event_filter = EventFilterState(
            source=filter_state["source"] if isinstance(filter_state["source"], str) else None,
            min_severity=(
                filter_state["min_severity"]
                if isinstance(filter_state["min_severity"], str)
                else None
            ),
            text=str(filter_state["text"]),
            group_near=bool(filter_state["group_near"]),
        )

        dock_state = base64.b64encode(bytes(self.saveState().data())).decode("ascii")
        current_tab = self.view_tabs.tabText(self.view_tabs.currentIndex())

        return WorkspaceModel(
            source_paths=source_paths,
            panels=[panel],
            active_panel=0,
            layout_mode="tabs",
            sync_groups=sync_groups,
            active_view_tab=current_tab or "Time Series",
            dock_state=dock_state,
            view=view,
            event_filter=event_filter,
            filter_tool=self.right_dock.analysis_tools.filter_tool_state(),
        )

    def save_workspace(self, path: str | Path) -> Path:
        """Şu anki oturumu bir workspace dosyasına yazar — `F3-068`."""
        dest = save_workspace(self.capture_workspace(), path)
        self.bottom_dock.append_log(f"Workspace kaydedildi: {dest}")
        return dest

    def restore_workspace(
        self,
        path: str | Path,
        *,
        on_missing_sources: Callable[[list[str]], None] | None = None,
    ) -> WorkspaceModel:
        """Bir workspace dosyasını okur ve mevcut oturuma uygular — `F3-069`, `F3-070`.

        Kaynak dosyaların yeniden açılması çağıranın işidir (menü akışı);
        bu metot, **zaten açık** kayda karşı düzeni ve kanal görünümünü
        yeniden kurar.

        `F3-070`: belge bozuksa `WorkspaceError` fırlatılır ve **açık oturum
        hiç değişmez** (uygulama okuma başarısız olunca hiç başlamaz). Eksik
        kaynak dosyalar sessizce atlanmaz: her biri Log'a yazılır,
        `on_missing_sources` (verilmişse) çağrılır ve `last_missing_sources`
        alanında tutulur.
        """
        try:
            model = load_workspace(path)
        except WorkspaceError:
            self.bottom_dock.append_log(
                f"Workspace okunamadi ({Path(path).name}); acik oturum korundu."
            )
            raise

        resolution = resolve_sources(
            model.source_paths, exists=lambda candidate: Path(candidate).exists()
        )
        self.last_missing_sources = list(resolution.missing)
        if resolution.has_missing:
            for missing in resolution.missing:
                self.bottom_dock.append_log(f"Workspace kaynagi bulunamadi: {missing}")
            if on_missing_sources is not None:
                on_missing_sources(list(resolution.missing))

        self.apply_workspace(model)
        self.bottom_dock.append_log(f"Workspace yuklendi: {Path(path)}")
        return model

    def apply_workspace(self, model: WorkspaceModel) -> None:
        """`model`'deki düzen + görünüm durumunu açık kayda uygular — `F3-069`."""
        # 1) Paneldeki kanallar (ilki grafiği sıfırlar, kalanlar eklenir).
        panel = model.panels[0] if model.panels else PanelState()
        if panel.channel_ids and self._repository is not None:
            self.open_channel(panel.channel_ids[0])
            for channel_id in panel.channel_ids[1:]:
                self._add_channel_to_plot(channel_id)

        # 2) Zoom kipi + eksen aralıkları (yalnız seri varsa anlamlı).
        self.plot_panel.set_zoom_mode(panel.zoom_mode)
        if panel.channel_ids:
            if panel.x_range is not None:
                self.plot_panel.set_x_range(*panel.x_range)
            if panel.y_range is not None:
                self.plot_panel.set_axis_range("left", *panel.y_range)

        # 3) Açık görünüm sekmesi.
        titles = self.view_tabs.tab_titles()
        if model.active_view_tab in titles:
            self.view_tabs.setCurrentIndex(titles.index(model.active_view_tab))

        # 4) Toolbar görünürlükleri + X senkronizasyonu.
        self.plot_tool_bar.markers_checkbox.setChecked(model.view.markers_visible)
        self.plot_tool_bar.tx_checkbox.setChecked(model.view.tx_visible)
        self.plot_tool_bar.sync_checkbox.setChecked(model.view.sync_x)

        # 5) İmleç zamanı gösterim kipi.
        self.status.set_cursor_time_mode(model.view.time_display_mode)

        # 6) Olay filtresi.
        self.bottom_dock.apply_event_filter_state(model.event_filter.to_dict())

        # 6b) Filter sekmesi ayarları (F4-038).
        self.right_dock.analysis_tools.apply_filter_tool_state(model.filter_tool)

        # 7) Dock yerleşimi (opak Qt state).
        if model.dock_state:
            try:
                self.restoreState(base64.b64decode(model.dock_state))
            except (ValueError, TypeError):
                self.bottom_dock.append_log("Workspace dock yerlesimi okunamadi; atlandi.")

    # -- klavye kısayolu işleyicileri (F3-072) ---------------------

    def _default_workspace_save_dialog(self) -> str:
        start_dir = self._settings.last_directory or str(Path.home())
        path, _selected = QFileDialog.getSaveFileName(
            self, "Workspace kaydet", start_dir, "SONAR workspace (*.json)"
        )
        return path

    def save_workspace_via_dialog(self) -> Path | None:
        """`Ctrl+S` — hedef sorar ve workspace'i kaydeder."""
        dialog = self.workspace_save_dialog or self._default_workspace_save_dialog
        chosen = dialog()
        if not chosen:
            return None
        dest = chosen if chosen.lower().endswith(".json") else chosen + ".json"
        return self.save_workspace(dest)

    def toggle_playback(self) -> None:
        """`Space` — oynat/duraklat (kayıt yoksa sessiz)."""
        button = self.playback_dock.buttons["button_play"]
        if button.isEnabled():
            button.toggle()

    def reset_plot_view(self) -> None:
        """`Home` — grafiğin görünümünü ev aralığına döndürür."""
        self.plot_panel.reset_view()

    def set_zoom_mode_x(self) -> None:
        self.plot_panel.set_zoom_mode("x")
        self.bottom_dock.append_log("Zoom modu: X")

    def set_zoom_mode_y(self) -> None:
        self.plot_panel.set_zoom_mode("y")
        self.bottom_dock.append_log("Zoom modu: Y")

    def set_zoom_mode_xy(self) -> None:
        self.plot_panel.set_zoom_mode("xy")
        self.bottom_dock.append_log("Zoom modu: XY")

    def toggle_cursor_mode(self) -> None:
        """`C` — crosshair imlecini görünür/gizli yapar."""
        if self.plot_panel.crosshair_visible():
            self.plot_panel.clear_cursor()
            return
        x_min, x_max = self.plot_panel.visible_x_range()
        self.plot_panel.set_cursor((x_min + x_max) / 2.0)

    def toggle_region_selection(self) -> None:
        """`R` — zaman bölgesi seçimini açar/kapatır."""
        if self.plot_panel.time_region_x() is not None:
            self.plot_panel.clear_time_region()
            return
        x_min, x_max = self.plot_panel.visible_x_range()
        span = x_max - x_min
        self.plot_panel.set_time_region(x_min + span / 3.0, x_max - span / 3.0)

    def goto_next_event_shortcut(self) -> None:
        """`F4` — sonraki olaya git."""
        self.playback_dock.goto_next_event()

    def goto_previous_event_shortcut(self) -> None:
        """`Shift+F4` — önceki olaya git."""
        self.playback_dock.goto_previous_event()

    def _on_axis_range_requested(self, axis: str, y_min: float, y_max: float) -> None:
        """Inspector Display'den gelen eksen aralığını seçili grafiğe uygular — `F3-036`.

        `F3-041`: değişiklik undo/redo geçmişine yazılır.
        """
        if axis == "left":
            _x0, _x1, old_min, old_max = self.plot_panel.visible_range()
        else:
            current = self.plot_panel.right_axis_y_range()
            if current is None:
                return
            old_min, old_max = current
        try:
            self._view_history.push(
                ViewCommand(
                    label="Eksen araligi",
                    apply=lambda: self.plot_panel.set_axis_range(axis, y_min, y_max),
                    revert=lambda: self.plot_panel.set_axis_range(axis, old_min, old_max),
                )
            )
        except ValueError as exc:
            self.bottom_dock.append_log(f"Eksen araligi uygulanamadi: {exc}")

    def apply_series_color(self, channel_id: str, color: str) -> None:
        """Bir serinin rengini **geri alınabilir** biçimde değiştirir — `F3-041`."""
        old_color = self.plot_panel.series_color(channel_id)
        if old_color == color:
            return
        self._view_history.push(
            ViewCommand(
                label="Renk degisikligi",
                apply=lambda: self.plot_panel.set_series_style(channel_id, color=color),
                revert=lambda: self.plot_panel.set_series_style(channel_id, color=old_color),
            )
        )

    def undo_view_change(self) -> bool:
        """Son görünüm değişikliğini geri alır — `F3-041`."""
        return self._view_history.undo()

    def redo_view_change(self) -> bool:
        """Geri alınan son görünüm değişikliğini yeniden uygular — `F3-041`."""
        return self._view_history.redo()

    def _on_cursor_moved(self, sample_seconds: float, _value: float) -> None:
        """Crosshair bir örneğe kenetlenince Inspector Raw görünümünü doldurur — `F3-040`.

        Yalnız gerçek `.bin` kaydında (raw byte erişimi) çalışır; simülasyon
        gibi ham offseti olmayan kaynaklarda Raw alanları boş kalır.
        """
        channel = self.plot_panel.channel
        source = self.base_repository()
        if channel is None or not isinstance(source, FileRecordingRepository):
            return
        try:
            timestamp_ns = self.plot_panel.timestamp_ns_for_x(sample_seconds)
            inspection = source.inspect_sample(channel.id, timestamp_ns)
        except (RuntimeError, LookupError, KeyError):
            return
        self.right_dock.inspector.show_raw_sample(inspection, channel.unit or "")

    def plot_point_budget(self) -> int:
        """Grafiğin piksel genişliğine karşılık gelen nokta bütçesi — `F4-055`.

        Sorgular bu bütçeyle çağrılır: viewport daraldığında repository
        daha az nokta döndürür. Ekranda ayırt edilemeyecek noktaları
        okumak ne çözünürlük kazandırır ne görünümü değiştirir.
        """
        return points_for_width(self.plot_panel.plot_pixel_width())

    def _plot_request(self) -> tuple[float, float, int, tuple[str, ...]]:
        lo, hi = self.plot_panel.visible_x_range()
        return lo, hi, self.plot_point_budget(), tuple(self.plot_panel.plotted_channel_ids())

    def refresh_plot_viewport(self) -> None:
        """Son viewport ve piksel bütçesine göre yalnız çizim serilerini yeniler."""
        self._plot_refresh_timer.stop()
        if not self.center_shows_plot:
            return
        if self._repository is None or self.plot_panel.channel is None:
            return
        request = self._plot_request()
        if request == self._last_plot_request:
            return
        lo, hi, budget, channel_ids = request
        span = TimeRange(
            self.plot_panel.timestamp_ns_for_x(lo), self.plot_panel.timestamp_ns_for_x(hi)
        )
        for channel_id in channel_ids:
            chunk = self._repository.query(channel_id, span, max_points=budget)
            with measure("render.plot", channel_id=channel_id, sample_count=len(chunk)):
                self.plot_panel.update_channel_data(channel_id, chunk)
        with measure("render.overlay"):
            self._refresh_processed_overlay()
        self._last_plot_request = self._plot_request()

    def refresh_analysis_views(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """Son seçimi saklar; etkin yüzeyi en fazla 20 Hz günceller — F4-061.

        Gizli sekmeler hesaplama/çizim yapmaz; açılınca aynı son seçimi alır.
        Ara sonuçlar kuyruk oluşturmaz: yalnız son veri snapshot'ı saklanır.
        """
        data = np.array(values, dtype=np.float64, copy=True)
        data.setflags(write=False)
        self._analysis_data = (channel, data, region_seconds)
        self._analysis_revision += 1
        if not self._analysis_timer.isActive():
            self._flush_analysis_views()

    def _flush_analysis_views(self) -> None:
        if self._analysis_data is None:
            return
        active = self.center_stack.currentWidget()
        if active not in (self.dashboard, self.spectrum_view, self.waterfall_view):
            return
        if self._analysis_rendered.get(active) == self._analysis_revision:
            return
        channel, data, region = self._analysis_data
        with measure(
            "render.analysis",
            panel=active.objectName(),
            channel_id=channel.id,
            sample_count=int(data.size),
        ):
            self._render_analysis_panel(active, channel, data, region)

    def _render_analysis_panel(
        self,
        active: QWidget,
        channel: ChannelMetadata,
        data: NDArray[np.float64],
        region: tuple[float, float] | None,
    ) -> None:
        if active is self.dashboard:
            self.dashboard.set_channel_data(channel, data, region_seconds=region)
        elif active is self.spectrum_view:
            self.spectrum_view.set_channel_data(channel, data, region_seconds=region)
        elif active is self.waterfall_view:
            self.waterfall_view.set_channel_data(channel, data, region_seconds=region)
        else:
            return
        self._analysis_rendered[active] = self._analysis_revision
        self._analysis_timer.start()

    def _on_center_view_changed(self, _index: int) -> None:
        # Sekme açıldığında en son seçim ilk boyamadan önce hazır olur.
        self._flush_analysis_views()
        if self.center_shows_plot:
            self._plot_refresh_timer.start()

    def clear_analysis_views(self) -> None:
        """Tüm analiz yüzeylerini boş duruma alır — `F4-052`."""
        self._analysis_timer.stop()
        self._analysis_data = None
        self._analysis_rendered.clear()
        self.dashboard.clear_analysis()
        self.spectrum_view.clear()
        self.waterfall_view.clear()

    def _on_stats_region_changed(self, start_ns: int, end_ns: int) -> None:
        """Grafikte zaman bölgesi seçilince istatistik kartını o pencereye daraltır — `F3-039`.

        Seçili (birincil) kanalın yalnız `[start_ns, end_ns)` aralığındaki
        örnekleri için mean/std/RMS/min/max/peak-peak yeniden hesaplanır.

        `F3-060`: hızlı sürüklemede her ara konum için sorgu yapılmaz;
        ilk konum hemen, sonrası kısa bir sessizlikten sonra çizilir.
        """
        payload = (int(start_ns), int(end_ns))
        immediate = self._scrub_debouncer.submit(payload, now=perf_counter())
        if immediate is not None:
            self._run_stats_region_query(immediate)
        else:
            self._scrub_timer.start()

    def _flush_scrub_region(self) -> None:
        """`F3-060` zamanlayıcı tiki: sessizlik dolduysa son bölgeyi çizer."""
        pending = self._scrub_debouncer.poll(perf_counter())
        if pending is None:
            return
        self._scrub_timer.stop()
        self._run_stats_region_query(pending)

    def _run_stats_region_query(self, region: tuple[int, int]) -> None:
        """Bir zaman bölgesi için istatistikleri sorgular ve karta yazar — `F3-060`.

        Sorgu bir token alır; sonuç geldiğinde daha yeni bir scrub sorgusu
        başlatılmışsa sonuç atılır (eski sorgu görünümü ezmez).
        """
        channel = self.plot_panel.channel
        if channel is None or self._repository is None:
            return
        start_ns, end_ns = region
        token = self._scrub_debouncer.begin_query()
        chunk = self._repository.query(channel.id, TimeRange(start_ns, end_ns))
        if not self._scrub_debouncer.is_current(token):
            return
        span = self.plot_panel.time_region_x()
        # F4-052: ROI değişince dört merkez bölgesi aynı seçimle güncellenir.
        self.refresh_analysis_views(channel, chunk.values, region_seconds=span)

    def open_channel(self, channel_id: str) -> None:
        """Seçilen kanalı çizer ve ayrıntısını gösterir.

        Kayıt kapatılmışsa (`F3-007`) sessizce döner: kapatılmış bir
        snapshot'a sorgu gönderilmez.
        """
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None or self._repository is None:
            return

        self._dsp_runner.cancel_all()
        self._dsp_projection = None
        self._processed_values = None
        span = self._repository.metadata().time_range
        chunk = self._repository.query(
            channel_id,
            span,
            max_points=self.plot_point_budget(),
        )
        with measure("render.plot", channel_id=channel_id, sample_count=len(chunk)):
            self.plot_panel.set_channel(channel, chunk, time_origin_ns=span.start_ns)
        # F3-041: grafik tek seriye sıfırlandı; eski görünüm komutları
        # kaldırılmış serilere atıfta bulunur, geçmişi temizle.
        self._view_history.clear()
        # F4-008: yeni kanal -> eski işlenmiş overlay geçersiz, işlem editörü
        # bu kanala bağlanır.
        self.plot_panel.clear_processed_overlay()
        self.right_dock.analysis_tools.step_editor.set_input_channel(channel_id)
        self.right_dock.analysis_tools.step_editor.set_sample_rate(channel.sample_rate_hz or 0.0)
        analysis_chunk = self._repository.query(channel_id, span)
        self.clear_analysis_views()
        self.show_plot()
        self.refresh_analysis_views(channel, analysis_chunk.values)
        self.plot_tool_bar.set_current_channel(channel_id)
        self.right_dock.show_channel(channel)
        self.bottom_dock.append_log(f"{channel.display_label} cizildi ({len(chunk)} ornek).")
        self._last_plot_request = self._plot_request()
        self._plot_refresh_timer.stop()

    def _add_channel_to_plot(self, channel_id: str) -> str | None:
        """Bir kanalı grafiğe **ekler** (SIFIRLAMADAN) — `F3-015`/`F3-016` ortak yolu.

        `open_channel` (çift tık) aksine `add_channel` var olan diğer
        serileri korur, boş grafiğe eklenirse tek seri olarak başlatır.
        Kayıt kapalıysa veya kanal bilinmiyorsa sessizce `None` döner;
        eklendiyse kanalın gösterim etiketini döndürür (çağıran log yazar).
        """
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None or self._repository is None:
            return None

        chunk = self._repository.query(
            channel_id,
            self._repository.metadata().time_range,
            max_points=self.plot_point_budget(),
        )
        self.plot_panel.add_channel(
            channel, chunk, time_origin_ns=self._repository.metadata().time_range.start_ns
        )
        self.plot_tool_bar.set_current_channel(channel_id)
        self.show_plot()
        self.right_dock.show_channel(channel)
        return f"{channel.display_label} ({len(chunk)} ornek)"

    def _on_channel_dropped(self, channel_id: str) -> None:
        """Data Explorer'dan grafiğe sürüklenen kanalı ekler — `F3-015`."""
        added = self._add_channel_to_plot(channel_id)
        if added is not None:
            self.bottom_dock.append_log(f"{added} suruklenerek eklendi.")

    def _on_channels_add_requested(self, channel_ids: list[str]) -> None:
        """Çoklu seçimden gelen kanalları **aynı** grafiğe ekler — `F3-016`.

        Her kanal ayrı bir seri olarak eklenir (`add_channel`); geçersiz
        veya kayıt kapalıyken gelen kimlikler sessizce atlanır. "Ayrı
        grafiklerde açma" çoklu-panel altyapısı kurulunca ele alınacak
        (plan Bölüm 5.3).
        """
        added = [
            label for cid in channel_ids if (label := self._add_channel_to_plot(cid)) is not None
        ]
        if added:
            self.bottom_dock.append_log(f"{len(added)} kanal grafige eklendi: {', '.join(added)}.")

    def refresh_bit_analysis(self) -> None:
        """`Run BIT Analysis` — seçili kaydın BIT özetini yeniler — `F3-052`.

        Kayıtlı veriyi yeniden **sorgular**; donanıma / cihaza hiçbir
        komut gönderilmez (yalnız repository okuması). Açık kayıt yoksa
        kullanıcıya bildirir.
        """
        if self._repository is None:
            self.bottom_dock.append_log("BIT ozeti icin acik kayit yok.")
            return
        span = self._repository.metadata().time_range
        self.right_dock.bit_status.set_results(self._repository.bit_results(span))
        self.bottom_dock.append_log("BIT ozeti yenilendi.")

    def load_simulation(self) -> None:
        """Sahte kaydı açar; veri kaynağı `Simülasyon` olarak görünür."""
        repository = MockRecordingRepository()
        self.set_repository(repository)

    def request_open_files(self) -> tuple[Path, ...]:
        """Dosya seçicisini açar — `F3-001`.

        İptal edilirse hiçbir şey değişmez: açık kayıt, paneller ve merkezdeki
        görünüm olduğu gibi kalır (kabul kriteri).
        """
        return self.file_open.request_open(self)

    def _on_load_requested(self, paths: Sequence[str]) -> None:
        """Seçim talebini worker'a verir — `F3-001`, `F3-002`.

        Çağrı hemen döner: dosyalar arka plan thread'inde açılır, pencere
        bu sırada etkileşimlere yanıt vermeye devam eder.
        """
        self._supersede_active_load()
        self.pending_load_paths = tuple(Path(path) for path in paths)
        count = len(self.pending_load_paths)
        names = ", ".join(path.name for path in self.pending_load_paths)
        self.bottom_dock.append_log(f"Yukleme talebi: {count} dosya ({names}).")
        self.status.start_load_progress(count)
        self.active_load_request_id = self.file_loader.submit(self.pending_load_paths)

    def _supersede_active_load(self) -> None:
        """Yeni bir açma isteği geldiğinde öncekini geçersiz kılar — `F3-004`.

        Önceki istek iptal edilir (worker boşuna dosya açmasın) ve o isteğe
        ait sonuçlar geri alınır. Böylece iki hızlı açma isteğinde ekrana
        **yalnız güncel** olan uygulanır; geriden gelen eski sonuç görünümü
        ezemez.
        """
        previous_id = self.active_load_request_id
        if not previous_id:
            return
        self.file_loader.cancel(previous_id)
        self._discard_results_of(previous_id)
        self.bottom_dock.append_log(f"Onceki yukleme istegi birakildi (#{previous_id}).")

    def cancel_active_load(self) -> None:
        """Süren yüklemeyi iptal eder — `F3-003`.

        **İptal tüm isteği bırakır.** İptal bayrağı worker'ın paylaşılan
        durumuna yazılır (worker sıradaki dosyaya geçmeden görür) ve o isteğe
        ait **zaten tamamlanmış** sonuçlar da geri alınır: açık dosya
        listesinden çıkarılır, snapshot'ları kapatılır.

        Neden yarısını tutmuyoruz: kullanıcı çok dosyalı bir açmayı iptal
        ettiğinde "5 dosyadan 2'si açık kaldı" durumu, tamamlanmamış bir
        işlemi tamamlanmış gibi gösterir. Kabul kriteri de bunu yasaklıyor
        ("yarım kayıt açık dosya listesine girmez"). İptal ya hepsi ya
        hiçbiri demektir; kullanıcı isterse yeniden açar.
        """
        request_id = self.active_load_request_id
        if not request_id:
            return
        self.file_loader.cancel(request_id)
        self._discard_results_of(request_id)
        self.bottom_dock.append_log(f"Yukleme iptal edildi (#{request_id}).")
        self.status.cancel_button.setEnabled(False)

    @staticmethod
    def _release(result: FileLoadResult) -> None:
        """Uygulanmayan bir sonucun snapshot'ını bırakır (kaynak sızmasın)."""
        if result.repository is not None:
            result.repository.close()

    def _discard_results_of(self, request_id: int) -> None:
        """İptal edilen isteğin tamamlanmış sonuçlarını geri alır."""
        kept: list[FileLoadResult] = []
        for result in self.loaded_results:
            if result.request_id == request_id:
                if result.repository is not None:
                    result.repository.close()
                continue
            kept.append(result)
        self.loaded_results = tuple(kept)
        self.failed_results = tuple(
            result for result in self.failed_results if result.request_id != request_id
        )

    def _on_load_progress(self, request_id: int, completed: int, total: int) -> None:
        if request_id != self.active_load_request_id:
            return
        self.status.set_load_progress(completed, total)

    def _on_file_loaded(self, result: FileLoadResult) -> None:
        """Worker'dan gelen tek dosya sonucunu kaydeder ve log'a yazar.

        Sonucun repository'ye ve ekrana bağlanması `F3-005`'in işi; burada
        yalnız sonucun GUI thread'ine ulaştığı garanti edilir.
        """
        if self.file_loader.is_cancelled(result.request_id):
            # Iptal edilen istegin YARIM kalan sonucu acik dosya listesine
            # girmez (F3-003). Worker o dosyayi zaten acmis olabilir;
            # snapshot'i birakiyoruz ki acik kaynak sizmasin.
            self._release(result)
            self.bottom_dock.append_log(f"Iptal edildi, alinmadi: {result.path.name}")
            return
        if result.request_id != self.active_load_request_id:
            # ESKIMIS sonuc (F3-004): kullanici bu istegi baslattiktan sonra
            # yeni bir acma istedi. Geriden gelen sonuc guncel gorunumu
            # ezmemeli; sessizce dusurulur ama log'da izi kalir.
            self._release(result)
            self.bottom_dock.append_log(
                f"Eskimis sonuc yok sayildi: {result.path.name} (#{result.request_id})"
            )
            return
        if result.succeeded:
            self.loaded_results = (*self.loaded_results, result)
            self.bottom_dock.append_log(f"Yuklendi: {result.path.name}")
            return
        self.failed_results = (*self.failed_results, result)
        if result.error_type == "FileNotFoundError":
            # Dosya kalici olarak yok: son dosyalar listesinde tutmak
            # kullaniciyi tekrar tekrar ayni hataya goturur.
            self._forget_recent(result.path)
        self._report_load_error(result)

    def _report_load_error(self, result: FileLoadResult) -> None:
        """Hatayı kullanıcı diline çevirip gösterir; teknik ayrıntıyı log'a yazar — `F3-006`."""
        message = describe_load_error(result.path, result.error_type, result.error)
        # Teknik ayrinti UYGULAMA LOG'una gider (kabul kriteri): tur, ham
        # ileti ve tam yol teshis icin kaybolmaz.
        logger.error("Dosya yuklenemedi - %s", message.technical_text)
        # Alt seritteki operator gunlugu kullanici dilinde kalir.
        self.bottom_dock.append_log(f"Yuklenemedi: {result.path.name} - {message.user_text}")
        notifier = self._error_notifier or error_dialogs.message_box_notifier
        notifier(self, message)

    def _on_load_finished(self, request_id: int) -> None:
        self.bottom_dock.append_log(f"Yukleme istegi bitti (#{request_id}).")
        if self.active_load_request_id not in (0, request_id):
            # Eskimis istek bitti ama guncel olan hala suruyor: onun
            # ilerleme gostergesini kapatmayiz (F3-004).
            return
        cancelled = self.file_loader.is_cancelled(request_id)
        self.status.finish_load_progress(CANCELLED_TEXT if cancelled else READY_TEXT)
        if request_id == self.active_load_request_id:
            self.active_load_request_id = 0
            if not cancelled:
                self._apply_loaded_results(request_id)

    def _apply_loaded_results(self, request_id: int) -> None:
        """Yüklenen kaydı repository'ye ve ekrana bağlar — `F3-005`.

        Çok dosyalı seçimde **ilk** başarılı kayıt etkin görünüm olur
        (seçim sırası `F3-001`'de korunuyor); diğerleri açık kalır ve
        log'da bildirilir. Önceki açma isteğinden kalan snapshot'lar
        kapatılır — pencere yalnız gösterdiği kaydın sahibidir.
        """
        applied = [
            result
            for result in self.loaded_results
            if result.request_id == request_id and result.repository is not None
        ]
        if not applied:
            if self.failed_results:
                self.bottom_dock.append_log("Acilabilen dosya yok; gorunum degismedi.")
            return

        primary = applied[0]
        assert primary.repository is not None
        self._remember_recent(result.path for result in applied)
        self._close_owned_repositories()
        self._owned_repositories = tuple(
            result.repository for result in applied if result.repository is not None
        )
        self.set_repository(primary.repository)
        self.bottom_dock.append_log(f"Goruntulenen kayit: {primary.path.name}")
        if len(applied) > 1:
            others = ", ".join(result.path.name for result in applied[1:])
            self.bottom_dock.append_log(f"Ayrica acik: {others}")

    def _remember_recent(self, paths: Iterable[Path]) -> None:
        """Açılan dosyaları son dosyalar listesine ve klasör hafızasına yazar."""
        ordered = list(paths)
        if not ordered:
            return
        updated = recent_files.add_all(self._settings.recent_files, ordered)
        directory = str(ordered[0].parent)
        self._settings = replace(self._settings, recent_files=updated, last_directory=directory)
        self.file_open.set_last_directory(directory)
        self._persist_settings()

    def _forget_recent(self, path: Path) -> None:
        remaining = recent_files.drop(self._settings.recent_files, path)
        if remaining == self._settings.recent_files:
            return
        self._settings = replace(self._settings, recent_files=remaining)
        self._persist_settings()

    def _persist_settings(self) -> None:
        """Ayarları kalıcı hâle getirir; yazamamak uygulamayı durdurmaz."""
        try:
            self._settings_writer(self._settings)
        except OSError as exc:
            logger.warning("Ayarlar kaydedilemedi: %s", exc)
            self.bottom_dock.append_log("Ayarlar kaydedilemedi; liste bu oturumda tutuluyor.")

    @property
    def recent_files(self) -> tuple[str, ...]:
        """Son açılan dosyalar, en yeniden eskiye."""
        return tuple(self._settings.recent_files)

    def open_recent(self, path: Path) -> None:
        """Son dosyalar listesinden bir kaydı açar — seçiciyle aynı yolu izler."""
        self._on_load_requested([str(path)])

    # -- favori kanal gruplari (F3-017) --------------------------------

    @property
    def favorite_group_names(self) -> tuple[str, ...]:
        """Kayıtlı favori grup adları, saklanma sırasıyla."""
        return tuple(favorite_groups.names(self._settings.favorite_groups))

    def save_favorite_group(self, name: str, channel_ids: Sequence[str] | None = None) -> None:
        """Bir kanal kümesini adlandırılmış favori grup olarak kalıcı kaydeder — `F3-017`.

        `channel_ids` verilmezse önce Channels ağacındaki seçim, o da
        boşsa grafikteki seriler kullanılır. Kaydedilecek kanal yoksa
        işlem yapılmaz (adsız/boş grup oluşturulmaz).
        """
        ids = list(channel_ids) if channel_ids is not None else self._favorite_source_ids()
        if not ids:
            self.bottom_dock.append_log("Favori grup icin kanal secili degil.")
            return
        try:
            updated = favorite_groups.save(self._settings.favorite_groups, name, ids)
        except ValueError as exc:
            self.bottom_dock.append_log(str(exc))
            return
        self._settings = replace(self._settings, favorite_groups=updated)
        self._persist_settings()
        self.bottom_dock.append_log(f"Favori grup kaydedildi: {name.strip()} ({len(ids)} kanal).")

    def open_favorite_group(self, name: str) -> None:
        """Kayıtlı bir favori grubu grafiğe açar; bulunamayan kanalları ayrı raporlar — `F3-017`.

        Kabul kriteri: grup tekrar açılır; bu kayıtta olmayan kanallar
        eklenmeden, ayrı bir log satırında bildirilir.
        """
        group = favorite_groups.get(self._settings.favorite_groups, name)
        if group is None:
            self.bottom_dock.append_log(f"Favori grup bulunamadi: {name}")
            return

        resolution = favorite_groups.resolve(group, (c.id for c in self._channels))
        added = [
            label
            for cid in resolution.found
            if (label := self._add_channel_to_plot(cid)) is not None
        ]
        self.bottom_dock.append_log(
            f"Favori grup '{group.name}': {len(added)} kanal grafige eklendi."
        )
        if resolution.has_missing:
            self.bottom_dock.append_log(
                f"Favori grup '{group.name}': {len(resolution.missing)} kanal bu kayitta yok: "
                f"{', '.join(resolution.missing)}"
            )

    def _favorite_source_ids(self) -> list[str]:
        selected = selected_channel_ids(self.left_dock.tree)
        if selected:
            return selected
        return self.plot_panel.plotted_channel_ids()

    def close_recordings(self) -> None:
        """Açık kayıtların kaynak dosyalarını bırakır — `F4-054`.

        Kaynak bellek eşlemesiyle okunur (`MappedSource`); eşleme açıkken
        Windows'ta dosya silinemez veya üzerine yazılamaz. Bu metot pencereyi
        kapatmadan kilidi bırakır.
        """
        self._close_owned_repositories()

    def _close_owned_repositories(self) -> None:
        for repository in self._owned_repositories:
            repository.close()
        self._owned_repositories = ()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Pencere kapanırken worker thread'i ve açık snapshot'lar bırakılır."""
        if self._export_runner is not None:
            # F3-066: süren dışa aktarma worker'ı çalışırken pencere çöpe
            # giderse "QThread destroyed while running" süreci çökertir.
            self._export_runner.cancel()
            self._export_runner.wait_done()
            self._export_runner = None
        # F4-008: süren DSP worker'ları da beklenir.
        self._dsp_runner.cancel_all()
        self._dsp_runner.wait_all()
        self._plot_refresh_timer.stop()
        self._scrub_timer.stop()
        self._analysis_timer.stop()
        self.file_loader.shutdown()
        self._close_owned_repositories()
        super().closeEvent(event)

    def set_repository(self, repository: RecordingRepository) -> None:
        """Bir veri kaynağını açar ve panellere dağıtır.

        Kaynak `F4-069` sarmalayıcısıyla sarılır: formül editörünün
        (`F4-073`) ürettiği türetilmiş kanallar ham kaynağa dokunmadan
        aynı sözleşme üzerinden sorgulanabilir olur.
        """
        if not isinstance(repository, DerivedChannelRepository):
            repository = DerivedChannelRepository(repository)
        self._repository = repository
        metadata = repository.metadata()
        channels = repository.channels()
        self.set_recording(metadata, channels)
        # F4-075: işaretler kayda aittir; yeni kaynak yeni bir liste demektir.
        self.set_annotations(AnnotationSet())

        span = metadata.time_range
        events = repository.events(span)
        self.bottom_dock.set_events(events, start_ns=span.start_ns)
        self.playback_dock.set_events(events)
        self.plot_panel.set_event_markers(
            [(event.timestamp_ns, severity_style(event.severity).color) for event in events]
        )
        transmissions = repository.transmissions(span)
        self.plot_panel.set_tx_regions([(tx.start_ns, tx.end_ns) for tx in transmissions])
        self.transmission_panel.set_intervals(transmissions, start_ns=span.start_ns)
        self.right_dock.bit_status.set_results(repository.bit_results(span))
        self._refresh_recording_tree()

    def _refresh_recording_tree(self) -> None:
        """ "Data Tree" sekmesini (`F3-009`) açık kayıtlarla senkronlar.

        Pencerenin sahibi olduğu kayıtlar varsa (`F3-001`den açılmış
        dosyalar) hepsi gösterilir — bir dosyayı kapatmak diğerlerini
        etkilemez (`F3-007`). Yalnız dışarıdan verilmiş tek bir kaynak
        (örn. simülasyon) açıksa o tek başına gösterilir.
        """
        if self._owned_repositories:
            recordings = [
                (repository.metadata(), repository.channels())
                for repository in self._owned_repositories
            ]
        elif self._repository is not None:
            recordings = [(self._repository.metadata(), self._repository.channels())]
        else:
            recordings = []
        self.left_dock.set_recordings(recordings)

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
        self.plot_tool_bar.markers_visible_toggled.connect(self._set_event_markers_visible)
        self.plot_tool_bar.tx_visible_toggled.connect(self._set_tx_regions_visible)
        layout.addWidget(self.plot_tool_bar)

        self.empty_state = EmptyStatePanel(container)
        self.empty_state.open_requested.connect(self.action("action_open").trigger)
        self.empty_state.simulation_requested.connect(self.action("action_load_simulation").trigger)

        self.dashboard = DashboardPanel(container)
        self.plot_panel = self.dashboard.time_series
        self.plot_panel.channel_dropped.connect(self._on_channel_dropped)
        self.plot_panel.time_region_changed.connect(self._on_stats_region_changed)
        self.plot_panel.cursor_moved.connect(self._on_cursor_moved)
        self.plot_panel.x_range_changed.connect(self._sync_timeline_viewport)
        self.plot_panel.plot_width_changed.connect(self._plot_refresh_timer.start)

        self.transmission_panel = TransmissionPanel(container)

        # F4-045: "Spectrum" sekmesi tam boy FFT/PSD görünümü.
        self.spectrum_view = SpectrumPanel(container)
        self.spectrum_view.setObjectName("panel_spectrum_view")

        # F4-051: "Spectrogram" sekmesi tam boy waterfall görünümü.
        self.waterfall_view = WaterfallPanel(container)
        self.waterfall_view.setObjectName("panel_waterfall_view")

        self.center_stack = QStackedWidget(container)
        self.center_stack.setObjectName("center_stack")
        self.center_stack.addWidget(self.empty_state)
        self.center_stack.addWidget(self.dashboard)
        self.center_stack.addWidget(self.transmission_panel)
        self.center_stack.addWidget(self.spectrum_view)
        self.center_stack.addWidget(self.waterfall_view)
        self.center_stack.setCurrentWidget(self.empty_state)
        self.center_stack.currentChanged.connect(self._on_center_view_changed)

        self.view_tabs.currentChanged.connect(self._on_view_tab_changed)

        layout.addWidget(self.center_stack, 1)
        return container

    def _on_view_tab_changed(self, index: int) -> None:
        """`F3-048` TX tablosu, `F4-045` Spectrum görünümü; ötekiler grafiği gösterir."""
        title = self.view_tabs.tabText(index)
        if title == "Transmission":
            self.center_stack.setCurrentWidget(self.transmission_panel)
        elif title == "Spectrum" and self._repository is not None:
            self.center_stack.setCurrentWidget(self.spectrum_view)
        elif title == "Spectrogram" and self._repository is not None:
            self.center_stack.setCurrentWidget(self.waterfall_view)
        elif self._repository is not None:
            self.show_plot()
        else:
            self.show_empty_state()

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
        # F4-073: formül editörü yalnız bu kayıttaki kanalları kabul etsin.
        self.right_dock.analysis_tools.formula_editor.set_channels(list(channels))
        self.right_dock.close_inspector()
        self.right_dock.bit_status.clear()
        self.plot_panel.clear()
        self.clear_analysis_views()
        self.show_empty_state()
        self.playback_dock.set_recording_range(metadata.time_range)
        # F3-061: imleç zamanının UTC/yerel görünümü için kanonik köken.
        self.status.set_time_origin(metadata.time_range.start_ns)
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

    def close_active_recording(self) -> None:
        """Etkin kaydı kapatır ve bağlı panelleri temizler — `F3-007`.

        Kapatılan kaydın snapshot'ı bırakılır; ondan sonra o kayda **sorgu
        yapılmaz** (`_repository` bırakılır, `open_channel` sessizce döner).
        Açık başka kayıt varsa sıradaki etkin görünüm olur — bir dosyayı
        kapatmak diğerlerini bozmaz (kabul kriteri).
        """
        if self._repository is None:
            return

        closed_path = self._active_source_label()
        # Suren yukleme varsa iptal edilir: kapatilan kayda ait sonuc geri
        # gelip gorunumu tazelemeye kalkmasin.
        if self.active_load_request_id:
            self.cancel_active_load()

        remaining = self._detach_active_repository()
        self.bottom_dock.append_log(f"Kayit kapatildi: {closed_path}")

        if remaining is None:
            self._clear_recording_panels()
            return

        self.set_repository(remaining)
        promoted_path = remaining.metadata().source_path
        self.bottom_dock.append_log(f"Goruntulenen kayit: {Path(promoted_path).name}")

    def _active_source_label(self) -> str:
        assert self._repository is not None
        return self._repository.metadata().source_path

    @property
    def repository(self) -> RecordingRepository | None:
        """Panellerin okuduğu kaynak — `F4-073` sarmalayıcısı dahil."""
        return self._repository

    def base_repository(self) -> RecordingRepository | None:
        """`F4-073` sarmalayıcısının altındaki asıl kaynak.

        `set_repository` kaynağı `DerivedChannelRepository` ile sarar;
        kimlik ve tür karşılaştırmaları (hangi dosya açık, ham kayıt
        incelemesi) sarmalayıcıyı değil **tabanı** görmelidir.
        """
        repository = self._repository
        if isinstance(repository, DerivedChannelRepository):
            return repository.base
        return repository

    def _detach_active_repository(self) -> FileRecordingRepository | None:
        """Etkin kaydı kapatıp listelerden çıkarır; varsa sıradakini döner."""
        active = self.base_repository()
        self._repository = None

        promoted: FileRecordingRepository | None = None
        kept_owned: list[FileRecordingRepository] = []
        for repository in self._owned_repositories:
            if repository is active:
                repository.close()
                continue
            kept_owned.append(repository)
            if promoted is None:
                promoted = repository
        self._owned_repositories = tuple(kept_owned)

        # Pencerenin sahibi olmadigi bir kaynak (ornegin simulasyon) ise
        # kapatma sorumlulugu cagirana ait; yalnizca birakilir.
        self.loaded_results = tuple(
            result for result in self.loaded_results if result.repository is not active
        )
        return promoted

    def _clear_recording_panels(self) -> None:
        """Hiç açık kayıt kalmadığında panelleri boş duruma döndürür."""
        self._channels = ()
        self.set_annotations(AnnotationSet())
        self._plot_refresh_timer.stop()
        self._last_plot_request = None
        self._dsp_projection = None
        self._processed_values = None
        self._dsp_runner.cancel_all()
        self.left_dock.clear()
        self.plot_tool_bar.set_channels([])
        self.right_dock.close_inspector()
        self.right_dock.bit_status.clear()
        self.plot_panel.clear()
        self.plot_panel.clear_event_markers()
        self.plot_panel.clear_tx_regions()
        self.transmission_panel.clear()
        self.playback_dock.timeline.clear()
        self._view_history.clear()
        self._scrub_timer.stop()
        self._scrub_debouncer.cancel()
        self.status.set_time_origin(None)
        self.status.set_cursor_time(None)
        self.clear_analysis_views()
        self.bottom_dock.clear_events()
        self.show_empty_state()
        self.status.set_field("file", "")
        self.status.set_field("connection", "")
        self.status.set_status(READY_TEXT)
        self.action("action_close").setEnabled(False)
        self.action("action_export").setEnabled(False)

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

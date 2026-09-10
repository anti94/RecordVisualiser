"""Ana pencere ve üç sütunlu düzen — `F1-007`, `F1-022`.

Yerleşim `docs/ui/layout-map.md` §1-2'ye göre kurulur:

    sol dock (~200 px) | merkez (esner) | sağ dock (~300 px)

Sütun genişlikleri sabit değil **öntanımlıdır**: kullanıcı ayırıcıyla
değiştirebilir ve düzen workspace ile kaydedilir. Pencere büyüdüğünde
yalnız merkez büyür; sağ sütundaki parametre alanları daralıp okunmaz
hâle gelmez.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.application import favorite_groups, recent_files
from sonar_analyzer.application.file_loader import (
    FileLoadResult,
    FileLoadService,
    LoaderCallable,
)
from sonar_analyzer.application.load_errors import describe_load_error
from sonar_analyzer.application.view_history import ViewCommand, ViewHistory
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
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
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock, selected_channel_ids
from sonar_analyzer.ui.docks.playback import PlaybackDock
from sonar_analyzer.ui.docks.right_column import RightColumnDock
from sonar_analyzer.ui.empty_state import EmptyStatePanel
from sonar_analyzer.ui.error_dialogs import LoadErrorNotifier
from sonar_analyzer.ui.file_open import FileOpenController
from sonar_analyzer.ui.plot_tool_bar import PlotToolBar
from sonar_analyzer.ui.plots.dashboard import DashboardPanel
from sonar_analyzer.ui.status_bar import CANCELLED_TEXT, READY_TEXT, AppStatusBar
from sonar_analyzer.ui.theme import apply_theme
from sonar_analyzer.ui.view_tab_bar import ViewTabBar

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
        #: `F3-041` görünüm ayarları (renk, eksen) undo/redo geçmişi.
        self._view_history = ViewHistory()
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
        if channel is None or not isinstance(self._repository, FileRecordingRepository):
            return
        try:
            timestamp_ns = self.plot_panel.timestamp_ns_for_x(sample_seconds)
            inspection = self._repository.inspect_sample(channel.id, timestamp_ns)
        except (RuntimeError, LookupError, KeyError):
            return
        self.right_dock.inspector.show_raw_sample(inspection, channel.unit or "")

    def _on_stats_region_changed(self, start_ns: int, end_ns: int) -> None:
        """Grafikte zaman bölgesi seçilince istatistik kartını o pencereye daraltır — `F3-039`.

        Seçili (birincil) kanalın yalnız `[start_ns, end_ns)` aralığındaki
        örnekleri için mean/std/RMS/min/max/peak-peak yeniden hesaplanır.
        """
        channel = self.plot_panel.channel
        if channel is None or self._repository is None:
            return
        chunk = self._repository.query(channel.id, TimeRange(int(start_ns), int(end_ns)))
        span = self.plot_panel.time_region_x()
        self.dashboard.statistics.set_channel_data(channel, chunk.values, region_seconds=span)

    def open_channel(self, channel_id: str) -> None:
        """Seçilen kanalı çizer ve ayrıntısını gösterir.

        Kayıt kapatılmışsa (`F3-007`) sessizce döner: kapatılmış bir
        snapshot'a sorgu gönderilmez.
        """
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None or self._repository is None:
            return

        chunk = self._repository.query(channel_id, self._repository.metadata().time_range)
        self.plot_panel.set_channel(channel, chunk)
        # F3-041: grafik tek seriye sıfırlandı; eski görünüm komutları
        # kaldırılmış serilere atıfta bulunur, geçmişi temizle.
        self._view_history.clear()
        self.dashboard.statistics.set_channel_data(channel, chunk.values)
        self.plot_tool_bar.set_current_channel(channel_id)
        self.show_plot()
        self.right_dock.show_channel(channel)
        self.bottom_dock.append_log(f"{channel.display_label} cizildi ({len(chunk)} ornek).")

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

        chunk = self._repository.query(channel_id, self._repository.metadata().time_range)
        self.plot_panel.add_channel(channel, chunk)
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

    def _close_owned_repositories(self) -> None:
        for repository in self._owned_repositories:
            repository.close()
        self._owned_repositories = ()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Pencere kapanırken worker thread'i ve açık snapshot'lar bırakılır."""
        self.file_loader.shutdown()
        self._close_owned_repositories()
        super().closeEvent(event)

    def set_repository(self, repository: RecordingRepository) -> None:
        """Bir veri kaynağını açar ve panellere dağıtır."""
        self._repository = repository
        metadata = repository.metadata()
        channels = repository.channels()
        self.set_recording(metadata, channels)

        span = metadata.time_range
        self.bottom_dock.set_events(repository.events(span), start_ns=span.start_ns)
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
        layout.addWidget(self.plot_tool_bar)

        self.empty_state = EmptyStatePanel(container)
        self.empty_state.open_requested.connect(self.action("action_open").trigger)
        self.empty_state.simulation_requested.connect(self.action("action_load_simulation").trigger)

        self.dashboard = DashboardPanel(container)
        self.plot_panel = self.dashboard.time_series
        self.plot_panel.channel_dropped.connect(self._on_channel_dropped)
        self.plot_panel.time_region_changed.connect(self._on_stats_region_changed)
        self.plot_panel.cursor_moved.connect(self._on_cursor_moved)

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

    def _detach_active_repository(self) -> FileRecordingRepository | None:
        """Etkin kaydı kapatıp listelerden çıkarır; varsa sıradakini döner."""
        active = self._repository
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
        self.left_dock.clear()
        self.plot_tool_bar.set_channels([])
        self.right_dock.close_inspector()
        self.right_dock.bit_status.clear()
        self.plot_panel.clear()
        self._view_history.clear()
        self.dashboard.statistics.clear()
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

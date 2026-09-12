"""Data Explorer paneli — `F1-024`.

Mockup bölge 1 (`docs/ui/layout-map.md` §2): `Open .bin File` düğmesi, dosya
özeti, `Channels` / `Data Tree` sekmeleri, arama kutusu ve onay kutulu kanal
ağacı.

Panel açılabilir, kapanabilir ve taşınabilir; sabit `objectName` taşır çünkü
workspace kaydı buna dayanır.

Kanal ağacı **yalnız kaynakta bulunan** kanalları gösterir. Boş kayıtta sahte
kanal listesi üretilmez; bunun yerine boş durum metni görünür (plan Bölüm 5.2).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.ui.docks.recording_tree import (
    RecordingTreeNode,
    build_recording_tree,
    flatten_channel_ids,
)
from sonar_analyzer.ui.drag_drop import CHANNEL_MIME_TYPE, encode_channel_id
from sonar_analyzer.ui.status_icons import channel_source_style, make_status_icon
from sonar_analyzer.ui.theme import DARK

DOCK_OBJECT_NAME = "dock_data_explorer"
DOCK_TITLE = "Data Explorer"

EMPTY_VALUE = "—"
EMPTY_TREE_HINT = "Kanal yok. Bir .bin dosyasi acin."

#: "Data Tree" sekmesinde henuz genisletilmemis sensor grubunun tek cocugu — F3-010 lazy yukleme.
_LAZY_PLACEHOLDER_TEXT = "Yukleniyor..."

#: Dosya ozetinde gosterilen alanlar (mockup bolge 1).
SUMMARY_FIELDS = ("File", "Size", "Start", "Duration", "Platform")

#: Yol parcasi -> agacta gosterilecek etiket.
#:
#: Kanal yolunda "/" ayractir, bu yuzden bir parca adi "/" ICEREMEZ. Mockup'ta
#: grup "Vehicle / Transmission" yaziyor; yolda "Vehicle" tutulur ve gosterim
#: etiketi burada eslenir.
GROUP_LABELS = {"Vehicle": "Vehicle / Transmission"}

#: `F3-012` kategori filtresi düğmeleri — mockup'taki beş grup (plan Bölüm 5.2).
CATEGORIES: tuple[str, ...] = (
    "Sensors",
    "Acoustic",
    "Navigation",
    "Vehicle/Transmission",
    "BIT",
)

#: Düğme etiketinden ağaçtaki GERÇEK üst düzey etikete (`GROUP_LABELS` çevirisi
#: sonrası). `BIT` hiçbir gerçek düğüme karşılık gelmez — bkz. `_build_category_filter`.
_CATEGORY_TO_GROUP_LABEL = {
    "Sensors": "Sensors",
    "Acoustic": "Acoustic",
    "Navigation": "Navigation",
    "Vehicle/Transmission": "Vehicle / Transmission",
    "BIT": "BIT",
}

#: Düğme üzerinde gösterilen KISA metin; tam ad `toolTip`'tedir. Dar sol
#: sütuna (200 px) beş tam kelimeli düğme sığmıyordu — bkz. `_build_category_filter`.
_CATEGORY_BUTTON_TEXT = {
    "Sensors": "Sens",
    "Acoustic": "Aco",
    "Navigation": "Nav",
    "Vehicle/Transmission": "V/T",
    "BIT": "BIT",
}

#: Her kategori düğmesinin sabit genişliği (piksel); üç düğme bir satırda
#: (3 × 46 + boşluklar) 200 px sütuna sığar.
_CATEGORY_BUTTON_WIDTH = 46

#: `F3-018` kanal sağ tık menüsü eylemleri, menüde görünen sırayla.
#:
#: `Plot` grafiği o kanala çevirir, `Add to Existing Plot` var olan
#: serileri **koruyarak** ekler; ikisi aynı şey değildir ve tek bir
#: madde altında birleştirilemez. Sıra plan Bölüm 5.2 ve
#: `docs/ui/acceptance-checklist.md` 2.11 ile aynıdır.
CHANNEL_MENU_ACTIONS: tuple[str, ...] = (
    "Plot",
    "Inspect",
    "Add to Existing Plot",
    "Export",
    "Copy Path",
)


def _category_slug(category: str) -> str:
    return category.lower().replace("/", "_")


def _channel_search_haystack(channel: ChannelMetadata) -> str:
    """Ad, ID, birim, yol ve kaynağı tek küçük-harf metinde birleştirir — `F3-011`.

    Kabul kriteri: "her alan için bilinen eşleşme bulunur" — kullanıcı
    kanal adını, kimliğini (`ch0`), birimini (`bar`) ya da kaynağını
    (`sensors`) yazdığında da kanal bulunmalı; yalnız görünen etiket
    (ad + birim) ve yol yetmez, `channel.id` ve `channel.source` de dahil
    edilir.
    """
    parts = [channel.name, channel.id, channel.path, channel.source.value]
    if channel.unit:
        parts.append(channel.unit)
    return " ".join(parts).casefold()


def selected_channel_ids(tree: QTreeWidget) -> list[str]:
    """Ağaçtaki seçili **yaprak** kanal kimlikleri, ilk görülme sırasıyla — `F3-016`.

    Grup/kayıt/cihaz düğümleri (`UserRole` boş) atlanır; aynı kimlik iki
    kez sayılmaz. Toplu "grafiğe ekle" komutunun girdisidir.
    """
    ids: list[str] = []
    for item in tree.selectedItems():
        channel_id = item.data(0, Qt.ItemDataRole.UserRole)
        if channel_id and str(channel_id) not in ids:
            ids.append(str(channel_id))
    return ids


def _all_children_are_leaves(node: RecordingTreeNode) -> bool:
    """Bir düğümün tüm çocukları kanal yaprağı mı — `F3-010` lazy sınırı.

    Yalnız bu düğümler (sensör grupları) yer tutucuyla kurulur ve
    genişletilene kadar açılmaz; `Kayıt`/`Cihaz` gibi ara düzeyler her
    zaman gerçek çocuklarıyla ve açık başlar (sayıları zaten az).
    """
    return bool(node.children) and all(child.is_leaf for child in node.children)


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return EMPTY_VALUE
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return EMPTY_VALUE


def _format_start(timestamp_ns: int) -> str:
    """Başlangıç zamanını okunabilir UTC olarak gösterir.

    Ham nanosaniye kullanıcıya bir şey anlatmıyor; kayıt ankoru
    `docs/adr/ADR-003-time-base.md` gereği UTC epoch nanosaniyedir.
    """
    if timestamp_ns <= 0:
        return EMPTY_VALUE
    moment = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return EMPTY_VALUE
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class _DraggableChannelTree(QTreeWidget):
    """Kanal yapraklarını sürüklenebilir yapan `QTreeWidget` — `F3-015`.

    Qt'nin widget-tabanlı görünümleri (`QTreeWidget`/`QListWidget`) için
    belgelenen genişletme noktası `mimeData()`'dır: `setDragEnabled(True)`
    ile birlikte üzerine yazıldığında, temel sınıf sürüklemeyi otomatik
    başlatır — ayrıca bir `QDrag`/`startDrag()` kurmaya gerek yoktur.

    Yalnız kanal yaprakları (`UserRole` verisi dolu) geçerli MIME verisi
    üretir; grup/kayıt/cihaz düğümleri **boş** `QMimeData` döner — hedef
    (`PlotPanel`) `CHANNEL_MIME_TYPE` formatını bulamayınca bırakmayı
    reddeder (kabul kriterinin "geçerli kanal" şartı).
    """

    def mimeTypes(self) -> list[str]:
        return [CHANNEL_MIME_TYPE]

    def mimeData(self, items: list[QTreeWidgetItem]) -> QMimeData:  # type: ignore[override]
        mime = QMimeData()
        channel_id = items[0].data(0, Qt.ItemDataRole.UserRole) if items else None
        if channel_id:
            mime.setData(CHANNEL_MIME_TYPE, encode_channel_id(str(channel_id)))
        return mime


class DataExplorerDock(QDockWidget):
    """Sol sütundaki veri gezgini."""

    #: Kullanici bir kanali cift tikladi (veya sag tik > Plot).
    channel_activated = Signal(str)
    #: `F3-016`: coklu secimden "secilenleri grafige ekle" istendi (kanal kimlikleri).
    channels_add_requested = Signal(list)
    #: `F3-018`: sag tik > Inspect — kanalin Inspector'da gosterilmesi istendi.
    channel_inspect_requested = Signal(str)
    #: `F3-018`: sag tik > Copy Path — kanal yolu panoya kopyalandi (yol metni).
    channel_path_copied = Signal(str)
    #: Sag tik > Export — kanalin disa aktarilmasi istendi (kanal kimligi).
    channel_export_requested = Signal(str)
    #: `Open .bin File` tiklandi.
    open_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(DOCK_TITLE, parent)
        self.setObjectName(DOCK_OBJECT_NAME)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self._summary_labels: dict[str, QLabel] = {}
        self._channels: tuple[ChannelMetadata, ...] = ()
        self._recording_tree: tuple[RecordingTreeNode, ...] = ()
        #: Genisletilmemis sensor grubu -> henuz eklenmemis kanal dugumleri (F3-010).
        self._pending_children: dict[int, tuple[RecordingTreeNode, ...]] = {}
        #: Kapali kategoriler — agactaki GERCEK ust duzey etiket (F3-012).
        #: Bos = hicbiri kapali degil, hepsi gorunur.
        self._disabled_group_labels: set[str] = set()
        self.category_buttons: dict[str, QPushButton] = {}
        #: `F3-018`: en son açılan sağ tık menüsü — referans tutulmazsa
        #: PySide nesneyi serbest bırakır; testler de buradan tetikler.
        self.context_menu: QMenu | None = None

        self.setWidget(self._build_body())
        self.clear()

    # -- kurulum ---------------------------------------------------------

    def _build_body(self) -> QWidget:
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.open_button = QPushButton("Open .bin File", body)
        self.open_button.setObjectName("button_open_bin")
        self.open_button.setAccessibleName("Kayıt dosyası aç")  # F3-073
        self.open_button.setToolTip("Bir .bin kaydı aç (Ctrl+O)")
        self.open_button.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_button)

        layout.addWidget(self._build_summary(body))
        layout.addWidget(self._build_category_filter(body))

        self.tabs = QTabWidget(body)
        self.tabs.setObjectName("tabs_data_explorer")
        self.tabs.addTab(self._build_channels_tab(body), "Channels")
        self.tabs.addTab(self._build_tree_tab(body), "Data Tree")
        layout.addWidget(self.tabs, 1)

        return body

    def _build_category_filter(self, parent: QWidget) -> QWidget:
        """Kategori seçim düğmeleri — `F3-012`.

        Her iki sekmeyi de (Channels ve Data Tree) birlikte süzer: bir
        kategori kapatılınca o kategorinin üst düzey düğümü **her iki**
        ağaçta da gizlenir. `BIT` düğmesi şimdilik ağaçta karşılığı
        olmayan tek kategoridir (BIT, `ChannelMetadata` tabanlı bir kanal
        değildir — sağ paneldeki ayrı BIT Status kartından gelir, plan
        Bölüm 5.2/`F1-035`); yine de **etkin bir kontrol** olarak
        sunulur ve tıklanabilir — yalnızca eşleşen bir düğüm olmadığı
        için görünür bir etkisi yoktur, uydurma bir BIT düğümü icat
        edilmez.

        Düğmeler **kısaltılmış** metinle (tam ad `toolTip`'te) ve **sabit
        dar genişlikle** iki satıra bölünmüş kurulur: sol sütun 200 px
        (`LEFT_COLUMN_WIDTH`), beş tam kelimeli düğme tek satırda bu
        sınırı büyük farkla aşardı (`button_open_bin`'in `F1-034`'teki
        aynı sorunuyla aynı neden — bkz. `theme.py` yorumu).
        """
        container = QWidget(parent)
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        rows = (CATEGORIES[:3], CATEGORIES[3:])
        for row_categories in rows:
            row = QHBoxLayout()
            row.setSpacing(2)
            for category in row_categories:
                button = QPushButton(_CATEGORY_BUTTON_TEXT[category], container)
                button.setObjectName(f"button_category_{_category_slug(category)}")
                button.setToolTip(category)
                button.setCheckable(True)
                button.setChecked(True)
                button.setFixedWidth(_CATEGORY_BUTTON_WIDTH)
                button.toggled.connect(self._make_category_toggle_handler(category))
                self.category_buttons[category] = button
                row.addWidget(button)
            row.addStretch(1)
            outer.addLayout(row)

        return container

    def _build_summary(self, parent: QWidget) -> QWidget:
        container = QGroupBox("Recording", parent)
        container.setObjectName("card_file_summary")
        form = QFormLayout(container)
        form.setContentsMargins(6, 4, 6, 4)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        for field in SUMMARY_FIELDS:
            value = QLabel(EMPTY_VALUE, container)
            value.setObjectName(f"label_summary_{field.lower()}")
            value.setWordWrap(True)
            value.setMinimumWidth(1)
            self._summary_labels[field] = value
            form.addRow(f"{field}:", value)

        return container

    def _build_channels_tab(self, parent: QWidget) -> QWidget:
        page = QWidget(parent)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)

        self.search = QLineEdit(page)
        self.search.setObjectName("input_channel_search")
        self.search.setPlaceholderText("Search...")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Kanal ara")  # F3-073
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.tree = _DraggableChannelTree(page)
        self.tree.setObjectName("tree_channels")
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setAccessibleName("Kanal ağacı")  # F3-073
        self.tree.setAccessibleDescription(
            "Enter: kanalı grafiğe çiz. Ok tuşları: gezin. F2 çevresi: bağlam menüsü."
        )
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # F3-073: çift tık VE Enter kanalı etkinleştirir (yalnız klavye akışı).
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemActivated.connect(self._on_item_double_clicked)
        # F3-015: kanal yapraklari PlotPanel'e suruklenebilir; agac disari
        # bir seyi kabul ETMEZ (yalniz kaynak).
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        # F3-016: birden fazla kanal secilip tek komutla grafige eklenebilir.
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemSelectionChanged.connect(self._refresh_add_selected_enabled)
        # F3-018: kanal yapraginda sag tik menusu (Plot / Inspect / Copy Path).
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu_handler(self.tree))
        layout.addWidget(self.tree, 1)

        self.add_selected_button = QPushButton("Grafige Ekle", page)
        self.add_selected_button.setObjectName("button_add_selected_channels")
        self.add_selected_button.setToolTip("Secili kanallari ayni grafige ekle")
        self.add_selected_button.setEnabled(False)
        self.add_selected_button.clicked.connect(lambda: self._emit_add_selected(self.tree))
        layout.addWidget(self.add_selected_button)

        self.empty_hint = QLabel(EMPTY_TREE_HINT, page)
        self.empty_hint.setObjectName("label_empty_channels")
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setMinimumWidth(1)
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_hint)

        return page

    def _build_tree_tab(self, parent: QWidget) -> QWidget:
        """Kayıt › Cihaz › Sensör grubu › Kanal ağacı — `F3-009`.

        "Channels" sekmesi kanal **yolundan** ağaç kurar; bu sekme **hangi
        kayıttan/cihazdan** geldiğini gösterir. Birden fazla dosya açıkken
        (`F2-036`) bu ayrım Channels sekmesinde görünmez.
        """
        page = QWidget(parent)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)

        self.data_tree = _DraggableChannelTree(page)
        self.data_tree.setObjectName("tree_data_tree")
        self.data_tree.setHeaderHidden(True)
        self.data_tree.setColumnCount(1)
        header = self.data_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_tree.itemDoubleClicked.connect(self._on_data_tree_item_double_clicked)
        self.data_tree.itemExpanded.connect(self._on_data_tree_item_expanded)
        self.data_tree.setDragEnabled(True)
        self.data_tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        # F3-016: bu sekmede de coklu secim + tek komutla ekleme.
        self.data_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.data_tree.itemSelectionChanged.connect(self._refresh_add_selected_enabled)
        # F3-018: bu sekmede de kanal sag tik menusu.
        self.data_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_tree.customContextMenuRequested.connect(
            self._context_menu_handler(self.data_tree)
        )
        layout.addWidget(self.data_tree, 1)

        self.add_selected_data_tree_button = QPushButton("Grafige Ekle", page)
        self.add_selected_data_tree_button.setObjectName("button_add_selected_data_tree")
        self.add_selected_data_tree_button.setToolTip("Secili kanallari ayni grafige ekle")
        self.add_selected_data_tree_button.setEnabled(False)
        self.add_selected_data_tree_button.clicked.connect(
            lambda: self._emit_add_selected(self.data_tree)
        )
        layout.addWidget(self.add_selected_data_tree_button)

        self.data_tree_empty_hint = QLabel(EMPTY_TREE_HINT, page)
        self.data_tree_empty_hint.setObjectName("label_empty_data_tree")
        self.data_tree_empty_hint.setWordWrap(True)
        self.data_tree_empty_hint.setMinimumWidth(1)
        self.data_tree_empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.data_tree_empty_hint)

        return page

    # -- veri ------------------------------------------------------------

    def clear(self) -> None:
        """Paneli kayıt açılmamış duruma döndürür."""
        for label in self._summary_labels.values():
            label.setText(EMPTY_VALUE)
        self._channels = ()
        self.tree.clear()
        self.empty_hint.setText(EMPTY_TREE_HINT)
        self.empty_hint.setVisible(True)
        self.set_recordings([])
        self._refresh_add_selected_enabled()

    def set_recording(
        self,
        metadata: RecordingMetadata,
        channels: Sequence[ChannelMetadata],
    ) -> None:
        """Dosya özetini ve **etkin** kaydın kanal ağacını (Channels sekmesi) doldurur.

        "Data Tree" sekmesi ayrıdır — açık tüm kayıtları gösterir, bkz.
        `set_recordings()`.
        """
        self._summary_labels["File"].setText(metadata.source_path or EMPTY_VALUE)
        self._summary_labels["Size"].setText(_format_size(metadata.file_size_bytes))
        self._summary_labels["Start"].setText(_format_start(metadata.start_ns))
        self._summary_labels["Duration"].setText(_format_duration(metadata.duration_seconds))
        self._summary_labels["Platform"].setText(metadata.device_id or EMPTY_VALUE)

        self._channels = tuple(channels)
        self._rebuild_tree()

    def set_recordings(
        self, recordings: Sequence[tuple[RecordingMetadata, Sequence[ChannelMetadata]]]
    ) -> None:
        """ "Data Tree" sekmesini **açık tüm kayıtlardan** kurar — `F3-009`.

        Kabul kriteri: kayıt, cihaz, sensör ve kanal hiyerarşisi doğru
        görünür. Boş liste (hiç kayıt açık değil) ağacı temizler.

        Kanal yaprakları **lazy** yüklenir (`F3-010`): sensör grubu düğümü
        gerçek kanal öğeleri yerine tek bir yer tutucuyla kurulur, gerçek
        öğeler yalnız grup ilk genişletildiğinde eklenir. Kayıt/cihaz/grup
        sayısı her zaman azdır (birkaç dosya, birkaç grup) — asıl maliyet
        binlerce kanal olabilecek yaprak düzeyindedir; `QTreeWidgetItem`
        kurulumu orada ertelenir.
        """
        self._recording_tree = build_recording_tree(recordings)
        self.data_tree.clear()
        self._pending_children.clear()
        for recording_node in self._recording_tree:
            item = self._add_lazy_node(None, recording_node)
            item.setExpanded(True)
        self.data_tree_empty_hint.setVisible(not recordings)
        self._apply_category_filter_to_data_tree()

    def _add_lazy_node(
        self, parent: QTreeWidgetItem | None, node: RecordingTreeNode
    ) -> QTreeWidgetItem:
        """Bir düğümü kurar; kanal yapraklarının **doğrudan** atasında durur.

        O düğüme tek bir yer tutucu çocuk eklenir (genişletme oku
        görünsün diye) ve gerçek kanallar `_pending_children`'da saklanır;
        `_on_data_tree_item_expanded` ilk genişletmede materyalize eder.
        """
        item = self._new_data_tree_item(parent, node.label)
        if node.is_leaf:
            item.setData(0, Qt.ItemDataRole.UserRole, node.channel_id)
            channel = next((c for c in self._channels if c.id == node.channel_id), None)
            if channel is not None:
                self._decorate_channel_item(item, channel)
            return item

        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        if _all_children_are_leaves(node):
            placeholder = self._new_data_tree_item(item, _LAZY_PLACEHOLDER_TEXT)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._pending_children[id(item)] = node.children
            return item

        for child in node.children:
            child_item = self._add_lazy_node(item, child)
            if not child.is_leaf and not _all_children_are_leaves(child):
                # Cocuk kendisi Kayit/Cihaz gibi bir ara duzeyse acik
                # baslar. Sensor grubu gibi cocuklari TAMAMEN yapraksa
                # genisletilmez -- bu tam olarak lazy sinirdir; onu burada
                # da acarsak setExpanded() itemExpanded'i hemen tetikler
                # ve yer tutucu aninda gercek binlerce yaprakla degisir.
                child_item.setExpanded(True)
        return item

    def _on_data_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Sensör grubu ilk genişletildiğinde yer tutucuyu gerçek kanallarla değiştirir."""
        pending = self._pending_children.pop(id(item), None)
        if pending is None:
            return
        item.takeChildren()
        for channel_node in pending:
            self._add_lazy_node(item, channel_node)

    def _new_data_tree_item(self, parent: QTreeWidgetItem | None, label: str) -> QTreeWidgetItem:
        if parent is None:
            return QTreeWidgetItem(self.data_tree, [label])
        return QTreeWidgetItem(parent, [label])

    def data_tree_channel_ids(self) -> list[str]:
        """ "Data Tree" sekmesindeki tüm kanal kimlikleri (testler için).

        Modelden okunur — lazy yükleme, ağaçta o an materyalize edilmiş
        `QTreeWidgetItem` sayısından bağımsızdır.
        """
        return flatten_channel_ids(self._recording_tree)

    def summary_value(self, field: str) -> str:
        """Özet alanının gösterilen değeri — testler ve kabul için."""
        try:
            return self._summary_labels[field].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz ozet alani: {field}") from exc

    def group_labels(self) -> list[str]:
        """Ağacın en üst düzeyindeki grup etiketleri."""
        labels: list[str] = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item is not None:
                labels.append(item.text(0))
        return labels

    def visible_channel_ids(self) -> list[str]:
        """Ağaçta o an görünen kanal kimlikleri."""
        return [channel_id for leaf, channel_id in self._channel_leaves() if self._is_visible(leaf)]

    def checked_channel_ids(self) -> list[str]:
        """İşaretli kanal kimlikleri."""
        return [
            channel_id
            for leaf, channel_id in self._channel_leaves()
            if leaf.checkState(0) == Qt.CheckState.Checked
        ]

    def item_for_channel(self, channel_id: str) -> QTreeWidgetItem | None:
        """Kanal kimliğine karşılık gelen ağaç öğesi."""
        for leaf, found_id in self._channel_leaves():
            if found_id == channel_id:
                return leaf
        return None

    # -- ic yardimcilar --------------------------------------------------

    def _rebuild_tree(self) -> None:
        """Kanal yollarından mockup'taki iç içe ağacı kurar.

        `Sensors/Accelerometer/X` üç düzey üretir: Sensors > Accelerometer > X.
        Ara düğümler yol parçasından, yaprak ise kanal adı ve biriminden gelir.
        """
        self.tree.clear()
        nodes: dict[str, QTreeWidgetItem] = {}

        for channel in self._channels:
            segments = [part for part in channel.path.split("/") if part]
            parent: QTreeWidgetItem | None = None
            prefix = ""

            for segment in segments[:-1]:
                prefix = f"{prefix}/{segment}" if prefix else segment
                node = nodes.get(prefix)
                if node is None:
                    label = GROUP_LABELS.get(segment, segment)
                    node = self._new_item(parent, label)
                    node.setFlags(node.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    nodes[prefix] = node
                parent = node

            leaf = self._new_item(parent, channel.display_label)
            leaf.setData(0, Qt.ItemDataRole.UserRole, channel.id)
            leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            leaf.setCheckState(0, Qt.CheckState.Unchecked)
            self._decorate_channel_item(leaf, channel)

        self.tree.expandAll()
        self.empty_hint.setVisible(not self._channels)
        self._apply_filter(self.search.text())

    def _new_item(self, parent: QTreeWidgetItem | None, label: str) -> QTreeWidgetItem:
        if parent is None:
            return QTreeWidgetItem(self.tree, [label])
        return QTreeWidgetItem(parent, [label])

    def _channel_leaves(self) -> list[tuple[QTreeWidgetItem, str]]:
        """Kanal kimliği taşıyan tüm yapraklar (derinlikten bağımsız)."""
        found: list[tuple[QTreeWidgetItem, str]] = []

        def walk(item: QTreeWidgetItem) -> None:
            channel_id = item.data(0, Qt.ItemDataRole.UserRole)
            if channel_id:
                found.append((item, str(channel_id)))
            for index in range(item.childCount()):
                child = item.child(index)
                if child is not None:
                    walk(child)

        for index in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(index)
            if top is not None:
                walk(top)
        return found

    @staticmethod
    def _is_visible(item: QTreeWidgetItem) -> bool:
        """Öğe ve tüm ataları görünür mü?

        Üst düzey öğede `parent()` gerçekten `None` döner; PySide taslakları
        bunu bazı sürümlerde opsiyonel saymasa da kontrol korunur.
        """
        node: QTreeWidgetItem | None = item
        while node is not None:
            if node.isHidden():
                return False
            node = node.parent()
        return True

    def _apply_filter(self, text: str) -> None:
        """Yaprakları ad, ID, birim ve kaynağa göre süzer — `F3-011`.

        Kabul: her alan için bilinen eşleşme bulunur; temizleme (`text`
        boş) tüm kanalları getirir — `needle` boşsa her yaprak eşleşir,
        bu davranış aşağıda zaten korunur.
        """
        needle = text.strip().casefold()
        channel_by_id = {channel.id: channel for channel in self._channels}

        def prune(item: QTreeWidgetItem) -> bool:
            if item.childCount() == 0:
                channel_id = item.data(0, Qt.ItemDataRole.UserRole)
                channel = channel_by_id.get(str(channel_id)) if channel_id else None
                haystack = (
                    _channel_search_haystack(channel)
                    if channel is not None
                    else f"{item.text(0)} {item.toolTip(0)}".casefold()
                )
                matches = not needle or needle in haystack
                item.setHidden(not matches)
                return matches

            any_visible = False
            for index in range(item.childCount()):
                child = item.child(index)
                if child is not None and prune(child):
                    any_visible = True
            item.setHidden(not any_visible)
            return any_visible

        for index in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(index)
            if top is None:
                continue
            if top.text(0) in self._disabled_group_labels:
                # F3-012: kapali kategori tum alt agaciyla gizlenir, metin
                # eslesmesi hic hesaplanmaz.
                top.setHidden(True)
                continue
            prune(top)

        if self._channels:
            nothing_found = not self.visible_channel_ids()
            self.empty_hint.setText(
                f"'{text}' ile eslesen kanal yok." if nothing_found else EMPTY_TREE_HINT
            )
            self.empty_hint.setVisible(nothing_found)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        channel_id = item.data(0, Qt.ItemDataRole.UserRole)
        if channel_id:
            self.channel_activated.emit(str(channel_id))

    def _on_data_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        channel_id = item.data(0, Qt.ItemDataRole.UserRole)
        if channel_id:
            self.channel_activated.emit(str(channel_id))

    # -- kanal sag tik menusu (F3-018) ---------------------------------

    def _context_menu_handler(self, tree: QTreeWidget) -> Callable[[QPoint], None]:
        """`QPoint -> None` imzalı tam tipli geri çağrı — pyright, sinyal
        taslağından `pos` tipini çıkaramıyor (bkz. `_make_category_toggle_handler`)."""

        def handler(pos: QPoint) -> None:
            self._show_channel_menu(tree, pos)

        return handler

    def _show_channel_menu(self, tree: QTreeWidget, pos: QPoint) -> None:
        """Sağ tıklanan **kanal yaprağı** için Plot / Inspect / Copy Path menüsü.

        Menü, imlecin ALTINDAKİ öğeye bağlanır (`itemAt`), o an *seçili*
        olana değil — "doğru seçime uygulanır" kabul kriteri. Grup/kayıt/
        cihaz düğümünde (UserRole boş) menü açılmaz. `exec()` yerine
        `popup()`: modal değil, testleri kilitlemez.
        """
        item = tree.itemAt(pos)
        channel_id = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if not channel_id:
            return

        menu = QMenu(tree)
        for label in CHANNEL_MENU_ACTIONS:
            menu.addAction(label).triggered.connect(
                self._channel_menu_handler(str(channel_id), label)
            )
        self.context_menu = menu
        menu.popup(tree.viewport().mapToGlobal(pos))

    def _channel_menu_handler(self, channel_id: str, action: str) -> Callable[[bool], None]:
        """`bool -> None` imzalı tam tipli geri çağrı (bkz. `_make_category_toggle_handler`)."""

        def handler(_checked: bool = False) -> None:
            self.apply_channel_context_action(channel_id, action)

        return handler

    def apply_channel_context_action(self, channel_id: str, action: str) -> None:
        """Bir sağ tık eylemini kanala uygular — `F3-018`.

        Menü ve testler aynı yolu kullanır; `action` `CHANNEL_MENU_ACTIONS`
        içinden gelmelidir.
        """
        if action == "Plot":
            self.channel_activated.emit(channel_id)
        elif action == "Add to Existing Plot":
            # Coklu secimle ayni yol: var olan seriler korunur.
            self.channels_add_requested.emit([channel_id])
        elif action == "Inspect":
            self.channel_inspect_requested.emit(channel_id)
        elif action == "Export":
            self.channel_export_requested.emit(channel_id)
        elif action == "Copy Path":
            self._copy_channel_path(channel_id)
        else:
            raise ValueError(f"Bilinmeyen kanal eylemi: {action!r}")

    # -- kanal ikonlari (plan Bolum 5.2) -------------------------------

    def _decorate_channel_item(self, item: QTreeWidgetItem, channel: ChannelMetadata) -> None:
        """Kanal yaprağına tür ikonu ve açıklayıcı ipucu koyar.

        İkon **yalnız renk değil**, bir de simge taşır (`status_icons`):
        renk körlüğünde ve gri tonlamalı ekran görüntüsünde renge dayalı
        bir ayrım kaybolurdu (plan Bölüm 6.4).

        İpucu kanalın yolunu, türünü ve kaynakta bulunup bulunmadığını
        yazar; "bağlantı durumu" burada **veri kaynağındaki varlıktır**:
        kayıtta karşılığı olmayan bir kanal seçilemez ve nedeni görünür
        olmalıdır.
        """
        style = channel_source_style(channel.source)
        item.setIcon(0, make_status_icon(style))

        available = channel.id in self._available_channel_ids
        state = "kaynakta var" if available else "kaynakta yok"
        item.setToolTip(0, f"{channel.path}\n{style.describe()} · {state}")
        if not available:
            # F3-013 kabulu: olmayan kanal secilemez ve sahte veriyle cizilmez.
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(0, QColor(DARK.text_secondary))

    @property
    def _available_channel_ids(self) -> set[str]:
        """Kaynakta gerçekten bulunan kanal kimlikleri."""
        return {channel.id for channel in self._channels}

    def _copy_channel_path(self, channel_id: str) -> None:
        channel = next((c for c in self._channels if c.id == channel_id), None)
        if channel is None:
            return
        QGuiApplication.clipboard().setText(channel.path)
        self.channel_path_copied.emit(channel.path)

    # -- coklu secim: secilenleri grafige ekle (F3-016) -----------------

    def _emit_add_selected(self, tree: QTreeWidget) -> None:
        channel_ids = selected_channel_ids(tree)
        if channel_ids:
            self.channels_add_requested.emit(channel_ids)

    def _refresh_add_selected_enabled(self) -> None:
        """ "Grafige Ekle" düğmeleri yalnız ilgili ağaçta yaprak seçiliyken etkin."""
        self.add_selected_button.setEnabled(bool(selected_channel_ids(self.tree)))
        self.add_selected_data_tree_button.setEnabled(bool(selected_channel_ids(self.data_tree)))

    # -- kategori filtreleri (F3-012) -------------------------------------

    def _make_category_toggle_handler(self, category: str) -> Callable[[bool], None]:
        """`category` değerini kapatan tam tipli bir geri çağrı üretir.

        `lambda checked, name=category: ...` yerine — pyright, PySide
        sinyalinin taslağında parametre tipini çıkaramadığı için lambda'yı
        `Unknown` sayardı; bu fabrika `bool -> None` imzasını açıkça verir.
        """

        def handler(checked: bool) -> None:
            self._on_category_toggled(category, checked=checked)

        return handler

    def _on_category_toggled(self, category: str, checked: bool) -> None:
        """Bir kategori düğmesi değiştiğinde her iki ağacı da yeniden süzer.

        `BIT` için `_CATEGORY_TO_GROUP_LABEL` hiçbir gerçek düğüme karşılık
        gelmez; bu yüzden bu kategori değiştiğinde ağaçlarda gözle görülür
        bir değişiklik olmaz — düğme yine de doğru şekilde işaretlenir/
        işareti kaldırılır (kabul: "BIT seçimleri doğru çalışır").
        """
        group_label = _CATEGORY_TO_GROUP_LABEL[category]
        if checked:
            self._disabled_group_labels.discard(group_label)
        else:
            self._disabled_group_labels.add(group_label)
        self._apply_filter(self.search.text())
        self._apply_category_filter_to_data_tree()

    def _apply_category_filter_to_data_tree(self) -> None:
        """ "Data Tree" sekmesinde kapalı kategorilerin düğümlerini gizler.

        Kayıt/cihaz düğümleri gerçek bir kategori adıyla asla eşleşmediği
        için (dosya adı, cihaz kimliği) yalnızca sensör grubu düzeyi
        etkilenir; lazy yükleme (`F3-010`) bundan bağımsızdır — gizlemek
        henüz materyalize edilmemiş bir grubu genişletmez.
        """

        def walk(item: QTreeWidgetItem) -> None:
            item.setHidden(item.text(0) in self._disabled_group_labels)
            for index in range(item.childCount()):
                child = item.child(index)
                if child is not None:
                    walk(child)

        for index in range(self.data_tree.topLevelItemCount()):
            top = self.data_tree.topLevelItem(index)
            if top is not None:
                walk(top)

    def enabled_categories(self) -> set[str]:
        """Şu anda seçili (görünür) kategori adları — testler için."""
        return {category for category in CATEGORIES if self.category_buttons[category].isChecked()}

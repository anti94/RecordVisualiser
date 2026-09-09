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

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata

DOCK_OBJECT_NAME = "dock_data_explorer"
DOCK_TITLE = "Data Explorer"

EMPTY_VALUE = "—"
EMPTY_TREE_HINT = "Kanal yok. Bir .bin dosyasi acin."

#: Dosya ozetinde gosterilen alanlar (mockup bolge 1).
SUMMARY_FIELDS = ("File", "Size", "Start", "Duration", "Platform")

#: Yol parcasi -> agacta gosterilecek etiket.
#:
#: Kanal yolunda "/" ayractir, bu yuzden bir parca adi "/" ICEREMEZ. Mockup'ta
#: grup "Vehicle / Transmission" yaziyor; yolda "Vehicle" tutulur ve gosterim
#: etiketi burada eslenir.
GROUP_LABELS = {"Vehicle": "Vehicle / Transmission"}


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


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return EMPTY_VALUE
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class DataExplorerDock(QDockWidget):
    """Sol sütundaki veri gezgini."""

    #: Kullanici bir kanali cift tikladi.
    channel_activated = Signal(str)
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

        self.setWidget(self._build_body())
        self.clear()

    # -- kurulum ---------------------------------------------------------

    def _build_body(self) -> QWidget:
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.open_button = QPushButton("Open .bin File", body)
        self.open_button.setObjectName("button_open_bin")
        self.open_button.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_button)

        layout.addWidget(self._build_summary(body))

        self.tabs = QTabWidget(body)
        self.tabs.setObjectName("tabs_data_explorer")
        self.tabs.addTab(self._build_channels_tab(body), "Channels")
        self.tabs.addTab(self._build_tree_tab(body), "Data Tree")
        layout.addWidget(self.tabs, 1)

        return body

    def _build_summary(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        form = QFormLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
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
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.tree = QTreeWidget(page)
        self.tree.setObjectName("tree_channels")
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, 1)

        self.empty_hint = QLabel(EMPTY_TREE_HINT, page)
        self.empty_hint.setObjectName("label_empty_channels")
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setMinimumWidth(1)
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_hint)

        return page

    def _build_tree_tab(self, parent: QWidget) -> QWidget:
        page = QWidget(parent)
        layout = QVBoxLayout(page)
        note = QLabel(
            "Data Tree, Channels ile ayni kanal modelini kullanir; "
            "ayri agac gorunumu sonraki iste eklenecek.",
            page,
        )
        note.setWordWrap(True)
        note.setMinimumWidth(1)
        layout.addWidget(note)
        layout.addStretch(1)
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

    def set_recording(
        self,
        metadata: RecordingMetadata,
        channels: Sequence[ChannelMetadata],
    ) -> None:
        """Dosya özetini ve kanal ağacını açılan kayıttan doldurur."""
        self._summary_labels["File"].setText(metadata.source_path or EMPTY_VALUE)
        self._summary_labels["Size"].setText(_format_size(metadata.file_size_bytes))
        self._summary_labels["Start"].setText(str(metadata.start_ns))
        self._summary_labels["Duration"].setText(_format_duration(metadata.duration_seconds))
        self._summary_labels["Platform"].setText(metadata.device_id or EMPTY_VALUE)

        self._channels = tuple(channels)
        self._rebuild_tree()

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
            leaf.setToolTip(0, channel.path)

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
        """Yaprakları süzer; altında görünen yaprak kalmayan grubu gizler."""
        needle = text.strip().casefold()

        def prune(item: QTreeWidgetItem) -> bool:
            if item.childCount() == 0:
                haystack = f"{item.text(0)} {item.toolTip(0)}".casefold()
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
            if top is not None:
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

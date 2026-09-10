"""Alt panel: Log / Messages ve Events — `F1-026`.

Mockup bölge 8 (`docs/ui/layout-map.md` §5). İkisi **aynı alanda ayrı
sekmelerdir**:

* `Log / Messages` — zaman damgalı işlem ve hata satırları.
* `Events` — olayların ayrıntılı tablosu.

Plan Bölüm 5.5: olayların ayrıntılı tablosu Log değil, ayrı `Events`
sekmesidir; ikisi karıştırılmaz. Log serbest metin, Events yapısal veridir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import (
    EVENT_COLUMNS,
    EventGroup,
    distinct_sources,
    event_cell_text,
    filter_events,
    group_near_events,
)
from sonar_analyzer.ui.status_icons import make_status_icon, severity_style

#: `F3-043` severity açılır kutusu: etiket -> alt sınır (`None` = hepsi).
_SEVERITY_CHOICES: tuple[tuple[str, Severity | None], ...] = (
    ("All severities", None),
    ("Info+", Severity.INFO),
    ("Warning+", Severity.WARNING),
    ("Error+", Severity.ERROR),
    ("Critical", Severity.CRITICAL),
)
_ALL_SOURCES = "All sources"

DOCK_OBJECT_NAME = "dock_bottom_panel"
DOCK_TITLE = "Log / Events"

LOG_TAB_TITLE = "Log / Messages"
EVENTS_TAB_TITLE = "Events"

#: Log'da tutulan azami satir sayisi; uzun oturumda bellek sinirsiz buyumez.
MAX_LOG_LINES = 2000

#: `F3-053` bir log satirinin azami uzunlugu. Log **durum mesajlari**
#: icindir; ham payload / uzun döküntü buraya düşerse kesilir.
MAX_LOG_MESSAGE_LEN = 500
_LOG_TRUNCATION_SUFFIX = "… (kesildi)"


def sanitize_log_message(message: str) -> str:
    """Log satırını tek satıra indirger ve `MAX_LOG_MESSAGE_LEN`'e kırpar — `F3-053`.

    Satır sonları/sekmeler boşluğa çevrilir, diğer kontrol karakterleri
    atılır (ham ikili payload log widget'ını bozmasın). Uzun metin
    kesilir: log serbest metin değil, **durum mesajı** alanıdır.
    """
    flattened = "".join(
        " " if char in "\r\n\t" else char for char in message if char >= " " or char in "\r\n\t"
    )
    collapsed = " ".join(flattened.split())
    if len(collapsed) > MAX_LOG_MESSAGE_LEN:
        keep = MAX_LOG_MESSAGE_LEN - len(_LOG_TRUNCATION_SUFFIX)
        return collapsed[:keep] + _LOG_TRUNCATION_SUFFIX
    return collapsed


def format_timestamp(timestamp_ns: int) -> str:
    """Nanosaniye zamanı `HH:MM:SS.mmm` biçiminde gösterir."""
    seconds, remainder = divmod(timestamp_ns, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return f"{moment.strftime('%H:%M:%S')}.{remainder // 1_000_000:03d}"


class BottomPanelDock(QDockWidget):
    """Merkez grafiklerin altındaki log ve olay alanı."""

    #: `F3-044` Events tablosunda bir satır seçildi (`Event`); seçim
    #: kalkınca `None` yayılır.
    event_selected = Signal(object)
    #: `F3-046` Events tablosunda bir satıra çift tıklandı (`Event`) —
    #: senkronize grafikler bu olayın zamanına gider.
    event_activated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(DOCK_TITLE, parent)
        self.setObjectName(DOCK_OBJECT_NAME)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("tabs_bottom_panel")
        self.tabs.addTab(self._build_log(), LOG_TAB_TITLE)
        self.tabs.addTab(self._build_events(), EVENTS_TAB_TITLE)
        self.setWidget(self.tabs)

    # -- kurulum ---------------------------------------------------------

    def _build_log(self) -> QWidget:
        self.log = QPlainTextEdit(self)
        self.log.setObjectName("text_log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(MAX_LOG_LINES)
        self.log.setPlaceholderText("Islem gecmisi burada gorunur.")
        return self.log

    def _build_events(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._build_event_filters(page))

        self.events = QTableWidget(0, len(EVENT_COLUMNS), page)
        self.events.setObjectName("table_events")
        self.events.setHorizontalHeaderLabels(list(EVENT_COLUMNS))
        self.events.verticalHeader().setVisible(False)
        self.events.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.events.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.events.horizontalHeader().setSectionResizeMode(
            len(EVENT_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        self.events.itemSelectionChanged.connect(self._on_event_row_selected)
        self.events.itemDoubleClicked.connect(self._on_event_row_activated)
        layout.addWidget(self.events, 1)

        # F3-043: filtre öncesi ham olaylar ve göreli-zaman ankoru.
        self._all_events: tuple[Event, ...] = ()
        self._events_start_ns = 0
        self._suppress_filter_refresh = False
        # F3-049: satır -> (tür, olay); tür "event" | "group" | "member".
        self._row_kinds: list[str] = []
        self._row_events: list[Event] = []
        self._row_group_index: list[int | None] = []
        self._row_groups: list[EventGroup] = []
        self._expanded_groups: set[int] = set()
        return page

    def _on_event_row_selected(self) -> None:
        row = self.events.currentRow()
        event = self._row_events[row] if 0 <= row < len(self._row_events) else None
        self.event_selected.emit(event)

    def _on_event_row_activated(self, item: object) -> None:
        del item
        row = self.events.currentRow()
        if not (0 <= row < len(self._row_events)):
            return
        if self._row_kinds[row] == "group":
            # F3-049: grup başlığına çift tıklama açar/kapatır — özgün
            # olayları alt satır olarak gösterir/gizler.
            group_index = self._group_index_for_row(row)
            if group_index is not None:
                self._expanded_groups ^= {group_index}
                self._render_grouped()
            return
        self.event_activated.emit(self._row_events[row])

    def selected_event(self) -> Event | None:
        """Şu an seçili olay; seçim yoksa `None` — `F3-044`."""
        row = self.events.currentRow()
        if 0 <= row < len(self._row_events):
            return self._row_events[row]
        return None

    def _build_event_filters(self, parent: QWidget) -> QWidget:
        """`F3-043` zaman + severity + kaynak + metin filtre çubuğu."""
        bar = QWidget(parent)
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(4)

        self.event_source_filter = QComboBox(bar)
        self.event_source_filter.setObjectName("combo_event_source_filter")
        self.event_source_filter.addItem(_ALL_SOURCES)
        self.event_source_filter.currentIndexChanged.connect(self._apply_event_filters)
        row.addWidget(self.event_source_filter)

        self.event_severity_filter = QComboBox(bar)
        self.event_severity_filter.setObjectName("combo_event_severity_filter")
        for label, _level in _SEVERITY_CHOICES:
            self.event_severity_filter.addItem(label)
        self.event_severity_filter.currentIndexChanged.connect(self._apply_event_filters)
        row.addWidget(self.event_severity_filter)

        row.addWidget(QLabel("t≥", bar))
        self.event_time_from = self._make_time_spin(bar, "spin_event_time_from")
        row.addWidget(self.event_time_from)
        row.addWidget(QLabel("t≤", bar))
        self.event_time_to = self._make_time_spin(bar, "spin_event_time_to")
        row.addWidget(self.event_time_to)

        self.event_text_filter = QLineEdit(bar)
        self.event_text_filter.setObjectName("input_event_text_filter")
        self.event_text_filter.setPlaceholderText("Message contains…")
        self.event_text_filter.setClearButtonEnabled(True)
        self.event_text_filter.textChanged.connect(self._apply_event_filters)
        row.addWidget(self.event_text_filter, 1)

        self.event_group_check = QCheckBox("Group repeats", bar)
        self.event_group_check.setObjectName("check_event_group_repeats")
        self.event_group_check.toggled.connect(self._apply_event_filters)
        row.addWidget(self.event_group_check)
        return bar

    def _make_time_spin(self, parent: QWidget, name: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(parent)
        spin.setObjectName(name)
        spin.setDecimals(3)
        spin.setRange(0.0, 0.0)
        spin.setSuffix(" s")
        spin.valueChanged.connect(self._apply_event_filters)
        return spin

    # -- log -------------------------------------------------------------

    def append_log(self, message: str, timestamp: datetime | None = None) -> None:
        """Log'a **zaman damgalı** bir durum satırı ekler — `F3-053`.

        Mesaj tek satıra indirgenip kırpılır: log durum mesajı içindir,
        ham payload buraya düşmez.
        """
        moment = timestamp or datetime.now()
        self.log.appendPlainText(f"[{moment.strftime('%H:%M:%S')}] {sanitize_log_message(message)}")

    def log_lines(self) -> list[str]:
        text = self.log.toPlainText()
        return text.splitlines() if text else []

    def clear_log(self) -> None:
        self.log.clear()

    # -- olaylar ---------------------------------------------------------

    def set_events(self, events: Sequence[Event], start_ns: int = 0) -> None:
        """Ham olay kümesini alır, filtre kontrollerini kurar ve tabloyu çizer.

        Sütunlar plan Bölüm 5.5'e göre ortak `event_table_model`'den gelir
        (`F3-042`). Filtre çubuğu (`F3-043`) bu tam kümenin üstüne uygulanır.
        `start_ns` göreli zaman içindir.
        """
        self._all_events = tuple(events)
        self._events_start_ns = start_ns
        self._suppress_filter_refresh = True
        try:
            self._populate_source_filter()
            self._set_time_filter_bounds()
        finally:
            self._suppress_filter_refresh = False
        self._apply_event_filters()

    def _populate_source_filter(self) -> None:
        self.event_source_filter.clear()
        self.event_source_filter.addItem(_ALL_SOURCES)
        for source in distinct_sources(self._all_events):
            self.event_source_filter.addItem(source)

    def _set_time_filter_bounds(self) -> None:
        if not self._all_events:
            span = 0.0
        else:
            latest = max(e.timestamp_ns for e in self._all_events)
            span = max(0.0, (latest - self._events_start_ns) / 1_000_000_000)
        for spin, value in ((self.event_time_from, 0.0), (self.event_time_to, span)):
            spin.setRange(0.0, span)
            spin.setValue(value)

    def _current_event_filters(self) -> dict[str, object]:
        source = self.event_source_filter.currentText()
        _label, min_severity = _SEVERITY_CHOICES[self.event_severity_filter.currentIndex()]
        return {
            "start_ns": self._events_start_ns + round(self.event_time_from.value() * 1_000_000_000),
            "end_ns": self._events_start_ns + round(self.event_time_to.value() * 1_000_000_000),
            "min_severity": min_severity,
            "source": "" if source == _ALL_SOURCES else source,
            "text": self.event_text_filter.text().strip(),
        }

    def _apply_event_filters(self) -> None:
        """`F3-043`/`F3-049` — filtreler + isteğe bağlı gruplama, satırları çizer."""
        if getattr(self, "_suppress_filter_refresh", False):
            return
        visible = filter_events(self._all_events, **self._current_event_filters())  # type: ignore[arg-type]
        if self.event_group_check.isChecked():
            self._row_groups = group_near_events(visible)
            self._render_grouped()
        else:
            self._row_groups = []
            self._expanded_groups.clear()
            self._render_rows([("event", event, None) for event in visible])

    def _render_grouped(self) -> None:
        rows: list[tuple[str, Event, int | None]] = []
        for index, group in enumerate(self._row_groups):
            expanded = group.is_group and index in self._expanded_groups
            kind = "group" if group.is_group else "event"
            rows.append((kind, group.representative, index if group.is_group else None))
            if expanded:
                rows.extend(("member", member, None) for member in group.events)
        self._render_rows(rows)

    def _render_rows(self, rows: Sequence[tuple[str, Event, int | None]]) -> None:
        self._row_kinds = [kind for kind, _event, _gi in rows]
        self._row_events = [event for _kind, event, _gi in rows]
        self._row_group_index = [gi for _kind, _event, gi in rows]
        severity_column = EVENT_COLUMNS.index("Severity")
        message_column = EVENT_COLUMNS.index("Message")
        time_column = EVENT_COLUMNS.index("Time")
        self.events.setRowCount(len(rows))
        for row, (kind, event, group_index) in enumerate(rows):
            style = severity_style(event.severity)
            group = self._row_groups[group_index] if group_index is not None else None
            for column, name in enumerate(EVENT_COLUMNS):
                text = event_cell_text(event, name, start_ns=self._events_start_ns)
                if column == message_column and group is not None:
                    prefix = "▾ " if group_index in self._expanded_groups else "▸ "
                    text = f"{prefix}{text}  (×{group.count})"
                elif kind == "member" and column == time_column:
                    text = f"    {text}"
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, event.timestamp_ns)
                if column == severity_column:
                    item.setIcon(make_status_icon(style))
                    item.setToolTip(style.describe())
                if event.severity.rank >= Severity.ERROR.rank:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.events.setItem(row, column, item)
        self.events.resizeColumnsToContents()

    def _group_index_for_row(self, row: int) -> int | None:
        if 0 <= row < len(self._row_group_index):
            return self._row_group_index[row]
        return None

    def event_row_count(self) -> int:
        """Filtre + gruplama sonrası görünen satır sayısı."""
        return self.events.rowCount()

    def group_count(self) -> int:
        """Gruplama açıkken oluşan grup sayısı — `F3-049`."""
        return len(self._row_groups)

    def is_group_expanded(self, group_index: int) -> bool:
        return group_index in self._expanded_groups

    def group_members(self, group_index: int) -> list[Event]:
        """Bir grubun özgün olayları — hiç değiştirilmeden — `F3-049`."""
        return list(self._row_groups[group_index].events)

    def event_cell(self, row: int, column: str) -> str:
        """Bir hücrenin metni — testler ve kabul için."""
        try:
            index = EVENT_COLUMNS.index(column)
        except ValueError as exc:
            raise KeyError(f"Tanimsiz olay sutunu: {column}") from exc
        item = self.events.item(row, index)
        return "" if item is None else item.text()

    def clear_events(self) -> None:
        self._all_events = ()
        self._row_kinds = []
        self._row_events = []
        self._row_group_index = []
        self._row_groups = []
        self._expanded_groups = set()
        self._suppress_filter_refresh = True
        try:
            self._populate_source_filter()
            self._set_time_filter_bounds()
            self.event_severity_filter.setCurrentIndex(0)
            self.event_text_filter.clear()
        finally:
            self._suppress_filter_refresh = False
        self.events.setRowCount(0)

    # -- sorgular --------------------------------------------------------

    def tab_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

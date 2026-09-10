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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QHeaderView,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QWidget,
)

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import EVENT_COLUMNS, event_cell_text
from sonar_analyzer.ui.status_icons import make_status_icon, severity_style

DOCK_OBJECT_NAME = "dock_bottom_panel"
DOCK_TITLE = "Log / Events"

LOG_TAB_TITLE = "Log / Messages"
EVENTS_TAB_TITLE = "Events"

#: Log'da tutulan azami satir sayisi; uzun oturumda bellek sinirsiz buyumez.
MAX_LOG_LINES = 2000


def format_timestamp(timestamp_ns: int) -> str:
    """Nanosaniye zamanı `HH:MM:SS.mmm` biçiminde gösterir."""
    seconds, remainder = divmod(timestamp_ns, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return f"{moment.strftime('%H:%M:%S')}.{remainder // 1_000_000:03d}"


class BottomPanelDock(QDockWidget):
    """Merkez grafiklerin altındaki log ve olay alanı."""

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
        self.events = QTableWidget(0, len(EVENT_COLUMNS), self)
        self.events.setObjectName("table_events")
        self.events.setHorizontalHeaderLabels(list(EVENT_COLUMNS))
        self.events.verticalHeader().setVisible(False)
        self.events.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.events.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.events.horizontalHeader().setSectionResizeMode(
            len(EVENT_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        return self.events

    # -- log -------------------------------------------------------------

    def append_log(self, message: str, timestamp: datetime | None = None) -> None:
        """Log'a zaman damgalı bir satır ekler."""
        moment = timestamp or datetime.now()
        self.log.appendPlainText(f"[{moment.strftime('%H:%M:%S')}] {message}")

    def log_lines(self) -> list[str]:
        text = self.log.toPlainText()
        return text.splitlines() if text else []

    def clear_log(self) -> None:
        self.log.clear()

    # -- olaylar ---------------------------------------------------------

    def set_events(self, events: Sequence[Event], start_ns: int = 0) -> None:
        """Olay tablosunu doldurur; mevcut satırları değiştirir — `F3-042`.

        Sütunlar plan Bölüm 5.5'e göre ortak `event_table_model`'den gelir.
        Şiddet sütununda hem ikon hem metin bulunur: durum yalnız renkle
        anlatılmaz (plan Bölüm 6.4). `start_ns` göreli zaman içindir.
        """
        severity_column = EVENT_COLUMNS.index("Severity")
        self.events.setRowCount(len(events))

        for row, event in enumerate(events):
            style = severity_style(event.severity)
            for column, name in enumerate(EVENT_COLUMNS):
                item = QTableWidgetItem(event_cell_text(event, name, start_ns=start_ns))
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

    def event_row_count(self) -> int:
        return self.events.rowCount()

    def event_cell(self, row: int, column: str) -> str:
        """Bir hücrenin metni — testler ve kabul için."""
        try:
            index = EVENT_COLUMNS.index(column)
        except ValueError as exc:
            raise KeyError(f"Tanimsiz olay sutunu: {column}") from exc
        item = self.events.item(row, index)
        return "" if item is None else item.text()

    def clear_events(self) -> None:
        self.events.setRowCount(0)

    # -- sorgular --------------------------------------------------------

    def tab_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

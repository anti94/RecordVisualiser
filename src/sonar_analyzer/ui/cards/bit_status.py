"""BIT / System Status kartı — `F1-035`.

Mockup bölge 4 (`docs/ui/layout-map.md` §4): genel durum rozeti,
`Run BIT Analysis` düğmesi, `Last Update` ve alt sistem/durum tablosu.

**Rozet ile tablo çelişemez:** tabloda Warning veya FAIL varsa rozet
"All Systems Nominal" yazamaz. Bu kural sınıfın içinde zorlanır, çağıranın
dikkatine bırakılmaz.

`Run BIT Analysis` kayıtlı veriyi yeniden özetler; **donanıma komut göndermez**
(plan Bölüm 5.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.event import BitResult, BitState
from sonar_analyzer.ui.status_icons import bit_style, make_status_icon

CARD_OBJECT_NAME = "card_bit_status"
CARD_TITLE = "BIT / System Status"

NOMINAL_TEXT = "All Systems Nominal"
WARNING_TEXT = "Attention Required"
FAILURE_TEXT = "System Fault"
UNKNOWN_TEXT = "Durum bilinmiyor"
NO_DATA_TEXT = "BIT verisi yok"

COLUMNS = ("Subsystem", "Status")
EMPTY_VALUE = "—"


class BitStatusCard(QGroupBox):
    """Sağ sütunun üst kartı."""

    #: `Run BIT Analysis` tiklandi.
    analysis_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        self._results: tuple[BitResult, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.badge = QLabel(NO_DATA_TEXT, self)
        self.badge.setObjectName("label_bit_badge")
        self.badge.setWordWrap(True)
        self.badge.setMinimumWidth(1)
        layout.addWidget(self.badge)

        controls = QHBoxLayout()
        self.run_button = QPushButton("Run BIT Analysis", self)
        self.run_button.setObjectName("button_run_bit")
        self.run_button.setToolTip("Kayitli BIT verisini yeniden ozetler; donanima komut gondermez")
        self.run_button.clicked.connect(self.analysis_requested.emit)
        controls.addWidget(self.run_button)

        self.last_update = QLabel(f"Last Update: {EMPTY_VALUE}", self)
        self.last_update.setObjectName("label_bit_last_update")
        self.last_update.setWordWrap(True)
        self.last_update.setMinimumWidth(1)
        controls.addWidget(self.last_update)
        layout.addLayout(controls)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setObjectName("table_bit_subsystems")
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

    # -- veri ------------------------------------------------------------

    def set_results(
        self,
        results: Sequence[BitResult],
        updated_at: datetime | None = None,
    ) -> None:
        """Alt sistem tablosunu ve rozeti doldurur.

        Her alt sistemin **en kötü** sonucu gösterilir: bir testin geçmesi,
        aynı bileşendeki başarısız testi gizlememelidir.
        """
        self._results = tuple(results)

        worst: dict[str, BitResult] = {}
        for result in self._results:
            current = worst.get(result.component)
            if current is None or _severity_rank(result.state) > _severity_rank(current.state):
                worst[result.component] = result

        self.table.setRowCount(len(worst))
        for row, (component, result) in enumerate(sorted(worst.items())):
            style = bit_style(result.state)

            name_item = QTableWidgetItem(component)
            self.table.setItem(row, 0, name_item)

            status_item = QTableWidgetItem(style.label)
            status_item.setIcon(make_status_icon(style))
            status_item.setToolTip(style.describe())
            self.table.setItem(row, 1, status_item)

        self._refresh_badge()
        moment = updated_at or datetime.now()
        self.last_update.setText(f"Last Update: {moment.strftime('%H:%M:%S')}")

    def clear(self) -> None:
        self._results = ()
        self.table.setRowCount(0)
        self.badge.setText(NO_DATA_TEXT)
        self.last_update.setText(f"Last Update: {EMPTY_VALUE}")

    # -- sorgular --------------------------------------------------------

    def badge_text(self) -> str:
        return self.badge.text()

    def row_count(self) -> int:
        return self.table.rowCount()

    def subsystem_names(self) -> list[str]:
        names: list[str] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                names.append(item.text())
        return names

    def status_text(self, component: str) -> str:
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0)
            status = self.table.item(row, 1)
            if name is not None and name.text() == component and status is not None:
                return status.text()
        raise KeyError(f"Tabloda yok: {component}")

    # -- ic yardimcilar --------------------------------------------------

    def _refresh_badge(self) -> None:
        states = [result.state for result in self._results]
        if not states:
            self.badge.setText(NO_DATA_TEXT)
            return

        if BitState.FAIL in states:
            self.badge.setText(FAILURE_TEXT)
        elif BitState.WARN in states:
            self.badge.setText(WARNING_TEXT)
        elif BitState.UNKNOWN in states or BitState.NOT_RUN in states:
            self.badge.setText(UNKNOWN_TEXT)
        else:
            self.badge.setText(NOMINAL_TEXT)


def _severity_rank(state: BitState) -> int:
    """Tablodaki "en kötü" seçimi için sıralama."""
    order = {
        BitState.PASS: 0,
        BitState.NOT_RUN: 1,
        BitState.UNKNOWN: 2,
        BitState.WARN: 3,
        BitState.FAIL: 4,
    }
    return order.get(state, 2)

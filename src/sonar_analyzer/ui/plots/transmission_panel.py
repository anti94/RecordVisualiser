"""Transmission sekmesi: TX durumu ve zaman aralıkları — `F3-048`.

Mockup `Transmission` ana sekmesi (plan Bölüm 5.5). Seçili kaydın
`TransmissionInterval` listesini durum + göreli/mutlak başlangıç-bitiş +
süre (sınır belirsizliğiyle) olarak tabloya döker.

Zaman biçimi `event_table_model` ile ortaktır (göreli `+s` + mutlak
`HH:MM:SS.mmm`).
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.ui.docks.event_table_model import format_event_time

PANEL_OBJECT_NAME = "panel_transmission"
EMPTY_HINT = "TX aralığı yok. Bir kayıt açın."

TX_COLUMNS: tuple[str, ...] = ("State", "Start", "End", "Duration", "Note")


def _duration_text(interval: TransmissionInterval) -> str:
    uncertainty_ms = interval.boundary_uncertainty_ns / 1_000_000
    return f"{interval.duration_seconds:.3f} s ±{uncertainty_ms:.0f} ms"


def _note_text(interval: TransmissionInterval) -> str:
    if not interval.closed:
        return "kayıt sonunda açık kaldı"
    return interval.mode or "—"


def transmission_row(interval: TransmissionInterval, *, start_ns: int) -> tuple[str, ...]:
    """Bir aralığın tablo satırı — `F3-048`."""
    return (
        interval.state.value.capitalize(),
        format_event_time(interval.start_ns, start_ns),
        format_event_time(interval.end_ns, start_ns),
        _duration_text(interval),
        _note_text(interval),
    )


class TransmissionPanel(QWidget):
    """Seçili kaydın TX aralıklarını gösteren tablo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(PANEL_OBJECT_NAME)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.hint = QLabel(EMPTY_HINT, self)
        self.hint.setObjectName("label_transmission_hint")
        self.hint.setMinimumWidth(1)
        layout.addWidget(self.hint)

        self.table = QTableWidget(0, len(TX_COLUMNS), self)
        self.table.setObjectName("table_transmission")
        self.table.setHorizontalHeaderLabels(list(TX_COLUMNS))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            len(TX_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

    def set_intervals(self, intervals: Sequence[TransmissionInterval], start_ns: int = 0) -> None:
        """TX aralıklarını tabloya yazar; mevcut satırları değiştirir — `F3-048`."""
        self.table.setRowCount(len(intervals))
        for row, interval in enumerate(intervals):
            for column, text in enumerate(transmission_row(interval, start_ns=start_ns)):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
        self.hint.setVisible(not intervals)

    def clear(self) -> None:
        self.table.setRowCount(0)
        self.hint.setVisible(True)

    def interval_count(self) -> int:
        return self.table.rowCount()

    def interval_cell(self, row: int, column: str) -> str:
        try:
            index = TX_COLUMNS.index(column)
        except ValueError as exc:
            raise KeyError(f"Tanimsiz TX sutunu: {column}") from exc
        item = self.table.item(row, index)
        return "" if item is None else item.text()

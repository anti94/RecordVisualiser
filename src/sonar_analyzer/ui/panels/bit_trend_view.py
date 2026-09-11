"""BIT / Status trend görünümü — `F4-081`.

Sağ sütundaki `BitStatusCard` (`F3-051`) bir **özet**tir: her alt sistemin
o anki en kötü durumu. Bu görünüm aynı veriye **zaman boyutunu** ekler —
`F4-080` trendinden gelen durum süresi, değişim sayısı, ilk arıza ve
aralık dökümü.

**İki yüzey aynı durumu gösterir.** Özet karttaki "Fail" ile buradaki
"Fail" aynı hesaba dayanır: ikisi de `bit_style()` etiketini kullanır ve
ikisi de bir alt sistemin **en kötü** durumunu gösterir. Farklı bir
durum görünüyorsa bu bir hatadır, tasarım değil — `F4-081` testi tam
olarak bunu denetler.

Özet "şu an ne durumda", trend "nasıl geldi" sorusunu yanıtlar; ikisi
birbirinin yerine geçmez.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.analysis.bit_trend import BitTrend, build_trends
from sonar_analyzer.domain.event import BitResult, BitState
from sonar_analyzer.domain.time_range import NS_PER_SECOND
from sonar_analyzer.ui.status_icons import bit_style, make_status_icon

VIEW_TITLE = "BIT / Status trend"
COLUMNS: tuple[str, ...] = (
    "Subsystem",
    "Durum",
    "Değişim",
    "Arıza süresi",
    "Arıza oranı",
    "İlk arıza",
)
EMPTY_HINT = "BIT verisi yok."
NO_FAILURE = "—"


def format_seconds(duration_ns: int) -> str:
    return f"{duration_ns / NS_PER_SECOND:.3f} s"


def format_ratio(ratio: float) -> str:
    return f"%{ratio * 100:.1f}"


def worst_state(trend: BitTrend) -> BitState | None:
    """Trendin **en kötü** durumu — özet kartla aynı ölçüt.

    Özet kart bir alt sistemin en kötü sonucunu gösterir; trend görünümü
    de aynı şeyi göstermelidir, yoksa iki yüzey aynı veriden farklı
    durum bildirirdi.
    """
    states = [interval.state for interval in trend.intervals]
    if not states:
        return None
    return max(states, key=lambda state: state.severity_rank)


class BitTrendView(QWidget):
    """Alt sistem başına durum süresi ve değişim özeti."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_bit_trend")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.heading = QLabel(VIEW_TITLE, self)
        self.heading.setObjectName("label_bit_trend_title")
        layout.addWidget(self.heading)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setObjectName("table_bit_trend")
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            len(COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        self.hint = QLabel(EMPTY_HINT, self)
        self.hint.setObjectName("label_bit_trend_hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self._trends: tuple[BitTrend, ...] = ()
        self._start_ns = 0

    # -- veri --------------------------------------------------------------

    def set_results(
        self,
        results: Sequence[BitResult],
        *,
        start_ns: int = 0,
        end_ns: int | None = None,
    ) -> None:
        """BIT sonuçlarını trendlere çevirip tabloyu doldurur.

        `end_ns` kaydın sonudur; son aralığın süresi onunla kapanır
        (`F4-080`). Verilmezse son koşudan sonrası **bilinmez** sayılır.
        """
        self._start_ns = start_ns
        self._trends = tuple(
            sorted(build_trends(results, end_ns=end_ns), key=lambda trend: trend.component)
        )

        self.table.setRowCount(len(self._trends))
        for row, trend in enumerate(self._trends):
            self._fill_row(row, trend)
        self.hint.setVisible(not self._trends)

    def clear(self) -> None:
        self._trends = ()
        self.table.setRowCount(0)
        self.hint.setVisible(True)

    def _fill_row(self, row: int, trend: BitTrend) -> None:
        state = worst_state(trend)
        style = bit_style(state) if state is not None else None
        first = trend.first_failure()
        values = (
            trend.component,
            style.label if style is not None else NO_FAILURE,
            str(trend.change_count),
            format_seconds(trend.failure_ns()),
            format_ratio(trend.failure_ratio()),
            NO_FAILURE if first is None else format_seconds(first.start_ns - self._start_ns),
        )
        for column, value in enumerate(values):
            cell = QTableWidgetItem(value)
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if column == 1 and style is not None:
                cell.setIcon(make_status_icon(style))
                cell.setToolTip(style.describe())
            self.table.setItem(row, column, cell)

    # -- sorgular ----------------------------------------------------------

    def trends(self) -> tuple[BitTrend, ...]:
        return self._trends

    def row_count(self) -> int:
        return self.table.rowCount()

    def subsystem_names(self) -> list[str]:
        names: list[str] = []
        for row in range(self.table.rowCount()):
            cell = self.table.item(row, 0)
            if cell is not None:
                names.append(cell.text())
        return names

    def cell(self, component: str, column: str) -> str:
        """Bir alt sistemin adlandırılmış sütunundaki metin."""
        if column not in COLUMNS:
            raise KeyError(f"Tanımsız trend sütunu: {column}")
        index = COLUMNS.index(column)
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0)
            value = self.table.item(row, index)
            if name is not None and name.text() == component and value is not None:
                return value.text()
        raise KeyError(f"Trend tablosunda yok: {component}")

    def status_text(self, component: str) -> str:
        """Alt sistemin durum etiketi — özet karttakiyle **aynı** olmalı."""
        return self.cell(component, "Durum")

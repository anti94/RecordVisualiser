"""Events tablosunda yakın tekrarları gruplama — `F3-049`.

Kabul: grup sayısı ve açılan ayrıntılar özgün olayları korur.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock

pytestmark = pytest.mark.gui

MS = 1_000_000


def _ev(t_ms: int, code: str = "THERMAL", message: str = "thermal repeat") -> Event:
    return Event(
        timestamp_ns=t_ms * MS,
        source="BIT",
        category="BIT",
        severity=Severity.WARNING,
        code=code,
        message=message,
    )


BURST = [_ev(1000), _ev(1050), _ev(1100)]
LONE = _ev(5000, code="VOLTAGE", message="voltage sag")
EVENTS = [*BURST, LONE]


@pytest.fixture()
def panel(qtbot: QtBot) -> BottomPanelDock:
    dock = BottomPanelDock()
    qtbot.addWidget(dock)
    dock.set_events(EVENTS, start_ns=0)
    return dock


def _double_click_row(panel: BottomPanelDock, row: int) -> None:
    panel.events.setCurrentCell(row, 0)
    item = panel.events.item(row, 0)
    assert item is not None
    panel.events.itemDoubleClicked.emit(item)


def test_ungrouped_table_shows_every_event(panel: BottomPanelDock) -> None:
    assert panel.event_row_count() == 4


def test_enabling_grouping_collapses_the_burst(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)

    assert panel.group_count() == 2
    assert panel.event_row_count() == 2  # 1 grup başlığı + 1 tekil
    assert "(×3)" in panel.event_cell(0, "Message")


def test_expanding_a_group_reveals_the_original_events(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)

    _double_click_row(panel, 0)

    assert panel.is_group_expanded(0)
    assert panel.event_row_count() == 5  # başlık + 3 üye + tekil
    assert panel.group_members(0) == BURST  # özgün olaylar korunur


def test_collapsing_a_group_hides_the_members_again(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)
    _double_click_row(panel, 0)
    assert panel.event_row_count() == 5

    _double_click_row(panel, 0)

    assert not panel.is_group_expanded(0)
    assert panel.event_row_count() == 2


def test_double_clicking_a_lone_event_navigates_not_expands(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)
    activated: list[Event] = []
    panel.event_activated.connect(activated.append)

    _double_click_row(panel, 1)  # tekil olay satırı

    assert activated == [LONE]
    assert panel.event_row_count() == 2  # açılma olmadı


def test_disabling_grouping_restores_the_flat_table(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)
    _double_click_row(panel, 0)
    assert panel.event_row_count() == 5

    panel.event_group_check.setChecked(False)

    assert panel.group_count() == 0
    assert panel.event_row_count() == 4


def test_grouping_does_not_mutate_the_source_events(panel: BottomPanelDock) -> None:
    panel.event_group_check.setChecked(True)
    _double_click_row(panel, 0)

    members = panel.group_members(0)
    for original, shown in zip(BURST, members):
        assert shown is original

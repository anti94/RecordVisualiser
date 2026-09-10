"""Events sekmesi filtre çubuğu — `F3-043`.

Kabul: birleşik filtre sonucu beklenen olay kümesidir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.bottom_panel import BottomPanelDock

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


def _ev(t_s: float, source: str, severity: Severity, message: str) -> Event:
    return Event(
        timestamp_ns=int(t_s * SECOND),
        source=source,
        category="BIT",
        severity=severity,
        code="X",
        message=message,
    )


EVENTS = [
    _ev(0, "BIT", Severity.INFO, "power ok"),
    _ev(1, "BIT", Severity.ERROR, "thermal fail"),
    _ev(2, "Comms", Severity.WARNING, "link degraded"),
    _ev(3, "Comms", Severity.CRITICAL, "link fail"),
    _ev(4, "BIT", Severity.ERROR, "voltage fail"),
]


@pytest.fixture()
def panel(qtbot: QtBot) -> BottomPanelDock:
    dock = BottomPanelDock()
    qtbot.addWidget(dock)
    dock.set_events(EVENTS, start_ns=0)
    return dock


def _visible_messages(panel: BottomPanelDock) -> list[str]:
    return [panel.event_cell(row, "Message") for row in range(panel.event_row_count())]


def test_no_filter_shows_all_events(panel: BottomPanelDock) -> None:
    assert panel.event_row_count() == len(EVENTS)


def test_source_filter_narrows_the_table(panel: BottomPanelDock) -> None:
    panel.event_source_filter.setCurrentText("Comms")

    assert _visible_messages(panel) == ["link degraded", "link fail"]


def test_severity_filter_narrows_the_table(panel: BottomPanelDock) -> None:
    panel.event_severity_filter.setCurrentText("Error+")

    assert _visible_messages(panel) == ["thermal fail", "link fail", "voltage fail"]


def test_text_filter_narrows_the_table(panel: BottomPanelDock) -> None:
    panel.event_text_filter.setText("link")

    assert _visible_messages(panel) == ["link degraded", "link fail"]


def test_time_filter_narrows_the_table(panel: BottomPanelDock) -> None:
    panel.event_time_from.setValue(1.0)
    panel.event_time_to.setValue(3.0)

    assert _visible_messages(panel) == ["thermal fail", "link degraded", "link fail"]


def test_combined_filters_yield_the_expected_set(panel: BottomPanelDock) -> None:
    panel.event_source_filter.setCurrentText("BIT")
    panel.event_severity_filter.setCurrentText("Error+")
    panel.event_time_to.setValue(3.0)

    assert _visible_messages(panel) == ["thermal fail"]


def test_clearing_a_filter_restores_rows(panel: BottomPanelDock) -> None:
    panel.event_source_filter.setCurrentText("Comms")
    assert panel.event_row_count() == 2

    panel.event_source_filter.setCurrentText("All sources")

    assert panel.event_row_count() == len(EVENTS)


def test_reloading_events_repopulates_the_source_list(panel: BottomPanelDock) -> None:
    panel.set_events([_ev(0, "Nav", Severity.INFO, "gps lock")], start_ns=0)

    combo = panel.event_source_filter
    items = [combo.itemText(i) for i in range(combo.count())]
    assert items == ["All sources", "Nav"]


def test_clear_events_resets_the_filter_bar(panel: BottomPanelDock) -> None:
    panel.event_severity_filter.setCurrentText("Error+")
    panel.event_text_filter.setText("fail")

    panel.clear_events()

    assert panel.event_row_count() == 0
    assert panel.event_severity_filter.currentIndex() == 0
    assert panel.event_text_filter.text() == ""

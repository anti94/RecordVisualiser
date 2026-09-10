"""PlaybackDock önceki/sonraki olaya ve zamana gitme — `F3-059`.

Kabul: sınır dışı zaman güvenli sınırlanır; olay sırası korunur.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.docks.playback import PlaybackDock

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000
#: Kayıt 100 s'te başlar — mutlak/göreli dönüşümü de sınanır.
START_NS = 100 * SECOND


def _ev(rel_s: float) -> Event:
    return Event(
        timestamp_ns=START_NS + int(rel_s * SECOND),
        source="BIT",
        category="BIT",
        severity=Severity.WARNING,
        code="X",
        message=f"olay @ +{rel_s}s",
    )


@pytest.fixture()
def dock(qtbot: QtBot) -> PlaybackDock:
    widget = PlaybackDock()
    qtbot.addWidget(widget)
    widget.set_recording_range(TimeRange(START_NS, START_NS + 20 * SECOND))
    widget.set_events([_ev(2.0), _ev(5.0), _ev(11.0)])
    return widget


def test_next_event_button_walks_events_in_time_order(dock: PlaybackDock) -> None:
    seen: list[Event] = []
    dock.event_navigated.connect(seen.append)

    dock.buttons["button_next_event"].click()
    assert abs(dock.position_s - 2.0) < 1e-3
    dock.buttons["button_next_event"].click()
    assert abs(dock.position_s - 5.0) < 1e-3
    dock.buttons["button_next_event"].click()
    assert abs(dock.position_s - 11.0) < 1e-3

    assert [e.timestamp_ns for e in seen] == [
        START_NS + 2 * SECOND,
        START_NS + 5 * SECOND,
        START_NS + 11 * SECOND,
    ]


def test_next_event_past_the_last_one_is_a_no_op(dock: PlaybackDock) -> None:
    dock.set_position(15.0)
    assert dock.goto_next_event() is False
    assert abs(dock.position_s - 15.0) < 1e-3


def test_previous_event_button_walks_back(dock: PlaybackDock) -> None:
    dock.set_position(12.0)

    assert dock.goto_previous_event() is True
    assert abs(dock.position_s - 11.0) < 1e-3
    assert dock.goto_previous_event() is True
    assert abs(dock.position_s - 5.0) < 1e-3


def test_previous_event_before_the_first_one_is_a_no_op(dock: PlaybackDock) -> None:
    dock.set_position(1.0)
    assert dock.goto_previous_event() is False
    assert abs(dock.position_s - 1.0) < 1e-3


def test_goto_time_clamps_out_of_range_targets(dock: PlaybackDock) -> None:
    dock.goto_time_ns(START_NS - 50 * SECOND)  # kayıt başından önce
    assert dock.position_s == 0.0

    dock.goto_time_ns(START_NS + 999 * SECOND)  # kayıt sonundan sonra
    assert abs(dock.position_s - 20.0) < 1e-3

    dock.goto_time_ns(START_NS + 7 * SECOND)  # aralık içinde
    assert abs(dock.position_s - 7.0) < 1e-3


def test_navigation_without_events_is_safe(qtbot: QtBot) -> None:
    widget = PlaybackDock()
    qtbot.addWidget(widget)
    widget.set_recording_range(TimeRange(0, 10 * SECOND))

    assert widget.goto_next_event() is False
    assert widget.goto_previous_event() is False

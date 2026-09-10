"""PlaybackClock + PlaybackDock ilerleme — `F3-057`."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.playback_state import PlaybackMachine
from sonar_analyzer.ui.docks.playback import PlaybackDock
from sonar_analyzer.ui.docks.playback_clock import PlaybackClock

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> PlaybackDock:
    widget = PlaybackDock()
    qtbot.addWidget(widget)
    widget.set_duration(2.0)
    return widget


def test_clock_tick_advances_the_machine_and_slider(dock: PlaybackDock) -> None:
    dock.machine.play()

    dock.clock.tick_once(0.5)

    assert abs(dock.machine.position_s - 0.5) < 1e-9
    assert abs(dock.position_s - 0.5) < 1e-3  # kaydırıcı izledi


def test_clock_only_runs_while_playing(qtbot: QtBot) -> None:
    machine = PlaybackMachine(5.0)
    clock = PlaybackClock(machine)
    assert not clock.is_running

    machine.play()
    assert clock.is_running

    machine.pause()
    assert not clock.is_running

    machine.play()
    machine.stop()
    assert not clock.is_running


def test_ticking_crosses_125ms_boundaries_in_order_through_the_dock(dock: PlaybackDock) -> None:
    crossed: list[int] = []
    dock.machine.add_record_listener(lambda i, _t: crossed.append(i))
    dock.machine.play()

    dock.clock.tick_once(0.30)  # 0.125 ve 0.25 geçilir

    assert crossed == [1, 2]


def test_reaching_the_end_via_ticks_pauses_the_dock(dock: PlaybackDock) -> None:
    dock.machine.play()

    dock.clock.tick_once(10.0)

    assert dock.machine.at_end
    assert not dock.is_playing
    assert not dock.buttons["button_play"].isChecked()

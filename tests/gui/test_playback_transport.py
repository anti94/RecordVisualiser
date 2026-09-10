"""PlaybackDock transport düğmeleri durum makinesini sürer — `F3-056`."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.playback_state import PlaybackState
from sonar_analyzer.ui.docks.playback import PlaybackDock

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> PlaybackDock:
    widget = PlaybackDock()
    qtbot.addWidget(widget)
    widget.set_duration(20.0)
    return widget


def test_play_button_toggles_the_machine(dock: PlaybackDock) -> None:
    play = dock.buttons["button_play"]

    play.setChecked(True)
    assert dock.machine.state is PlaybackState.PLAYING
    assert dock.is_playing

    play.setChecked(False)
    assert dock.machine.state is PlaybackState.PAUSED
    assert not dock.is_playing


def test_skip_start_stops_and_returns_to_zero(dock: PlaybackDock) -> None:
    dock.buttons["button_play"].setChecked(True)
    dock.set_position(8.0)
    assert dock.machine.position_s == 8.0

    dock.buttons["button_skip_start"].click()

    assert dock.machine.state is PlaybackState.STOPPED
    assert dock.machine.position_s == 0.0
    assert dock.position_s == 0.0
    assert not dock.buttons["button_play"].isChecked()


def test_setting_a_new_duration_resets_playback(dock: PlaybackDock) -> None:
    dock.buttons["button_play"].setChecked(True)
    dock.set_position(5.0)

    dock.set_duration(30.0)

    assert dock.machine.state is PlaybackState.STOPPED
    assert dock.machine.position_s == 0.0
    assert dock.machine.duration_s == 30.0


def test_slider_move_seeks_the_machine(dock: PlaybackDock) -> None:
    dock.set_position(12.5)

    assert abs(dock.machine.position_s - 12.5) < 1e-6

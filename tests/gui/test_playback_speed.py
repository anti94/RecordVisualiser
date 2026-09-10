"""Oynatma hızı seçici kayıt zamanı ilerlemesini ölçekler — `F3-058`.

Kabul: 0.25x–10x seçenekleri kayıt zamanı ilerlemesini ölçekler.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.docks.playback import PLAYBACK_SPEEDS, PlaybackDock

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> PlaybackDock:
    widget = PlaybackDock()
    qtbot.addWidget(widget)
    widget.set_duration(20.0)
    return widget


def test_default_speed_is_one_x(dock: PlaybackDock) -> None:
    assert dock.playback_speed == 1.0
    assert dock.speed_selector.currentData() == 1.0
    assert dock.speed_selector.currentText() == "1x"


def test_all_speed_multipliers_are_offered(dock: PlaybackDock) -> None:
    offered = [dock.speed_selector.itemData(i) for i in range(dock.speed_selector.count())]
    assert offered == list(PLAYBACK_SPEEDS)
    assert PLAYBACK_SPEEDS[0] == 0.25
    assert PLAYBACK_SPEEDS[-1] == 10.0


def test_selecting_two_x_doubles_record_time_progress(dock: PlaybackDock) -> None:
    dock.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(2.0))
    assert dock.playback_speed == 2.0

    dock.machine.play()
    dock.clock.tick_once(0.5)  # 0.5 s gerçek süre × 2x

    assert abs(dock.machine.position_s - 1.0) < 1e-9


def test_selecting_quarter_x_slows_record_time_progress(dock: PlaybackDock) -> None:
    dock.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(0.25))
    assert dock.playback_speed == 0.25

    dock.machine.play()
    dock.clock.tick_once(1.0)  # 1.0 s gerçek süre × 0.25x

    assert abs(dock.machine.position_s - 0.25) < 1e-9


def test_speed_changed_signal_carries_the_multiplier(dock: PlaybackDock) -> None:
    seen: list[float] = []
    dock.speed_changed.connect(seen.append)

    dock.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(5.0))
    dock.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(0.5))

    assert seen == [5.0, 0.5]


def test_every_multiplier_scales_the_tick(dock: PlaybackDock) -> None:
    for multiplier in PLAYBACK_SPEEDS:
        dock.machine.stop()
        dock.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(multiplier))
        dock.machine.play()

        dock.clock.tick_once(0.1)

        assert abs(dock.machine.position_s - 0.1 * multiplier) < 1e-9

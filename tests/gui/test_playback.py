"""Playback / Time Control şeridi — `F1-027`.

Kabul: kontrol şeridi merkez grafiklerin altında ve logun üstündedir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.playback import (
    TRANSPORT_BUTTONS,
    PlaybackDock,
    format_elapsed,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


@pytest.fixture()
def strip(qtbot: QtBot) -> PlaybackDock:
    dock = PlaybackDock()
    qtbot.addWidget(dock)
    dock.show()
    qtbot.waitExposed(dock)
    dock.set_duration(60.0)
    return dock


# -- yerlesim --------------------------------------------------------------


def test_strip_is_in_the_bottom_area(window: MainWindow) -> None:
    assert isinstance(window.playback_dock, PlaybackDock)
    assert window.dockWidgetArea(window.playback_dock) == Qt.DockWidgetArea.BottomDockWidgetArea


def test_strip_is_below_center_and_above_log(window: MainWindow, qtbot: QtBot) -> None:
    """Kabul kriteri: merkezin altında, logun üstünde."""
    qtbot.waitUntil(lambda: window.playback_dock.height() > 0, timeout=2000)

    center_bottom = window.center.mapTo(window, window.center.rect().bottomLeft()).y()
    strip_top = window.playback_dock.mapTo(window, window.playback_dock.rect().topLeft()).y()
    log_top = window.bottom_dock.mapTo(window, window.bottom_dock.rect().topLeft()).y()

    assert strip_top >= center_bottom, "serit merkezin altinda olmali"
    assert strip_top < log_top, "serit logun ustunde olmali"


def test_strip_has_stable_object_name(window: MainWindow) -> None:
    assert window.playback_dock.objectName() == "dock_playback"


# -- icerik ----------------------------------------------------------------


def test_transport_buttons_exist_in_mockup_order(strip: PlaybackDock) -> None:
    assert list(strip.buttons) == [name for name, _, _ in TRANSPORT_BUTTONS]
    assert len(TRANSPORT_BUTTONS) == 5


def test_controls_are_disabled_without_a_recording(qtbot: QtBot) -> None:
    dock = PlaybackDock()
    qtbot.addWidget(dock)
    assert dock.duration_s == 0.0
    assert not dock.slider.isEnabled()
    assert not dock.go_button.isEnabled()
    for button in dock.buttons.values():
        assert not button.isEnabled()


def test_recording_enables_controls_and_sets_duration(window: MainWindow) -> None:
    repo = MockRecordingRepository(duration_s=90.0)
    window.set_recording(repo.metadata(), repo.channels())

    strip = window.playback_dock
    assert strip.duration_s == 90.0
    assert strip.slider.isEnabled()
    assert strip.time_text() == "00:00:00 / 00:01:30"


# -- oynatma ---------------------------------------------------------------


def test_play_button_toggles_and_emits(strip: PlaybackDock, qtbot: QtBot) -> None:
    play = strip.buttons["button_play"]
    assert not strip.is_playing

    states: list[bool] = []
    strip.play_toggled.connect(states.append)

    with qtbot.waitSignal(strip.play_toggled, timeout=2000):
        play.click()
    assert states == [True]
    assert strip.is_playing
    assert play.text() == "||"

    play.click()
    assert not strip.is_playing
    assert play.text() == ">"


def test_skip_buttons_move_the_cursor(strip: PlaybackDock) -> None:
    strip.buttons["button_skip_end"].click()
    assert strip.position_s == 60.0

    strip.buttons["button_skip_start"].click()
    assert strip.position_s == 0.0


def test_slider_updates_time_label(strip: PlaybackDock) -> None:
    strip.set_position(12.5)
    assert strip.position_s == 12.5
    assert strip.time_text() == "00:00:12 / 00:01:00"


def test_position_is_clamped(strip: PlaybackDock) -> None:
    strip.set_position(-5.0)
    assert strip.position_s == 0.0

    strip.set_position(999.0)
    assert strip.position_s == 60.0


def test_moving_the_slider_emits_position(strip: PlaybackDock, qtbot: QtBot) -> None:
    positions: list[float] = []
    strip.position_changed.connect(positions.append)

    with qtbot.waitSignal(strip.position_changed, timeout=2000):
        strip.set_position(30.0)
    assert positions == [30.0]


# -- Start / End / Go ------------------------------------------------------


def test_go_emits_requested_range(strip: PlaybackDock, qtbot: QtBot) -> None:
    strip.start_input.setValue(10.0)
    strip.end_input.setValue(20.0)

    ranges: list[tuple[float, float]] = []

    def record(start: float, end: float) -> None:
        ranges.append((start, end))

    strip.range_requested.connect(record)

    with qtbot.waitSignal(strip.range_requested, timeout=2000):
        strip.go_button.click()

    assert ranges == [(10.0, 20.0)]
    assert strip.position_s == 10.0


def test_reversed_range_is_rejected(strip: PlaybackDock) -> None:
    """Ters aralık sessizce düzeltilmiyor; neden ipucunda yazıyor."""
    strip.set_position(5.0)
    strip.start_input.setValue(30.0)
    strip.end_input.setValue(10.0)

    strip.go_button.click()

    assert strip.position_s == 5.0, "imlec tasinmamali"
    assert "buyuk olmali" in strip.start_input.toolTip()


def test_range_inputs_are_bounded_by_duration(strip: PlaybackDock) -> None:
    assert strip.start_input.maximum() == 60.0
    assert strip.end_input.maximum() == 60.0
    assert strip.end_input.value() == 60.0


def test_format_elapsed() -> None:
    assert format_elapsed(0) == "00:00:00"
    assert format_elapsed(90) == "00:01:30"
    assert format_elapsed(5046) == "01:24:06"
    assert format_elapsed(-5) == "00:00:00"

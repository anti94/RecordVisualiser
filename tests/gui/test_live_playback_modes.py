"""Canlı ve playback mod geçişleri — `F5-024`.

Kabul: **iki saat aynı grafiği eşzamanlı ilerletmez.**

Plan Bölüm 13: "Canlı ve playback modlarının aynı anda yanlışlıkla
karışmasını önle." Karışırlarsa kullanıcı gördüğü zamanın hangi kaynaktan
geldiğini bilemez; bu yüzden geçiş sessizce değil, biri **durdurularak**
yapılır ve durduruluş loglanır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=2.0))
    window.open_channel("ch0")
    return window


def _attach_live(win: MainWindow) -> None:
    win.set_live_source(
        FileReplaySource(MockRecordingRepository(duration_s=2.0), sleep=lambda _s: None)
    )
    win.connect_live_source()


def _play_button(win: MainWindow):  # type: ignore[no-untyped-def]
    return win.playback_dock.buttons["button_play"]


# --------------------------------------------------------------------------- #
# baslangic: canli mod kapali, playback serbest
# --------------------------------------------------------------------------- #


def test_live_mode_is_off_before_any_stream(win: MainWindow) -> None:
    assert win.live_mode is False
    assert _play_button(win).isEnabled() is True


def test_playback_works_normally_without_a_live_stream(win: MainWindow) -> None:
    _play_button(win).setChecked(True)
    assert win.playback_dock.is_playing is True
    assert win.live_mode is False


# --------------------------------------------------------------------------- #
# canli baslarsa PLAYBACK DURUR
# --------------------------------------------------------------------------- #


def test_starting_live_pauses_a_running_playback(win: MainWindow) -> None:
    _play_button(win).setChecked(True)
    assert win.playback_dock.is_playing is True

    _attach_live(win)
    try:
        win.start_live_stream(buffer_capacity=10_000)
        assert win.playback_dock.is_playing is False  # playback saati durdu
        assert win.live_mode is True
    finally:
        win.stop_live_stream()


def test_the_pause_is_logged_not_silent(win: MainWindow) -> None:
    _play_button(win).setChecked(True)
    _attach_live(win)
    try:
        win.start_live_stream(buffer_capacity=10_000)
    finally:
        win.stop_live_stream()

    assert any("playback duraklatildi" in line for line in win.bottom_dock.log_lines())


def test_the_play_button_is_disabled_while_live(win: MainWindow) -> None:
    """Kullanıcı canlı akış sürerken ikinci saati **başlatamaz**."""
    _attach_live(win)
    try:
        win.start_live_stream(buffer_capacity=10_000)
        assert _play_button(win).isEnabled() is False
    finally:
        win.stop_live_stream()


def test_stopping_live_gives_playback_back(win: MainWindow) -> None:
    _attach_live(win)
    win.start_live_stream(buffer_capacity=10_000)
    win.stop_live_stream()

    assert win.live_mode is False
    assert _play_button(win).isEnabled() is True
    _play_button(win).setChecked(True)
    assert win.playback_dock.is_playing is True


# --------------------------------------------------------------------------- #
# playback baslarsa CANLI DURUR (karsi yon)
# --------------------------------------------------------------------------- #


def test_starting_playback_stops_a_running_live_stream(win: MainWindow) -> None:
    _attach_live(win)
    win.start_live_stream(buffer_capacity=10_000)
    assert win.live_mode is True

    _play_button(win).setEnabled(True)  # kullanici/kod dugmeyi yeniden acsa bile
    _play_button(win).setChecked(True)

    assert win.live_mode is False  # canli akis durduruldu
    assert any("canli akis durduruldu" in line for line in win.bottom_dock.log_lines())


def test_the_two_clocks_are_never_running_together(win: MainWindow, qtbot: QtBot) -> None:
    """Kabul kriterinin kendisi: her geçişte en çok **bir** saat ilerler."""
    _attach_live(win)
    try:
        for _ in range(3):  # ileri geri gecisler
            win.start_live_stream(buffer_capacity=10_000)
            assert not (win.live_mode and win.playback_dock.is_playing)

            _play_button(win).setEnabled(True)
            _play_button(win).setChecked(True)
            assert not (win.live_mode and win.playback_dock.is_playing)

            _play_button(win).setChecked(False)
            assert not (win.live_mode and win.playback_dock.is_playing)
    finally:
        win.stop_live_stream()


def test_pumping_after_playback_took_over_does_nothing(win: MainWindow) -> None:
    """Canlı akış durdurulduktan sonra kare sürmek grafiği ilerletmez."""
    _attach_live(win)
    win.set_live_plot_channel("ch0")
    win.start_live_stream(buffer_capacity=10_000)

    _play_button(win).setEnabled(True)
    _play_button(win).setChecked(True)  # playback devraldi, canli durdu

    assert win.pump_live_stream() == 0

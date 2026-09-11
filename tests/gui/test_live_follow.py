"""Canlı sona takip ve sabit aralık — `F5-023`.

Kabul: **kullanıcı geçmişe bakarken viewport zorla sona taşınmaz.**

Bu, canlı grafiklerin en can sıkıcı hatasının testi: kullanıcı bir anı
incelemek için geriye kaydırır, bir sonraki paket gelir ve görünüm sona
zıplar. Burada kaydırma takibi **kapatır**; sonraki paketler viewport'a
dokunmaz.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import DEFAULT_LIVE_FOLLOW_WINDOW_S, MainWindow

pytestmark = pytest.mark.gui

DURATION_S = 2.0  # 16 pencere


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(900, 600)
    return window


def _start(win: MainWindow, qtbot: QtBot, *, wanted: int = 4) -> None:
    """Canlı akışı başlatıp **tam** `wanted` paket işler.

    Kareler `limit=1` ile sürülür: akış hâlâ devam ederken viewport'un ne
    yaptığını ölçmek istiyoruz. Tek karede hepsini yutsaydık "akış
    sürerken" durumu hiç yaşanmazdı.
    """
    win.set_live_source(
        FileReplaySource(MockRecordingRepository(duration_s=DURATION_S), sleep=lambda _s: None)
    )
    win.connect_live_source()
    win.set_live_plot_channel("ch0")
    win.start_live_stream(buffer_capacity=100_000)
    _pump_to(win, qtbot, wanted)


def _pump_to(win: MainWindow, qtbot: QtBot, wanted: int) -> None:
    """Repository'deki paket sayısı `wanted` olana kadar birer birer işler."""

    def pumped() -> bool:
        win.pump_live_stream(limit=1)
        repository = win.live_repository
        return repository is not None and repository.packet_count >= wanted

    qtbot.waitUntil(pumped, timeout=5000)


def _x_range(win: MainWindow) -> tuple[float, float]:
    x_min, x_max, _y_min, _y_max = win.plot_panel.visible_range()
    return x_min, x_max


# --------------------------------------------------------------------------- #
# varsayilan: sona takip
# --------------------------------------------------------------------------- #


def test_following_is_on_by_default(win: MainWindow) -> None:
    assert win.live_follow is True
    assert win.live_follow_window_s == DEFAULT_LIVE_FOLLOW_WINDOW_S


def test_the_viewport_follows_the_live_end(win: MainWindow, qtbot: QtBot) -> None:
    try:
        _start(win, qtbot, wanted=4)
        early_max = _x_range(win)[1]

        _pump_to(win, qtbot, 12)
        later_max = _x_range(win)[1]
    finally:
        win.stop_live_stream()

    assert later_max > early_max  # gorunum sona dogru kaydi


def test_the_follow_window_width_is_respected(win: MainWindow, qtbot: QtBot) -> None:
    win_seconds = 0.5
    try:
        win.set_live_follow_window(win_seconds)
        _start(win, qtbot, wanted=12)
        x_min, x_max = _x_range(win)
    finally:
        win.stop_live_stream()

    assert abs((x_max - x_min) - win_seconds) < 0.05


def test_a_non_positive_follow_window_is_refused(win: MainWindow) -> None:
    with pytest.raises(ValueError, match="Takip penceresi pozitif olmali"):
        win.set_live_follow_window(0)


# --------------------------------------------------------------------------- #
# KULLANICI GECMISE BAKARKEN VIEWPORT ZORLA SONA TASINMAZ
# --------------------------------------------------------------------------- #


def test_user_navigation_turns_following_off(win: MainWindow, qtbot: QtBot) -> None:
    try:
        _start(win, qtbot, wanted=4)
        assert win.live_follow is True

        win.plot_panel.set_x_range(0.0, 0.4)  # kullanici geriye kaydirdi
        assert win.live_follow is False
    finally:
        win.stop_live_stream()


def test_the_viewport_stays_put_after_the_user_looks_back(win: MainWindow, qtbot: QtBot) -> None:
    """Kabul kriterinin kendisi: sonraki paketler görünümü sona taşımaz."""
    try:
        _start(win, qtbot, wanted=4)
        win.plot_panel.set_x_range(0.0, 0.4)  # gecmise bak
        pinned = _x_range(win)

        _pump_to(win, qtbot, 14)
        after = _x_range(win)
    finally:
        win.stop_live_stream()

    assert abs(after[0] - pinned[0]) < 1e-6
    assert abs(after[1] - pinned[1]) < 1e-6  # viewport hic kaymadi


def test_new_data_still_arrives_while_the_viewport_is_pinned(win: MainWindow, qtbot: QtBot) -> None:
    """Takip kapalıyken veri akmaya devam eder — yalnız görünüm sabittir."""
    try:
        _start(win, qtbot, wanted=4)
        win.plot_panel.set_x_range(0.0, 0.4)
        before = win.live_repository.buffer.count("ch0") if win.live_repository else 0

        _pump_to(win, qtbot, 14)
        after = win.live_repository.buffer.count("ch0") if win.live_repository else 0
    finally:
        win.stop_live_stream()

    assert after > before  # tampon doluyor


def test_following_can_be_switched_back_on_and_catches_up(win: MainWindow, qtbot: QtBot) -> None:
    try:
        _start(win, qtbot, wanted=4)
        win.plot_panel.set_x_range(0.0, 0.4)
        pinned_max = _x_range(win)[1]

        win.set_live_follow(True)  # kullanici "sona don" dedi

        _pump_to(win, qtbot, 12)
        resumed_max = _x_range(win)[1]
    finally:
        win.stop_live_stream()

    assert resumed_max > pinned_max  # sona yetisti


# --------------------------------------------------------------------------- #
# takip kendi kendini kapatmaz
# --------------------------------------------------------------------------- #


def test_the_follow_scroll_does_not_switch_itself_off(win: MainWindow, qtbot: QtBot) -> None:
    """Programatik kaydırma `x_range_changed` yaymaz; takip açık kalır."""
    try:
        _start(win, qtbot, wanted=12)
        assert win.live_follow is True  # onlarca karede bir kez bile kapanmadi
    finally:
        win.stop_live_stream()


def test_navigation_without_a_live_stream_leaves_following_untouched(win: MainWindow) -> None:
    """Kayıtlı dosyada gezinmek canlı takip bayrağını değiştirmez."""
    assert win.live_follow is True
    win.plot_panel.set_x_range(0.0, 1.0)
    assert win.live_follow is True

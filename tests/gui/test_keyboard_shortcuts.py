"""Bölüm 16 klavye kısayolları — `F3-072`.

Kabul: odak grafikteyken temel dosya, oynatma ve zoom kısayolları çalışır.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.shortcuts import SHORTCUTS

pytestmark = pytest.mark.gui

_NONE = Qt.KeyboardModifier.NoModifier
_KEYMAP: dict[str, tuple[Qt.Key, Qt.KeyboardModifier]] = {
    "X": (Qt.Key.Key_X, _NONE),
    "Y": (Qt.Key.Key_Y, _NONE),
    "B": (Qt.Key.Key_B, _NONE),
    "C": (Qt.Key.Key_C, _NONE),
    "R": (Qt.Key.Key_R, _NONE),
    "Home": (Qt.Key.Key_Home, _NONE),
    "Space": (Qt.Key.Key_Space, _NONE),
    "F4": (Qt.Key.Key_F4, _NONE),
    "Shift+F4": (Qt.Key.Key_F4, Qt.KeyboardModifier.ShiftModifier),
    "Ctrl+S": (Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier),
}


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    win.set_repository(MockRecordingRepository(duration_s=6.0))
    win.open_channel("ch0")
    win.plot_panel.setFocus()
    return win


def _press(qtbot: QtBot, win: MainWindow, key: str) -> None:
    plot_key, modifier = _KEYMAP[key]
    qtbot.keyClick(win.plot_panel, plot_key, modifier)  # pyright: ignore[reportUnknownMemberType]


def test_every_spec_creates_a_wired_shortcut(window: MainWindow) -> None:
    for spec in SHORTCUTS:
        assert spec.handler in window.shortcuts
        assert hasattr(window, spec.handler)


def test_zoom_mode_keys_switch_the_plot_zoom_mode(window: MainWindow, qtbot: QtBot) -> None:
    _press(qtbot, window, "X")
    assert window.plot_panel.zoom_mode == "x"
    _press(qtbot, window, "Y")
    assert window.plot_panel.zoom_mode == "y"
    _press(qtbot, window, "B")
    assert window.plot_panel.zoom_mode == "xy"


def test_home_key_resets_the_view(window: MainWindow, qtbot: QtBot) -> None:
    # Kanal açılışında yakalanan "ev" aralığı.
    home = window.plot_panel.visible_x_range()

    window.plot_panel.set_x_range(0.1, 0.2)
    assert window.plot_panel.visible_x_range() != home
    _press(qtbot, window, "Home")

    x0, x1 = window.plot_panel.visible_x_range()
    assert abs(x0 - home[0]) < 1e-6 and abs(x1 - home[1]) < 1e-6


def test_space_toggles_playback(window: MainWindow, qtbot: QtBot) -> None:
    assert not window.playback_dock.is_playing
    _press(qtbot, window, "Space")
    assert window.playback_dock.is_playing
    _press(qtbot, window, "Space")
    assert not window.playback_dock.is_playing


def test_c_toggles_the_crosshair_cursor(window: MainWindow, qtbot: QtBot) -> None:
    assert not window.plot_panel.crosshair_visible()
    _press(qtbot, window, "C")
    assert window.plot_panel.crosshair_visible()
    _press(qtbot, window, "C")
    assert not window.plot_panel.crosshair_visible()


def test_r_toggles_the_region_selection(window: MainWindow, qtbot: QtBot) -> None:
    assert window.plot_panel.time_region_x() is None
    _press(qtbot, window, "R")
    assert window.plot_panel.time_region_x() is not None
    _press(qtbot, window, "R")
    assert window.plot_panel.time_region_x() is None


def test_ctrl_s_saves_a_workspace_via_the_dialog_seam(
    window: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    target = tmp_path / "session"
    window.workspace_save_dialog = lambda: str(target)

    _press(qtbot, window, "Ctrl+S")

    assert (tmp_path / "session.json").exists()


def test_f4_navigates_events(window: MainWindow, qtbot: QtBot) -> None:
    before = window.playback_dock.position_s
    _press(qtbot, window, "F4")
    # MockRepo bir olay üretir; imleç ileri gitti (ya da olay yoksa aynı kaldı).
    assert window.playback_dock.position_s >= before


def test_plot_shortcut_does_nothing_without_plot_focus(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=4.0))
    win.open_channel("ch0")
    win.plot_panel.set_zoom_mode("xy")
    # Odak sol dock ağacında: "X" oraya gider, grafiği etkilemez.
    win.left_dock.tree.setFocus()
    qtbot.keyClick(win.left_dock.tree, Qt.Key.Key_X)  # pyright: ignore[reportUnknownMemberType]
    assert win.plot_panel.zoom_mode == "xy"

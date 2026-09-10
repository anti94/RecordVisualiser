"""Görünüm ayarları için undo/redo — `F3-041`.

Kabul: renk veya eksen değişikliği geri alınıp yeniden uygulanır.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
_EPS = 1e-6


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    win.left_dock.channel_activated.emit("ch0")
    return win


# -- renk degisikligi -----------------------------------------


def test_series_colour_change_undo_and_redo(window: MainWindow) -> None:
    original = window.plot_panel.series_color("ch0")
    assert original != "#ff0000"

    window.apply_series_color("ch0", "#ff0000")
    assert window.plot_panel.series_color("ch0") == "#ff0000"

    assert window.undo_view_change() is True
    assert window.plot_panel.series_color("ch0") == original

    assert window.redo_view_change() is True
    assert window.plot_panel.series_color("ch0") == "#ff0000"


def test_applying_the_same_colour_adds_no_history_entry(window: MainWindow) -> None:
    current = window.plot_panel.series_color("ch0")

    window.apply_series_color("ch0", current)

    assert window.undo_view_change() is False


# -- eksen degisikligi --------------------------------------


def _apply_axis(window: MainWindow, y_min: float, y_max: float) -> None:
    inspector = window.right_dock.inspector
    inspector.axis_combo.setCurrentIndex(0)  # Left axis
    inspector.y_min_spin.setValue(y_min)
    inspector.y_max_spin.setValue(y_max)
    inspector.apply_button.click()


def test_axis_range_change_undo_and_redo(window: MainWindow) -> None:
    _, _, y0_min, y0_max = window.plot_panel.visible_range()

    _apply_axis(window, -5.0, 12.0)
    _, _, y1_min, y1_max = window.plot_panel.visible_range()
    assert abs(y1_min - (-5.0)) < _EPS and abs(y1_max - 12.0) < _EPS

    assert window.undo_view_change() is True
    _, _, yr_min, yr_max = window.plot_panel.visible_range()
    assert abs(yr_min - y0_min) < 1e-3 and abs(yr_max - y0_max) < 1e-3

    assert window.redo_view_change() is True
    _, _, yb_min, yb_max = window.plot_panel.visible_range()
    assert abs(yb_min - (-5.0)) < _EPS and abs(yb_max - 12.0) < _EPS


def test_inspector_apply_is_undoable(window: MainWindow) -> None:
    inspector = window.right_dock.inspector
    _, _, y0_min, y0_max = window.plot_panel.visible_range()

    inspector.axis_combo.setCurrentIndex(0)
    inspector.y_min_spin.setValue(-8.0)
    inspector.y_max_spin.setValue(3.0)
    inspector.apply_button.click()

    assert abs(window.plot_panel.visible_range()[2] - (-8.0)) < _EPS
    assert window.undo_view_change() is True
    _, _, yr_min, yr_max = window.plot_panel.visible_range()
    assert abs(yr_min - y0_min) < 1e-3 and abs(yr_max - y0_max) < 1e-3


# -- gecmis kanal degisince temizlenir --------------------


def test_switching_channel_clears_the_history(window: MainWindow) -> None:
    window.apply_series_color("ch0", "#00ff00")
    _apply_axis(window, -1.0, 1.0)

    window.left_dock.channel_activated.emit("ch5")

    assert window.undo_view_change() is False
    assert window.redo_view_change() is False

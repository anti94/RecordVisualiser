"""Üç sütunlu ana pencere düzeni — `F1-022`.

Kabul: solda yaklaşık 200 px, sağda 300 px panel; merkez esnek alan.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import (
    DEFAULT_WINDOW_SIZE,
    LEFT_COLUMN_MIN_WIDTH,
    LEFT_COLUMN_WIDTH,
    RIGHT_COLUMN_MIN_WIDTH,
    RIGHT_COLUMN_WIDTH,
    MainWindow,
)

pytestmark = pytest.mark.gui

#: Qt dock genisliklerini kenarlik/ayirici payiyla yerlestirir; tam esitlik
#: beklenmez, mockup orani korunmali.
WIDTH_TOLERANCE = 40


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.resize(*DEFAULT_WINDOW_SIZE)
    win.show()
    qtbot.waitExposed(win)
    win.apply_default_layout()
    return win


def test_three_columns_exist(window: MainWindow) -> None:
    assert window.left_dock is not None
    assert window.right_dock is not None
    assert window.centralWidget() is window.center


def test_left_column_is_about_200px(window: MainWindow) -> None:
    left, _, _ = window.column_widths()
    assert abs(left - LEFT_COLUMN_WIDTH) <= WIDTH_TOLERANCE, f"sol sutun {left} px"


def test_right_column_is_about_300px(window: MainWindow) -> None:
    _, _, right = window.column_widths()
    assert abs(right - RIGHT_COLUMN_WIDTH) <= WIDTH_TOLERANCE, f"sag sutun {right} px"


def test_center_takes_the_rest(window: MainWindow) -> None:
    left, center, right = window.column_widths()
    assert center > left + right, "merkez en genis alan olmali"
    assert left + center + right <= DEFAULT_WINDOW_SIZE[0]


def test_only_center_grows_when_window_widens(window: MainWindow, qtbot: QtBot) -> None:
    """Pencere genişleyince yan sütunlar sabit kalmalı, merkez büyümeli."""
    before_left, before_center, before_right = window.column_widths()

    window.resize(DEFAULT_WINDOW_SIZE[0] + 400, DEFAULT_WINDOW_SIZE[1])
    qtbot.waitUntil(lambda: window.center.width() > before_center, timeout=2000)

    after_left, after_center, after_right = window.column_widths()
    assert after_center > before_center
    assert abs(after_left - before_left) <= WIDTH_TOLERANCE
    assert abs(after_right - before_right) <= WIDTH_TOLERANCE


def test_columns_are_in_correct_areas(window: MainWindow) -> None:
    assert window.dockWidgetArea(window.left_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.right_dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_minimum_widths_protect_readability(window: MainWindow) -> None:
    """Asgari genişlik tabanın altına inmemeli ve öntanımlı genişliği aşmamalı.

    Panel içeriği (düğme, form etiketleri) kendi asgari genişliğini dayatabilir;
    önemli olan sütunun okunur kalması ve yine de mockup ölçüsüne oturabilmesi.
    """
    left_min = window.left_dock.minimumWidth()
    right_min = window.right_dock.minimumWidth()

    assert left_min >= LEFT_COLUMN_MIN_WIDTH, f"sol sutun tabani {left_min} px"
    assert left_min <= LEFT_COLUMN_WIDTH, "asgari genislik ontanimliyi asarsa sutun bozulur"
    assert right_min >= RIGHT_COLUMN_MIN_WIDTH, f"sag sutun tabani {right_min} px"
    assert right_min <= RIGHT_COLUMN_WIDTH


def test_docks_have_stable_object_names(window: MainWindow) -> None:
    """Workspace kaydı dock adlarına dayanır; adlar değişirse düzen geri yüklenemez."""
    assert window.left_dock.objectName() == "dock_data_explorer"
    assert window.right_dock.objectName() == "dock_right_column"


def test_reset_layout_restores_default_widths(window: MainWindow, qtbot: QtBot) -> None:
    window.resizeDocks([window.left_dock], [LEFT_COLUMN_WIDTH + 200], Qt.Orientation.Horizontal)
    qtbot.waitUntil(lambda: window.left_dock.width() > LEFT_COLUMN_WIDTH + 100, timeout=2000)

    window.apply_default_layout()
    qtbot.waitUntil(
        lambda: abs(window.left_dock.width() - LEFT_COLUMN_WIDTH) <= WIDTH_TOLERANCE,
        timeout=2000,
    )


def test_state_can_be_saved_and_restored(window: MainWindow) -> None:
    """Workspace için gereken Qt durum serileştirmesi çalışmalı."""
    state = window.saveState()
    assert not state.isEmpty()
    assert window.restoreState(state)

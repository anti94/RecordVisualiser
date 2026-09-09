"""Mockup ana analiz sekmeleri — `F1-038`.

Kabul: sekiz sekme aynı sıradadır; henüz desteklenmeyen sekmeler açıkça pasiftir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.view_tab_bar import TAB_TITLES, ViewTabBar

pytestmark = pytest.mark.gui

EXPECTED_ORDER = (
    "Time Series",
    "Spectrum",
    "Spectrogram",
    "Cross Analysis",
    "BIT / Status",
    "Transmission",
    "3D View",
    "Report",
)


@pytest.fixture()
def bar(qtbot: QtBot) -> ViewTabBar:
    widget = ViewTabBar()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_eight_tabs_in_mockup_order(bar: ViewTabBar) -> None:
    assert TAB_TITLES == EXPECTED_ORDER
    assert bar.tab_titles() == list(EXPECTED_ORDER)
    assert bar.count() == 8


def test_time_series_is_selected_by_default(bar: ViewTabBar) -> None:
    assert bar.tabText(bar.currentIndex()) == "Time Series"


def test_only_time_series_is_enabled_in_this_phase(bar: ViewTabBar) -> None:
    """Kabul kriteri: desteklenmeyen sekmeler açıkça pasiftir."""
    assert bar.enabled_tabs() == ["Time Series"]
    for index, title in enumerate(EXPECTED_ORDER):
        if title == "Time Series":
            assert bar.isTabEnabled(index)
        else:
            assert not bar.isTabEnabled(index), f"{title} henuz pasif olmali"


def test_disabled_tabs_explain_why(bar: ViewTabBar) -> None:
    for index, title in enumerate(EXPECTED_ORDER):
        if title == "Time Series":
            continue
        assert bar.tabToolTip(index) == NOT_YET_AVAILABLE


def test_tabs_are_not_hidden() -> None:
    """Pasif sekme gizlenmiyor, yalnız tıklanamıyor."""
    bar = ViewTabBar()
    for index in range(bar.count()):
        assert bar.tabText(index) != ""


def test_bar_is_used_in_the_main_window(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    assert isinstance(win.view_tabs, ViewTabBar)


def test_bar_is_above_the_center_stack(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    bar_top = win.view_tabs.mapTo(win, win.view_tabs.rect().topLeft()).y()
    stack_top = win.center_stack.mapTo(win, win.center_stack.rect().topLeft()).y()
    assert bar_top < stack_top

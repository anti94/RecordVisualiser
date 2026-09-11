"""Menü ve toolbar eylem iskeleti — `F1-023`.

Kabul: File, View, Analysis, Tools ve Help eylemleri erişilebilirdir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QMenu
from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.actions import MENU_SPECS, NOT_YET_AVAILABLE
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

EXPECTED_MENUS = ["&File", "&View", "&Analysis", "&Tools", "&Help"]


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


def menus(window: MainWindow) -> list[QMenu]:
    return [window.menu(spec.name) for spec in MENU_SPECS]


def menu_titles(window: MainWindow) -> list[str]:
    return [menu.title() for menu in menus(window)]


def test_all_five_menus_exist(window: MainWindow) -> None:
    assert menu_titles(window) == EXPECTED_MENUS


def test_menus_have_stable_object_names(window: MainWindow) -> None:
    names = [menu.objectName() for menu in menus(window)]
    assert names == [
        "menu_file",
        "menu_view",
        "menu_analysis",
        "menu_tools",
        "menu_help",
    ]


def test_file_actions_are_reachable(window: MainWindow) -> None:
    for name in ("action_open", "action_close", "action_export", "action_exit"):
        assert window.action(name) is not None


def test_open_action_has_shortcut(window: MainWindow) -> None:
    assert window.action("action_open").shortcut().toString() == "Ctrl+O"
    assert window.action("action_exit").shortcut().toString() == "Ctrl+Q"


def test_unimplemented_analysis_actions_are_disabled_with_reason(
    window: MainWindow,
) -> None:
    """İşlevi olmayan eylem gizlenmiyor, pasif ve nedeni yazıyor."""
    analysis_menu = next(m for m in menus(window) if m.objectName() == "menu_analysis")
    menu_action_names = {a.objectName() for a in analysis_menu.actions()}

    for name in ("action_fft", "action_spectrogram", "action_filter", "action_statistics"):
        action = window.action(name)
        assert action.isEnabled() is False, f"{name} etkin gorunmemeli"
        assert NOT_YET_AVAILABLE in action.toolTip()
        assert name in menu_action_names, f"{name} menuden gizlenmemeli"


def test_actions_requiring_recording_are_disabled_at_start(window: MainWindow) -> None:
    for name in ("action_close", "action_export"):
        action = window.action(name)
        assert not action.isEnabled()
        assert action.toolTip() != ""


def test_toolbar_contains_quick_actions(window: MainWindow) -> None:
    """Şerit sırası sabittir; `F5-019` bağlantı, `F5-032` kayıt ikilisini ekledi."""
    names = [a.objectName() for a in window.toolbar.actions()]
    assert names == [
        "action_open",
        "action_export",
        "action_connect",
        "action_disconnect",
        "action_record",
        "action_stop_recording",
        "action_reset_layout",
        "action_settings",
    ]
    assert window.toolbar.objectName() == "toolbar_quick_tools"


def test_toolbar_and_menu_share_the_same_action(window: MainWindow) -> None:
    """Aynı QAction paylaşıldığı için bir yerde pasifse her yerde pasif."""
    toolbar_open = next(a for a in window.toolbar.actions() if a.objectName() == "action_open")
    assert toolbar_open is window.action("action_open")


def test_view_actions_toggle_docks(window: MainWindow, qtbot: QtBot) -> None:
    action = window.action("action_toggle_data_explorer")
    assert action.isChecked()
    assert window.left_dock.isVisible()

    action.setChecked(False)
    qtbot.waitUntil(lambda: not window.left_dock.isVisible(), timeout=2000)

    action.setChecked(True)
    qtbot.waitUntil(lambda: window.left_dock.isVisible(), timeout=2000)


def test_closing_dock_unchecks_its_action(window: MainWindow, qtbot: QtBot) -> None:
    """Panel doğrudan kapatılırsa menüdeki işaret de kalkmalı."""
    action = window.action("action_toggle_right_column")
    window.right_dock.close()
    qtbot.waitUntil(lambda: not action.isChecked(), timeout=2000)


def test_reset_layout_action_is_connected(window: MainWindow, qtbot: QtBot) -> None:
    from PySide6.QtCore import Qt

    from sonar_analyzer.ui.main_window import LEFT_COLUMN_WIDTH

    window.resizeDocks([window.left_dock], [LEFT_COLUMN_WIDTH + 200], Qt.Orientation.Horizontal)
    qtbot.waitUntil(lambda: window.left_dock.width() > LEFT_COLUMN_WIDTH + 100, timeout=2000)

    window.action("action_reset_layout").trigger()
    qtbot.waitUntil(lambda: abs(window.left_dock.width() - LEFT_COLUMN_WIDTH) <= 40, timeout=2000)


def test_unknown_action_raises(window: MainWindow) -> None:
    with pytest.raises(KeyError, match="Tanimsiz eylem"):
        window.action("action_yok")


def test_unknown_menu_raises(window: MainWindow) -> None:
    with pytest.raises(KeyError, match="Tanimsiz menu"):
        window.menu("menu_yok")


def test_menu_bar_order_matches_specs(window: MainWindow) -> None:
    """Menü çubuğundaki sıra tanım sırasıyla aynı olmalı."""
    bar_titles: list[str] = []
    for action in window.menuBar().actions():
        # Once degiskene atanir: isinstance daralmasi cagri ifadesine degil
        # degiskene uygulanir.
        candidate = action.menu()
        if isinstance(candidate, QMenu):
            bar_titles.append(candidate.title())
    assert bar_titles == [spec.title for spec in MENU_SPECS]

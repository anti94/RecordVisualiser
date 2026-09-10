"""Kanal sağ tık eylemleri — `F3-018`.

Kabul: Plot, Inspect ve Copy Path **doğru seçime** uygulanır — menü,
imlecin altındaki kanala bağlanır, o an seçili olana değil.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.docks.data_explorer import CHANNEL_MENU_ACTIONS
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


# -- ortak yol: apply_channel_context_action dogru kanala uygulanir -------


def test_plot_action_plots_exactly_that_channel(window: MainWindow) -> None:
    window.left_dock.apply_channel_context_action("ch5", "Plot")

    assert window.plot_panel.plotted_channel_ids() == ["ch5"]
    assert window.center_shows_plot


def test_inspect_action_shows_that_channel_without_plotting(window: MainWindow) -> None:
    window.left_dock.apply_channel_context_action("ch3", "Inspect")

    assert window.right_dock.inspector_is_open
    assert window.right_dock.inspector.field_value("Path") == "Sensors/Accelerometer/Y"
    assert window.plot_panel.plotted_channel_ids() == [], "Inspect grafigi degistirmez"


def test_copy_path_action_emits_the_selected_channel_path(window: MainWindow) -> None:
    received: list[str] = []
    window.left_dock.channel_path_copied.connect(received.append)

    window.left_dock.apply_channel_context_action("ch5", "Copy Path")

    assert received == ["Acoustic/Hydrophone 1"]
    log = "\n".join(window.bottom_dock.log_lines())
    assert "Acoustic/Hydrophone 1" in log


def test_copy_path_writes_to_the_clipboard(window: MainWindow) -> None:
    from PySide6.QtGui import QGuiApplication

    window.left_dock.apply_channel_context_action("ch6", "Copy Path")

    assert QGuiApplication.clipboard().text() == "Navigation/Depth"


def test_unknown_action_is_rejected(window: MainWindow) -> None:
    with pytest.raises(ValueError, match="Bilinmeyen kanal eylemi"):
        window.left_dock.apply_channel_context_action("ch0", "Nonsense")


# -- gercek menu: imlec altindaki kanala baglanir, secime degil ----------


def _menu_at_channel(window: MainWindow, channel_id: str) -> None:
    tree = window.left_dock.tree
    tree.expandAll()
    item = window.left_dock.item_for_channel(channel_id)
    assert item is not None
    tree.scrollToItem(item)
    pos = tree.visualItemRect(item).center()
    tree.customContextMenuRequested.emit(pos)


def _trigger(window: MainWindow, action_text: str) -> None:
    menu = window.left_dock.context_menu
    assert menu is not None
    match = [a for a in menu.actions() if a.text() == action_text]
    assert match, f"menude {action_text!r} yok"
    match[0].trigger()


def test_menu_lists_the_three_actions_in_order(window: MainWindow) -> None:
    _menu_at_channel(window, "ch0")

    menu = window.left_dock.context_menu
    assert menu is not None
    assert [a.text() for a in menu.actions()] == list(CHANNEL_MENU_ACTIONS)


def test_menu_plot_applies_to_the_right_clicked_channel_not_the_selected_one(
    window: MainWindow,
) -> None:
    # ch0 secili, ama ch6'ya sag tiklaniyor: eylem ch6'ya uygulanmali.
    selected = window.left_dock.item_for_channel("ch0")
    assert selected is not None
    selected.setSelected(True)

    _menu_at_channel(window, "ch6")
    _trigger(window, "Plot")

    assert window.plot_panel.plotted_channel_ids() == ["ch6"]


def test_menu_copy_path_applies_to_the_right_clicked_channel(window: MainWindow) -> None:
    received: list[str] = []
    window.left_dock.channel_path_copied.connect(received.append)

    _menu_at_channel(window, "ch1")
    _trigger(window, "Copy Path")

    assert received == ["Sensors/Temperature"]


def test_right_click_on_a_group_node_opens_no_menu(window: MainWindow) -> None:
    tree = window.left_dock.tree
    tree.expandAll()
    top = tree.topLevelItem(0)
    assert top is not None
    tree.scrollToItem(top)

    tree.customContextMenuRequested.emit(tree.visualItemRect(top).center())

    assert window.left_dock.context_menu is None


def test_data_tree_tab_also_has_the_channel_menu(window: MainWindow) -> None:
    data_tree = window.left_dock.data_tree
    recording_item = data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    group_item = device_item.child(0)
    assert group_item is not None
    data_tree.expandItem(group_item)  # F3-010: yapraklar lazy
    leaf = group_item.child(0)
    assert leaf is not None
    data_tree.scrollToItem(leaf)

    data_tree.customContextMenuRequested.emit(data_tree.visualItemRect(leaf).center())

    menu = window.left_dock.context_menu
    assert menu is not None
    assert [a.text() for a in menu.actions()] == list(CHANNEL_MENU_ACTIONS)

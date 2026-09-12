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


# -- plan Bolum 5.2: bes eylem, belgelenen sirayla -----------------------


def test_the_menu_offers_every_action_the_plan_lists() -> None:
    """Plan Bölüm 5.2 ve kabul listesi 2.11 aynı beş eylemi sayar."""
    assert CHANNEL_MENU_ACTIONS == (
        "Plot",
        "Inspect",
        "Add to Existing Plot",
        "Export",
        "Copy Path",
    )


def test_add_to_existing_plot_keeps_the_series_already_drawn(window: MainWindow) -> None:
    """`Plot` grafiği o kanala çevirir; `Add to Existing Plot` eklemelidir.

    İkisini tek eyleme indirmek, bir kanalı karşılaştırmak isteyen
    kullanıcının önceki seriyi kaybetmesi demekti.
    """
    window.left_dock.apply_channel_context_action("ch0", "Plot")
    assert window.plot_panel.plotted_channel_ids() == ["ch0"]

    window.left_dock.apply_channel_context_action("ch1", "Add to Existing Plot")

    assert window.plot_panel.plotted_channel_ids() == ["ch0", "ch1"]


def test_plot_replaces_where_add_appends(window: MainWindow) -> None:
    """Karşı yön: `Plot` gerçekten değiştiriyor mu."""
    window.left_dock.apply_channel_context_action("ch0", "Plot")
    window.left_dock.apply_channel_context_action("ch1", "Plot")

    assert window.plot_panel.plotted_channel_ids() == ["ch1"]


def test_add_to_existing_plot_reports_what_it_added(window: MainWindow) -> None:
    window.left_dock.apply_channel_context_action("ch2", "Add to Existing Plot")

    log = "\n".join(window.bottom_dock.log_lines())
    assert "1 kanal grafige eklendi" in log


def test_export_action_exports_the_chosen_channel_not_the_focused_one(
    window: MainWindow, tmp_path: Path, qtbot: QtBot
) -> None:
    """Sağ tıklanan kanal ile grafikteki kanal farklıysa, seçilen kazanmalı."""
    window.left_dock.apply_channel_context_action("ch0", "Plot")

    target = tmp_path / "secilen.csv"
    window.export_save_dialog = lambda _t, _f: str(target)
    window.export_confirm_overwrite = lambda _p: True

    window.left_dock.apply_channel_context_action("ch3", "Export")
    qtbot.waitUntil(target.is_file, timeout=10_000)

    text = target.read_text(encoding="utf-8")
    assert "channel_id=ch3" in text
    assert "channel_id=ch0" not in text


def test_export_action_ignores_an_unknown_channel(window: MainWindow) -> None:
    """Var olmayan kanal için dosya seçtirmek, boş bir dosya üretirdi."""
    asked: list[str] = []

    def dialog(title: str, _filter: str) -> str:
        asked.append(title)
        return ""

    window.export_save_dialog = dialog
    window.left_dock.channel_export_requested.emit("olmayan")

    assert asked == []


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

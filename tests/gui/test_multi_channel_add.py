"""Çoklu kanal ekleme eylemleri — `F3-016`.

Kabul: seçilen kanallar aynı grafikte açılır.

Not (plan Bölüm 5.3): "ayrı grafiklerde açma" çoklu-panel/tab altyapısı
kurulunca ele alınacak — bu iş yalnız **aynı** grafiğe toplu eklemeyi
kapsar. Toplu ekleme, tek kanal sürükle-bırağıyla (`F3-015`) aynı
`PlotPanel.add_channel` katmanını kullanır: var olan seriler korunur.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QTreeWidgetItem
from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.docks.data_explorer import selected_channel_ids
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


def _select(window: MainWindow, *channel_ids: str) -> None:
    for channel_id in channel_ids:
        item = window.left_dock.item_for_channel(channel_id)
        assert item is not None
        item.setSelected(True)


def _first_group_item(tree_item: QTreeWidgetItem) -> QTreeWidgetItem:
    child = tree_item.child(0)
    assert child is not None
    return child


# -- kabul kriteri: secilenler ayni grafikte -------------------------------


def test_adding_several_selected_channels_puts_them_on_one_plot(window: MainWindow) -> None:
    _select(window, "ch0", "ch5", "ch6")

    window.left_dock.add_selected_button.click()

    assert window.plot_panel.plotted_channel_ids() == ["ch0", "ch5", "ch6"]
    assert window.center_shows_plot


def test_multi_add_preserves_series_already_on_the_plot(window: MainWindow) -> None:
    leaf = window.left_dock.item_for_channel("ch1")
    assert leaf is not None
    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)
    assert window.plot_panel.plotted_channel_ids() == ["ch1"]

    _select(window, "ch0", "ch6")
    window.left_dock.add_selected_button.click()

    assert window.plot_panel.plotted_channel_ids() == ["ch1", "ch0", "ch6"]


def test_a_single_selected_channel_is_added_too(window: MainWindow) -> None:
    _select(window, "ch3")

    window.left_dock.add_selected_button.click()

    assert window.plot_panel.plotted_channel_ids() == ["ch3"]


# -- dugme etkinligi: yalnizca yaprak seciliyken --------------------------


def test_button_is_disabled_with_no_selection(window: MainWindow) -> None:
    assert not window.left_dock.add_selected_button.isEnabled()


def test_button_enables_when_a_leaf_is_selected(window: MainWindow) -> None:
    _select(window, "ch0")

    assert window.left_dock.add_selected_button.isEnabled()


def test_button_stays_disabled_when_only_a_group_is_selected(window: MainWindow) -> None:
    top = window.left_dock.tree.topLevelItem(0)
    assert top is not None
    top.setSelected(True)

    assert not window.left_dock.add_selected_button.isEnabled()


def test_selecting_a_group_and_a_leaf_adds_only_the_leaf(window: MainWindow) -> None:
    top = window.left_dock.tree.topLevelItem(0)
    assert top is not None
    top.setSelected(True)
    _select(window, "ch5")

    window.left_dock.add_selected_button.click()

    assert window.plot_panel.plotted_channel_ids() == ["ch5"]


def test_button_disables_again_after_closing_the_recording(window: MainWindow) -> None:
    _select(window, "ch0")
    assert window.left_dock.add_selected_button.isEnabled()

    window.close_active_recording()

    assert not window.left_dock.add_selected_button.isEnabled()


# -- Data Tree sekmesi de ayni komutu sunar ------------------------------


def test_data_tree_tab_multi_add_works(window: MainWindow) -> None:
    recording_item = window.left_dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = _first_group_item(recording_item)
    group_item = _first_group_item(device_item)
    window.left_dock.data_tree.expandItem(group_item)  # F3-010: yapraklar lazy

    leaves = [group_item.child(i) for i in range(group_item.childCount())]
    assert len(leaves) >= 2
    for leaf in leaves[:2]:
        assert leaf is not None
        leaf.setSelected(True)

    assert window.left_dock.add_selected_data_tree_button.isEnabled()
    window.left_dock.add_selected_data_tree_button.click()

    assert len(window.plot_panel.plotted_channel_ids()) == 2


# -- gecersiz / bilinmeyen kimlikler sessizce atlanir --------------------


def test_unknown_channel_ids_are_skipped(window: MainWindow) -> None:
    window.left_dock.channels_add_requested.emit(["yok-boyle", "ch0", "hic-yok"])

    assert window.plot_panel.plotted_channel_ids() == ["ch0"]


def test_selected_channel_ids_returns_each_leaf_once(window: MainWindow) -> None:
    _select(window, "ch6", "ch2", "ch0")

    ids = selected_channel_ids(window.left_dock.tree)

    assert set(ids) == {"ch0", "ch2", "ch6"}
    assert len(ids) == len(set(ids))

"""Klavye odak sırası ve yalnız-klavye ana akış — `F3-073`.

Kabul: ana akış yalnız klavyeyle tamamlanabilir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"


def _first_channel_leaf(win: MainWindow):  # type: ignore[no-untyped-def]
    tree = win.left_dock.tree
    top = tree.topLevelItem(0)
    assert top is not None
    return top if top.childCount() == 0 else top.child(0)


def test_main_flow_completes_with_keyboard_only(qtbot: QtBot, tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    shutil.copyfile(FIXTURE, target)

    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]

    # 1) Kaydı klavyeyle aç: "Open .bin File" düğmesine odaklan, Space ile bas.
    win.left_dock.open_button.setFocus()
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        qtbot.keyClick(  # pyright: ignore[reportUnknownMemberType]
            win.left_dock.open_button, Qt.Key.Key_Space
        )

    # 2) Kanal ağacına Tab ile geç, ilk kanalı seç ve Enter ile çiz.
    win.left_dock.search.setFocus()
    win.focusNextChild()
    assert win.focusWidget() is win.left_dock.tree

    leaf = _first_channel_leaf(win)
    win.left_dock.tree.setCurrentItem(leaf)
    qtbot.keyClick(  # pyright: ignore[reportUnknownMemberType]
        win.left_dock.tree, Qt.Key.Key_Return
    )

    # 3) Grafik artık bir kanal gösteriyor — akış tamamlandı.
    assert win.plot_panel.plotted_channel_ids() != []


def test_left_dock_tab_order_is_open_then_search_then_tree(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    win.left_dock.open_button.setFocus()
    win.focusNextChild()
    assert win.focusWidget() is win.left_dock.search
    win.focusNextChild()
    assert win.focusWidget() is win.left_dock.tree


def test_plot_can_hold_keyboard_focus(qtbot: QtBot) -> None:
    """`F3-073`: grafik artık Tab ile durulabilir ve kısayolları için odak alır."""
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    assert win.plot_panel.focusPolicy() != Qt.FocusPolicy.NoFocus
    win.plot_panel.setFocus()
    assert win.focusWidget() is win.plot_panel


def test_key_controls_carry_accessible_names(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)

    assert win.left_dock.open_button.accessibleName()
    assert win.left_dock.tree.accessibleName()
    assert win.left_dock.tree.accessibleDescription()
    assert win.plot_panel.accessibleName()
    assert win.plot_panel.accessibleDescription()
    assert win.playback_dock.buttons["button_play"].accessibleName()
    assert win.bottom_dock.events.accessibleName()


def test_enter_on_a_channel_row_plots_it(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    win.set_repository(MockRecordingRepository(duration_s=4.0))

    leaf = _first_channel_leaf(win)
    win.left_dock.tree.setFocus()
    win.left_dock.tree.setCurrentItem(leaf)
    qtbot.keyClick(  # pyright: ignore[reportUnknownMemberType]
        win.left_dock.tree, Qt.Key.Key_Return
    )

    assert win.plot_panel.plotted_channel_ids() != []

"""Kanal sürükle-bırak akışı — `F3-015`.

Kabul: geçerli kanal mevcut veya boş grafiğe bırakılabilir.

Gerçek bir `QDrag.exec()` fare fiziğiyle sürükleme testlerde bloklar; bunun
yerine iki katman ayrı doğrulanır:

1. Kaynak: `_DraggableChannelTree.mimeData()` yaprak için geçerli, grup/
   kayıt/cihaz düğümü için boş `QMimeData` üretiyor mu (`test_data_explorer`
   modülü değil, burada — MIME sözleşmesi sürükle-bırağın parçası).
2. Hedef: `PlotPanel.eventFilter()` `DragEnter`/`Drop` olaylarını doğrudan
   inşa edilmiş `QDragEnterEvent`/`QDropEvent` ile alıp `channel_dropped`
   sinyalini doğru yayıyor mu; `MainWindow._on_channel_dropped` bunu
   `add_channel()`'a (EKLEME, `set_channel` gibi SIFIRLAMA değil) doğru
   yönlendiriyor mu.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.drag_drop import CHANNEL_MIME_TYPE, decode_channel_id, encode_channel_id
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _channel_mime(channel_id: str) -> QMimeData:
    mime = QMimeData()
    mime.setData(CHANNEL_MIME_TYPE, encode_channel_id(channel_id))
    return mime


def _drop_event(mime: QMimeData) -> QDropEvent:
    return QDropEvent(
        QPoint(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _drag_enter_event(mime: QMimeData) -> QDragEnterEvent:
    return QDragEnterEvent(
        QPoint(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# -- hedef: PlotPanel olay filtresi -----------------------------------------


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_drag_enter_with_valid_channel_mime_is_accepted(panel: PlotPanel) -> None:
    # `mime` bir isimli yerel değişkende tutulmalı: PySide6/shiboken, sahipsiz
    # bir QMimeData'yı yalnız Qt olayının argümanı olarak geçici tutulursa
    # hemen çöp toplar — olay sonra sarkan bir işaretçiye (dangling pointer)
    # sahip olur (bkz. worklog: erişim ihlali/`access violation`).
    mime = _channel_mime("ch0")
    event = _drag_enter_event(mime)

    handled = panel.eventFilter(panel.plot, event)

    assert handled
    assert event.isAccepted()


def test_drag_enter_without_channel_mime_is_ignored(panel: PlotPanel) -> None:
    mime = QMimeData()
    event = _drag_enter_event(mime)

    handled = panel.eventFilter(panel.plot, event)

    assert not handled


def test_drop_with_valid_channel_mime_emits_channel_dropped(panel: PlotPanel) -> None:
    received: list[str] = []
    panel.channel_dropped.connect(received.append)
    mime = _channel_mime("ch3")
    event = _drop_event(mime)

    handled = panel.eventFilter(panel.plot, event)

    assert handled
    assert received == ["ch3"]


def test_drop_without_channel_mime_emits_nothing(panel: PlotPanel) -> None:
    """Grup/kayıt/cihaz sürüklemesi (boş `QMimeData`) reddedilir — kabul kriteri."""
    received: list[str] = []
    panel.channel_dropped.connect(received.append)
    mime = QMimeData()
    event = _drop_event(mime)

    handled = panel.eventFilter(panel.plot, event)

    assert not handled
    assert received == []


# -- kabul kriteri: gercek dosyadan bosk / dolu grafige birakma ------------


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


def test_dropping_a_channel_on_the_empty_plot_adds_it_as_the_sole_series(
    window: MainWindow,
) -> None:
    """Kabul kriteri (ilk yarı): geçerli kanal BOŞ grafiğe bırakılabilir."""
    assert window.plot_panel.plotted_channel_ids() == []

    window.plot_panel.channel_dropped.emit("ch0")

    assert window.plot_panel.plotted_channel_ids() == ["ch0"]
    assert window.center_shows_plot


def test_dropping_a_second_channel_adds_it_without_removing_the_first(
    window: MainWindow,
) -> None:
    """Kabul kriteri (ikinci yarı): geçerli kanal MEVCUT grafiğe bırakılabilir."""
    window.plot_panel.channel_dropped.emit("ch0")

    window.plot_panel.channel_dropped.emit("ch6")

    assert window.plot_panel.plotted_channel_ids() == ["ch0", "ch6"]


def test_dropping_the_same_channel_twice_updates_in_place(window: MainWindow) -> None:
    window.plot_panel.channel_dropped.emit("ch0")

    window.plot_panel.channel_dropped.emit("ch0")

    assert window.plot_panel.plotted_channel_ids() == ["ch0"]


def test_dropping_an_unknown_channel_id_is_a_harmless_no_op(window: MainWindow) -> None:
    window.plot_panel.channel_dropped.emit("hic-boyle-bir-kanal-yok")

    assert window.plot_panel.plotted_channel_ids() == []
    assert not window.center_shows_plot


def test_double_click_still_replaces_while_drop_still_adds(window: MainWindow) -> None:
    """`open_channel` (çift tık) SIFIRLAR, sürükleme EKLER — iki yol farklı davranır."""
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None
    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)
    assert window.plot_panel.plotted_channel_ids() == ["ch0"]

    window.plot_panel.channel_dropped.emit("ch6")
    assert window.plot_panel.plotted_channel_ids() == ["ch0", "ch6"]

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)
    assert window.plot_panel.plotted_channel_ids() == ["ch0"]


# -- kaynak: _DraggableChannelTree MIME uretimi -----------------------------


def test_leaf_item_produces_valid_channel_mime_data(window: MainWindow) -> None:
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None

    mime = window.left_dock.tree.mimeData([leaf])

    assert mime.hasFormat(CHANNEL_MIME_TYPE)
    assert decode_channel_id(bytes(mime.data(CHANNEL_MIME_TYPE).data())) == "ch0"


def test_group_item_produces_no_channel_mime_data(window: MainWindow) -> None:
    """Yaprak olmayan (grup/kayıt/cihaz) düğüm sürüklemesi geçersiz kanal üretir."""
    recording_item = window.left_dock.data_tree.topLevelItem(0)
    assert recording_item is not None

    mime = window.left_dock.data_tree.mimeData([recording_item])

    assert not mime.hasFormat(CHANNEL_MIME_TYPE)

"""Data Explorer paneli — `F1-024`.

Kabul: panel açılır, kapanır ve taşınır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.data_explorer import (
    DOCK_OBJECT_NAME,
    EMPTY_VALUE,
    SUMMARY_FIELDS,
    DataExplorerDock,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


# -- panel yasam dongusu ---------------------------------------------------


def test_dock_is_used_as_left_column(window: MainWindow) -> None:
    assert isinstance(window.left_dock, DataExplorerDock)
    assert window.left_dock.objectName() == DOCK_OBJECT_NAME


def test_dock_can_be_closed_and_reopened(window: MainWindow, qtbot: QtBot) -> None:
    assert window.left_dock.isVisible()

    window.left_dock.close()
    qtbot.waitUntil(lambda: not window.left_dock.isVisible(), timeout=2000)

    window.left_dock.show()
    qtbot.waitUntil(lambda: window.left_dock.isVisible(), timeout=2000)


def test_dock_can_float_and_dock_again(window: MainWindow, qtbot: QtBot) -> None:
    """Taşınabilirlik: panel pencereden ayrılıp geri yerleşebilmeli."""
    window.left_dock.setFloating(True)
    qtbot.waitUntil(lambda: window.left_dock.isFloating(), timeout=2000)

    window.left_dock.setFloating(False)
    qtbot.waitUntil(lambda: not window.left_dock.isFloating(), timeout=2000)
    assert window.dockWidgetArea(window.left_dock) == Qt.DockWidgetArea.LeftDockWidgetArea


def test_dock_can_move_to_right_area(window: MainWindow) -> None:
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.left_dock)
    assert window.dockWidgetArea(window.left_dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_dock_features_allow_move_close_float(dock: DataExplorerDock) -> None:
    features = dock.features()
    assert features & QDockWidget.DockWidgetFeature.DockWidgetMovable
    assert features & QDockWidget.DockWidgetFeature.DockWidgetClosable
    assert features & QDockWidget.DockWidgetFeature.DockWidgetFloatable


# -- icerik ---------------------------------------------------------------


def test_summary_is_empty_before_a_recording(dock: DataExplorerDock) -> None:
    for field in SUMMARY_FIELDS:
        assert dock.summary_value(field) == EMPTY_VALUE
    assert dock.visible_channel_ids() == []
    assert dock.empty_hint.isVisible()


def test_tabs_are_channels_and_data_tree(dock: DataExplorerDock) -> None:
    assert [dock.tabs.tabText(i) for i in range(dock.tabs.count())] == [
        "Channels",
        "Data Tree",
    ]


def test_open_button_emits_request(dock: DataExplorerDock, qtbot: QtBot) -> None:
    with qtbot.waitSignal(dock.open_requested, timeout=2000):
        dock.open_button.click()


def test_open_button_triggers_main_window_action(window: MainWindow, qtbot: QtBot) -> None:
    with qtbot.waitSignal(window.action("action_open").triggered, timeout=2000):
        window.left_dock.open_button.click()


def test_recording_fills_summary_and_tree(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    dock.set_recording(repo.metadata(), repo.channels())

    assert dock.summary_value("File") == "Simülasyon"
    assert dock.summary_value("Duration") == "00:00:10"
    assert dock.summary_value("Platform") == "Simülasyon"
    assert len(dock.visible_channel_ids()) == 8
    assert not dock.empty_hint.isVisible()


def test_tree_groups_channels_by_source(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    assert dock.group_labels() == [
        "Sensors",
        "Acoustic",
        "Navigation",
        "Vehicle / Transmission",
    ]


def test_tree_is_hierarchical(dock: DataExplorerDock) -> None:
    """Mockup'taki gibi Accelerometer, Sensors altinda alt grup olmali."""
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    sensors = dock.tree.topLevelItem(0)
    assert sensors is not None
    children = [sensors.child(i).text(0) for i in range(sensors.childCount())]  # type: ignore[union-attr]
    assert "Accelerometer" in children

    accelerometer = next(
        sensors.child(i)
        for i in range(sensors.childCount())
        if sensors.child(i) is not None and sensors.child(i).text(0) == "Accelerometer"  # type: ignore[union-attr]
    )
    assert accelerometer is not None
    axes = [accelerometer.child(i).text(0) for i in range(accelerometer.childCount())]  # type: ignore[union-attr]
    assert axes == ["Accel X [g]", "Accel Y [g]", "Accel Z [g]"]


def test_search_filters_channels(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    dock.search.setText("hydro")
    assert dock.visible_channel_ids() == ["ch5"]

    dock.search.setText("")
    assert len(dock.visible_channel_ids()) == 8


def test_search_without_match_shows_hint(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    dock.search.setText("bulunmayan-kanal")
    assert dock.visible_channel_ids() == []
    assert dock.empty_hint.isVisible()
    assert "eslesen kanal yok" in dock.empty_hint.text()


def test_channels_are_checkable(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    assert dock.checked_channel_ids() == []
    item = dock.item_for_channel("ch0")
    assert item is not None
    item.setCheckState(0, Qt.CheckState.Checked)

    assert dock.checked_channel_ids() == ["ch0"]


def test_nested_channel_is_also_checkable(dock: DataExplorerDock) -> None:
    """Alt gruptaki kanal da isaretlenebilmeli."""
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    item = dock.item_for_channel("ch3")  # Sensors > Accelerometer > Y
    assert item is not None
    item.setCheckState(0, Qt.CheckState.Checked)
    assert dock.checked_channel_ids() == ["ch3"]


def test_double_click_emits_channel_id(dock: DataExplorerDock, qtbot: QtBot) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    child = dock.item_for_channel("ch0")
    assert child is not None

    seen: list[str] = []
    dock.channel_activated.connect(seen.append)

    with qtbot.waitSignal(dock.channel_activated, timeout=2000):
        dock.tree.itemDoubleClicked.emit(child, 0)
    assert seen == ["ch0"]


def test_clear_returns_to_empty_state(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())
    assert dock.visible_channel_ids()

    dock.clear()
    assert dock.visible_channel_ids() == []
    assert dock.summary_value("File") == EMPTY_VALUE
    assert dock.empty_hint.isVisible()


def test_unknown_summary_field_raises(dock: DataExplorerDock) -> None:
    with pytest.raises(KeyError, match="Tanimsiz ozet alani"):
        dock.summary_value("Yok")


def test_channel_labels_include_unit(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    dock.set_recording(repo.metadata(), repo.channels())

    child = dock.item_for_channel("ch0")
    assert child is not None
    assert child.text(0) == "Pressure [bar]"
    assert child.toolTip(0) == "Sensors/Pressure"


def test_repository_query_still_works_after_ui_use() -> None:
    """Panel yalnız okur; repository durumu bozulmamalı."""
    repo = MockRecordingRepository(duration_s=5.0)
    chunk = repo.query("ch0", TimeRange(0, 5 * SECOND))
    assert len(chunk) == 40

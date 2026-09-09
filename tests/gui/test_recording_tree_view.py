"""Kayıt/cihaz/sensör/kanal ağacının "Data Tree" sekmesindeki gösterimi — `F3-009`.

Kabul: kayıt, cihaz, sensör ve kanal hiyerarşisi doğru görünür.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _metadata(source_path: str, device_id: str = "") -> RecordingMetadata:
    return RecordingMetadata(
        recording_id="r1",
        source_path=source_path,
        time_range=TimeRange(0, 1),
        format_version=1,
        channel_count=1,
        record_count=1,
        record_period_ns=125_000_000,
        file_size_bytes=544,
        device_id=device_id,
    )


def _channel(channel_id: str, path: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=path,
        name=path.rsplit("/", 1)[-1],
        dtype="float32",
        source=ChannelSource.SENSORS,
    )


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


# -- widget duzeyi: set_recordings ------------------------------------------


def test_set_recordings_populates_the_data_tree(dock: DataExplorerDock) -> None:
    metadata = _metadata("kayit.bin", device_id="SONAR-01")
    channels = [_channel("ch0", "Sensors/Pressure")]

    dock.set_recordings([(metadata, channels)])

    assert dock.data_tree.topLevelItemCount() == 1
    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    assert recording_item.text(0) == "kayit.bin"
    device_item = recording_item.child(0)
    assert device_item is not None
    assert device_item.text(0) == "SONAR-01"
    assert dock.data_tree_channel_ids() == ["ch0"]


def test_set_recordings_with_empty_list_shows_the_hint(dock: DataExplorerDock) -> None:
    dock.tabs.setCurrentIndex(1)  # "Data Tree" sekmesi etkin olmali
    dock.set_recordings([(_metadata("kayit.bin"), [_channel("ch0", "Sensors/Pressure")])])
    assert not dock.data_tree_empty_hint.isVisible()

    dock.set_recordings([])

    assert dock.data_tree.topLevelItemCount() == 0
    assert dock.data_tree_empty_hint.isVisible()


def test_clear_also_empties_the_data_tree(dock: DataExplorerDock) -> None:
    dock.tabs.setCurrentIndex(1)  # "Data Tree" sekmesi etkin olmali
    dock.set_recordings([(_metadata("kayit.bin"), [_channel("ch0", "Sensors/Pressure")])])

    dock.clear()

    assert dock.data_tree.topLevelItemCount() == 0
    assert dock.data_tree_empty_hint.isVisible()


def test_double_clicking_a_data_tree_leaf_activates_the_channel(
    qtbot: QtBot, dock: DataExplorerDock
) -> None:
    metadata = _metadata("kayit.bin", device_id="SONAR-01")
    dock.set_recordings([(metadata, [_channel("ch0", "Sensors/Pressure")])])
    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    group_item = device_item.child(0)
    assert group_item is not None
    leaf = group_item.child(0)
    assert leaf is not None

    with qtbot.waitSignal(dock.channel_activated, timeout=1000) as blocker:
        dock.data_tree.itemDoubleClicked.emit(leaf, 0)
    emitted: list[object] = blocker.args or []  # type: ignore[assignment]
    assert emitted == ["ch0"]


def test_group_node_double_click_does_not_activate_a_channel(
    qtbot: QtBot, dock: DataExplorerDock
) -> None:
    """Yaprak olmayan düğüm (kayıt/cihaz/grup) tıklaması sinyal üretmez."""
    metadata = _metadata("kayit.bin", device_id="SONAR-01")
    dock.set_recordings([(metadata, [_channel("ch0", "Sensors/Pressure")])])
    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None

    with qtbot.assertNotEmitted(dock.channel_activated):
        dock.data_tree.itemDoubleClicked.emit(recording_item, 0)


# -- pencere duzeyi: gercek .bin ile ------------------------------------


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(VALID_FIXTURE, target)
    return target


def _open(qtbot: QtBot, window: MainWindow, paths: list[Path]) -> None:
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    return win


def test_opening_a_real_file_populates_the_data_tree(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    target = _copy(tmp_path, "kayit.bin")

    _open(qtbot, window, [target])

    assert window.left_dock.data_tree.topLevelItemCount() == 1
    recording_item = window.left_dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    assert recording_item.text(0) == "kayit.bin"
    assert len(window.left_dock.data_tree_channel_ids()) == 8


def test_closing_a_recording_clears_it_from_the_data_tree(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])

    window.action("action_close").trigger()

    assert window.left_dock.data_tree.topLevelItemCount() == 0


def test_multiple_open_files_each_get_a_recording_node(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")

    _open(qtbot, window, [first, second])

    assert window.left_dock.data_tree.topLevelItemCount() == 2
    labels = {
        window.left_dock.data_tree.topLevelItem(i).text(0)  # type: ignore[union-attr]
        for i in range(2)
    }
    assert labels == {"birinci.bin", "ikinci.bin"}


def test_closing_one_of_two_recordings_leaves_the_other_in_the_tree(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")
    _open(qtbot, window, [first, second])

    window.action("action_close").trigger()

    assert window.left_dock.data_tree.topLevelItemCount() == 1
    remaining = window.left_dock.data_tree.topLevelItem(0)
    assert remaining is not None
    assert remaining.text(0) == "ikinci.bin"

"""Kanal ağacında lazy yükleme — `F3-010`.

Kabul: açılmamış dallar gerektiğinde yüklenir; binlerce kanal gezilebilir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock

pytestmark = pytest.mark.gui

THOUSANDS = 3_000


def _metadata(source_path: str = "kayit.bin", device_id: str = "SONAR-01") -> RecordingMetadata:
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


def _many_channels(count: int, group: str = "Sensors") -> list[ChannelMetadata]:
    return [
        ChannelMetadata(
            id=f"ch{i}",
            path=f"{group}/Kanal{i}",
            name=f"Kanal{i}",
            dtype="float32",
            source=ChannelSource.SENSORS,
        )
        for i in range(count)
    ]


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.tabs.setCurrentIndex(1)  # "Data Tree" sekmesi
    return widget


def _group_item(dock: DataExplorerDock):
    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    group_item = device_item.child(0)
    assert group_item is not None
    return group_item


# -- acilmamis dallar gerektiginde yuklenir ---------------------------------


def test_unopened_group_is_not_materialized_with_thousands_of_channels(
    dock: DataExplorerDock,
) -> None:
    """Kabul kriteri (ilk yarı): açılmamış dallar yüklenmez."""
    dock.set_recordings([(_metadata(), _many_channels(THOUSANDS))])

    group_item = _group_item(dock)

    # Binlerce kanal MODELDE var...
    assert len(dock.data_tree_channel_ids()) == THOUSANDS
    # ...ama agacta HENUZ tek bir yer tutucudan baska bir sey yok.
    assert group_item.childCount() == 1
    assert group_item.child(0).data(0, Qt.ItemDataRole.UserRole) != "ch0"  # gercek kanal degil


def test_expanding_the_group_materializes_exactly_the_real_channels(
    dock: DataExplorerDock,
) -> None:
    """Kabul kriteri (ikinci yarı): gerektiğinde yüklenir — binlerce kanal gezilebilir."""
    dock.set_recordings([(_metadata(), _many_channels(THOUSANDS))])
    group_item = _group_item(dock)

    dock.data_tree.expandItem(group_item)

    assert group_item.childCount() == THOUSANDS
    leaf_ids = {group_item.child(i).data(0, Qt.ItemDataRole.UserRole) for i in range(THOUSANDS)}
    assert leaf_ids == {f"ch{i}" for i in range(THOUSANDS)}


def test_collapsing_and_reexpanding_does_not_duplicate_channels(
    dock: DataExplorerDock,
) -> None:
    dock.set_recordings([(_metadata(), _many_channels(50))])
    group_item = _group_item(dock)

    dock.data_tree.expandItem(group_item)
    assert group_item.childCount() == 50
    dock.data_tree.collapseItem(group_item)
    dock.data_tree.expandItem(group_item)

    assert group_item.childCount() == 50


def test_second_expand_is_a_harmless_no_op(dock: DataExplorerDock) -> None:
    """İlk genişletmeden sonraki genişletme çağrıları hata vermez veya yinelemez."""
    dock.set_recordings([(_metadata(), _many_channels(10))])
    group_item = _group_item(dock)

    dock.data_tree.expandItem(group_item)
    dock.data_tree.expandItem(group_item)  # zaten genisletilmis, tekrar cagirmak guvenli

    assert group_item.childCount() == 10


# -- binlerce kanal gezilebilir: cift tiklamayla dogru kanal aktive olur ----


def test_a_channel_deep_in_a_large_group_can_still_be_activated(
    qtbot: QtBot, dock: DataExplorerDock
) -> None:
    dock.set_recordings([(_metadata(), _many_channels(THOUSANDS))])
    group_item = _group_item(dock)
    dock.data_tree.expandItem(group_item)

    target = group_item.child(THOUSANDS - 1)
    assert target is not None

    with qtbot.waitSignal(dock.channel_activated, timeout=1000) as blocker:
        dock.data_tree.itemDoubleClicked.emit(target, 0)
    emitted: list[object] = blocker.args or []  # type: ignore[assignment]
    assert emitted == [f"ch{THOUSANDS - 1}"]


def test_multiple_groups_are_each_lazy_independently(dock: DataExplorerDock) -> None:
    acoustic_channel = ChannelMetadata(
        id="acoustic0",
        path="Acoustic/Hydrophone",
        name="Hydrophone",
        dtype="float32",
        source=ChannelSource.ACOUSTIC,
    )
    channels = [*_many_channels(500, "Sensors"), acoustic_channel]
    dock.set_recordings([(_metadata(), channels)])
    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    assert device_item.childCount() == 2  # Sensors, Acoustic

    sensors_group = device_item.child(0)
    acoustic_group = device_item.child(1)
    assert sensors_group is not None
    assert acoustic_group is not None
    assert sensors_group.childCount() == 1  # yer tutucu
    assert acoustic_group.childCount() == 1  # yer tutucu (tek kanal bile lazy)

    dock.data_tree.expandItem(acoustic_group)
    assert acoustic_group.childCount() == 1
    assert acoustic_group.child(0).data(0, Qt.ItemDataRole.UserRole) == "acoustic0"
    # Sensors grubu HALA genisletilmedi.
    assert sensors_group.childCount() == 1
    assert sensors_group.child(0).data(0, Qt.ItemDataRole.UserRole) != "ch0"


# -- recording/cihaz duzeyi HER ZAMAN eager (az sayida) ----------------------


def test_recording_and_device_levels_are_never_lazy(dock: DataExplorerDock) -> None:
    """Kayıt/cihaz düzeyi zaten az sayıdadır; yalnız kanal yaprakları ertelenir."""
    dock.set_recordings([(_metadata(), _many_channels(1000))])

    recording_item = dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    assert recording_item.childCount() == 1  # cihaz dugumu, gercek
    device_item = recording_item.child(0)
    assert device_item is not None
    assert device_item.text(0) == "SONAR-01"
    assert recording_item.isExpanded()
    assert device_item.isExpanded()

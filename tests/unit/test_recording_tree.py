"""Kayıt/cihaz/sensör/kanal ağaç modeli — `F3-009`.

Kabul: kayıt, cihaz, sensör ve kanal hiyerarşisi doğru görünür.
"""

from __future__ import annotations

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.docks.recording_tree import (
    UNKNOWN_DEVICE_LABEL,
    RecordingTreeNode,
    build_recording_tree,
    flatten_channel_ids,
)


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


def _channel(
    channel_id: str, path: str, source: ChannelSource = ChannelSource.SENSORS
) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id, path=path, name=path.rsplit("/", 1)[-1], dtype="float32", source=source
    )


# -- dort duzey: kayit / cihaz / sensor / kanal -----------------------------


def test_full_hierarchy_has_four_levels() -> None:
    """Kabul kriteri birebir: kayıt, cihaz, sensör ve kanal hiyerarşisi görünür."""
    metadata = _metadata("C:/kayitlar/deniz.bin", device_id="SONAR-01")
    channels = [_channel("ch0", "Sensors/Pressure")]

    tree = build_recording_tree([(metadata, channels)])

    assert len(tree) == 1
    recording_node = tree[0]
    assert recording_node.label == "deniz.bin"
    assert not recording_node.is_leaf

    device_node = recording_node.children[0]
    assert device_node.label == "SONAR-01"
    assert not device_node.is_leaf

    group_node = device_node.children[0]
    assert group_node.label == "Sensors"
    assert not group_node.is_leaf

    channel_node = group_node.children[0]
    assert channel_node.is_leaf
    assert channel_node.channel_id == "ch0"


def test_recording_label_uses_the_file_name_not_the_full_path() -> None:
    metadata = _metadata("D:\\veri\\kayitlar\\ornek_001.bin")
    tree = build_recording_tree([(metadata, [])])
    assert tree[0].label == "ornek_001.bin"


def test_unknown_device_is_labeled_explicitly_not_fabricated() -> None:
    """Cihaz kimliği yoksa uydurma bir ad üretilmez."""
    metadata = _metadata("kayit.bin", device_id="")
    tree = build_recording_tree([(metadata, [])])
    assert tree[0].children[0].label == UNKNOWN_DEVICE_LABEL


def test_channels_are_grouped_by_path_first_segment() -> None:
    metadata = _metadata("kayit.bin")
    channels = [
        _channel("ch0", "Sensors/Pressure"),
        _channel("ch1", "Sensors/Temperature"),
        _channel("ch2", "Acoustic/Hydrophone 1", ChannelSource.ACOUSTIC),
    ]

    tree = build_recording_tree([(metadata, channels)])

    device_node = tree[0].children[0]
    group_labels = [group.label for group in device_node.children]
    assert group_labels == ["Sensors", "Acoustic"]
    assert len(device_node.children[0].children) == 2


def test_vehicle_group_uses_the_display_label() -> None:
    """channel-map.md: yolda 'Vehicle', gösterimde 'Vehicle / Transmission'."""
    metadata = _metadata("kayit.bin")
    channels = [_channel("ch7", "Vehicle/Voltage", ChannelSource.TRANSMISSION)]

    tree = build_recording_tree([(metadata, channels)])

    device_node = tree[0].children[0]
    assert device_node.children[0].label == "Vehicle / Transmission"


def test_empty_recording_still_shows_recording_and_device_nodes() -> None:
    """Bozuk/boş dosyada bile kaydın açık olduğu gizlenmez."""
    metadata = _metadata("bos.bin", device_id="SONAR-02")
    tree = build_recording_tree([(metadata, [])])

    assert len(tree) == 1
    assert tree[0].label == "bos.bin"
    device_node = tree[0].children[0]
    assert device_node.label == "SONAR-02"
    assert device_node.children == ()


# -- coklu kayit -------------------------------------------------------


def test_multiple_recordings_appear_as_separate_top_level_nodes() -> None:
    first = _metadata("birinci.bin", device_id="SONAR-01")
    second = _metadata("ikinci.bin", device_id="SONAR-02")
    channels = [_channel("ch0", "Sensors/Pressure")]

    tree = build_recording_tree([(first, channels), (second, channels)])

    assert [node.label for node in tree] == ["birinci.bin", "ikinci.bin"]


def test_empty_recordings_list_produces_an_empty_tree() -> None:
    assert build_recording_tree([]) == ()


# -- yardimci: flatten_channel_ids ------------------------------------------


def test_flatten_channel_ids_finds_every_leaf_regardless_of_depth() -> None:
    metadata = _metadata("kayit.bin")
    channels = [
        _channel("ch0", "Sensors/Pressure"),
        _channel("ch1", "Acoustic/Hydrophone 1", ChannelSource.ACOUSTIC),
    ]
    tree = build_recording_tree([(metadata, channels)])

    assert flatten_channel_ids(tree) == ["ch0", "ch1"]


def test_flatten_channel_ids_empty_for_channel_less_tree() -> None:
    node = RecordingTreeNode("kayit.bin", children=(RecordingTreeNode("cihaz"),))
    assert flatten_channel_ids((node,)) == []

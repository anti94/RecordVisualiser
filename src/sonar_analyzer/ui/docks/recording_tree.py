"""Kayıt/cihaz/sensör/kanal ağaç modeli — `F3-009`.

"Channels" sekmesi tek kaydın kanal **yollarından** ağaç kurar
(`Sensors/Accelerometer/X` → Sensors › Accelerometer › X). "Data Tree"
sekmesi bundan farklı bir eksende gösterir: **hangi kayıttan, hangi
cihazdan geldiği** — birden fazla dosya açıkken (`F2-036` çoklu kayıt
desteği) bu bilgi Channels sekmesinde kaybolur.

Dört düzey:

    Kayıt (dosya adı)
      └─ Cihaz (RecordingMetadata.device_id)
           └─ Sensör grubu (kanal yolunun ilk parçası: Sensors, Acoustic, ...)
                └─ Kanal

Qt'ye bağımlı değildir — saf veri modeli, widget kurulumundan ayrı test edilir.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata

#: Cihaz kimliği bilinmiyorsa — uydurma bir ad üretilmez, bu acıkça gösterilir.
UNKNOWN_DEVICE_LABEL = "Bilinmeyen cihaz"

#: Yol parçasından gösterim etiketine — `data_explorer.py::GROUP_LABELS` ile aynı.
GROUP_LABELS = {"Vehicle": "Vehicle / Transmission"}


def _empty_children() -> tuple[RecordingTreeNode, ...]:
    return ()


@dataclass(frozen=True)
class RecordingTreeNode:
    """Ağaçtaki tek bir düğüm; `channel_id` yalnız yaprakta dolu olur."""

    label: str
    channel_id: str | None = None
    children: tuple[RecordingTreeNode, ...] = field(default_factory=_empty_children)

    @property
    def is_leaf(self) -> bool:
        return self.channel_id is not None


def _recording_label(metadata: RecordingMetadata) -> str:
    """Kaydın ağaçtaki adı — dosya adı, yol boşsa kaynak metni olduğu gibi."""
    source = metadata.source_path
    if not source:
        return "(adsız kayıt)"
    # Path ayracı '/' ve '\' her ikisi de olabilir (Windows/POSIX karışık
    # gelebilir); son parçayı almak icin ikisini de sinamak yeterli.
    tail = source.replace("\\", "/").rsplit("/", 1)[-1]
    return tail or source


def _group_label(channel: ChannelMetadata) -> str:
    """Kanal yolunun ilk parçası — sensör grubu."""
    first_segment = channel.path.split("/", 1)[0] if channel.path else channel.source.value
    return GROUP_LABELS.get(first_segment, first_segment)


def _build_channel_nodes(channels: Sequence[ChannelMetadata]) -> tuple[RecordingTreeNode, ...]:
    """Sensör grubuna göre gruplanmış kanal yaprakları."""
    groups: dict[str, list[RecordingTreeNode]] = {}
    order: list[str] = []
    for channel in channels:
        label = _group_label(channel)
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(RecordingTreeNode(channel.display_label, channel_id=channel.id))

    return tuple(RecordingTreeNode(group, children=tuple(groups[group])) for group in order)


def build_recording_tree(
    recordings: Sequence[tuple[RecordingMetadata, Sequence[ChannelMetadata]]],
) -> tuple[RecordingTreeNode, ...]:
    """Açık kayıtlardan `Kayıt › Cihaz › Sensör grubu › Kanal` ağacını kurar.

    Bir kaydın hiç kanalı yoksa (bozuk/boş dosya) yine de **Kayıt** ve
    **Cihaz** düğümü görünür — dosyanın açık olduğu gizlenmez, yalnızca
    altında kanal yoktur.
    """
    tree: list[RecordingTreeNode] = []
    for metadata, channels in recordings:
        device_label = metadata.device_id or UNKNOWN_DEVICE_LABEL
        device_node = RecordingTreeNode(device_label, children=_build_channel_nodes(channels))
        tree.append(RecordingTreeNode(_recording_label(metadata), children=(device_node,)))
    return tuple(tree)


def flatten_channel_ids(nodes: Sequence[RecordingTreeNode]) -> list[str]:
    """Ağaçtaki tüm kanal kimliklerini derinlik-önce sırayla döner (testler için)."""
    found: list[str] = []
    for node in nodes:
        if node.is_leaf:
            assert node.channel_id is not None
            found.append(node.channel_id)
        found.extend(flatten_channel_ids(node.children))
    return found

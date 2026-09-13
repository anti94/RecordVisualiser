"""Data Explorer'da Tx/Rx ağacı — `F7-047`.

Kabul: **Ağaçta `Tx` ve `Rx` iki üst düğüm; altlarında sensörler görünür.**

Ağaç kanal **yolundan** kurulur, ayrı bir Profil C dalı yazılmaz. Bu
bilinçli: iki ayrı ağaç kurma yolu olsaydı, biri düzeltilip öteki
unutulurdu. Repository `Tx/Sensor 00` biçiminde yol üretiyor ve ağaç onu
zaten iki düzeye açıyor.

Testler bunu **gerçek repository çıktısıyla** doğrular. Elle kurulmuş
kanal listeleri yalnız kendilerini sınar; repository'nin ürettiği yollar
ikisinin ayrışmadığını da gösterir.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem
from pytestqt.qtbot import QtBot
from tools.profile_c_writer import WriteSpec, write_recording

from sonar_analyzer.io.schema.loader import load_text
from sonar_analyzer.repository.folder_repository import (
    FolderRecordingRepository,
)
from sonar_analyzer.ui.docks.data_explorer import GROUP_LABELS, DataExplorerDock

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

SENSORS = 4
SAMPLES = 8


@pytest.fixture
def explorer(qtbot: QtBot, tmp_path: Path) -> Iterator[DataExplorerDock]:
    schema = load_text(
        EXAMPLE.read_text(encoding="utf-8")
        .replace("sensor_count = 32", f"sensor_count = {SENSORS}")
        .replace("frame_samples = 820", f"frame_samples = {SAMPLES}")
    )
    folder = write_recording(tmp_path, WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES))
    repository = FolderRecordingRepository()
    repository.open(folder, schema)

    dock = DataExplorerDock()
    qtbot.addWidget(dock)
    dock.set_recording(repository.metadata(), repository.channels())
    yield dock
    repository.close()


def _top_level_items(dock: DataExplorerDock) -> list[QTreeWidgetItem]:
    """Üst düzey düğümler.

    `topLevelItem` tip olarak `None` dönebilir; sayaç içinde dönemez ama
    katı tip denetimi bunu bilemez. Boş olanı elemek, testin gerçek
    hatayı göstermesini sağlar: `None` üzerinden `.text()` çağırmak
    "hangi düğüm yok" sorusunu cevaplamaz.
    """
    tree = dock.tree
    found: list[QTreeWidgetItem] = []
    for index in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(index)
        assert item is not None, f"{index}. ust duzey dugum bos"
        found.append(item)
    return found


def _top_level_labels(dock: DataExplorerDock) -> list[str]:
    return [item.text(0) for item in _top_level_items(dock)]


def _child_items(item: QTreeWidgetItem) -> list[QTreeWidgetItem]:
    found: list[QTreeWidgetItem] = []
    for index in range(item.childCount()):
        child = item.child(index)
        assert child is not None, f"{index}. cocuk bos"
        found.append(child)
    return found


def _children(item: QTreeWidgetItem) -> list[str]:
    return [child.text(0) for child in _child_items(item)]


def _node(dock: DataExplorerDock, label: str) -> QTreeWidgetItem:
    for item in _top_level_items(dock):
        if item.text(0) == label:
            return item
    raise AssertionError(f"{label!r} ust duzey dugumu bulunamadi: {_top_level_labels(dock)}")


# --------------------------------------------------------------------------- #
# IKI UST DUGUM
# --------------------------------------------------------------------------- #


def test_the_tree_has_exactly_two_top_level_nodes(explorer: DataExplorerDock) -> None:
    """Asıl kabul: Tx ve Rx; başka üst düğüm olmamalı."""
    assert len(_top_level_labels(explorer)) == 2


def test_both_streams_appear(explorer: DataExplorerDock) -> None:
    labels = _top_level_labels(explorer)

    assert GROUP_LABELS["Tx"] in labels
    assert GROUP_LABELS["Rx"] in labels


def test_the_labels_say_which_is_which(explorer: DataExplorerDock) -> None:
    """İki harf tek başına yayın ile dinlemeyi ayırt ettirmez.

    Karıştırılırsa okunan veri yanlış yorumlanır ve hiçbir şey hata
    vermez.
    """
    labels = _top_level_labels(explorer)

    assert any("Transmit" in label for label in labels)
    assert any("Receive" in label for label in labels)


def test_each_stream_holds_every_sensor(explorer: DataExplorerDock) -> None:
    for key in ("Tx", "Rx"):
        children = _children(_node(explorer, GROUP_LABELS[key]))
        assert len(children) == SENSORS, f"{key}: {len(children)} sensor"


def test_sensors_are_listed_in_order(explorer: DataExplorerDock) -> None:
    """Sıfır dolgu olmasaydı `Sensor 10` `Sensor 2`'den önce gelirdi."""
    children = _children(_node(explorer, GROUP_LABELS["Rx"]))

    assert children == sorted(children)


# --------------------------------------------------------------------------- #
# YAPRAKLAR KANAL KIMLIGI TASIYOR
# --------------------------------------------------------------------------- #


def test_every_leaf_carries_a_channel_id(explorer: DataExplorerDock) -> None:
    """Kimlik taşımayan bir yaprak tıklandığında hiçbir şey olmazdı."""
    node = _node(explorer, GROUP_LABELS["Rx"])

    for child in _child_items(node):
        value = child.data(0, Qt.ItemDataRole.UserRole)
        assert isinstance(value, str)
        assert value.startswith("rx-s")


def test_tx_and_rx_leaves_have_distinct_ids(explorer: DataExplorerDock) -> None:
    tx = _node(explorer, GROUP_LABELS["Tx"])
    rx = _node(explorer, GROUP_LABELS["Rx"])

    tx_ids = {item.data(0, Qt.ItemDataRole.UserRole) for item in _child_items(tx)}
    rx_ids = {item.data(0, Qt.ItemDataRole.UserRole) for item in _child_items(rx)}

    assert not (tx_ids & rx_ids)


def test_the_stream_nodes_are_not_selectable(explorer: DataExplorerDock) -> None:
    """Üst düğüm bir kanal değildir; seçilebilir olsaydı boş grafik açardı."""
    node = _node(explorer, GROUP_LABELS["Tx"])

    assert not bool(node.flags() & Qt.ItemFlag.ItemIsSelectable)


def test_leaves_are_checkable(explorer: DataExplorerDock) -> None:
    """Çoklu seçim için kutucuk gerekir (`F3-016`)."""
    leaf = _child_items(_node(explorer, GROUP_LABELS["Rx"]))[0]

    assert bool(leaf.flags() & Qt.ItemFlag.ItemIsUserCheckable)
    assert leaf.checkState(0) == Qt.CheckState.Unchecked


# --------------------------------------------------------------------------- #
# EKSIK AKIM
# --------------------------------------------------------------------------- #


def test_a_missing_stream_produces_no_node(qtbot: QtBot, tmp_path: Path) -> None:
    """Yayın yapılmayan bir oturumda `Tx` düğümü hiç çıkmamalı.

    Boş bir `Tx` düğümü göstermek, kullanıcının orada veri arayıp
    bulamamasına yol açardı.
    """
    schema = load_text(
        EXAMPLE.read_text(encoding="utf-8")
        .replace("sensor_count = 32", f"sensor_count = {SENSORS}")
        .replace("frame_samples = 820", f"frame_samples = {SAMPLES}")
    )
    folder = write_recording(
        tmp_path, WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES, tx_seconds=())
    )
    repository = FolderRecordingRepository()
    repository.open(folder, schema)

    dock = DataExplorerDock()
    qtbot.addWidget(dock)
    dock.set_recording(repository.metadata(), repository.channels())

    labels = _top_level_labels(dock)
    assert labels == [GROUP_LABELS["Rx"]]
    repository.close()


def test_a_recording_with_no_channels_shows_no_nodes(qtbot: QtBot, tmp_path: Path) -> None:
    """Kanal yoksa ağaç boş kalmalı; hayalet düğüm üretilmemeli."""
    schema = load_text(
        EXAMPLE.read_text(encoding="utf-8")
        .replace("sensor_count = 32", f"sensor_count = {SENSORS}")
        .replace("frame_samples = 820", f"frame_samples = {SAMPLES}")
    )
    folder = write_recording(tmp_path, WriteSpec(seconds=1, sensors=SENSORS, samples=SAMPLES))
    repository = FolderRecordingRepository()
    repository.open(folder, schema)

    dock = DataExplorerDock()
    qtbot.addWidget(dock)
    dock.set_recording(repository.metadata(), [])

    assert dock.tree.topLevelItemCount() == 0
    repository.close()


# --------------------------------------------------------------------------- #
# F7-052 — KAYIT KARTI
# --------------------------------------------------------------------------- #


def test_the_card_shows_the_profile_and_version(explorer: DataExplorerDock) -> None:
    """Asıl kabul: hangi şemayla okunduğu kartta görünmeli.

    Aynı klasör iki farklı şemayla açıldığında iki farklı sonuç verir.
    Hangisi kullanıldı sorusunun cevabı ekranda olmazsa yanlış olan fark
    edilmez.
    """
    text = explorer.summary_value("Format")

    assert "Profil C" in text
    assert "v1" in text


def test_the_card_shows_the_channel_count(explorer: DataExplorerDock) -> None:
    text = explorer.summary_value("Format")

    assert f"{2 * SENSORS} kanal" in text


def test_the_card_shows_the_folder_path(explorer: DataExplorerDock) -> None:
    """Kaynak klasör görünmezse, iki benzer kayıt ayırt edilemez."""
    text = explorer.summary_value("File")

    assert "2023-11-14T22-13-20Z" in text


def test_the_card_shows_a_nonzero_size(explorer: DataExplorerDock) -> None:
    text = explorer.summary_value("Size")

    assert text != "—"

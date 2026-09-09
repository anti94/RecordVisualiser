"""Ad, ID, birim ve kaynak araması — `F3-011`.

Kabul: her alan için bilinen eşleşme bulunur; temizleme tüm kanalları getirir.

`MockRecordingRepository`'nin sekiz kanalı (`channel-map.md` §2 ile aynı
sıra/birim) bilinen değerler taşıdığı için doğrudan kullanılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    repo = MockRecordingRepository(duration_s=5.0)
    widget.set_recording(repo.metadata(), repo.channels())
    return widget


# -- her alan icin bilinen eslesme: ad ----------------------------------


def test_search_by_name_finds_the_known_channel(dock: DataExplorerDock) -> None:
    dock.search.setText("Depth")
    assert dock.visible_channel_ids() == ["ch6"]


def test_search_by_name_is_case_insensitive(dock: DataExplorerDock) -> None:
    dock.search.setText("depth")
    assert dock.visible_channel_ids() == ["ch6"]


# -- her alan icin bilinen eslesme: ID -----------------------------------


def test_search_by_channel_id_finds_the_known_channel(dock: DataExplorerDock) -> None:
    """Kabul kriteri: ID alanı için bilinen eşleşme bulunur (kimlik görünen etikette yok)."""
    dock.search.setText("ch7")
    assert dock.visible_channel_ids() == ["ch7"]


# -- her alan icin bilinen eslesme: birim ---------------------------------


def test_search_by_unit_finds_all_matching_channels(dock: DataExplorerDock) -> None:
    """`bar` yalnız ch0'da (Pressure); diğer kanallarda 'bar' geçmez."""
    dock.search.setText("bar")
    assert dock.visible_channel_ids() == ["ch0"]


def test_search_by_shared_path_segment_finds_the_three_axis_channels(
    dock: DataExplorerDock,
) -> None:
    """`g` birimini paylaşan üç ivmeölçer kanalı (ch2, ch3, ch4) yol üzerinden birlikte bulunur."""
    dock.search.setText("accelerometer")
    assert set(dock.visible_channel_ids()) == {"ch2", "ch3", "ch4"}


# -- her alan icin bilinen eslesme: kaynak --------------------------------


def test_search_by_source_finds_only_that_groups_channels(dock: DataExplorerDock) -> None:
    """Kabul kriteri: kaynak (ChannelSource) alanı için bilinen eşleşme bulunur.

    `Acoustic/Hydrophone 1` yolu 'acoustic' içerdiği için bu örnek yol
    aramasıyla da bulunurdu; asıl kanıt `transmission` — yolda hiç
    geçmeyen ama `ChannelSource.TRANSMISSION.value` olan kelime.
    """
    dock.search.setText("transmission")
    assert dock.visible_channel_ids() == ["ch7"]


def test_search_by_source_acoustic_finds_the_hydrophone(dock: DataExplorerDock) -> None:
    dock.search.setText("acoustic")
    assert dock.visible_channel_ids() == ["ch5"]


def test_search_by_source_sensors_finds_the_five_sensor_channels(
    dock: DataExplorerDock,
) -> None:
    dock.search.setText("sensors")
    assert set(dock.visible_channel_ids()) == {"ch0", "ch1", "ch2", "ch3", "ch4"}


# -- temizleme tum kanallari getirir --------------------------------------


def test_clearing_the_search_restores_every_channel(dock: DataExplorerDock) -> None:
    """Kabul kriteri birebir: temizleme tüm kanalları getirir."""
    dock.search.setText("transmission")
    assert dock.visible_channel_ids() == ["ch7"]

    dock.search.setText("")

    assert set(dock.visible_channel_ids()) == {f"ch{i}" for i in range(8)}


def test_clearing_after_a_dead_end_search_restores_every_channel(
    dock: DataExplorerDock,
) -> None:
    dock.search.setText("hicbir-kanalla-eslesmez")
    assert dock.visible_channel_ids() == []

    dock.search.setText("")

    assert len(dock.visible_channel_ids()) == 8


# -- eslesmeyen arama --------------------------------------------------


def test_unknown_field_value_finds_nothing(dock: DataExplorerDock) -> None:
    dock.search.setText("kelvin")  # hicbir kanalin biriminde yok
    assert dock.visible_channel_ids() == []
    assert dock.empty_hint.isVisible()

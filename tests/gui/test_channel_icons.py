"""Kanal ağacı ikon sistemi — plan Bölüm 5.2.

Kanal türü, kaynaktaki durumu ve alarm seviyesi için tutarlı bir ikon
sistemi gerekir. Kural plan Bölüm 6.4'ten gelir: durum **yalnız renkle**
anlatılmaz. Her ikon bir simge taşır ve ipucu aynı bilgiyi metinle de
verir; renk körlüğünde ve gri tonlamalı ekran görüntüsünde yalnız renge
dayalı bir ayrım kaybolurdu.

Testler ikonun *çizildiğini* değil, **ayırt edici** olduğunu denetler:
farklı kaynaklar farklı simge alır, aynı kaynak her zaman aynısını alır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.data_explorer import DataExplorerDock
from sonar_analyzer.ui.status_icons import CHANNEL_SOURCE_STYLES, channel_source_style

pytestmark = pytest.mark.gui


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    repo = MockRecordingRepository(duration_s=5.0)
    widget.set_recording(repo.metadata(), repo.channels())
    return widget


# --------------------------------------------------------------------------- #
# STIL TABLOSU
# --------------------------------------------------------------------------- #


def test_every_channel_source_has_a_style() -> None:
    """Eşlenmemiş bir kaynak, ikonsuz bir kanal demek olurdu."""
    for source in ChannelSource:
        assert source in CHANNEL_SOURCE_STYLES


def test_each_style_carries_a_symbol_and_a_label() -> None:
    """Renk üçüncü ipucudur; simge ve metin olmadan ayrım renge bağlı kalırdı."""
    for style in CHANNEL_SOURCE_STYLES.values():
        assert style.symbol.strip()
        assert style.label.strip()
        assert style.color.startswith("#")


def test_different_sources_are_distinguishable_without_colour() -> None:
    """İki kaynak aynı simgeyi alırsa gri tonlamada ayırt edilemezler."""
    symbols = [style.symbol for style in CHANNEL_SOURCE_STYLES.values()]
    assert len(symbols) == len(set(symbols))


def test_an_unknown_source_falls_back_without_raising() -> None:
    assert channel_source_style(ChannelSource.UNKNOWN).label == "Unknown"


def test_the_same_source_always_gets_the_same_style() -> None:
    first = channel_source_style(ChannelSource.SENSORS)
    second = channel_source_style(ChannelSource.SENSORS)
    assert first == second


# --------------------------------------------------------------------------- #
# AGACTA GORUNUYOR MU
# --------------------------------------------------------------------------- #


def test_a_channel_leaf_carries_an_icon(dock: DataExplorerDock) -> None:
    item = dock.item_for_channel("ch0")

    assert item is not None
    assert not item.icon(0).isNull(), "kanal yapragi ikonsuz kalmamali"


def test_the_tooltip_names_the_source_in_words(dock: DataExplorerDock) -> None:
    """İkon tek başına yetmez; ipucu aynı bilgiyi metinle de vermeli."""
    item = dock.item_for_channel("ch0")

    assert item is not None
    tooltip = item.toolTip(0)
    assert "Sensors" in tooltip


def test_the_tooltip_still_shows_the_full_path(dock: DataExplorerDock) -> None:
    """İpucunun asıl işi kısaltılan etiketin tam yolunu göstermekti."""
    item = dock.item_for_channel("ch0")

    assert item is not None
    assert item.toolTip(0).startswith("Sensors/Pressure")


def test_the_tooltip_states_whether_the_channel_exists_in_the_source(
    dock: DataExplorerDock,
) -> None:
    """ "Bağlantı durumu" burada kaynakta bulunup bulunmamasıdır."""
    item = dock.item_for_channel("ch0")

    assert item is not None
    assert "kaynakta var" in item.toolTip(0)


def test_an_acoustic_channel_gets_a_different_icon_than_a_sensor(
    dock: DataExplorerDock,
) -> None:
    """Aynı ikonu vermek, ikon sistemini süsten ibaret bırakırdı."""
    sensor = dock.item_for_channel("ch0")
    acoustic = dock.item_for_channel("ch5")
    assert sensor is not None
    assert acoustic is not None

    sensor_style = channel_source_style(ChannelSource.SENSORS)
    acoustic_style = channel_source_style(ChannelSource.ACOUSTIC)
    assert sensor_style.symbol != acoustic_style.symbol
    assert "Sensors" in sensor.toolTip(0)
    assert "Acoustic" in acoustic.toolTip(0)

"""Boş grafik alanı yönlendirmesi — plan Bölüm 5.3.

Boş bir dikdörtgen, özelliğin **yokluğundan** ayırt edilemez: kullanıcı
oraya kanal sürükleyebileceğini bilemez ve uygulamanın bozuk olduğunu
düşünebilir. Bu yüzden grafik boşken ne yapılacağını söyleyen bir metin
görünür.

Yönlendirme yalnız boşken görünmeli: seri varken de göstermek, verinin
üstüne yazı basmak olurdu. Testler iki yönü de denetler.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.ui.plots.plot_panel import EMPTY_PLOT_HINT, PlotPanel

pytestmark = pytest.mark.gui


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        name=f"Kanal {channel_id}",
        path=f"Sensors/{channel_id}",
        unit="bar",
        dtype="float32",
        source=ChannelSource.SENSORS,
        sample_rate_hz=8.0,
    )


def _chunk(channel_id: str) -> DataChunk:
    count = 8
    return DataChunk(
        channel_id=channel_id,
        timestamps_ns=np.arange(count, dtype=np.int64) * 125_000_000,
        values=np.arange(count, dtype=np.float64),
    )


def test_a_fresh_panel_shows_the_hint(panel: PlotPanel) -> None:
    assert panel.plotted_channel_ids() == []
    assert panel.empty_hint_visible()


def test_the_hint_says_what_to_do_not_just_that_it_is_empty(panel: PlotPanel) -> None:
    """ "Veri yok" bilgi verir; "kanalı buraya sürükleyin" yol gösterir."""
    text = panel.empty_hint_text()
    assert "surukleyin" in text
    assert "cift tiklayin" in text
    assert text == EMPTY_PLOT_HINT


def test_plotting_a_channel_hides_the_hint(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    assert panel.plotted_channel_ids() == ["ch0"]
    assert not panel.empty_hint_visible(), "veri varken yazi verinin ustune basilmamali"


def test_removing_the_last_channel_brings_the_hint_back(panel: PlotPanel) -> None:
    """Kullanıcı son seriyi kaldırdığında yine yönlendirilmeli."""
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.remove_channel("ch0")

    assert panel.plotted_channel_ids() == []
    assert panel.empty_hint_visible()


def test_removing_one_of_two_channels_keeps_the_hint_hidden(panel: PlotPanel) -> None:
    """Karşı yön: grafik hâlâ doluyken yönlendirme dönmemeli."""
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.add_channel(_channel("ch1"), _chunk("ch1"))
    panel.remove_channel("ch0")

    assert panel.plotted_channel_ids() == ["ch1"]
    assert not panel.empty_hint_visible()


def test_clearing_the_panel_restores_the_hint(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.add_channel(_channel("ch1"), _chunk("ch1"))
    panel.clear()

    assert panel.empty_hint_visible()

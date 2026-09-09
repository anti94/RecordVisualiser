"""Grafikten kanal kaldırma — `F3-014`.

Kabul: seri ve legend temizlenir; diğer seriler korunur.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import EMPTY_TITLE, PlotPanel

pytestmark = pytest.mark.gui


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str, name: str, unit: str = "bar") -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit=unit,
        sample_rate_hz=100.0,
    )


# -- coklu seri: ekleme diger serileri bozmaz -------------------------------


def test_add_channel_keeps_the_previous_series(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))

    assert panel.plotted_channel_ids() == ["ch0", "ch1"]
    assert panel.curve_data("ch0")[1].size > 0
    assert panel.curve_data("ch1")[1].size > 0


def test_legend_lists_every_added_channel(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))

    assert panel.legend_labels() == ["Pressure [bar]", "Temperature [C]"]


# -- kabul kriteri: seri ve legend temizlenir; digerleri korunur -----------


def test_remove_channel_clears_its_series_and_legend_entry(panel: PlotPanel) -> None:
    """Kabul kriteri (ilk yarı): seri ve legend temizlenir."""
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))

    panel.remove_channel("ch0")

    assert "ch0" not in panel.plotted_channel_ids()
    assert panel.curve_data("ch0")[0].size == 0
    assert "Pressure [bar]" not in panel.legend_labels()


def test_remove_channel_preserves_the_other_series(panel: PlotPanel) -> None:
    """Kabul kriteri (ikinci yarı): diğer seriler korunur."""
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    ch1_chunk = sine("ch1", 25.0, 0.5, frequency_hz=1.0)
    panel.add_channel(_channel("ch1", "Temperature", "C"), ch1_chunk)

    panel.remove_channel("ch0")

    assert panel.plotted_channel_ids() == ["ch1"]
    assert "Temperature [C]" in panel.legend_labels()
    remaining_y = panel.curve_data("ch1")[1]
    assert remaining_y.tolist() == ch1_chunk.values.tolist()


def test_removing_the_middle_channel_of_three_keeps_the_other_two(panel: PlotPanel) -> None:
    for i in range(3):
        chunk = sine(
            f"ch{i}", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=1.0, amplitude=float(i)
        )
        panel.add_channel(_channel(f"ch{i}", f"Kanal{i}"), chunk)

    panel.remove_channel("ch1")

    assert panel.plotted_channel_ids() == ["ch0", "ch2"]
    assert set(panel.legend_labels()) == {"Kanal0 [bar]", "Kanal2 [bar]"}


def test_removing_an_unknown_channel_is_a_harmless_no_op(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    panel.remove_channel("hic-eklenmemis-kanal")

    assert panel.plotted_channel_ids() == ["ch0"]


def test_removing_the_last_channel_returns_to_the_empty_state(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    panel.remove_channel("ch0")

    assert panel.plotted_channel_ids() == []
    assert panel.channel is None
    assert panel.sample_count == 0
    assert EMPTY_TITLE in panel.title_text()
    assert panel.legend_labels() == []


# -- birincil kanal, kaldirmadan sonra dogru devrediliyor -------------------


def test_removing_the_primary_channel_promotes_the_next_one(panel: PlotPanel) -> None:
    """`channel`/`sample_count`/`curve_data()` (parametresiz) doğru seriye taşınır."""
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    ch1_chunk = sine("ch1", 25.0, 0.5, frequency_hz=1.0)
    panel.add_channel(_channel("ch1", "Temperature", "C"), ch1_chunk)
    assert panel.channel is not None
    assert panel.channel.id == "ch0"

    panel.remove_channel("ch0")

    assert panel.channel is not None
    assert panel.channel.id == "ch1"
    assert panel.curve_data()[1].tolist() == ch1_chunk.values.tolist()


def test_removing_a_non_primary_channel_keeps_the_primary(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))

    panel.remove_channel("ch1")

    assert panel.channel is not None
    assert panel.channel.id == "ch0"


# -- gorunum: baslik tek/coklu seride farkli ---------------------------


def test_title_shows_single_channel_when_only_one_remains(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))
    assert panel.title_text() == "2 kanal"

    panel.remove_channel("ch1")

    assert panel.title_text() == "Pressure [bar]"


# -- geriye donuk uyumluluk: set_channel hala TEK seriye sifirliyor --------


def test_set_channel_still_resets_to_a_single_series(panel: PlotPanel) -> None:
    """`F1-031`'in özgün davranışı korunuyor: `set_channel` tüm önceki serileri siler."""
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "Temperature", "C"), sine("ch1", 25.0, 0.5, frequency_hz=1.0))

    panel.set_channel(_channel("ch2", "Depth", "m"), sine("ch2", 30.0, 2.0, frequency_hz=0.5))

    assert panel.plotted_channel_ids() == ["ch2"]
    assert panel.legend_labels() == ["Depth [m]"]


def test_add_channel_updates_in_place_without_duplicate_legend_entry(
    panel: PlotPanel,
) -> None:
    """Aynı kanalı iki kez eklemek yeni seri/legend girdisi açmaz, günceller."""
    panel.add_channel(_channel("ch0", "Pressure"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    updated_chunk = sine("ch0", 200.0, 1.0, frequency_hz=2.0)

    panel.add_channel(_channel("ch0", "Pressure"), updated_chunk)

    assert panel.plotted_channel_ids() == ["ch0"]
    assert panel.legend_labels() == ["Pressure [bar]"]
    assert panel.curve_data("ch0")[1].tolist() == updated_chunk.values.tolist()

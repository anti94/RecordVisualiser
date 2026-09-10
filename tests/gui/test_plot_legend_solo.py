"""Legend gizleme ve solo — `F3-030`.

Kabul: seri görünürlüğü ve solo geri dönüşü doğru çalışır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 420)
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


def _add(panel: PlotPanel, channel_id: str, name: str, unit: str = "bar") -> None:
    panel.add_channel(
        _channel(channel_id, name, unit),
        sine(channel_id, sample_rate_hz=100.0, duration_s=1.0, frequency_hz=2.0),
    )


def _three(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    _add(panel, "ch1", "B")
    _add(panel, "ch2", "C")


# -- seri gorunurlugu -------------------------------------------


def test_hiding_a_series_keeps_it_plotted_but_not_visible(panel: PlotPanel) -> None:
    _three(panel)

    panel.set_series_visible("ch1", False)

    assert panel.plotted_channel_ids() == ["ch0", "ch1", "ch2"]
    assert not panel.is_series_visible("ch1")
    assert panel.visible_channel_ids() == ["ch0", "ch2"]


def test_showing_a_hidden_series_again(panel: PlotPanel) -> None:
    _three(panel)
    panel.set_series_visible("ch1", False)

    panel.set_series_visible("ch1", True)

    assert panel.is_series_visible("ch1")
    assert panel.visible_channel_ids() == ["ch0", "ch1", "ch2"]


def test_visibility_of_an_unknown_series_raises(panel: PlotPanel) -> None:
    _three(panel)
    with pytest.raises(KeyError):
        panel.set_series_visible("nope", False)
    with pytest.raises(KeyError):
        panel.is_series_visible("nope")


# -- solo + geri donus ----------------------------------------


def test_solo_shows_only_the_target_series(panel: PlotPanel) -> None:
    _three(panel)

    panel.solo_series("ch1")

    assert panel.soloed_channel() == "ch1"
    assert panel.visible_channel_ids() == ["ch1"]


def test_clear_solo_restores_the_pre_solo_visibility(panel: PlotPanel) -> None:
    _three(panel)
    panel.set_series_visible("ch0", False)  # solo oncesi ch0 gizli

    panel.solo_series("ch2")
    assert panel.visible_channel_ids() == ["ch2"]

    panel.clear_solo()

    assert panel.soloed_channel() is None
    # ch0 yine gizli, ch1 ve ch2 yine gorunur
    assert panel.visible_channel_ids() == ["ch1", "ch2"]


def test_toggle_solo_turns_it_on_then_off(panel: PlotPanel) -> None:
    _three(panel)

    panel.toggle_solo("ch0")
    assert panel.soloed_channel() == "ch0"
    assert panel.visible_channel_ids() == ["ch0"]

    panel.toggle_solo("ch0")
    assert panel.soloed_channel() is None
    assert panel.visible_channel_ids() == ["ch0", "ch1", "ch2"]


def test_switching_solo_target_updates_the_visible_series(panel: PlotPanel) -> None:
    _three(panel)
    panel.solo_series("ch0")

    panel.solo_series("ch2")

    assert panel.soloed_channel() == "ch2"
    assert panel.visible_channel_ids() == ["ch2"]

    panel.clear_solo()
    assert panel.visible_channel_ids() == ["ch0", "ch1", "ch2"]


def test_a_series_added_during_solo_starts_hidden_then_shows_after_clear(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    _add(panel, "ch1", "B")
    panel.solo_series("ch0")

    _add(panel, "ch2", "C")

    assert not panel.is_series_visible("ch2")
    panel.clear_solo()
    assert panel.visible_channel_ids() == ["ch0", "ch1", "ch2"]


def test_removing_the_soloed_series_ends_solo(panel: PlotPanel) -> None:
    _three(panel)
    panel.solo_series("ch1")

    panel.remove_channel("ch1")

    assert panel.soloed_channel() is None
    assert panel.visible_channel_ids() == ["ch0", "ch2"]


def test_solo_unknown_channel_raises(panel: PlotPanel) -> None:
    _three(panel)
    with pytest.raises(KeyError):
        panel.solo_series("nope")


def test_set_channel_resets_solo_state(panel: PlotPanel) -> None:
    _three(panel)
    panel.solo_series("ch1")

    panel.set_channel(
        _channel("ch9", "Z", "m"),
        sine("ch9", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=1.0),
    )

    assert panel.soloed_channel() is None
    assert panel.visible_channel_ids() == ["ch9"]

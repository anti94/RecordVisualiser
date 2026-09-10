"""Seri rengi, çizgi ve marker ayarı — `F3-031`.

Kabul: aynı kanal paneller arasında tutarlı varsayılan renkle açılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.status_icons import channel_color

pytestmark = pytest.mark.gui


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
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


# -- kabul kriteri: paneller arasi tutarli varsayilan renk -------


def test_same_channel_gets_the_same_default_color_in_two_panels(
    qtbot: QtBot,
) -> None:
    panel_a = PlotPanel()
    panel_b = PlotPanel()
    qtbot.addWidget(panel_a)
    qtbot.addWidget(panel_b)

    for panel in (panel_a, panel_b):
        panel.add_channel(
            _channel("ch3", "Accel Y", "g"),
            sine("ch3", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=1.0),
        )

    assert panel_a.series_color("ch3") == panel_b.series_color("ch3")
    assert panel_a.series_color("ch3") == channel_color("ch3")


def test_default_series_color_is_a_pure_function_of_channel_id() -> None:
    assert PlotPanel.default_series_color("ch0") == channel_color("ch0")
    assert PlotPanel.default_series_color("ch0") == PlotPanel.default_series_color("ch0")


def test_default_style_has_solid_line_no_marker(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")

    style = panel.series_style("ch0")
    assert style.line_style == "solid"
    assert style.width == 1
    assert style.symbol is None
    assert style.color == channel_color("ch0")


# -- renk / cizgi / marker gecersiz kilma ----------------------


def test_overriding_the_colour_updates_only_that_series(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    _add(panel, "ch1", "B")
    other_before = panel.series_color("ch1")

    panel.set_series_style("ch0", color="#ff0000")

    assert panel.series_color("ch0") == "#ff0000"
    assert panel.series_color("ch1") == other_before


def test_partial_update_keeps_the_other_fields(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    original_colour = panel.series_color("ch0")

    panel.set_series_style("ch0", width=3, line_style="dash")

    style = panel.series_style("ch0")
    assert style.width == 3
    assert style.line_style == "dash"
    assert style.color == original_colour
    assert style.symbol is None


def test_setting_and_clearing_a_marker(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")

    panel.set_series_style("ch0", symbol="o")
    assert panel.series_style("ch0").symbol == "o"

    panel.set_series_style("ch0", symbol=None)
    assert panel.series_style("ch0").symbol is None


def test_invalid_line_style_raises(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    with pytest.raises(ValueError, match="cizgi bicimi"):
        panel.set_series_style("ch0", line_style="wavy")


def test_invalid_marker_raises(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    with pytest.raises(ValueError, match="marker"):
        panel.set_series_style("ch0", symbol="star")


def test_style_of_an_unknown_channel_raises(panel: PlotPanel) -> None:
    with pytest.raises(KeyError):
        panel.series_style("nope")
    with pytest.raises(KeyError):
        panel.set_series_style("nope", color="#123456")


# -- kalicilik: yeniden ekleme stili korur --------------------


def test_re_adding_the_same_channel_keeps_the_custom_style(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    panel.set_series_style("ch0", color="#00ff00", width=4, symbol="s")

    # ayni kanali guncelle (yeni veri)
    panel.add_channel(
        _channel("ch0", "A"),
        sine("ch0", sample_rate_hz=200.0, duration_s=1.0, frequency_hz=2.0),
    )

    style = panel.series_style("ch0")
    assert style.color == "#00ff00"
    assert style.width == 4
    assert style.symbol == "s"


def test_removing_a_series_drops_its_style(panel: PlotPanel) -> None:
    _add(panel, "ch0", "A")
    panel.remove_channel("ch0")

    with pytest.raises(KeyError):
        panel.series_style("ch0")

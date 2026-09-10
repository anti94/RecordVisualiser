"""Yalnız X yakınlaştırma kipi — `F3-022`.

Kabul: X aralığı değişirken Y aralığı sabit kalır.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

_EPS = 1e-6


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


def _populate(panel: PlotPanel, channel_id: str = "ch0") -> None:
    chunk = sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0)
    panel.add_channel(_channel(channel_id, "Pressure"), chunk)


def _span(lo: float, hi: float) -> float:
    return hi - lo


def _mid(lo: float, hi: float) -> float:
    return (lo + hi) / 2.0


# -- kip secimi -----------------------------------------------------


def test_default_zoom_mode_is_xy(panel: PlotPanel) -> None:
    assert panel.zoom_mode == "xy"


def test_setting_x_mode_disables_y_mouse_interaction(panel: PlotPanel) -> None:
    panel.set_zoom_mode("x")

    assert panel.zoom_mode == "x"
    assert panel.plot.getViewBox().state["mouseEnabled"] == [True, False]


def test_unknown_zoom_mode_raises(panel: PlotPanel) -> None:
    with pytest.raises(ValueError, match="Bilinmeyen yakinlastirma kipi"):
        panel.set_zoom_mode("diagonal")


def test_non_positive_zoom_factor_raises(panel: PlotPanel) -> None:
    _populate(panel)
    with pytest.raises(ValueError, match="pozitif"):
        panel.zoom(0.0)


# -- kabul kriteri: X degisir, Y sabit ----------------------------


def test_x_zoom_shrinks_x_span_and_leaves_y_untouched(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.set_zoom_mode("x")
    panel.zoom(0.5)

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert abs(_span(x1_min, x1_max) - _span(x0_min, x0_max) * 0.5) < _EPS
    assert abs(y1_min - y0_min) < _EPS
    assert abs(y1_max - y0_max) < _EPS


def test_x_zoom_keeps_the_x_centre_fixed(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, _, _ = panel.visible_range()
    centre_before = _mid(x0_min, x0_max)

    panel.set_zoom_mode("x")
    panel.zoom(0.25)

    x1_min, x1_max, _, _ = panel.visible_range()
    assert abs(_mid(x1_min, x1_max) - centre_before) < _EPS


def test_x_zoom_out_widens_x_span_only(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.set_zoom_mode("x")
    panel.zoom(2.0)

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert _span(x1_min, x1_max) > _span(x0_min, x0_max)
    assert abs(y1_min - y0_min) < _EPS
    assert abs(y1_max - y0_max) < _EPS


def test_x_zoom_does_not_touch_series_data(panel: PlotPanel) -> None:
    _populate(panel)
    x_before, y_before = panel.curve_data("ch0")

    panel.set_zoom_mode("x")
    panel.zoom(0.3)

    x_after, y_after = panel.curve_data("ch0")
    assert np.array_equal(x_before, x_after)
    assert np.array_equal(y_before, y_after)


# -- ontanimli xy kipi iki ekseni de olcekler --------------------


def test_xy_mode_scales_both_axes(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.zoom(0.5)  # kip "xy"

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert abs(_span(x1_min, x1_max) - _span(x0_min, x0_max) * 0.5) < _EPS
    assert abs(_span(y1_min, y1_max) - _span(y0_min, y0_max) * 0.5) < _EPS

"""Yalnız Y yakınlaştırma kipi — `F3-023`.

Kabul: Y aralığı değişirken X aralığı sabit kalır.
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


def _populate(panel: PlotPanel, channel_id: str = "ch0", unit: str = "bar") -> None:
    chunk = sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0)
    panel.add_channel(_channel(channel_id, "Pressure", unit), chunk)


def _span(lo: float, hi: float) -> float:
    return hi - lo


def _mid(lo: float, hi: float) -> float:
    return (lo + hi) / 2.0


def test_setting_y_mode_disables_x_mouse_interaction(panel: PlotPanel) -> None:
    panel.set_zoom_mode("y")

    assert panel.zoom_mode == "y"
    assert panel.plot.getViewBox().state["mouseEnabled"] == [False, True]


# -- kabul kriteri: Y degisir, X sabit ---------------------------


def test_y_zoom_shrinks_y_span_and_leaves_x_untouched(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.set_zoom_mode("y")
    panel.zoom(0.5)

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert abs(_span(y1_min, y1_max) - _span(y0_min, y0_max) * 0.5) < _EPS
    assert abs(x1_min - x0_min) < _EPS
    assert abs(x1_max - x0_max) < _EPS


def test_y_zoom_keeps_the_y_centre_fixed(panel: PlotPanel) -> None:
    _populate(panel)
    _, _, y0_min, y0_max = panel.visible_range()
    centre_before = _mid(y0_min, y0_max)

    panel.set_zoom_mode("y")
    panel.zoom(0.25)

    _, _, y1_min, y1_max = panel.visible_range()
    assert abs(_mid(y1_min, y1_max) - centre_before) < _EPS


def test_y_zoom_out_widens_y_span_only(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.set_zoom_mode("y")
    panel.zoom(3.0)

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert _span(y1_min, y1_max) > _span(y0_min, y0_max)
    assert abs(x1_min - x0_min) < _EPS
    assert abs(x1_max - x0_max) < _EPS


def test_y_zoom_does_not_touch_series_data(panel: PlotPanel) -> None:
    _populate(panel)
    x_before, y_before = panel.curve_data("ch0")

    panel.set_zoom_mode("y")
    panel.zoom(0.4)

    x_after, y_after = panel.curve_data("ch0")
    assert np.array_equal(x_before, x_after)
    assert np.array_equal(y_before, y_after)


def test_switching_from_x_to_y_mode_updates_mouse_axes(panel: PlotPanel) -> None:
    panel.set_zoom_mode("x")
    assert panel.plot.getViewBox().state["mouseEnabled"] == [True, False]

    panel.set_zoom_mode("y")
    assert panel.plot.getViewBox().state["mouseEnabled"] == [False, True]


# -- ikinci Y ekseni de ayni oranda olceklenir (F3-020 ile birlikte) --


def test_y_zoom_scales_the_second_y_axis_proportionally(panel: PlotPanel) -> None:
    _populate(panel, "ch0", "bar")
    panel.add_channel(
        _channel("ch1", "Temp", "C"),
        sine("ch1", sample_rate_hz=100.0, duration_s=2.0, frequency_hz=3.0),
    )
    assert panel.right_axis_visible
    before = panel.right_axis_y_range()
    assert before is not None
    r0_min, r0_max = before

    panel.set_zoom_mode("y")
    panel.zoom(0.5)

    after = panel.right_axis_y_range()
    assert after is not None
    r1_min, r1_max = after
    assert abs((r1_max - r1_min) - (r0_max - r0_min) * 0.5) < 1e-3

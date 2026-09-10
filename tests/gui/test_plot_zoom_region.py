"""XY (bölge) yakınlaştırma — `F3-024`.

Kabul: iki eksen seçilen bölgeye yakınlaşır.
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


def _channel(channel_id: str, name: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=100.0,
    )


def _populate(panel: PlotPanel) -> None:
    chunk = sine("ch0", sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0, amplitude=3.0)
    panel.add_channel(_channel("ch0", "Pressure"), chunk)


# -- kabul kriteri: iki eksen secilen bolgeye oturur -------------


def test_zoom_to_region_sets_both_axes_to_the_selected_box(panel: PlotPanel) -> None:
    _populate(panel)

    panel.zoom_to_region(0.2, 0.8, -1.0, 1.0)

    x_min, x_max, y_min, y_max = panel.visible_range()
    assert abs(x_min - 0.2) < _EPS
    assert abs(x_max - 0.8) < _EPS
    assert abs(y_min - (-1.0)) < _EPS
    assert abs(y_max - 1.0) < _EPS


def test_zoom_to_region_changes_both_axes_not_just_one(panel: PlotPanel) -> None:
    _populate(panel)
    x0_min, x0_max, y0_min, y0_max = panel.visible_range()

    panel.zoom_to_region(0.5, 1.5, -0.25, 0.25)

    x1_min, x1_max, y1_min, y1_max = panel.visible_range()
    assert (x1_min, x1_max) != (x0_min, x0_max)
    assert (y1_min, y1_max) != (y0_min, y0_max)


def test_region_zoom_ignores_the_active_zoom_mode(panel: PlotPanel) -> None:
    """Bölge seçimi tanımı gereği iki eksenli — kip "x" olsa bile Y de oturur."""
    _populate(panel)
    panel.set_zoom_mode("x")

    panel.zoom_to_region(0.3, 0.6, 0.0, 2.0)

    _, _, y_min, y_max = panel.visible_range()
    assert abs(y_min - 0.0) < _EPS
    assert abs(y_max - 2.0) < _EPS


def test_region_centre_becomes_the_view_centre(panel: PlotPanel) -> None:
    _populate(panel)

    panel.zoom_to_region(1.0, 1.4, -2.0, -1.0)

    x_min, x_max, y_min, y_max = panel.visible_range()
    assert abs((x_min + x_max) / 2.0 - 1.2) < _EPS
    assert abs((y_min + y_max) / 2.0 - (-1.5)) < _EPS


# -- gecersiz bolge --------------------------------------------


@pytest.mark.parametrize(
    ("x0", "x1", "y0", "y1"),
    [
        (0.8, 0.2, 0.0, 1.0),  # x ters
        (0.2, 0.8, 1.0, 0.0),  # y ters
        (0.5, 0.5, 0.0, 1.0),  # x sifir genislik
        (0.2, 0.8, 1.0, 1.0),  # y sifir yukseklik
    ],
)
def test_invalid_region_raises(
    panel: PlotPanel, x0: float, x1: float, y0: float, y1: float
) -> None:
    _populate(panel)
    with pytest.raises(ValueError, match="Gecersiz bolge"):
        panel.zoom_to_region(x0, x1, y0, y1)


# -- veri degismez -------------------------------------------


def test_region_zoom_does_not_touch_series_data(panel: PlotPanel) -> None:
    _populate(panel)
    x_before, y_before = panel.curve_data("ch0")

    panel.zoom_to_region(0.1, 0.9, -2.5, 2.5)

    x_after, y_after = panel.curve_data("ch0")
    assert np.array_equal(x_before, x_after)
    assert np.array_equal(y_before, y_after)

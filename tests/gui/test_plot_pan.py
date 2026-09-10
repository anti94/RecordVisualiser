"""Pan etkileşimi — `F3-021`.

Kabul: sürükleme görünür aralığı değiştirir; veri değişmez.
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


def _populate(panel: PlotPanel, channel_id: str = "ch0") -> list[float]:
    chunk = sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0)
    panel.add_channel(_channel(channel_id, "Pressure"), chunk)
    return [float(v) for v in chunk.values]


# -- gorunur aralik degisir ------------------------------------------


def test_pan_shifts_the_visible_x_range_by_the_requested_amount(panel: PlotPanel) -> None:
    _populate(panel)
    x_min_before, x_max_before = panel.visible_x_range()

    panel.pan(0.5)

    x_min_after, x_max_after = panel.visible_x_range()
    assert abs(x_min_after - (x_min_before + 0.5)) < 1e-6
    assert abs(x_max_after - (x_max_before + 0.5)) < 1e-6


def test_pan_can_move_the_view_in_both_directions(panel: PlotPanel) -> None:
    _populate(panel)
    start_min, _ = panel.visible_x_range()

    panel.pan(1.0)
    panel.pan(-1.0)

    end_min, _ = panel.visible_x_range()
    assert abs(end_min - start_min) < 1e-6


def test_pan_shifts_the_y_range_too(panel: PlotPanel) -> None:
    _populate(panel)
    _, _, y_min_before, y_max_before = panel.visible_range()

    panel.pan(0.0, dy=2.0)

    _, _, y_min_after, y_max_after = panel.visible_range()
    assert abs(y_min_after - (y_min_before + 2.0)) < 1e-6
    assert abs(y_max_after - (y_max_before + 2.0)) < 1e-6


# -- veri degismez --------------------------------------------------


def test_pan_does_not_change_the_plotted_curve_data(panel: PlotPanel) -> None:
    original_values = _populate(panel)
    x_before, y_before = panel.curve_data("ch0")

    panel.pan(0.7, dy=1.3)

    x_after, y_after = panel.curve_data("ch0")
    assert np.array_equal(x_before, x_after)
    assert np.array_equal(y_before, y_after)
    assert y_after.tolist() == original_values


def test_pan_leaves_every_series_untouched(panel: PlotPanel) -> None:
    _populate(panel, "ch0")
    second = sine("ch1", sample_rate_hz=100.0, duration_s=2.0, frequency_hz=3.0)
    panel.add_channel(_channel("ch1", "Temp", "C"), second)
    snapshots = {cid: panel.curve_data(cid) for cid in panel.plotted_channel_ids()}

    panel.pan(0.4)

    for cid, (x_before, y_before) in snapshots.items():
        x_after, y_after = panel.curve_data(cid)
        assert np.array_equal(x_before, x_after), cid
        assert np.array_equal(y_before, y_after), cid


def test_pan_keeps_the_sample_count_and_channel_list(panel: PlotPanel) -> None:
    _populate(panel)
    count_before = panel.sample_count

    panel.pan(5.0)

    assert panel.sample_count == count_before
    assert panel.plotted_channel_ids() == ["ch0"]


# -- yapilandirma: pyqtgraph pan modu acik --------------------------

#: pyqtgraph `ViewBox.PanMode` sabitinin degeri (stub tasimadigi icin
#: modulden alinamiyor; RectMode = 1, PanMode = 3).
_PAN_MODE = 3


def test_view_box_is_in_pan_mode_with_mouse_enabled(panel: PlotPanel) -> None:
    view_box = panel.plot.getViewBox()
    assert view_box.state["mouseMode"] == _PAN_MODE
    assert view_box.state["mouseEnabled"] == [True, True]

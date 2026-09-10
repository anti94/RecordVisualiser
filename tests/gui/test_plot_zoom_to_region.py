"""Seçili bölgeye yakınlaşma — `F3-029`.

Kabul: grafik yalnız seçilen zaman aralığını gösterir.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

BASE_NS = 1_767_225_600_000_000_000
STEP_NS = NS_PER_SECOND // 10
_EPS = 1e-6


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
        sample_rate_hz=10.0,
    )


def _populate(
    panel: PlotPanel, channel_id: str = "ch0", unit: str = "bar", scale: float = 1.0
) -> None:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(10)], dtype=np.int64)
    values = np.arange(10, dtype=np.float64) * scale  # 0..9*scale
    panel.add_channel(
        _channel(channel_id, "Sig", unit),
        DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values),
    )


# -- kabul kriteri: yalniz secilen zaman araligi -----------------


def test_zoom_to_time_region_sets_x_to_exactly_the_selection(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_time_region(0.3, 0.6)

    assert panel.zoom_to_time_region()

    x_min, x_max = panel.visible_x_range()
    assert abs(x_min - 0.3) < _EPS
    assert abs(x_max - 0.6) < _EPS


def test_zoom_to_time_region_fits_y_to_the_windowed_samples(panel: PlotPanel) -> None:
    _populate(panel, scale=1.0)  # ornek degerleri = indeks
    panel.set_time_region(0.3, 0.6)  # indeks 3..6 -> deger 3..6

    panel.zoom_to_time_region()

    _, _, y_min, y_max = panel.visible_range()
    assert y_min <= 3.0 and y_max >= 6.0
    assert y_min > 0.0, "pencere disindaki 0..2 gorunmemeli"
    assert y_max < 9.0, "pencere disindaki 7..9 gorunmemeli"


def test_zoom_to_time_region_clears_the_band_by_default(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_time_region(0.2, 0.8)

    panel.zoom_to_time_region()

    assert panel.time_region_x() is None


def test_zoom_to_time_region_can_keep_the_band(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_time_region(0.2, 0.8)

    panel.zoom_to_time_region(clear_region=False)

    assert panel.time_region_x() == (0.2, 0.8)


def test_zoom_to_time_region_without_a_selection_returns_false(panel: PlotPanel) -> None:
    _populate(panel)
    before = panel.visible_range()

    assert panel.zoom_to_time_region() is False
    assert panel.visible_range() == before


def test_reset_view_restores_the_full_range_after_a_region_zoom(panel: PlotPanel) -> None:
    _populate(panel)
    home = panel.visible_range()
    panel.set_time_region(0.3, 0.6)
    panel.zoom_to_time_region()
    assert panel.visible_x_range() != (home[0], home[1])

    panel.reset_view()

    now = panel.visible_range()
    assert all(abs(a - b) < 1e-3 for a, b in zip(now, home))


def test_region_zoom_does_not_change_series_data(panel: PlotPanel) -> None:
    _populate(panel)
    x_before, y_before = panel.curve_data("ch0")
    panel.set_time_region(0.2, 0.7)

    panel.zoom_to_time_region()

    x_after, y_after = panel.curve_data("ch0")
    assert np.array_equal(x_before, x_after)
    assert np.array_equal(y_before, y_after)


def test_region_zoom_fits_the_second_y_axis_window(panel: PlotPanel) -> None:
    _populate(panel, "ch0", "bar", scale=1.0)
    _populate(panel, "ch1", "C", scale=100.0)  # 0..900, sag eksen
    assert panel.right_axis_visible
    panel.set_time_region(0.4, 0.5)  # indeks 4,5 -> ch1 degerleri 400, 500

    panel.zoom_to_time_region()

    right = panel.right_axis_y_range()
    assert right is not None
    r_min, r_max = right
    assert r_min <= 400.0 and r_max >= 500.0
    assert r_min > 0.0 and r_max < 900.0

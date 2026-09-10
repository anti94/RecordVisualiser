"""TX aralıklarını gölgeli bölge olarak çizme — `F3-047`.

Kabul: START/STOP sınırları zaman ekseniyle eşleşir.
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
STEP_NS = NS_PER_SECOND // 8
_EPS = 1e-6


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 420)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{channel_id}",
        name=channel_id,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="u",
        sample_rate_hz=8.0,
    )


def _chunk(channel_id: str, count: int = 16) -> DataChunk:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(count)], dtype=np.int64)
    return DataChunk(
        channel_id=channel_id,
        timestamps_ns=stamps,
        values=np.arange(count, dtype=np.float64),
    )


SPANS = [
    (BASE_NS + 250_000_000, BASE_NS + 750_000_000),
    (BASE_NS + 1_250_000_000, BASE_NS + 1_500_000_000),
]


# -- kabul kriteri: START/STOP sinirlari zaman ekseniyle eslesir -


def test_tx_region_edges_match_the_time_mapping(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    panel.set_tx_regions(SPANS)

    assert panel.tx_region_count() == 2
    lo0, hi0 = panel.tx_region_x(0)
    assert abs(lo0 - 0.25) < _EPS
    assert abs(hi0 - 0.75) < _EPS
    lo1, hi1 = panel.tx_region_x(1)
    assert abs(lo1 - 1.25) < _EPS
    assert abs(hi1 - 1.5) < _EPS
    # birebir F3-019 esleme fonksiyonuyla
    assert lo0 == panel.x_for_timestamp_ns(SPANS[0][0])
    assert hi0 == panel.x_for_timestamp_ns(SPANS[0][1])


def test_reversed_span_bounds_are_normalised(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    panel.set_tx_regions([(BASE_NS + 900_000_000, BASE_NS + 400_000_000)])

    lo, hi = panel.tx_region_x(0)
    assert abs(lo - 0.4) < _EPS
    assert abs(hi - 0.9) < _EPS


def test_regions_set_before_any_series_appear_after_a_series_is_added(panel: PlotPanel) -> None:
    panel.set_tx_regions(SPANS)
    assert panel.tx_region_count() == 0

    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    assert panel.tx_region_count() == 2


def test_clear_tx_regions_removes_them(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_tx_regions(SPANS)

    panel.clear_tx_regions()

    assert panel.tx_region_count() == 0
    assert panel.tx_region_times_ns() == []


def test_region_edges_are_stable_under_pan_and_zoom(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_tx_regions(SPANS)

    panel.pan(5.0)
    panel.zoom(0.3)

    lo, hi = panel.tx_region_x(0)
    assert abs(lo - 0.25) < _EPS
    assert abs(hi - 0.75) < _EPS


def test_regions_survive_a_channel_switch(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_tx_regions(SPANS)

    panel.set_channel(_channel("ch1"), _chunk("ch1"))

    assert panel.tx_region_count() == 2
    lo, _hi = panel.tx_region_x(0)
    assert abs(lo - 0.25) < _EPS


def test_emptying_the_panel_drops_regions_but_keeps_the_pending_set(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_tx_regions(SPANS)

    panel.remove_channel("ch0")
    assert panel.tx_region_count() == 0

    panel.add_channel(_channel("ch2"), _chunk("ch2"))
    assert panel.tx_region_count() == 2


def test_tx_region_times_ns_reports_the_source_bounds(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_tx_regions(SPANS)

    assert panel.tx_region_times_ns() == SPANS

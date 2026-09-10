"""Zaman bölgesi seçimi — `F3-028`.

Kabul: seçili başlangıç/bitiş repository aralığına (mutlak epoch-ns
`TimeRange`) dönüşür.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND, TimeRange
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

BASE_NS = 1_767_225_600_000_000_000
STEP_NS = NS_PER_SECOND // 10


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 420)
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
        sample_rate_hz=10.0,
    )


def _populate(panel: PlotPanel) -> None:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(10)], dtype=np.int64)
    values = np.arange(10, dtype=np.float64)
    panel.add_channel(
        _channel("ch0", "Pressure"),
        DataChunk(channel_id="ch0", timestamps_ns=stamps, values=values),
    )


# -- kabul kriteri: secim -> TimeRange --------------------------


def test_selected_region_converts_to_an_absolute_time_range(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_time_region(0.2, 0.7)

    assert panel.time_region_range() == TimeRange(BASE_NS + 200_000_000, BASE_NS + 700_000_000)


def test_region_bounds_may_be_given_in_any_order(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_time_region(0.7, 0.2)

    assert panel.time_region_x() == (0.2, 0.7)
    assert panel.time_region_range() == TimeRange(BASE_NS + 200_000_000, BASE_NS + 700_000_000)


def test_no_region_selected_yields_none(panel: PlotPanel) -> None:
    _populate(panel)

    assert panel.time_region_x() is None
    assert panel.time_region_range() is None


def test_clear_time_region_removes_the_selection(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_time_region(0.1, 0.9)
    assert panel.time_region_range() is not None

    panel.clear_time_region()

    assert panel.time_region_x() is None
    assert panel.time_region_range() is None


def test_set_time_region_before_data_is_a_no_op(panel: PlotPanel) -> None:
    panel.set_time_region(0.2, 0.7)

    assert panel.time_region_x() is None
    assert panel.time_region_range() is None


def test_emptying_the_panel_clears_the_region(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_time_region(0.2, 0.7)

    panel.clear()

    assert panel.time_region_range() is None


# -- sinyal: secim degisince (start_ns, end_ns) yayilir ---------


def test_time_region_changed_signal_carries_epoch_ns_bounds(panel: PlotPanel) -> None:
    _populate(panel)
    received: list[tuple[int, int]] = []

    def _record(start_ns: int, end_ns: int) -> None:
        received.append((start_ns, end_ns))

    panel.time_region_changed.connect(_record)

    panel.set_time_region(0.3, 0.6)

    assert received
    assert received[-1] == (BASE_NS + 300_000_000, BASE_NS + 600_000_000)


def test_region_range_start_is_not_after_end(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_time_region(0.55, 0.15)

    time_range = panel.time_region_range()
    assert time_range is not None
    assert time_range.start_ns <= time_range.end_ns
    assert time_range.duration_ns == 400_000_000

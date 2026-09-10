"""Olay zaman işaretleri — `F3-045`.

Kabul: olay zamanı grafik X koordinatıyla eşleşir.
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


def _chunk(channel_id: str, count: int = 8) -> DataChunk:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(count)], dtype=np.int64)
    values = np.arange(count, dtype=np.float64)
    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


MARKS = [(BASE_NS + 250_000_000, "#ff0000"), (BASE_NS + 750_000_000, "#00ff00")]


# -- kabul kriteri: olay zamani X koordinatiyla eslesir ---------


def test_marker_x_matches_the_time_mapping(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    panel.set_event_markers(MARKS)

    assert panel.event_marker_count() == 2
    assert abs(panel.event_marker_x(0) - 0.25) < _EPS
    assert abs(panel.event_marker_x(1) - 0.75) < _EPS
    # birebir F3-019 esleme fonksiyonuyla
    assert panel.event_marker_x(0) == panel.x_for_timestamp_ns(MARKS[0][0])


def test_markers_set_before_any_series_appear_once_a_series_is_added(panel: PlotPanel) -> None:
    panel.set_event_markers(MARKS)
    assert panel.event_marker_count() == 0  # ankor yok

    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    assert panel.event_marker_count() == 2
    assert abs(panel.event_marker_x(0) - 0.25) < _EPS


def test_clear_event_markers_removes_them(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_event_markers(MARKS)

    panel.clear_event_markers()

    assert panel.event_marker_count() == 0
    assert panel.event_marker_times_ns() == []


def test_marker_position_is_stable_under_pan_and_zoom(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_event_markers(MARKS)

    panel.pan(3.0)
    panel.zoom(0.25)

    assert abs(panel.event_marker_x(0) - 0.25) < _EPS
    assert abs(panel.event_marker_x(1) - 0.75) < _EPS


def test_markers_outside_the_data_range_still_place(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))

    panel.set_event_markers(
        [(BASE_NS - NS_PER_SECOND, "#fff"), (BASE_NS + 5 * NS_PER_SECOND, "#fff")]
    )

    assert abs(panel.event_marker_x(0) - (-1.0)) < _EPS
    assert abs(panel.event_marker_x(1) - 5.0) < _EPS


def test_markers_survive_a_channel_switch(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_event_markers(MARKS)

    # set_channel -> clear + add: ankor yeniden kurulur
    panel.set_channel(_channel("ch1"), _chunk("ch1"))

    assert panel.event_marker_count() == 2
    assert abs(panel.event_marker_x(0) - 0.25) < _EPS


def test_emptying_the_panel_drops_the_markers_but_keeps_the_pending_set(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_event_markers(MARKS)

    panel.remove_channel("ch0")
    assert panel.event_marker_count() == 0

    panel.add_channel(_channel("ch2"), _chunk("ch2"))
    assert panel.event_marker_count() == 2


def test_event_marker_times_ns_reports_the_source_timestamps(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0"), _chunk("ch0"))
    panel.set_event_markers(MARKS)

    assert panel.event_marker_times_ns() == [MARKS[0][0], MARKS[1][0]]

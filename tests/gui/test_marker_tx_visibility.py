"""Marker ve TX görünürlüğü kontrolleri — `F3-050`.

Kabul: görünürlük değişimi olay verisini etkilemez.
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
from sonar_analyzer.ui.plot_tool_bar import PlotToolBar
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

BASE_NS = 1_767_225_600_000_000_000
STEP_NS = NS_PER_SECOND // 8
MARKS = [(BASE_NS + 250_000_000, "#ff0000"), (BASE_NS + 750_000_000, "#00ff00")]
SPANS = [(BASE_NS + 100_000_000, BASE_NS + 400_000_000)]


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 420)
    widget.show()
    qtbot.waitExposed(widget)
    widget.add_channel(
        ChannelMetadata(
            id="ch0",
            path="Sensors/ch0",
            name="ch0",
            dtype="float32",
            source=ChannelSource.SENSORS,
            unit="u",
            sample_rate_hz=8.0,
        ),
        DataChunk(
            channel_id="ch0",
            timestamps_ns=np.array([BASE_NS + i * STEP_NS for i in range(16)], dtype=np.int64),
            values=np.arange(16, dtype=np.float64),
        ),
    )
    widget.set_event_markers(MARKS)
    widget.set_tx_regions(SPANS)
    return widget


# -- kabul kriteri: gorunurluk verisi etkilemez ---------------


def test_hiding_markers_keeps_the_underlying_data(panel: PlotPanel) -> None:
    panel.set_event_markers_visible(False)

    assert not panel.event_markers_visible
    # veri (zamanlar) ve cizgi nesneleri aynen durur, yalniz gizli
    assert panel.event_marker_times_ns() == [MARKS[0][0], MARKS[1][0]]
    assert panel.event_marker_count() == 2


def test_showing_markers_again_restores_them_at_the_same_positions(panel: PlotPanel) -> None:
    before = [panel.event_marker_x(i) for i in range(panel.event_marker_count())]

    panel.set_event_markers_visible(False)
    panel.set_event_markers_visible(True)

    after = [panel.event_marker_x(i) for i in range(panel.event_marker_count())]
    assert panel.event_markers_visible
    assert before == after
    assert panel.event_marker_count() == 2


def test_hiding_tx_regions_keeps_the_underlying_data(panel: PlotPanel) -> None:
    panel.set_tx_regions_visible(False)

    assert not panel.tx_regions_visible
    assert panel.tx_region_times_ns() == SPANS
    assert panel.tx_region_count() == 1  # bant korunur, yalniz gizli


def test_showing_tx_regions_again_restores_them(panel: PlotPanel) -> None:
    lo_before, hi_before = panel.tx_region_x(0)

    panel.set_tx_regions_visible(False)
    panel.set_tx_regions_visible(True)

    assert panel.tx_regions_visible
    assert panel.tx_region_x(0) == (lo_before, hi_before)


def test_markers_stay_hidden_across_a_channel_switch(panel: PlotPanel) -> None:
    panel.set_event_markers_visible(False)

    panel.set_channel(
        ChannelMetadata(
            id="ch1",
            path="Sensors/ch1",
            name="ch1",
            dtype="float32",
            source=ChannelSource.SENSORS,
            unit="u",
            sample_rate_hz=8.0,
        ),
        DataChunk(
            channel_id="ch1",
            timestamps_ns=np.array([BASE_NS + i * STEP_NS for i in range(8)], dtype=np.int64),
            values=np.arange(8, dtype=np.float64),
        ),
    )

    assert not panel.event_markers_visible
    assert panel.event_marker_count() == 2  # cizgiler korunur


# -- PlotToolBar kontrolleri sinyal yayar --------------------


def test_toolbar_checkboxes_emit_visibility_signals(qtbot: QtBot) -> None:
    bar = PlotToolBar()
    qtbot.addWidget(bar)
    marker_states: list[bool] = []
    tx_states: list[bool] = []
    bar.markers_visible_toggled.connect(marker_states.append)
    bar.tx_visible_toggled.connect(tx_states.append)

    bar.markers_checkbox.setChecked(False)
    bar.tx_checkbox.setChecked(False)
    bar.markers_checkbox.setChecked(True)

    assert marker_states == [False, True]
    assert tx_states == [False]

"""Crosshair ve cursor okuması — `F3-026`.

Kabul: cursor zamanı ve en yakın örnek değeri doğru gösterilir.
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
STEP_NS = NS_PER_SECOND // 10  # 100 ms


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 420)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str, name: str, unit: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit=unit,
        sample_rate_hz=10.0,
    )


def _ramp_chunk(channel_id: str, scale: float) -> DataChunk:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(10)], dtype=np.int64)
    values = np.arange(10, dtype=np.float64) * scale
    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


def _populate(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "Pressure", "bar"), _ramp_chunk("ch0", 10.0))


# -- en yakin ornek ------------------------------------------------


def test_nearest_sample_snaps_down_to_the_closer_sample(panel: PlotPanel) -> None:
    _populate(panel)

    assert panel.nearest_sample(0.24) == (0.2, 20.0)


def test_nearest_sample_snaps_up_to_the_closer_sample(panel: PlotPanel) -> None:
    _populate(panel)

    assert panel.nearest_sample(0.26) == (0.3, 30.0)


def test_nearest_sample_exact_hit_returns_that_sample(panel: PlotPanel) -> None:
    _populate(panel)

    assert panel.nearest_sample(0.5) == (0.5, 50.0)


def test_nearest_sample_clamps_beyond_the_data_range(panel: PlotPanel) -> None:
    _populate(panel)

    assert panel.nearest_sample(-3.0) == (0.0, 0.0)
    assert panel.nearest_sample(99.0) == (0.9, 90.0)


def test_nearest_sample_of_a_named_non_primary_series(panel: PlotPanel) -> None:
    _populate(panel)
    panel.add_channel(_channel("ch1", "Temp", "C"), _ramp_chunk("ch1", 2.0))

    assert panel.nearest_sample(0.31, "ch1") == (0.3, 6.0)


def test_nearest_sample_is_none_without_data(panel: PlotPanel) -> None:
    assert panel.nearest_sample(0.0) is None


# -- crosshair gorunurlugu + konum ------------------------------


def test_set_cursor_shows_the_crosshair_and_records_x(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor(0.42, 15.0)

    assert panel.crosshair_visible()
    assert panel.cursor_x() == 0.42


def test_clear_cursor_hides_the_crosshair(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_cursor(0.42)
    assert panel.crosshair_visible()

    panel.clear_cursor()

    assert not panel.crosshair_visible()
    assert panel.cursor_x() is None
    assert panel.cursor_readout_text() == ""


def test_set_cursor_on_an_empty_panel_is_a_no_op(panel: PlotPanel) -> None:
    panel.set_cursor(1.0)

    assert not panel.crosshair_visible()
    assert panel.cursor_x() is None


def test_emptying_the_panel_clears_the_cursor(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_cursor(0.3)

    panel.clear()

    assert not panel.crosshair_visible()
    assert panel.cursor_x() is None


# -- kabul kriteri: okuma metni ve sinyal ----------------------


def test_readout_text_shows_time_name_value_and_unit(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor(0.62)

    text = panel.cursor_readout_text()
    assert "t=0.600 s" in text
    assert "Pressure" in text
    assert "60" in text
    assert "bar" in text


def test_cursor_moved_signal_carries_the_nearest_sample(panel: PlotPanel) -> None:
    _populate(panel)
    received: list[tuple[float, float]] = []

    def _record(sample_t: float, sample_v: float) -> None:
        received.append((sample_t, sample_v))

    panel.cursor_moved.connect(_record)

    panel.set_cursor(0.74)

    assert received == [(0.7, 70.0)]

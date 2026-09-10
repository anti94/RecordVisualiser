"""İki cursor fark ölçümü — `F3-027`.

Kabul: Δzaman, Δdeğer ve sıfır olmayan süre için frekans doğrudur.
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


def _populate(panel: PlotPanel) -> None:
    stamps = np.array([BASE_NS + i * STEP_NS for i in range(10)], dtype=np.int64)
    values = np.arange(10, dtype=np.float64) * 10.0  # 0, 10, 20, ... 90
    panel.add_channel(
        _channel("ch0", "Pressure"),
        DataChunk(channel_id="ch0", timestamps_ns=stamps, values=values),
    )


# -- kabul kriteri: dt / dvalue / frekans ------------------------


def test_delta_between_two_snapped_cursors(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.19)  # -> ornek 0.2 / 20
    panel.set_cursor_b(0.71)  # -> ornek 0.7 / 70

    reading = panel.delta_measurement()
    assert reading is not None
    assert abs(reading.dt_seconds - 0.5) < 1e-9
    assert abs(reading.dvalue - 50.0) < 1e-9
    assert reading.frequency_hz is not None
    assert abs(reading.frequency_hz - 2.0) < 1e-9


def test_delta_is_signed_when_b_is_before_a(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.8)  # 0.8 / 80
    panel.set_cursor_b(0.3)  # 0.3 / 30

    reading = panel.delta_measurement()
    assert reading is not None
    assert abs(reading.dt_seconds - (-0.5)) < 1e-9
    assert abs(reading.dvalue - (-50.0)) < 1e-9
    # frekans daima pozitif: 1 / |dt|
    assert reading.frequency_hz is not None
    assert abs(reading.frequency_hz - 2.0) < 1e-9


def test_zero_duration_reports_no_frequency(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.5)
    panel.set_cursor_b(0.52)  # ayni ornege kenetlenir (0.5)

    reading = panel.delta_measurement()
    assert reading is not None
    assert reading.dt_seconds == 0.0
    assert reading.dvalue == 0.0
    assert reading.frequency_hz is None


def test_frequency_matches_one_over_dt_for_a_short_interval(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.2)
    panel.set_cursor_b(0.3)  # dt = 0.1 s -> 10 Hz

    reading = panel.delta_measurement()
    assert reading is not None
    assert reading.frequency_hz is not None
    assert abs(reading.frequency_hz - 10.0) < 1e-9


# -- yasam dongusu -----------------------------------------------


def test_delta_is_none_until_both_cursors_are_set(panel: PlotPanel) -> None:
    _populate(panel)
    assert panel.delta_measurement() is None

    panel.set_cursor_a(0.2)
    assert panel.delta_measurement() is None

    panel.set_cursor_b(0.4)
    assert panel.delta_measurement() is not None


def test_cursor_positions_snap_to_sample_times(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.34)
    panel.set_cursor_b(0.66)

    assert panel.cursor_a_x() == 0.3
    assert panel.cursor_b_x() == 0.7


def test_clear_delta_cursors_resets_everything(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_cursor_a(0.2)
    panel.set_cursor_b(0.7)

    panel.clear_delta_cursors()

    assert panel.cursor_a_x() is None
    assert panel.cursor_b_x() is None
    assert panel.delta_measurement() is None
    assert panel.delta_readout_text() == ""


def test_setting_cursors_before_data_is_a_no_op(panel: PlotPanel) -> None:
    panel.set_cursor_a(0.2)
    panel.set_cursor_b(0.7)

    assert panel.cursor_a_x() is None
    assert panel.delta_measurement() is None


def test_emptying_the_panel_clears_the_delta_cursors(panel: PlotPanel) -> None:
    _populate(panel)
    panel.set_cursor_a(0.2)
    panel.set_cursor_b(0.7)

    panel.clear()

    assert panel.cursor_a_x() is None
    assert panel.cursor_b_x() is None


# -- okuma metni ----------------------------------------------


def test_readout_text_reports_dt_dvalue_and_frequency(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.2)
    panel.set_cursor_b(0.7)

    text = panel.delta_readout_text()
    assert "Δt=0.500 s" in text
    assert "50" in text
    assert "bar" in text
    assert "f=2" in text
    assert "Hz" in text


def test_readout_text_omits_frequency_for_zero_duration(panel: PlotPanel) -> None:
    _populate(panel)

    panel.set_cursor_a(0.5)
    panel.set_cursor_b(0.5)

    text = panel.delta_readout_text()
    assert "Δt=0.000 s" in text
    assert "Hz" not in text

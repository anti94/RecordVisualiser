"""Ortak zaman ekseninde çoklu seri — `F3-019`.

Kabul: farklı kanalların zamanları aynı X koordinatına eşlenir.
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

#: Rastgele değil, okunur bir mutlak epoch ankoru (2026-01-01T00:00:00Z civarı).
BASE_NS = 1_767_225_600_000_000_000


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    return widget


def _channel(channel_id: str, name: str, unit: str = "u") -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit=unit,
        sample_rate_hz=8.0,
    )


def _chunk(channel_id: str, start_ns: int, period_ns: int, count: int) -> DataChunk:
    stamps = np.array([start_ns + i * period_ns for i in range(count)], dtype=np.int64)
    values = np.arange(count, dtype=np.float64)
    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


PERIOD_8HZ = NS_PER_SECOND // 8
PERIOD_4HZ = NS_PER_SECOND // 4


# -- kabul: ayni mutlak an -> ayni X -------------------------------------


def test_two_channels_with_identical_timestamps_share_the_x_array(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 8))
    panel.add_channel(_channel("ch1", "B"), _chunk("ch1", BASE_NS, PERIOD_8HZ, 8))

    x0, _ = panel.curve_data("ch0")
    x1, _ = panel.curve_data("ch1")

    assert x0.tolist() == x1.tolist()
    assert x0[0] == 0.0


def test_a_later_starting_channel_aligns_on_absolute_time(panel: PlotPanel) -> None:
    """ch1, ch0'dan 3 örnek geç başlar; çakışan anlar aynı X'e düşer."""
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 8))
    panel.add_channel(_channel("ch1", "B"), _chunk("ch1", BASE_NS + 3 * PERIOD_8HZ, PERIOD_8HZ, 8))

    x0, _ = panel.curve_data("ch0")
    x1, _ = panel.curve_data("ch1")

    # ch0[3] ile ch1[0] ayni mutlak an -> ayni X.
    assert float(x0[3]) == float(x1[0])
    assert float(x1[0]) == 0.375


def test_channels_at_different_sample_rates_still_align(panel: PlotPanel) -> None:
    panel.add_channel(_channel("fast", "Fast"), _chunk("fast", BASE_NS, PERIOD_8HZ, 8))
    panel.add_channel(_channel("slow", "Slow"), _chunk("slow", BASE_NS, PERIOD_4HZ, 4))

    x_fast, _ = panel.curve_data("fast")
    x_slow, _ = panel.curve_data("slow")

    # slow[1] (t = +250 ms) ile fast[2] (t = +250 ms) ayni X.
    assert float(x_slow[1]) == float(x_fast[2])
    assert x_slow.tolist() == [0.0, 0.25, 0.5, 0.75]


# -- eslem yardimcilari: x_for_timestamp_ns / timestamp_ns_for_x --------


def test_anchor_is_the_first_added_series_start(panel: PlotPanel) -> None:
    assert panel.time_anchor_ns is None

    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 4))
    panel.add_channel(_channel("ch1", "B"), _chunk("ch1", BASE_NS - 10 * PERIOD_8HZ, PERIOD_8HZ, 4))

    assert panel.time_anchor_ns == BASE_NS


def test_x_for_timestamp_maps_anchor_to_zero_and_one_second_to_one(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 4))

    assert panel.x_for_timestamp_ns(BASE_NS) == 0.0
    assert panel.x_for_timestamp_ns(BASE_NS + NS_PER_SECOND) == 1.0
    assert panel.x_for_timestamp_ns(BASE_NS - NS_PER_SECOND) == -1.0


def test_timestamp_for_x_is_the_inverse(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 4))

    assert panel.timestamp_ns_for_x(0.0) == BASE_NS
    assert panel.timestamp_ns_for_x(2.5) == BASE_NS + 2_500_000_000
    round_trip = panel.timestamp_ns_for_x(panel.x_for_timestamp_ns(BASE_NS + 123_456_789))
    assert round_trip == BASE_NS + 123_456_789


def test_mapping_helpers_raise_before_any_series(panel: PlotPanel) -> None:
    with pytest.raises(RuntimeError, match="ankoru yok"):
        panel.x_for_timestamp_ns(BASE_NS)
    with pytest.raises(RuntimeError, match="ankoru yok"):
        panel.timestamp_ns_for_x(0.0)


# -- ankor kalicidir: seri duzenlense de eksen kaymasin ----------------


def test_anchor_survives_removing_the_first_series(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 4))
    panel.add_channel(_channel("ch1", "B"), _chunk("ch1", BASE_NS, PERIOD_8HZ, 4))

    panel.remove_channel("ch0")
    panel.add_channel(_channel("ch2", "C"), _chunk("ch2", BASE_NS + PERIOD_8HZ, PERIOD_8HZ, 4))

    assert panel.time_anchor_ns == BASE_NS
    x2, _ = panel.curve_data("ch2")
    assert float(x2[0]) == 0.125


def test_clearing_resets_the_anchor(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "A"), _chunk("ch0", BASE_NS, PERIOD_8HZ, 4))
    panel.clear()

    assert panel.time_anchor_ns is None

    panel.add_channel(_channel("ch9", "Z"), _chunk("ch9", BASE_NS + NS_PER_SECOND, PERIOD_8HZ, 4))
    assert panel.time_anchor_ns == BASE_NS + NS_PER_SECOND

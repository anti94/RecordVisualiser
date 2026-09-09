"""Tek kanallı PlotPanel — `F1-031`.

Kabul: sahte sinüs zaman ve birim etiketleriyle görünür.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.plots.plot_panel import EMPTY_TITLE, PlotPanel, to_seconds

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def make_channel(**overrides: object) -> ChannelMetadata:
    defaults: dict[str, object] = {
        "id": "ch0",
        "path": "Sensors/Pressure",
        "name": "Pressure",
        "dtype": "float32",
        "source": ChannelSource.SENSORS,
        "unit": "bar",
        "sample_rate_hz": 100.0,
    }
    defaults.update(overrides)
    return ChannelMetadata(**defaults)  # type: ignore[arg-type]


# -- bos durum -------------------------------------------------------------


def test_starts_empty(panel: PlotPanel) -> None:
    assert panel.channel is None
    assert panel.sample_count == 0
    assert EMPTY_TITLE in panel.title_text()

    x, y = panel.curve_data()
    assert x.size == 0
    assert y.size == 0


def test_time_axis_is_labelled_before_any_data(panel: PlotPanel) -> None:
    assert "Time" in panel.axis_label("bottom")
    assert "(s)" in panel.axis_label("bottom")


# -- sahte sinus -----------------------------------------------------------


def test_sine_is_drawn_with_all_samples(panel: PlotPanel) -> None:
    channel = make_channel()
    chunk = sine("ch0", sample_rate_hz=100.0, duration_s=2.0, frequency_hz=5.0)

    panel.set_channel(channel, chunk)

    x, y = panel.curve_data()
    assert x.size == 200
    assert y.size == 200
    assert panel.sample_count == 200
    assert np.isclose(float(y.max()), 1.0, atol=1e-3)
    assert np.isclose(float(y.min()), -1.0, atol=1e-3)


def test_title_shows_channel_and_unit(panel: PlotPanel) -> None:
    panel.set_channel(make_channel(), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    assert panel.title_text() == "Pressure [bar]"


def test_axes_show_name_and_units(panel: PlotPanel) -> None:
    """Kabul kriteri: zaman ve birim etiketleri görünür."""
    panel.set_channel(make_channel(), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    left = panel.axis_label("left")
    bottom = panel.axis_label("bottom")

    assert "Pressure" in left
    assert "(bar)" in left
    assert "Time" in bottom
    assert "(s)" in bottom


def test_channel_without_unit_still_labels_axis(panel: PlotPanel) -> None:
    channel = make_channel(unit=None)
    panel.set_channel(channel, sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    assert panel.title_text() == "Pressure"
    assert "Pressure" in panel.axis_label("left")


# -- zaman ekseni ----------------------------------------------------------


def test_time_axis_is_relative_seconds(panel: PlotPanel) -> None:
    """Mutlak epoch değil, kayıt başına göre saniye çizilmeli."""
    start = 1_788_901_200 * SECOND
    chunk = sine("ch0", 100.0, 1.0, frequency_hz=2.0, start_ns=start)

    panel.set_channel(make_channel(), chunk)

    x, _ = panel.curve_data()
    assert float(x[0]) == 0.0
    assert 0.98 < float(x[-1]) < 1.0, "son ornek ~1 s'de olmali"


def test_to_seconds_helper() -> None:
    stamps = np.array([0, SECOND, 2 * SECOND], dtype=np.int64)
    assert to_seconds(stamps, 0).tolist() == [0.0, 1.0, 2.0]
    assert to_seconds(stamps, SECOND).tolist() == [-1.0, 0.0, 1.0]


# -- tutarlilik ------------------------------------------------------------


def test_mismatched_chunk_is_rejected(panel: PlotPanel) -> None:
    """Başka kanalın verisi sessizce çizilmemeli."""
    chunk = sine("ch9", 100.0, 1.0, frequency_hz=2.0)
    with pytest.raises(ValueError, match="baska kanala ait"):
        panel.set_channel(make_channel(), chunk)


def test_clear_returns_to_empty_state(panel: PlotPanel) -> None:
    panel.set_channel(make_channel(), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.clear()

    assert panel.channel is None
    assert panel.sample_count == 0
    assert panel.curve_data()[0].size == 0
    assert EMPTY_TITLE in panel.title_text()


def test_unknown_axis_raises(panel: PlotPanel) -> None:
    with pytest.raises(KeyError, match="Tanimsiz eksen"):
        panel.axis_label("top")


def test_repository_channel_can_be_plotted(panel: PlotPanel) -> None:
    """Sahte repository'den gelen kanal doğrudan çizilebilmeli."""
    repo = MockRecordingRepository(duration_s=10.0)
    channel = next(c for c in repo.channels() if c.id == "ch5")
    chunk = repo.query("ch5", TimeRange(0, 10 * SECOND))

    panel.set_channel(channel, chunk)

    assert panel.sample_count == 80
    assert panel.title_text() == "Hydrophone 1 [Pa]"
    x, _ = panel.curve_data()
    assert float(x[0]) == 0.0

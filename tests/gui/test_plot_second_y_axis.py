"""İkinci (sağ) Y ekseni — `F3-020`.

Kabul: seri doğru eksen ve birimle gösterilir. İlk serinin birimi sol
ekseni sahiplenir; farklı birimli seriler sağ eksene gider.
"""

from __future__ import annotations

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
        sample_rate_hz=100.0,
    )


def _add(panel: PlotPanel, channel_id: str, name: str, unit: str) -> None:
    panel.add_channel(
        _channel(channel_id, name, unit),
        sine(channel_id, sample_rate_hz=100.0, duration_s=1.0, frequency_hz=2.0),
    )


# -- tek birim: yalniz sol eksen ---------------------------------------


def test_first_channel_owns_the_left_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")

    assert panel.axis_for_channel("ch0") == "left"
    assert panel.left_unit == "bar"
    assert not panel.right_axis_visible


def test_a_second_channel_with_the_same_unit_stays_on_the_left(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch0b", "Pressure2", "bar")

    assert panel.axis_for_channel("ch0b") == "left"
    assert not panel.right_axis_visible


# -- ikinci birim: sag eksen acilir ----------------------------------


def test_a_different_unit_goes_to_the_right_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    assert panel.axis_for_channel("ch0") == "left"
    assert panel.axis_for_channel("ch1") == "right"
    assert panel.right_axis_visible
    assert panel.right_unit == "C"


def test_axes_are_labelled_with_their_units(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    assert "bar" in panel.axis_label("left")
    assert "C" in panel.axis_label("right")


def test_right_axis_series_data_is_still_reachable(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    x, y = panel.curve_data("ch1")

    assert x.size == y.size > 0
    assert "Temperature [C]" in panel.legend_labels()


def test_a_third_distinct_unit_falls_back_to_the_right_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")
    _add(panel, "ch5", "Hydrophone", "Pa")

    assert panel.axis_for_channel("ch5") == "right"
    assert panel.right_unit == "C", "ilk sag birim korunur"


# -- eksen kaldirma / sifirlama --------------------------------------


def test_removing_the_only_right_series_hides_the_right_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")
    assert panel.right_axis_visible

    panel.remove_channel("ch1")

    assert not panel.right_axis_visible
    assert panel.right_unit is None
    assert panel.axis_for_channel("ch0") == "left"


def test_removing_a_left_series_keeps_the_right_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    panel.remove_channel("ch0")

    assert panel.right_axis_visible
    assert panel.axis_for_channel("ch1") == "right"


def test_set_channel_resets_to_a_single_left_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")
    assert panel.right_axis_visible

    panel.set_channel(
        _channel("ch6", "Depth", "m"),
        sine("ch6", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=1.0),
    )

    assert panel.plotted_channel_ids() == ["ch6"]
    assert panel.axis_for_channel("ch6") == "left"
    assert panel.left_unit == "m"
    assert not panel.right_axis_visible


def test_clear_drops_both_units(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    panel.clear()

    assert panel.left_unit is None
    assert panel.right_unit is None
    assert not panel.right_axis_visible


def test_axis_for_unknown_channel_raises(panel: PlotPanel) -> None:
    with pytest.raises(KeyError):
        panel.axis_for_channel("hic-yok")

"""Autoscale ve görünüm sıfırlama — `F3-025`.

Kabul: görünür veriye sığdırma ve ilk aralığa dönüş çalışır.
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

_TOL = 1e-3


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
        sample_rate_hz=100.0,
    )


def _add(panel: PlotPanel, channel_id: str, name: str, unit: str = "bar", amp: float = 1.0) -> None:
    chunk = sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0, amplitude=amp)
    panel.add_channel(_channel(channel_id, name, unit), chunk)


def _close(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    assert len(a) == len(b)
    return all(abs(x - y) < _TOL for x, y in zip(a, b))


# -- reset_view: ilk aralraga donus --------------------------------


def test_reset_view_returns_to_the_home_range_after_pan(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure")
    home = panel.visible_range()

    panel.pan(5.0, dy=3.0)
    assert not _close(panel.visible_range(), home)

    panel.reset_view()

    assert _close(panel.visible_range(), home)


def test_reset_view_returns_to_home_after_zoom(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure")
    home = panel.visible_range()

    panel.zoom(0.2)
    panel.reset_view()

    assert _close(panel.visible_range(), home)


def test_home_range_follows_the_latest_data(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", amp=1.0)
    _add(panel, "ch1", "Big", amp=10.0)
    home_with_two = panel.visible_range()

    panel.pan(3.0)
    panel.reset_view()

    assert _close(panel.visible_range(), home_with_two)
    # buyuk genlikli seri Y araligina sigmali
    _, _, y_min, y_max = panel.visible_range()
    assert y_min < -9.0 < 9.0 < y_max


def test_reset_view_restores_the_second_y_axis(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", "bar", amp=1.0)
    _add(panel, "ch1", "Temp", "C", amp=5.0)
    home_right = panel.right_axis_y_range()
    assert home_right is not None

    panel.set_zoom_mode("y")
    panel.zoom(0.3)
    panel.reset_view()

    now_right = panel.right_axis_y_range()
    assert now_right is not None
    assert _close(now_right, home_right)


# -- autoscale: veriye sigdirma -----------------------------------


def test_autoscale_fits_all_data_after_a_zoom_in(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure", amp=2.0)
    panel.zoom(0.1)  # cok yakinlas

    panel.autoscale()

    x_min, x_max, y_min, y_max = panel.visible_range()
    # 2 s'lik veri ve +/-2 genlik gorunur olmali
    assert x_min <= 0.05 and x_max >= 1.95
    assert y_min <= -1.9 and y_max >= 1.9


def test_autoscale_re_enables_auto_range(panel: PlotPanel) -> None:
    _add(panel, "ch0", "Pressure")
    panel.zoom(0.5)

    panel.autoscale()

    assert panel.plot.getViewBox().state["autoRange"] == [True, True]


def test_autoscale_and_reset_view_are_no_ops_on_an_empty_panel(panel: PlotPanel) -> None:
    panel.autoscale()
    panel.reset_view()

    assert panel.plotted_channel_ids() == []

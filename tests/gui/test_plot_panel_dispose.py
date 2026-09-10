"""Panel kaynak sınırı ve kapatma temizliği — `F3-034`.

Kabul: kapanan panelin signal ve sorgu kaynakları serbest kalır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.plot_workspace import MAX_PANELS, PlotWorkspace

pytestmark = pytest.mark.gui


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.fixture()
def workspace(qtbot: QtBot) -> PlotWorkspace:
    widget = PlotWorkspace()
    qtbot.addWidget(widget)
    widget.resize(800, 500)
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
        unit="bar",
        sample_rate_hz=100.0,
    )


def _fill(panel: PlotPanel, channel_id: str = "ch0") -> None:
    panel.add_channel(
        _channel(channel_id),
        sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0),
    )


# -- dispose: veri ve sinyaller serbest ------------------------


def test_dispose_drops_all_series_and_data(panel: PlotPanel) -> None:
    _fill(panel, "ch0")
    _fill(panel, "ch1")

    panel.dispose()

    assert panel.plotted_channel_ids() == []
    assert panel.sample_count == 0
    x, y = panel.curve_data("ch0")
    assert x.size == 0 and y.size == 0


def test_disposed_panel_stops_emitting_x_range_changed(panel: PlotPanel) -> None:
    _fill(panel)
    seen: list[tuple[float, float]] = []

    def _rec(lo: float, hi: float) -> None:
        seen.append((lo, hi))

    panel.x_range_changed.connect(_rec)
    panel.set_x_range(0.1, 0.4)
    assert seen  # dispose oncesi calisiyor
    seen.clear()

    panel.dispose()
    panel.set_x_range(0.5, 0.9)

    assert seen == [], "dispose sonrasi sinyal yayilmamali"


def test_dispose_is_idempotent(panel: PlotPanel) -> None:
    _fill(panel)

    panel.dispose()
    panel.dispose()  # ikinci cagri sessizce doner

    assert panel.plotted_channel_ids() == []


def test_dispose_tears_down_the_second_y_axis(panel: PlotPanel) -> None:
    _fill(panel, "ch0")
    panel.add_channel(
        _channel("t1"),
        sine("t1", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=3.0),
    )
    # ikinci birim yok (hepsi "bar"), yine de dispose sorunsuz olmali
    panel.dispose()

    assert not panel.right_axis_visible


# -- workspace: kaynak siniri --------------------------------


def test_workspace_enforces_the_panel_limit(workspace: PlotWorkspace) -> None:
    for _ in range(MAX_PANELS):
        workspace.open_panel()

    assert workspace.at_capacity
    with pytest.raises(RuntimeError, match="Panel limiti"):
        workspace.open_panel()


def test_closing_a_panel_frees_a_slot_under_the_limit(workspace: PlotWorkspace) -> None:
    panels = [workspace.open_panel() for _ in range(MAX_PANELS)]
    assert workspace.at_capacity

    workspace.close_panel(panels[0])

    assert not workspace.at_capacity
    reopened = workspace.open_panel()
    assert reopened in workspace.panels


def test_workspace_close_disposes_the_panel(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()
    _fill(a)
    _fill(b)

    seen: list[tuple[float, float]] = []

    def _rec(lo: float, hi: float) -> None:
        seen.append((lo, hi))

    a.x_range_changed.connect(_rec)
    workspace.close_panel(a)
    seen.clear()

    a.set_x_range(0.2, 0.6)

    assert seen == [], "kapatilan panel artik sinyal yaymamali"
    assert a.plotted_channel_ids() == []

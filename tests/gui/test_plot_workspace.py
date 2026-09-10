"""Grafik tabı ve bölünmüş görünüm — `F3-033`.

Kabul: paneller açılır, bölünür ve bağımsız kapatılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.plot_workspace import PlotWorkspace

pytestmark = pytest.mark.gui

_EPS = 1e-6


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


# -- panel acma -------------------------------------------------


def test_open_panel_adds_independent_plot_panels(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()

    assert workspace.count == 2
    assert isinstance(a, PlotPanel)
    assert a is not b
    assert workspace.panels == (a, b)


def test_default_layout_is_tabs(workspace: PlotWorkspace) -> None:
    assert workspace.layout_mode == "tabs"
    workspace.open_panel()
    assert workspace.is_tab_layout


# -- bagimsiz kapatma ---------------------------------------


def test_closing_one_panel_leaves_the_others(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()
    c = workspace.open_panel()

    workspace.close_panel(b)

    assert workspace.count == 2
    assert workspace.panels == (a, c)


def test_a_closed_panel_no_longer_follows_x_navigation(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()
    _fill(a)
    _fill(b)
    a.set_x_range(0.1, 0.5)
    assert abs(b.visible_x_range()[0] - 0.1) < _EPS

    workspace.close_panel(b)
    a.set_x_range(0.6, 0.9)

    # b artik izlemiyor: son senkron degerinde kaldi
    assert abs(b.visible_x_range()[0] - 0.1) < _EPS


def test_closing_all_panels_is_safe(workspace: PlotWorkspace) -> None:
    workspace.open_panel()
    workspace.open_panel()

    workspace.close_all()

    assert workspace.count == 0
    assert workspace.active_panel is None


# -- ortak X senkronu (F3-032 ile) -------------------------


def test_all_open_panels_share_the_x_window(workspace: PlotWorkspace) -> None:
    panels = [workspace.open_panel() for _ in range(3)]
    for i, panel in enumerate(panels):
        _fill(panel, f"ch{i}")

    panels[0].set_x_range(0.2, 0.7)

    for panel in panels[1:]:
        lo, hi = panel.visible_x_range()
        assert abs(lo - 0.2) < _EPS
        assert abs(hi - 0.7) < _EPS


# -- bolunmus gorunum -------------------------------------


def test_split_moves_panels_into_a_splitter_keeping_them(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()
    _fill(a)
    _fill(b)

    workspace.split()

    assert workspace.layout_mode == "split"
    assert workspace.is_split_layout
    assert workspace.panels == (a, b)
    # bagli kalirlar
    a.set_x_range(0.3, 0.6)
    assert abs(b.visible_x_range()[0] - 0.3) < _EPS


def test_toggling_back_to_tabs_restores_a_tab_widget(workspace: PlotWorkspace) -> None:
    workspace.open_panel()
    workspace.split()

    workspace.tabs()

    assert workspace.layout_mode == "tabs"
    assert workspace.is_tab_layout
    assert workspace.count == 1


def test_opening_a_panel_after_split_adds_it_to_the_splitter(workspace: PlotWorkspace) -> None:
    workspace.open_panel()
    workspace.split()

    c = workspace.open_panel()

    assert workspace.count == 2
    assert workspace.index_of(c) == 1
    assert workspace.is_split_layout


def test_unknown_layout_mode_raises(workspace: PlotWorkspace) -> None:
    with pytest.raises(ValueError, match="Bilinmeyen yerlesim"):
        workspace.set_layout_mode("grid")


def test_tab_close_button_closes_that_panel(workspace: PlotWorkspace) -> None:
    a = workspace.open_panel()
    b = workspace.open_panel()

    workspace.close_panel_at(0)

    assert workspace.count == 1
    assert workspace.panels == (b,)
    assert a not in workspace.panels

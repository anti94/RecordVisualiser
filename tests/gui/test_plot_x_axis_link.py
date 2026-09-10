"""Paneller arası X senkronizasyonu — `F3-032`.

Kabul: bir grafikte gezinme bağlı grafikleri günceller; döngü oluşmaz.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.x_axis_link import XAxisLink

pytestmark = pytest.mark.gui

_EPS = 1e-6


def _make_panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str, name: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=100.0,
    )


def _populate(panel: PlotPanel, channel_id: str = "ch0") -> None:
    panel.add_channel(
        _channel(channel_id, "Sig"),
        sine(channel_id, sample_rate_hz=100.0, duration_s=2.0, frequency_hz=1.0),
    )


def _x_close(panel: PlotPanel, lo: float, hi: float) -> bool:
    x_lo, x_hi = panel.visible_x_range()
    return abs(x_lo - lo) < _EPS and abs(x_hi - hi) < _EPS


# -- kabul: bir panelde gezinme digerlerini gunceller ------------


def test_navigating_one_panel_updates_the_linked_panel(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    b = _make_panel(qtbot)
    _populate(a)
    _populate(b)
    link = XAxisLink()
    link.add(a)
    link.add(b)

    a.set_x_range(0.3, 0.9)

    assert _x_close(b, 0.3, 0.9)


def test_three_panels_all_follow(qtbot: QtBot) -> None:
    panels = [_make_panel(qtbot) for _ in range(3)]
    link = XAxisLink()
    for p in panels:
        _populate(p)
        link.add(p)

    panels[1].set_x_range(0.1, 0.4)

    assert _x_close(panels[0], 0.1, 0.4)
    assert _x_close(panels[2], 0.1, 0.4)


def test_pan_and_zoom_also_propagate(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    b = _make_panel(qtbot)
    _populate(a)
    _populate(b)
    link = XAxisLink()
    link.add(a)
    link.add(b)

    a.set_x_range(0.0, 1.0)
    a.pan(0.25)

    lo_a, hi_a = a.visible_x_range()
    assert _x_close(b, lo_a, hi_a)


# -- dongu olusmaz --------------------------------------------


def test_no_feedback_loop_between_two_panels(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    b = _make_panel(qtbot)
    _populate(a)
    _populate(b)
    link = XAxisLink()
    link.add(a)
    link.add(b)

    a_emits: list[tuple[float, float]] = []
    b_emits: list[tuple[float, float]] = []

    def _rec_a(lo: float, hi: float) -> None:
        a_emits.append((lo, hi))

    def _rec_b(lo: float, hi: float) -> None:
        b_emits.append((lo, hi))

    a.x_range_changed.connect(_rec_a)
    b.x_range_changed.connect(_rec_b)

    a.set_x_range(0.2, 0.8)

    # A gezinme yaptigi icin birkac kez yayabilir ama SINIRLI kalmali;
    # B disaridan uygulandigi icin HIC yaymamali (dongu yok).
    assert 1 <= len(a_emits) <= 3
    assert b_emits == []
    assert _x_close(b, 0.2, 0.8)


def test_y_range_is_not_synchronised(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    b = _make_panel(qtbot)
    _populate(a, "ch0")
    _populate(b, "ch1")
    link = XAxisLink()
    link.add(a)
    link.add(b)
    _, _, b_y_min_before, b_y_max_before = b.visible_range()

    a.set_zoom_mode("y")
    a.zoom(0.5)  # yalniz A'nin Y'si degisir

    _, _, b_y_min_after, b_y_max_after = b.visible_range()
    assert abs(b_y_min_after - b_y_min_before) < _EPS
    assert abs(b_y_max_after - b_y_max_before) < _EPS


# -- gruptan cikarma ----------------------------------------


def test_removed_panel_stops_following(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    b = _make_panel(qtbot)
    _populate(a)
    _populate(b)
    link = XAxisLink()
    link.add(a)
    link.add(b)
    a.set_x_range(0.1, 0.5)
    assert _x_close(b, 0.1, 0.5)

    link.remove(b)
    a.set_x_range(0.6, 0.9)

    assert _x_close(b, 0.1, 0.5), "cikarilan panel artik izlemez"
    assert link.panels == (a,)


def test_adding_the_same_panel_twice_is_idempotent(qtbot: QtBot) -> None:
    a = _make_panel(qtbot)
    link = XAxisLink()
    link.add(a)
    link.add(a)

    assert link.panels == (a,)

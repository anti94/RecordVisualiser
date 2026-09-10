"""Timeline viewport seçimini grafiğe bağlama — `F3-055`.

Kabul: bölge taşıma tüm bağlı grafiklerin zaman aralığını değiştirir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND, TimeRange
from sonar_analyzer.ui.docks.timeline_overview import TimelineOverview
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.x_axis_link import XAxisLink

pytestmark = pytest.mark.gui

START = 1_000_000_000_000
END = START + 10 * NS_PER_SECOND
BASE_NS = START
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
_EPS = 1e-6


@pytest.fixture()
def timeline(qtbot: QtBot) -> TimelineOverview:
    widget = TimelineOverview()
    qtbot.addWidget(widget)
    widget.resize(600, 30)
    widget.set_recording(TimeRange(START, END))
    return widget


# -- viewport durumu -----------------------------------------


def test_set_viewport_round_trips_to_ns(timeline: TimelineOverview) -> None:
    timeline.set_viewport_ns(START + 2 * NS_PER_SECOND, START + 6 * NS_PER_SECOND)

    assert timeline.viewport_ns() == (START + 2 * NS_PER_SECOND, START + 6 * NS_PER_SECOND)


def test_no_viewport_before_it_is_set(timeline: TimelineOverview) -> None:
    assert timeline.viewport_ns() is None


def test_dragging_the_viewport_emits_the_new_bounds(timeline: TimelineOverview) -> None:
    timeline.set_viewport_ns(START, START + 2 * NS_PER_SECOND)  # 2 s geniş
    received: list[tuple[int, int]] = []

    def _rec(start_ns: int, end_ns: int) -> None:
        received.append((start_ns, end_ns))

    timeline.viewport_changed.connect(_rec)

    timeline.drag_viewport_to(0.5)  # merkeze

    assert received
    start_ns, end_ns = received[-1]
    assert end_ns - start_ns == 2 * NS_PER_SECOND  # genişlik korunur
    assert abs((start_ns + end_ns) / 2 - (START + 5 * NS_PER_SECOND)) < NS_PER_SECOND // 100


def test_drag_is_clamped_to_the_recording_span(timeline: TimelineOverview) -> None:
    timeline.set_viewport_ns(START, START + 4 * NS_PER_SECOND)

    timeline.drag_viewport_to(5.0)  # aralık dışı sağ

    start_ns, end_ns = timeline.viewport_ns()  # type: ignore[misc]
    assert end_ns == END
    assert start_ns == END - 4 * NS_PER_SECOND


def test_programmatic_set_viewport_does_not_emit(timeline: TimelineOverview) -> None:
    received: list[object] = []
    timeline.viewport_changed.connect(received.append)

    timeline.set_viewport_ns(START, START + NS_PER_SECOND)

    assert received == []


# -- bagli grafikler viewport surukleyince gider ----------


def _panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _fill(panel: PlotPanel, channel_id: str) -> None:
    stamps = np.array([BASE_NS + i * (NS_PER_SECOND // 4) for i in range(40)], dtype=np.int64)
    panel.add_channel(
        ChannelMetadata(
            id=channel_id,
            path=f"Sensors/{channel_id}",
            name=channel_id,
            dtype="float32",
            source=ChannelSource.SENSORS,
            unit="u",
            sample_rate_hz=4.0,
        ),
        DataChunk(
            channel_id=channel_id, timestamps_ns=stamps, values=np.arange(40, dtype=np.float64)
        ),
    )


def test_moving_the_region_changes_all_linked_graphs(qtbot: QtBot) -> None:
    primary = _panel(qtbot)
    secondary = _panel(qtbot)
    _fill(primary, "ch0")
    _fill(secondary, "ch1")
    link = XAxisLink()
    link.add(primary)
    link.add(secondary)

    # timeline'ın viewport sürüklemesinin yaptığı iş: primary X aralığını
    # [2 s, 4 s] yap -> link ötekini de taşır.
    primary.set_x_range(2.0, 4.0)

    for panel in (primary, secondary):
        lo, hi = panel.visible_x_range()
        assert abs(lo - 2.0) < _EPS
        assert abs(hi - 4.0) < _EPS


# -- MainWindow: grafik <-> timeline iki yonlu ------------


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    win.left_dock.channel_activated.emit("ch0")
    return win


def test_plot_navigation_updates_the_timeline_viewport(window: MainWindow) -> None:
    window.plot_panel.set_x_range(0.2, 0.6)

    viewport = window.playback_dock.timeline.viewport_ns()
    assert viewport is not None
    start_ns, end_ns = viewport
    span_s = (end_ns - start_ns) / NS_PER_SECOND
    assert abs(span_s - 0.4) < 1e-2


def test_dragging_the_timeline_moves_the_plot(window: MainWindow) -> None:
    window.plot_panel.set_x_range(0.0, 0.3)
    timeline = window.playback_dock.timeline
    assert timeline.viewport_ns() is not None

    timeline.drag_viewport_to(0.7)

    lo, hi = window.plot_panel.visible_x_range()
    assert abs((hi - lo) - 0.3) < 1e-2, "genişlik korunur"
    assert lo > 0.3, "pencere sağa kaydı"

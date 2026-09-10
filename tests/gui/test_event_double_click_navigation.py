"""Olay çift tıklaması ile ortak zamana gitme — `F3-046`.

Kabul: senkronize grafikler seçilen olay zamanına gider.
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
from sonar_analyzer.domain.time_range import NS_PER_SECOND
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.x_axis_link import XAxisLink

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
BASE_NS = 1_767_225_600_000_000_000
_EPS = 1e-6


# -- MainWindow.go_to_time --------------------------------------


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


def test_go_to_time_centres_the_view_on_the_timestamp(window: MainWindow) -> None:
    x_min, x_max = window.plot_panel.visible_x_range()
    span_before = x_max - x_min
    target_ns = window.plot_panel.timestamp_ns_for_x(0.6)

    assert window.go_to_time(target_ns) is True

    new_min, new_max = window.plot_panel.visible_x_range()
    assert abs((new_max - new_min) - span_before) < 1e-3
    assert abs((new_min + new_max) / 2.0 - 0.6) < 1e-3


def test_go_to_time_without_a_plotted_series_returns_false(qtbot: QtBot, tmp_path: Path) -> None:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)

    assert win.go_to_time(BASE_NS) is False


def test_double_clicking_an_event_row_navigates_the_graph(window: MainWindow) -> None:
    assert window.bottom_dock.event_row_count() > 0
    event_time_cell = window.bottom_dock.event_cell(0, "Time")  # "+X.XXX s (…)"
    relative_s = float(event_time_cell.split(" s")[0])

    window.bottom_dock.events.selectRow(0)
    first_item = window.bottom_dock.events.item(0, 0)
    assert first_item is not None
    window.bottom_dock.events.itemDoubleClicked.emit(first_item)

    new_min, new_max = window.plot_panel.visible_x_range()
    assert abs((new_min + new_max) / 2.0 - relative_s) < 1e-2


# -- senkronize grafikler da gider (X-axis link) --------------


def _panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _fill(panel: PlotPanel, channel_id: str) -> None:
    stamps = np.array([BASE_NS + i * (NS_PER_SECOND // 4) for i in range(16)], dtype=np.int64)
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
            channel_id=channel_id,
            timestamps_ns=stamps,
            values=np.arange(16, dtype=np.float64),
        ),
    )


def test_linked_panels_follow_the_event_navigation(qtbot: QtBot) -> None:
    primary = _panel(qtbot)
    secondary = _panel(qtbot)
    _fill(primary, "ch0")
    _fill(secondary, "ch1")
    link = XAxisLink()
    link.add(primary)
    link.add(secondary)

    # olay çift tıklamasının primary'de yaptığı iş: t=2.5 s'e ortala
    event_x = primary.x_for_timestamp_ns(BASE_NS + 2_500_000_000)
    x_min, x_max = primary.visible_x_range()
    half = (x_max - x_min) / 2.0
    primary.set_x_range(event_x - half, event_x + half)

    s_min, s_max = secondary.visible_x_range()
    assert abs((s_min + s_max) / 2.0 - 2.5) < _EPS
    assert abs((s_max - s_min) - (x_max - x_min)) < _EPS

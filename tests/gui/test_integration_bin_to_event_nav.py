"""Entegrasyon: BIN → repository → grafik → olay zamanı — `F3-075`.

Kabul: dosyadan olay gezinmesine kadar olan zincir uçtan uca geçer.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Severity
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"
NS_PER_S = 1_000_000_000


@pytest.fixture()
def opened(qtbot: QtBot, tmp_path: Path) -> tuple[MainWindow, FileRecordingRepository]:
    """Gerçek `.bin`'i dosya diyaloğu üzerinden açar; (pencere, repo) döndürür."""
    target = tmp_path / "kayit.bin"
    shutil.copyfile(FIXTURE, target)

    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()

    probe = FileRecordingRepository()
    probe.open(target)
    return win, probe


def test_bin_opens_and_lists_its_channels(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    win, _probe = opened
    # Kayıt açıldı: kapatma etkin, kanallar ağaçta ve araç çubuğunda.
    assert win.action("action_close").isEnabled()
    assert win.left_dock.visible_channel_ids()  # ağaç dolu
    assert win.plot_tool_bar.channel_selector.count() > 0


def test_channel_from_bin_reaches_the_plot(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    win, _probe = opened
    win.open_channel("ch0")
    assert win.plot_panel.plotted_channel_ids() == ["ch0"]
    assert win.plot_panel.sample_count > 0


def test_events_from_bin_reach_every_panel(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    win, probe = opened
    win.open_channel("ch0")

    span = probe.metadata().time_range
    events = probe.events(span)
    assert len(events) == 4

    win.bottom_dock.set_events(events, start_ns=span.start_ns)
    assert win.bottom_dock.events.rowCount() == 4
    assert win.plot_panel.event_marker_count() == 4


def test_activating_an_event_centres_the_plot_on_its_time(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    win, probe = opened
    win.open_channel("ch0")
    span = probe.metadata().time_range
    events = probe.events(span)
    error_event = next(e for e in events if e.severity is Severity.ERROR)

    # Olay tablosundan bir satır etkinleştirmek grafiği o ana götürür (F3-046).
    win.bottom_dock.event_activated.emit(error_event)

    x_min, x_max = win.plot_panel.visible_x_range()
    centre_ns = win.plot_panel.timestamp_ns_for_x((x_min + x_max) / 2.0)
    assert abs(centre_ns - error_event.timestamp_ns) < 2_000_000  # < 2 ms


def test_playback_next_event_jumps_to_the_first_event_time(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    win, probe = opened
    win.open_channel("ch0")
    span = probe.metadata().time_range
    first_rel_s = (probe.events(span)[0].timestamp_ns - span.start_ns) / NS_PER_S

    assert win.playback_dock.position_s == 0.0
    assert win.playback_dock.goto_next_event() is True
    assert abs(win.playback_dock.position_s - first_rel_s) < 1e-3


def test_full_chain_bin_to_event_navigation(
    opened: tuple[MainWindow, FileRecordingRepository],
) -> None:
    """Tek akış: dosya açık -> kanal çizili -> olaya git -> grafik + imleç orada."""
    win, probe = opened
    win.open_channel("ch0")
    span = probe.metadata().time_range
    events = probe.events(span)
    win.bottom_dock.set_events(events, start_ns=span.start_ns)

    target = events[-1]  # "Transmisyon durdu" @ +0.75 s
    win.bottom_dock.event_activated.emit(target)

    x_min, x_max = win.plot_panel.visible_x_range()
    centre_ns = win.plot_panel.timestamp_ns_for_x((x_min + x_max) / 2.0)
    assert abs(centre_ns - target.timestamp_ns) < 2_000_000

    # Ayrı olarak playback imleci de olaylar arasında gezinebilir.
    win.playback_dock.set_position(0.0)
    win.playback_dock.goto_next_event()
    assert win.playback_dock.position_s > 0.0

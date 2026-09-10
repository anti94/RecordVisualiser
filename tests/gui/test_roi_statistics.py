"""ROI istatistiklerinin dashboard kartına bağlanması — `F3-039`.

Kabul: sağ alt merkez kartı seçilen kanalın mean, std, RMS, min, max
ve peak-peak değerlerini gösterir (zaman bölgesi seçilince o pencere
için).
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
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.statistics_panel import STAT_FIELDS, StatisticsPanel

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


# -- StatisticsPanel: ROI etiketi ve pencere degerleri --------


def test_statistics_panel_shows_all_six_fields_for_a_region(qtbot: QtBot) -> None:
    panel = StatisticsPanel()
    qtbot.addWidget(panel)
    channel = ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=8.0,
    )

    panel.set_channel_data(
        channel, np.array([101.0, 101.5, 102.0], dtype=np.float64), region_seconds=(0.25, 0.55)
    )

    assert "0.25" in panel.title() and "0.55" in panel.title()
    assert panel.field_value("Mean") == "101.5 bar"
    assert panel.field_value("Min") == "101 bar"
    assert panel.field_value("Max") == "102 bar"
    assert panel.field_value("Peak-Peak") == "1 bar"
    for field in STAT_FIELDS:
        assert panel.field_value(field) != "—"


def test_statistics_panel_without_a_region_uses_the_plain_title(qtbot: QtBot) -> None:
    panel = StatisticsPanel()
    qtbot.addWidget(panel)
    channel = ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=8.0,
    )

    panel.set_channel_data(channel, np.array([1.0, 2.0, 3.0], dtype=np.float64))

    assert panel.title() == "Statistics (Pressure)"


# -- uctan uca: grafikte bolge secince kart guncellenir -------


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


def test_selecting_a_time_region_rescopes_the_stats_card(window: MainWindow, qtbot: QtBot) -> None:
    # CH0 (Pressure) = 100.0 + 0.5*n ; period 0.125 s ; n = 0..7
    window.left_dock.channel_activated.emit("ch0")
    stats = window.dashboard.statistics

    # [0.25, 0.55) s -> ornek n = 2, 3, 4 -> 101.0, 101.5, 102.0
    window.plot_panel.set_time_region(0.25, 0.55)
    qtbot.waitUntil(lambda: "0.25–0.55 s" in stats.title())

    assert stats.field_value("Mean") == "101.5 bar"
    assert stats.field_value("Min") == "101 bar"
    assert stats.field_value("Max") == "102 bar"
    assert stats.field_value("Peak-Peak") == "1 bar"
    assert "0.25" in stats.title()


def test_full_channel_stats_before_any_region(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    stats = window.dashboard.statistics

    # tum kanal: 100.0 .. 103.5, mean 101.75
    assert stats.field_value("Mean") == "101.8 bar"
    assert stats.title() == "Statistics (Pressure)"

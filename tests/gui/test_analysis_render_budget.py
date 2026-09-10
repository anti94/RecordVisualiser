"""Gizli sekmeler hesaplanmaz; hızlı güncellemelerin sonuncusu görünür olur."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4, sample_rate_hz=1000))
    window.open_channel("ch0")
    qtbot.wait(100)
    return window


def _tab(win: MainWindow, title: str) -> None:
    win.view_tabs.setCurrentIndex(win.view_tabs.tab_titles().index(title))


def test_hidden_tabs_skip_computation_and_receive_only_the_latest_snapshot(
    win: MainWindow, qtbot: QtBot
) -> None:
    assert not win.spectrum_view.has_spectrum
    assert not win.waterfall_view.has_slices
    channel = win.plot_panel.channel
    assert channel is not None
    with (
        patch.object(
            win.dashboard, "set_channel_data", wraps=win.dashboard.set_channel_data
        ) as dash,
        patch.object(
            win.spectrum_view, "set_channel_data", wraps=win.spectrum_view.set_channel_data
        ) as spectrum,
        patch.object(
            win.waterfall_view, "set_channel_data", wraps=win.waterfall_view.set_channel_data
        ) as waterfall,
    ):
        data = np.empty(256)
        for index in range(100):
            data.fill(float(index))
            win.refresh_analysis_views(channel, data, region_seconds=(index, index + 1))
        data[:] = -500  # üreticinin daha sonra diziyi kullanması saklanan seçimi bozmaz
        assert dash.call_count == 1
        qtbot.waitUntil(
            lambda: (
                (selection := win.dashboard.selection()) is not None
                and selection.region_seconds == (99, 100)
            )
        )
        assert dash.call_count == 2
        assert spectrum.call_count == waterfall.call_count == 0
        _tab(win, "Spectrum")
        result = win.spectrum_view.result()
        assert result is not None
        np.testing.assert_allclose(
            result.amplitudes,
            one_sided_fft(
                np.full(256, 99.0), 1000, window=win.spectrum_view.window_kind
            ).amplitudes,
        )
        assert spectrum.call_count == 1
        _tab(win, "Spectrogram")
        assert waterfall.call_count == 1
        assert "99" in win.waterfall_view.title()
        _tab(win, "Spectrum")
        assert spectrum.call_count == 1  # değişmeyen seçim yeniden hesaplanmaz


def test_dashboard_waits_while_hidden_and_catches_up_when_selected(
    win: MainWindow, qtbot: QtBot
) -> None:
    selection = win.dashboard.selection()
    _tab(win, "Spectrum")
    win.plot_panel.set_time_region(1.0, 2.0)
    qtbot.waitUntil(lambda: "1–2 s" in win.spectrum_view.title())
    assert win.dashboard.selection() == selection
    _tab(win, "Time Series")
    latest = win.dashboard.selection()
    assert latest is not None and latest.region_seconds == (1, 2)
    assert latest.sample_count == 1000


def test_close_discards_a_pending_render(win: MainWindow, qtbot: QtBot) -> None:
    channel = win.plot_panel.channel
    assert channel is not None
    for size in (200, 400):
        win.refresh_analysis_views(channel, np.ones(size))
    win.action("action_close").trigger()
    qtbot.wait(100)
    assert win.dashboard.selection() is None
    assert not win.spectrum_view.has_spectrum
    assert not win.waterfall_view.has_slices


def test_hidden_time_plot_defers_viewport_refresh_until_selected(
    win: MainWindow, qtbot: QtBot
) -> None:
    _tab(win, "Spectrum")
    with patch.object(
        win.plot_panel, "update_channel_data", wraps=win.plot_panel.update_channel_data
    ) as update:
        win.plot_panel.set_x_range(1, 1.02)
        qtbot.wait(100)
        assert update.call_count == 0
        _tab(win, "Time Series")
        qtbot.waitUntil(lambda: win.plot_panel.sample_count == 20)
        assert update.call_count == 1

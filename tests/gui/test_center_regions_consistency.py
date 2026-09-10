"""Zaman serisi, STFT, FFT ve istatistik birlikte bağlı — `F4-052`.

Kabul: mockup'ın dört merkez bölgesi **aynı seçimle** tutarlı güncellenir.

"Tutarlı" ölçülebilir bir iddiadır: aynı kanal, aynı örnek sayısı, aynı
zaman aralığı. `DashboardPanel.selection()` bu üçlüyü dışa verir ve her
hücrenin kendi sonucu onunla karşılaştırılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def repo() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=60.0, sample_rate_hz=200.0)


@pytest.fixture()
def win(qtbot: QtBot, repo: MockRecordingRepository) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(repo)
    window.open_channel("ch0")
    return window


def _assert_consistent(win: MainWindow) -> None:
    """Dört bölge de aynı kanalı, aynı örnek sayısını, aynı aralığı gösteriyor."""
    selection = win.dashboard.selection()
    assert selection is not None

    # 1) Zaman serisi — seçimin kaynağı.
    channel = win.plot_panel.channel
    assert channel is not None
    assert channel.id == selection.channel_id

    # 2) İstatistik kartı.
    assert selection.channel_name in win.dashboard.statistics.title()

    # 3) FFT hücresi — aynı örnek sayısı.
    spectrum = win.dashboard.fft.result()
    assert spectrum is not None
    assert spectrum.sample_count == selection.sample_count
    assert selection.channel_name in win.dashboard.fft.title()

    # 4) Spektrogram hücresi — aynı kanal, aynı sample rate.
    spectrogram = win.dashboard.spectrogram.result()
    assert spectrogram is not None
    assert spectrogram.sample_rate_hz == channel.sample_rate_hz
    assert selection.channel_name in win.dashboard.spectrogram.title()

    # Tam boy görünümler de aynı seçimde.
    view_spectrum = win.spectrum_view.result()
    assert view_spectrum is not None
    assert view_spectrum.sample_count == selection.sample_count
    assert win.waterfall_view.has_slices
    assert selection.channel_name in win.waterfall_view.title()


# --------------------------------------------------------------------------- #
# kanal seçimi
# --------------------------------------------------------------------------- #


def test_opening_a_channel_updates_every_region(win: MainWindow) -> None:
    _assert_consistent(win)
    selection = win.dashboard.selection()
    assert selection is not None
    assert selection.channel_id == "ch0"
    assert selection.region_seconds is None
    assert selection.sample_count > 0


def test_analysis_uses_full_samples_while_the_plot_is_bounded(win: MainWindow) -> None:
    _x, plotted = win.plot_panel.curve_data()
    selection = win.dashboard.selection()
    assert selection is not None
    assert selection.sample_count == 12_000
    assert plotted.size < selection.sample_count
    assert plotted.size <= win.plot_point_budget()


def test_switching_channels_moves_every_region_together(win: MainWindow) -> None:
    before = win.dashboard.selection()
    assert before is not None

    win.open_channel("ch1")

    after = win.dashboard.selection()
    assert after is not None
    assert after.channel_id == "ch1"
    assert after.channel_name != before.channel_name
    _assert_consistent(win)


# --------------------------------------------------------------------------- #
# ROI seçimi
# --------------------------------------------------------------------------- #


def _select_region(win: MainWindow, qtbot: QtBot, start_s: float, end_s: float) -> None:
    """Gerçek ROI yolunu sürer: grafikte bölge kur, sonucun gelmesini bekle."""
    win.plot_panel.set_time_region(start_s, end_s)
    qtbot.waitUntil(
        lambda: (s := win.dashboard.selection()) is not None and s.region_seconds is not None,
        timeout=5_000,
    )


def test_a_roi_narrows_every_region_to_the_same_window(win: MainWindow, qtbot: QtBot) -> None:
    assert win.dashboard.selection() is not None

    _select_region(win, qtbot, 0.0, 15.0)  # 60 s kaydın ilk çeyreği

    after = win.dashboard.selection()
    assert after is not None
    assert after.region_seconds == (0.0, 15.0)
    assert after.sample_count == 3_000  # 15 s × 200 Hz; analiz azaltılmaz.
    _assert_consistent(win)


def test_the_same_region_text_appears_in_every_title(win: MainWindow, qtbot: QtBot) -> None:
    _select_region(win, qtbot, 5.0, 35.0)

    selection = win.dashboard.selection()
    assert selection is not None and selection.region_seconds is not None
    low, _high = selection.region_seconds
    marker = f"{low:.3g}"

    for title in (
        win.dashboard.statistics.title(),
        win.dashboard.fft.title(),
        win.dashboard.spectrogram.title(),
        win.waterfall_view.title(),
    ):
        assert marker in title, title


def test_a_second_roi_keeps_the_regions_in_step(win: MainWindow, qtbot: QtBot) -> None:
    for start_s, end_s in ((0.0, 30.0), (10.0, 25.0)):
        _select_region(win, qtbot, start_s, end_s)
        _assert_consistent(win)


# --------------------------------------------------------------------------- #
# tek giriş noktası
# --------------------------------------------------------------------------- #


def test_refresh_analysis_views_updates_all_surfaces(win: MainWindow) -> None:
    channel = win.plot_panel.channel
    assert channel is not None
    _x, raw = win.plot_panel.curve_data()

    win.clear_analysis_views()
    assert win.dashboard.selection() is None
    assert not win.dashboard.fft.has_spectrum
    assert not win.dashboard.spectrogram.has_spectrogram
    assert not win.spectrum_view.has_spectrum
    assert not win.waterfall_view.has_slices

    win.refresh_analysis_views(channel, raw, region_seconds=(1.0, 2.0))

    selection = win.dashboard.selection()
    assert selection is not None
    assert selection.region_seconds == (1.0, 2.0)
    _assert_consistent(win)


def test_closing_the_recording_empties_every_region(win: MainWindow) -> None:
    win.clear_analysis_views()
    assert win.dashboard.selection() is None
    assert win.dashboard.statistics.title() == "Statistics"
    assert win.dashboard.fft.title() == "FFT"
    assert win.dashboard.spectrogram.title() == "Spectrogram"
    assert win.waterfall_view.title() == "Waterfall"

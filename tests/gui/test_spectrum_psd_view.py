"""Spectrum sekmesi ve PSD görünümü — `F4-045`.

Kabul: FFT/PSD seçimi eksen etiketini ve doğru sonucu değiştirir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.psd import welch_psd
from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.spectrum_panel import (
    SPECTRUM_MODES,
    SpectrumMode,
    SpectrumPanel,
    psd_unit,
)

pytestmark = pytest.mark.gui

FS = 1_000.0
#: Bin genişliği 0.5 Hz — 100 ve 250 Hz tam bine oturur (sızıntı yok).
N = 2_000

CHANNEL = ChannelMetadata(
    id="ch0",
    path="Acoustic/Hydrophone 1",
    name="Hydrophone 1",
    dtype="float64",
    source=ChannelSource.ACOUSTIC,
    unit="Pa",
    sample_rate_hz=FS,
)


def _tone(amp: float, freq_hz: float) -> NDArray[np.float64]:
    k = np.arange(N, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


@pytest.fixture()
def panel(qtbot: QtBot) -> SpectrumPanel:
    widget = SpectrumPanel()
    qtbot.addWidget(widget)
    return widget


# --------------------------------------------------------------------------- #
# kip seçimi
# --------------------------------------------------------------------------- #


def test_the_selector_offers_fft_and_psd(panel: SpectrumPanel) -> None:
    labels = [panel.mode_selector.itemText(i) for i in range(panel.mode_selector.count())]
    assert labels == ["FFT", "PSD"]
    assert SPECTRUM_MODES == ("fft", "psd")


def test_fft_is_the_default_mode(panel: SpectrumPanel) -> None:
    assert panel.mode is SpectrumMode.FFT


def test_selecting_psd_changes_the_mode(panel: SpectrumPanel) -> None:
    panel.mode_selector.setCurrentIndex(panel.mode_selector.findData(SpectrumMode.PSD))
    assert panel.mode is SpectrumMode.PSD


def test_set_mode_moves_the_selector_too(panel: SpectrumPanel) -> None:
    panel.set_mode(SpectrumMode.PSD)
    assert panel.mode_selector.currentText() == "PSD"
    panel.set_mode("fft")
    assert panel.mode_selector.currentText() == "FFT"


# --------------------------------------------------------------------------- #
# eksen etiketi kiple değişir
# --------------------------------------------------------------------------- #


def test_the_y_axis_label_switches_between_amplitude_and_psd(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 100.0))
    assert "Amplitude" in panel.amplitude_axis_label()
    assert "Pa" in panel.amplitude_axis_label()

    panel.set_mode(SpectrumMode.PSD)
    label = panel.amplitude_axis_label()
    assert "PSD" in label
    assert psd_unit("Pa") in label
    assert "Amplitude" not in label

    panel.set_mode(SpectrumMode.FFT)
    assert "Amplitude" in panel.amplitude_axis_label()


def test_the_frequency_axis_is_unchanged_by_the_mode(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 100.0))
    before = panel.frequency_axis_label()
    panel.set_mode(SpectrumMode.PSD)
    assert panel.frequency_axis_label() == before
    assert "Hz" in before


def test_the_title_names_the_active_mode(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 100.0))
    assert panel.title().startswith("FFT")
    panel.set_mode(SpectrumMode.PSD)
    assert panel.title().startswith("PSD")


def test_psd_unit_helper() -> None:
    assert psd_unit("Pa") == "Pa²/Hz"
    assert psd_unit(None) == ""


# --------------------------------------------------------------------------- #
# sonuç kiple değişir
# --------------------------------------------------------------------------- #


def test_fft_mode_produces_the_amplitude_spectrum(panel: SpectrumPanel) -> None:
    panel.set_window(WindowKind.RECTANGULAR)
    signal = _tone(2.0, 100.0)
    panel.set_channel_data(CHANNEL, signal)

    result = panel.result()
    assert result is not None
    assert panel.psd_result() is None
    assert abs(result.peak_amplitude - 2.0) < 1e-9

    expected = one_sided_fft(signal, FS, window=WindowKind.RECTANGULAR)
    _freqs, values = panel.curve_data()
    assert np.allclose(values, expected.amplitudes)


def test_psd_mode_produces_the_power_density(panel: SpectrumPanel) -> None:
    panel.set_window(WindowKind.HANN)
    signal = _tone(2.0, 100.0)
    panel.set_channel_data(CHANNEL, signal)
    panel.set_mode(SpectrumMode.PSD)

    psd = panel.psd_result()
    assert psd is not None
    assert panel.result() is None
    assert abs(psd.peak_frequency_hz - 100.0) < psd.resolution_hz

    expected = welch_psd(signal, FS, window=WindowKind.HANN)
    _freqs, values = panel.curve_data()
    assert np.allclose(values, expected.density)


def test_the_two_modes_give_different_curves(panel: SpectrumPanel) -> None:
    signal = _tone(2.0, 100.0)
    panel.set_channel_data(CHANNEL, signal)
    _f1, fft_values = panel.curve_data()

    panel.set_mode(SpectrumMode.PSD)
    _f2, psd_values = panel.curve_data()

    assert fft_values.shape != psd_values.shape or not np.allclose(fft_values, psd_values)


def test_switching_back_recomputes_the_fft(panel: SpectrumPanel) -> None:
    panel.set_window(WindowKind.RECTANGULAR)
    panel.set_channel_data(CHANNEL, _tone(3.0, 250.0))
    panel.set_mode(SpectrumMode.PSD)
    panel.set_mode(SpectrumMode.FFT)

    result = panel.result()
    assert result is not None
    assert abs(result.peak_amplitude - 3.0) < 1e-9


def test_changing_the_mode_without_data_only_moves_the_axis(panel: SpectrumPanel) -> None:
    panel.set_mode(SpectrumMode.PSD)
    assert not panel.has_spectrum
    assert "PSD" in panel.amplitude_axis_label()


def test_new_data_uses_the_active_mode(panel: SpectrumPanel) -> None:
    panel.set_mode(SpectrumMode.PSD)
    panel.set_channel_data(CHANNEL, _tone(1.0, 60.0))
    assert panel.psd_result() is not None
    assert panel.result() is None


# --------------------------------------------------------------------------- #
# Spectrum görünüm sekmesi
# --------------------------------------------------------------------------- #


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0))
    window.open_channel("ch0")
    return window


def test_the_spectrum_tab_is_enabled(win: MainWindow) -> None:
    assert "Spectrum" in win.view_tabs.enabled_tabs()


def test_selecting_the_spectrum_tab_shows_the_spectrum_view(win: MainWindow) -> None:
    titles = win.view_tabs.tab_titles()
    win.view_tabs.setCurrentIndex(titles.index("Spectrum"))
    assert win.center_stack.currentWidget() is win.spectrum_view
    assert not win.center_shows_plot


def test_the_spectrum_view_follows_the_open_channel(win: MainWindow) -> None:
    assert win.spectrum_view.has_spectrum
    result = win.spectrum_view.result()
    assert result is not None
    assert result.sample_rate_hz == 200.0


def test_the_spectrum_view_switches_to_psd_independently(win: MainWindow) -> None:
    win.spectrum_view.set_mode(SpectrumMode.PSD)
    assert win.spectrum_view.psd_result() is not None
    # Dashboard hücresi kendi kipinde kalır.
    assert win.dashboard.fft.mode is SpectrumMode.FFT
    assert win.dashboard.fft.result() is not None


def test_going_back_to_time_series_shows_the_dashboard(win: MainWindow) -> None:
    titles = win.view_tabs.tab_titles()
    win.view_tabs.setCurrentIndex(titles.index("Spectrum"))
    win.view_tabs.setCurrentIndex(titles.index("Time Series"))
    assert win.center_shows_plot

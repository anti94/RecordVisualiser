"""Seçili aralık FFT'si mockup alt grafiğine bağlı — `F4-042`.

Kabul: ROI değişince FFT yenilenir; frekans ve genlik birimi görünür.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.spectrum_panel import (
    NO_DATA_MESSAGE,
    NO_RATE_MESSAGE,
    SpectrumPanel,
)

pytestmark = pytest.mark.gui

FS = 1_000.0
N = 1_000

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
# panel: eksen birimleri
# --------------------------------------------------------------------------- #


def test_starts_empty_without_a_fake_result(panel: SpectrumPanel) -> None:
    assert not panel.has_spectrum
    assert panel.result() is None
    assert panel.message_text() == NO_DATA_MESSAGE


def test_frequency_and_amplitude_units_are_shown(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 50.0))
    assert "Frequency" in panel.frequency_axis_label()
    assert "Hz" in panel.frequency_axis_label()
    assert "Amplitude" in panel.amplitude_axis_label()
    assert "Pa" in panel.amplitude_axis_label()


def test_a_channel_without_a_unit_still_labels_the_amplitude(panel: SpectrumPanel) -> None:
    unitless = ChannelMetadata(
        id="c", path="p", name="n", dtype="float64", sample_rate_hz=FS, unit=None
    )
    panel.set_channel_data(unitless, _tone(1.0, 50.0))
    assert "Amplitude" in panel.amplitude_axis_label()


def test_the_title_names_the_channel(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 50.0))
    assert "Hydrophone 1" in panel.title()


# --------------------------------------------------------------------------- #
# panel: hesap
# --------------------------------------------------------------------------- #


def test_a_known_tone_is_drawn_at_its_frequency(panel: SpectrumPanel) -> None:
    panel.set_window(WindowKind.RECTANGULAR)
    panel.set_channel_data(CHANNEL, _tone(2.0, 120.0))

    result = panel.result()
    assert result is not None
    assert abs(result.peak_frequency_hz - 120.0) < 1e-9
    assert abs(result.peak_amplitude - 2.0) < 1e-9

    freqs, amps = panel.curve_data()
    assert np.allclose(freqs, result.frequencies_hz)
    assert np.allclose(amps, result.amplitudes)


def test_an_unknown_sample_rate_is_explained_not_faked(panel: SpectrumPanel) -> None:
    rateless = ChannelMetadata(id="c", path="p", name="n", dtype="float64", sample_rate_hz=None)
    panel.set_channel_data(rateless, _tone(1.0, 50.0))
    assert not panel.has_spectrum
    assert panel.message_text() == NO_RATE_MESSAGE


def test_an_empty_selection_is_explained(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, np.empty(0, dtype=np.float64))
    assert not panel.has_spectrum
    assert panel.message_text() == NO_DATA_MESSAGE


def test_clear_returns_to_the_empty_state(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 50.0))
    assert panel.has_spectrum
    panel.clear()
    assert not panel.has_spectrum
    assert panel.title() == "FFT"


def test_the_region_span_appears_in_the_title(panel: SpectrumPanel) -> None:
    panel.set_channel_data(CHANNEL, _tone(1.0, 50.0), region_seconds=(0.25, 0.75))
    assert "0.25" in panel.title()
    assert "0.75" in panel.title()


# --------------------------------------------------------------------------- #
# ROI değişince yenilenir (MainWindow yolu)
# --------------------------------------------------------------------------- #


@pytest.fixture()
def repo() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0)


@pytest.fixture()
def win(qtbot: QtBot, repo: MockRecordingRepository) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(repo)
    window.open_channel("ch0")
    return window


def test_opening_a_channel_fills_the_fft_cell(win: MainWindow) -> None:
    assert win.dashboard.fft.has_spectrum
    result = win.dashboard.fft.result()
    assert result is not None
    assert result.sample_rate_hz == 200.0


def test_the_roi_narrows_the_spectrum_window(
    win: MainWindow, repo: MockRecordingRepository, qtbot: QtBot
) -> None:
    full = win.dashboard.fft.result()
    assert full is not None
    full_count = full.sample_count

    span = repo.metadata().time_range
    quarter = span.duration_ns // 4
    win.plot_panel.time_region_changed.emit(span.start_ns, span.start_ns + quarter)
    qtbot.waitUntil(
        lambda: (r := win.dashboard.fft.result()) is not None and r.sample_count < full_count,
        timeout=5_000,
    )

    narrowed = win.dashboard.fft.result()
    assert narrowed is not None
    assert narrowed.sample_count < full_count
    # Daha kısa pencere -> daha kaba frekans çözünürlüğü.
    assert narrowed.resolution_hz > full.resolution_hz
    assert "s" in win.dashboard.fft.title()


def test_a_second_roi_change_refreshes_again(
    win: MainWindow, repo: MockRecordingRepository, qtbot: QtBot
) -> None:
    span = repo.metadata().time_range
    half = span.duration_ns // 2
    quarter = span.duration_ns // 4

    win.plot_panel.time_region_changed.emit(span.start_ns, span.start_ns + half)
    qtbot.waitUntil(lambda: win.dashboard.fft.has_spectrum, timeout=5_000)
    first = win.dashboard.fft.result()
    assert first is not None

    win.plot_panel.time_region_changed.emit(span.start_ns, span.start_ns + quarter)
    qtbot.waitUntil(
        lambda: (
            (r := win.dashboard.fft.result()) is not None and r.sample_count < first.sample_count
        ),
        timeout=5_000,
    )
    second = win.dashboard.fft.result()
    assert second is not None
    assert second.sample_count < first.sample_count


def test_switching_channels_refreshes_the_cell(win: MainWindow) -> None:
    before = win.dashboard.fft.title()
    win.open_channel("ch1")
    assert win.dashboard.fft.has_spectrum
    assert win.dashboard.fft.title() != before

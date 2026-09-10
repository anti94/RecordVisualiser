"""Mockup orta spektrogramı sonuçlara bağlı — `F4-048`.

Kabul: hidrofon, zaman, frekans ve dB renk ölçeği veriyi doğru gösterir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.spectrum import amplitude_to_db
from sonar_analyzer.analysis.stft import stft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.spectrogram_panel import (
    COLOR_BAR_LABEL,
    DEFAULT_DYNAMIC_RANGE_DB,
    NO_DATA_MESSAGE,
    NO_RATE_MESSAGE,
    SpectrogramPanel,
)

pytestmark = pytest.mark.gui

FS = 1_000.0
N = 8_000
#: 256'lık parçada tam bine oturan frekans (64. bin).
BIN_TONE_HZ = 250.0

HYDROPHONE = ChannelMetadata(
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


def _chirp(f0: float, f1: float) -> NDArray[np.float64]:
    t = np.arange(N, dtype=np.float64) / FS
    duration = N / FS
    return np.sin(2.0 * math.pi * (f0 * t + 0.5 * (f1 - f0) / duration * t * t))


@pytest.fixture()
def panel(qtbot: QtBot) -> SpectrogramPanel:
    widget = SpectrogramPanel()
    qtbot.addWidget(widget)
    return widget


# --------------------------------------------------------------------------- #
# boş durum
# --------------------------------------------------------------------------- #


def test_starts_empty_without_a_fake_map(panel: SpectrogramPanel) -> None:
    assert not panel.has_spectrogram
    assert panel.result() is None
    assert panel.levels() is None
    assert panel.image_data().size == 0
    assert panel.message_text() == NO_DATA_MESSAGE


def test_an_unknown_sample_rate_is_explained_not_faked(panel: SpectrogramPanel) -> None:
    rateless = ChannelMetadata(id="c", path="p", name="n", dtype="float64", sample_rate_hz=None)
    panel.set_channel_data(rateless, _tone(1.0, BIN_TONE_HZ))
    assert not panel.has_spectrogram
    assert panel.message_text() == NO_RATE_MESSAGE


def test_an_empty_selection_is_explained(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, np.empty(0, dtype=np.float64))
    assert not panel.has_spectrogram
    assert panel.message_text() == NO_DATA_MESSAGE


def test_clear_returns_to_the_empty_state(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ))
    assert panel.has_spectrogram
    panel.clear()
    assert not panel.has_spectrogram
    assert panel.title() == "Spectrogram"


# --------------------------------------------------------------------------- #
# hidrofon
# --------------------------------------------------------------------------- #


def test_the_title_names_the_hydrophone(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ))
    assert "Hydrophone 1" in panel.title()


def test_the_region_span_appears_in_the_title(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ), region_seconds=(1.5, 4.5))
    assert "1.5" in panel.title()
    assert "4.5" in panel.title()


# --------------------------------------------------------------------------- #
# zaman ve frekans eksenleri
# --------------------------------------------------------------------------- #


def test_the_axes_are_labelled_with_their_units(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ))
    assert "Time" in panel.time_axis_label()
    assert "s" in panel.time_axis_label()
    assert "Frequency" in panel.frequency_axis_label()
    assert "Hz" in panel.frequency_axis_label()


def test_the_image_matrix_is_time_by_frequency(panel: SpectrogramPanel) -> None:
    signal = _tone(1.0, BIN_TONE_HZ)
    panel.set_channel_data(HYDROPHONE, signal)

    result = panel.result()
    assert result is not None
    # pyqtgraph görüntüsü (sütun, satır) düzeninde: (zaman, frekans).
    assert panel.image_data().shape == (result.frame_count, result.bin_count)


def test_the_axes_come_from_the_stft(panel: SpectrogramPanel) -> None:
    signal = _chirp(50.0, 400.0)
    panel.set_window(WindowKind.HANN)
    panel.set_channel_data(HYDROPHONE, signal)

    result = panel.result()
    expected = stft(signal, FS, window=WindowKind.HANN)
    assert result is not None
    assert np.allclose(result.times_s, expected.times_s)
    assert np.allclose(result.frequencies_hz, expected.frequencies_hz)
    assert result.frequencies_hz[-1] == FS / 2.0


def test_a_steady_tone_shows_a_flat_ridge_at_its_row(panel: SpectrogramPanel) -> None:
    panel.set_window(WindowKind.RECTANGULAR)
    panel.set_channel_data(HYDROPHONE, _tone(2.0, BIN_TONE_HZ))

    result = panel.result()
    assert result is not None
    assert np.allclose(result.peak_frequencies_hz(), BIN_TONE_HZ)

    # Görüntüde de her zaman sütununun en parlak hücresi aynı satırda.
    image = panel.image_data()
    rows = np.argmax(image, axis=1)
    assert np.all(rows == rows[0])
    assert abs(float(result.frequencies_hz[rows[0]]) - BIN_TONE_HZ) < 1e-9


def test_a_chirp_rises_across_the_image(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _chirp(50.0, 400.0))
    result = panel.result()
    assert result is not None
    peaks = result.peak_frequencies_hz()
    assert peaks[-1] > peaks[0]
    slope, _intercept = np.polyfit(result.times_s, peaks, 1)
    assert float(slope) > 0.0


# --------------------------------------------------------------------------- #
# dB renk ölçeği
# --------------------------------------------------------------------------- #


def test_the_image_values_are_amplitude_decibels(panel: SpectrogramPanel) -> None:
    signal = _tone(1.0, BIN_TONE_HZ)
    panel.set_window(WindowKind.HANN)
    panel.set_channel_data(HYDROPHONE, signal)

    result = panel.result()
    assert result is not None
    assert np.allclose(panel.image_data(), amplitude_to_db(result.magnitudes).T)


def test_the_colour_scale_spans_the_dynamic_range_below_the_peak(
    panel: SpectrogramPanel,
) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0, BIN_TONE_HZ))

    levels = panel.levels()
    result = panel.result()
    assert levels is not None and result is not None

    low, high = levels
    peak_db = float(np.max(amplitude_to_db(result.magnitudes)))
    assert abs(high - peak_db) < 1e-9
    assert abs((high - low) - DEFAULT_DYNAMIC_RANGE_DB) < 1e-9


def test_the_dynamic_range_is_configurable(panel: SpectrogramPanel) -> None:
    panel.set_dynamic_range_db(40.0)
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ))

    levels = panel.levels()
    assert levels is not None
    assert abs((levels[1] - levels[0]) - 40.0) < 1e-9


def test_a_nonpositive_dynamic_range_is_rejected(panel: SpectrogramPanel) -> None:
    with pytest.raises(ValueError, match="dinamik aralık"):
        panel.set_dynamic_range_db(0.0)


def test_the_colour_bar_is_labelled_in_db(panel: SpectrogramPanel) -> None:
    assert panel.color_bar_label() == COLOR_BAR_LABEL == "dB"


def test_a_louder_tone_shifts_the_scale_up(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0, BIN_TONE_HZ))
    quiet = panel.levels()
    panel.set_channel_data(HYDROPHONE, _tone(10.0, BIN_TONE_HZ))
    loud = panel.levels()

    assert quiet is not None and loud is not None
    assert loud[1] > quiet[1]
    assert abs((loud[1] - quiet[1]) - 20.0) < 1e-6  # 10x genlik -> +20 dB


# --------------------------------------------------------------------------- #
# MainWindow yolu
# --------------------------------------------------------------------------- #


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


def test_opening_a_channel_fills_the_spectrogram_cell(win: MainWindow) -> None:
    assert win.dashboard.spectrogram.has_spectrogram
    result = win.dashboard.spectrogram.result()
    assert result is not None
    assert result.sample_rate_hz == 200.0
    assert "Pressure" in win.dashboard.spectrogram.title()


def test_the_roi_narrows_the_spectrogram(win: MainWindow, qtbot: QtBot) -> None:
    full = win.dashboard.spectrogram.result()
    assert full is not None

    win.plot_panel.set_time_region(0.0, 15.0)
    qtbot.waitUntil(lambda: "0–15 s" in win.dashboard.spectrogram.title(), timeout=5_000)

    narrowed = win.dashboard.spectrogram.result()
    assert narrowed is not None
    # Seçilen aralık başlıkta ve STFT o pencereden hesaplandı.
    assert "15" in win.dashboard.spectrogram.title()
    assert 0 < narrowed.frame_count < full.frame_count


def test_switching_channels_refreshes_the_cell(win: MainWindow) -> None:
    before = win.dashboard.spectrogram.title()
    win.open_channel("ch1")
    assert win.dashboard.spectrogram.has_spectrogram
    assert win.dashboard.spectrogram.title() != before

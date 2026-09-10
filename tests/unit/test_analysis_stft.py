"""STFT ve spektrogram matrisi — `F4-046`.

Kabul: chirp eğimi, zaman sütunları ve frekans satırları referansla
eşleşir. Kenar/overlap/eksen doğrulamaları `F4-047`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import segment_starts, segment_step
from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.stft import StftError, stft
from sonar_analyzer.analysis.windows import WindowKind

Vec = NDArray[np.float64]

FS = 1_000.0
N = 8_000  # 8 saniye
SEGMENT = 256
ALL_WINDOWS = list(WindowKind)


def _tone(amp: float, freq_hz: float, count: int = N) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


def _linear_chirp(f0: float, f1: float, count: int = N) -> Vec:
    """f0'dan f1'e doğrusal süpüren chirp (anlık frekans t'de doğrusal)."""
    t = np.arange(count, dtype=np.float64) / FS
    duration = count / FS
    phase = 2.0 * math.pi * (f0 * t + 0.5 * (f1 - f0) / duration * t * t)
    return np.sin(phase)


# --------------------------------------------------------------------------- #
# matris biçimi
# --------------------------------------------------------------------------- #


def test_matrix_shape_is_bins_by_frames() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.5)
    expected_frames = len(segment_starts(N, SEGMENT, 0.5))
    assert result.magnitudes.shape == (SEGMENT // 2 + 1, expected_frames)
    assert result.bin_count == SEGMENT // 2 + 1
    assert result.frame_count == expected_frames


def test_metadata_is_reported() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.75, window="hamming")
    assert result.segment_length == SEGMENT
    assert result.overlap == 0.75
    assert result.hop == segment_step(SEGMENT, 0.75)
    assert result.window_kind == "hamming"
    assert result.sample_rate_hz == FS


def test_magnitudes_are_never_negative() -> None:
    rng = np.random.default_rng(3)
    result = stft(rng.normal(size=N), FS, segment_length=SEGMENT)
    assert np.all(result.magnitudes >= 0.0)


# --------------------------------------------------------------------------- #
# frekans satırları referansla eşleşir
# --------------------------------------------------------------------------- #


def test_frequency_rows_are_the_segment_rfft_grid() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(SEGMENT, d=1.0 / FS))
    assert result.frequencies_hz[0] == 0.0
    assert result.frequencies_hz[-1] == FS / 2.0
    assert abs(result.resolution_hz - FS / SEGMENT) < 1e-12


def test_row_count_follows_the_segment_length() -> None:
    for length in (64, 128, 512):
        result = stft(_tone(1.0, 100.0), FS, segment_length=length)
        assert result.bin_count == length // 2 + 1


def test_a_steady_tone_sits_on_one_row_in_every_column() -> None:
    # 250 Hz, 256'lık parçada tam bine oturur (250 / (1000/256) = 64).
    result = stft(_tone(2.0, 250.0), FS, segment_length=SEGMENT, window=WindowKind.RECTANGULAR)
    peaks = result.peak_frequencies_hz()
    assert np.allclose(peaks, 250.0)
    row = int(np.argmin(np.abs(result.frequencies_hz - 250.0)))
    assert np.allclose(result.magnitudes[row, :], 2.0, atol=1e-9)


def test_a_frame_matches_the_one_sided_fft_of_its_samples() -> None:
    signal = _tone(1.5, 250.0)
    result = stft(signal, FS, segment_length=SEGMENT, overlap=0.5, window=WindowKind.HANN)
    starts = segment_starts(N, SEGMENT, 0.5)

    for index in (0, 3, result.frame_count - 1):
        expected = one_sided_fft(
            signal[starts[index] : starts[index] + SEGMENT], FS, window=WindowKind.HANN
        )
        assert np.allclose(result.frame(index), expected.amplitudes, atol=1e-12)


@pytest.mark.parametrize("window", ALL_WINDOWS)
def test_the_tone_amplitude_is_recovered_for_every_window(window: WindowKind) -> None:
    result = stft(_tone(3.0, 250.0), FS, segment_length=SEGMENT, window=window)
    assert abs(float(np.max(result.magnitudes)) - 3.0) < 1e-9


# --------------------------------------------------------------------------- #
# zaman sütunları referansla eşleşir
# --------------------------------------------------------------------------- #


def test_time_columns_are_the_segment_centres() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.5)
    starts = np.asarray(segment_starts(N, SEGMENT, 0.5), dtype=np.float64)
    expected = (starts + SEGMENT / 2.0) / FS
    assert np.allclose(result.times_s, expected)


def test_the_first_column_is_half_a_segment_in() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.5)
    assert abs(result.times_s[0] - SEGMENT / 2.0 / FS) < 1e-12


def test_columns_are_evenly_spaced_by_the_hop() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.5)
    steps = np.diff(result.times_s)
    assert np.allclose(steps, result.time_step_s)
    assert abs(result.time_step_s - result.hop / FS) < 1e-12


def test_columns_stay_inside_the_signal_duration() -> None:
    result = stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=0.5)
    assert result.times_s[0] > 0.0
    assert result.times_s[-1] < N / FS


def test_more_overlap_gives_more_columns() -> None:
    counts = [
        stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=value).frame_count
        for value in (0.0, 0.5, 0.75)
    ]
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]


# --------------------------------------------------------------------------- #
# chirp eğimi referansla eşleşir
# --------------------------------------------------------------------------- #


def test_a_linear_chirp_traces_a_straight_line_with_the_reference_slope() -> None:
    f0, f1 = 50.0, 400.0
    duration = N / FS
    result = stft(_linear_chirp(f0, f1), FS, segment_length=SEGMENT, overlap=0.75)

    peaks = result.peak_frequencies_hz()
    slope, intercept = np.polyfit(result.times_s, peaks, 1)

    expected_slope = (f1 - f0) / duration  # Hz/s
    assert abs(float(slope) - expected_slope) < 0.02 * expected_slope
    assert abs(float(intercept) - f0) < 3.0 * result.resolution_hz

    # Ölçülen tepe, her sütunda anlık frekansa bir bin toleransında oturur.
    instantaneous = f0 + expected_slope * result.times_s
    assert np.max(np.abs(peaks - instantaneous)) < 3.0 * result.resolution_hz


def test_a_descending_chirp_has_a_negative_slope() -> None:
    result = stft(_linear_chirp(400.0, 50.0), FS, segment_length=SEGMENT, overlap=0.75)
    slope, _intercept = np.polyfit(result.times_s, result.peak_frequencies_hz(), 1)
    assert float(slope) < 0.0
    assert abs(float(slope) + 350.0 / (N / FS)) < 0.02 * (350.0 / (N / FS))


def test_a_steady_tone_has_a_flat_ridge() -> None:
    result = stft(_tone(1.0, 250.0), FS, segment_length=SEGMENT, overlap=0.5)
    slope, _intercept = np.polyfit(result.times_s, result.peak_frequencies_hz(), 1)
    assert abs(float(slope)) < 1e-9


# --------------------------------------------------------------------------- #
# hata yolları (kapsamlısı F4-047)
# --------------------------------------------------------------------------- #


def test_empty_signal_is_rejected() -> None:
    with pytest.raises(StftError, match="boş sinyal"):
        stft(np.empty(0, dtype=np.float64), FS)


def test_a_segment_longer_than_the_signal_is_rejected() -> None:
    with pytest.raises(StftError, match="uzun olamaz"):
        stft(np.zeros(100), FS, segment_length=256)


def test_an_invalid_overlap_is_rejected() -> None:
    with pytest.raises(StftError, match="örtüşme"):
        stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, overlap=1.0)


def test_an_unknown_window_is_rejected() -> None:
    with pytest.raises(StftError, match="bilinmeyen pencere"):
        stft(_tone(1.0, 100.0), FS, segment_length=SEGMENT, window="gaussian")


def test_input_is_not_mutated() -> None:
    signal = _tone(1.0, 100.0)
    snapshot = signal.copy()
    stft(signal, FS, segment_length=SEGMENT)
    assert np.array_equal(signal, snapshot)

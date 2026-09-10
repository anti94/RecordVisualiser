"""STFT kenar, overlap ve eksen eşleme doğrulamaları — `F4-047`.

Kabul: son pencere ve boş seçim **tanımlı** davranır; eksenler kaymaz.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import segment_starts, segment_step
from sonar_analyzer.analysis.stft import StftError, stft
from sonar_analyzer.analysis.windows import WindowKind

Vec = NDArray[np.float64]

FS = 1_000.0
SEGMENT = 256
#: 256'lık parçada tam bine oturan frekans (1000/256 = 3.90625; 64. bin).
BIN_TONE_HZ = 250.0


def _tone(amp: float, freq_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


# --------------------------------------------------------------------------- #
# son pencere
# --------------------------------------------------------------------------- #


def test_the_trailing_remainder_produces_no_column() -> None:
    # 1000 örnek, 256'lık parça, örtüşmesiz -> son tam parça 512'de başlar.
    signal = np.zeros(1_000, dtype=np.float64)
    result = stft(signal, FS, segment_length=SEGMENT, overlap=0.0)
    starts = segment_starts(1_000, SEGMENT, 0.0)

    assert result.frame_count == len(starts) == 3
    assert starts[-1] + SEGMENT <= 1_000
    # 768..999 arası hiçbir sütuna girmiyor.
    assert starts[-1] + SEGMENT == 768


def test_samples_beyond_the_last_full_window_do_not_reach_the_matrix() -> None:
    signal = np.zeros(1_000, dtype=np.float64)
    signal[768:] = _tone(50.0, BIN_TONE_HZ, 1_000)[768:]  # yalnız artan kısımda güçlü ton
    result = stft(signal, FS, segment_length=SEGMENT, overlap=0.0)
    # Sinyalin geri kalanı sıfır olduğundan matris de sıfır kalmalı.
    assert float(np.max(result.magnitudes)) < 1e-12


def test_a_signal_that_fits_exactly_is_fully_covered() -> None:
    result = stft(np.zeros(1_024), FS, segment_length=SEGMENT, overlap=0.0)
    assert result.frame_count == 4
    starts = segment_starts(1_024, SEGMENT, 0.0)
    assert starts[-1] + SEGMENT == 1_024


def test_a_segment_equal_to_the_signal_is_a_single_column() -> None:
    result = stft(_tone(1.0, BIN_TONE_HZ, SEGMENT), FS, segment_length=SEGMENT, overlap=0.5)
    assert result.frame_count == 1
    assert abs(result.times_s[0] - SEGMENT / 2.0 / FS) < 1e-12


def test_a_single_sample_segment_gives_one_row() -> None:
    result = stft(np.array([2.0, -2.0, 1.0]), FS, segment_length=1, overlap=0.0)
    assert result.bin_count == 1
    assert result.frequencies_hz[0] == 0.0
    assert result.frame_count == 3


def test_a_two_sample_segment_has_dc_and_nyquist_rows() -> None:
    result = stft(np.array([1.0, -1.0, 1.0, -1.0]), FS, segment_length=2, overlap=0.0)
    assert result.bin_count == 2
    assert result.frequencies_hz[-1] == FS / 2.0


def test_an_odd_segment_has_no_exact_nyquist_row() -> None:
    result = stft(np.zeros(1_000), FS, segment_length=255, overlap=0.0)
    assert result.bin_count == 128
    assert result.frequencies_hz[-1] < FS / 2.0


# --------------------------------------------------------------------------- #
# boş / yetersiz seçim
# --------------------------------------------------------------------------- #


def test_an_empty_selection_is_rejected_with_a_reason() -> None:
    with pytest.raises(StftError, match="boş sinyal"):
        stft(np.empty(0, dtype=np.float64), FS)


def test_a_selection_shorter_than_the_segment_is_rejected_not_truncated() -> None:
    with pytest.raises(StftError, match="uzun olamaz"):
        stft(np.zeros(255), FS, segment_length=SEGMENT)


def test_the_default_segment_shrinks_to_a_short_selection() -> None:
    result = stft(np.zeros(100), FS)
    assert result.segment_length == 100
    assert result.frame_count == 1


@pytest.mark.parametrize("bad", [0, -1, -256])
def test_a_nonpositive_segment_length_is_rejected(bad: int) -> None:
    with pytest.raises(StftError, match="parça uzunluğu"):
        stft(np.zeros(1_000), FS, segment_length=bad)


def test_a_nonpositive_sample_rate_is_rejected() -> None:
    with pytest.raises(StftError, match="sample rate"):
        stft(np.zeros(1_000), 0.0, segment_length=SEGMENT)


def test_a_two_dimensional_selection_is_rejected() -> None:
    with pytest.raises(StftError, match="tek boyutlu"):
        stft(np.zeros((4, 4)), FS, segment_length=2)


# --------------------------------------------------------------------------- #
# overlap
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", [-0.1, 1.0, 2.0, math.inf, math.nan])
def test_an_invalid_overlap_is_rejected(bad: float) -> None:
    with pytest.raises(StftError, match="örtüşme"):
        stft(np.zeros(1_000), FS, segment_length=SEGMENT, overlap=bad)


@pytest.mark.parametrize("overlap", [0.0, 0.25, 0.5, 0.75, 0.9])
def test_the_hop_and_frame_count_follow_the_overlap(overlap: float) -> None:
    total = 4_000
    result = stft(np.zeros(total), FS, segment_length=SEGMENT, overlap=overlap)
    assert result.hop == segment_step(SEGMENT, overlap)
    assert result.frame_count == len(segment_starts(total, SEGMENT, overlap))
    assert result.overlap == overlap


def test_zero_overlap_columns_do_not_share_samples() -> None:
    result = stft(np.zeros(1_024), FS, segment_length=SEGMENT, overlap=0.0)
    assert result.hop == SEGMENT
    assert np.allclose(np.diff(result.times_s), SEGMENT / FS)


# --------------------------------------------------------------------------- #
# eksenler kaymaz
# --------------------------------------------------------------------------- #


def test_both_axes_are_strictly_increasing() -> None:
    result = stft(_tone(1.0, BIN_TONE_HZ, 4_000), FS, segment_length=SEGMENT, overlap=0.5)
    assert np.all(np.diff(result.frequencies_hz) > 0.0)
    assert np.all(np.diff(result.times_s) > 0.0)


@pytest.mark.parametrize("overlap", [0.0, 0.5, 0.75])
def test_a_steady_tone_keeps_the_same_row_at_every_overlap(overlap: float) -> None:
    result = stft(
        _tone(1.0, BIN_TONE_HZ, 4_000),
        FS,
        segment_length=SEGMENT,
        overlap=overlap,
        window=WindowKind.RECTANGULAR,
    )
    peaks = result.peak_frequencies_hz()
    assert np.allclose(peaks, BIN_TONE_HZ)


def test_the_row_index_matches_the_analytic_bin() -> None:
    result = stft(
        _tone(1.0, BIN_TONE_HZ, 4_000), FS, segment_length=SEGMENT, window=WindowKind.RECTANGULAR
    )
    expected_row = round(BIN_TONE_HZ / result.resolution_hz)
    assert expected_row == 64
    assert int(np.argmax(result.magnitudes[:, 0])) == expected_row


def _burst(total: int, start: int, length: int) -> Vec:
    """Yalnız `[start, start+length)` aralığında ton taşıyan sinyal."""
    signal = np.zeros(total, dtype=np.float64)
    signal[start : start + length] = _tone(1.0, BIN_TONE_HZ, total)[start : start + length]
    return signal


@pytest.mark.parametrize("overlap", [0.5, 0.75, 0.9])
def test_a_burst_lands_at_its_own_time_regardless_of_overlap(overlap: float) -> None:
    total, start, length = 4_000, 2_000, SEGMENT
    burst_centre_s = (start + length / 2.0) / FS

    result = stft(_burst(total, start, length), FS, segment_length=SEGMENT, overlap=overlap)
    energy = np.sum(result.magnitudes, axis=0)
    loudest = int(np.argmax(energy))

    # En güçlü sütunun merkezi, patlamanın merkezine yarım pencereden yakın.
    assert abs(result.times_s[loudest] - burst_centre_s) <= SEGMENT / 2.0 / FS


def test_a_burst_is_silent_far_from_its_own_time() -> None:
    total, start, length = 4_000, 2_000, SEGMENT
    result = stft(_burst(total, start, length), FS, segment_length=SEGMENT, overlap=0.5)
    energy = np.sum(result.magnitudes, axis=0)
    burst_centre_s = (start + length / 2.0) / FS

    far = np.abs(result.times_s - burst_centre_s) > 2.0 * SEGMENT / FS
    assert np.any(far)
    assert float(np.max(energy[far])) < 0.01 * float(np.max(energy))


def test_the_time_axis_does_not_depend_on_the_window() -> None:
    signal = _tone(1.0, BIN_TONE_HZ, 4_000)
    reference = stft(signal, FS, segment_length=SEGMENT, overlap=0.5, window=WindowKind.HANN)
    for window in WindowKind:
        other = stft(signal, FS, segment_length=SEGMENT, overlap=0.5, window=window)
        assert np.allclose(other.times_s, reference.times_s)
        assert np.allclose(other.frequencies_hz, reference.frequencies_hz)


def test_the_axes_lengths_match_the_matrix() -> None:
    result = stft(_tone(1.0, BIN_TONE_HZ, 4_000), FS, segment_length=SEGMENT, overlap=0.5)
    assert result.frequencies_hz.shape == (result.bin_count,)
    assert result.times_s.shape == (result.frame_count,)
    assert result.magnitudes.shape == (result.bin_count, result.frame_count)

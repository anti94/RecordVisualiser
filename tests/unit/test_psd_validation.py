"""PSD pencere, overlap ve birim sınır doğrulamaları — `F4-044`.

Kabul: geçersiz overlap reddedilir; güç/Hz ve dB dönüşümü doğrudur.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import (
    DEFAULT_DB_FLOOR,
    PsdError,
    power_to_db,
    segment_starts,
    segment_step,
    validate_overlap,
    welch_psd,
)
from sonar_analyzer.analysis.spectrum import amplitude_to_db
from sonar_analyzer.analysis.windows import WindowKind

Vec = NDArray[np.float64]

FS = 1_000.0
LENGTH = 1_000


def _tone(amp: float, freq_hz: float, count: int = LENGTH) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


# --------------------------------------------------------------------------- #
# overlap
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", [-0.01, -1.0, 1.0, 1.5, 10.0, math.nan, math.inf])
def test_invalid_overlap_is_rejected(bad: float) -> None:
    with pytest.raises(PsdError, match="örtüşme"):
        validate_overlap(bad)


@pytest.mark.parametrize("good", [0.0, 0.25, 0.5, 0.75, 0.99])
def test_valid_overlap_is_accepted(good: float) -> None:
    validate_overlap(good)


@pytest.mark.parametrize("bad", [-0.5, 1.0, 2.0])
def test_welch_rejects_an_invalid_overlap(bad: float) -> None:
    with pytest.raises(PsdError, match="örtüşme"):
        welch_psd(_tone(1.0, 50.0), FS, segment_length=256, overlap=bad)


def test_overlap_one_is_rejected_because_it_would_never_advance() -> None:
    with pytest.raises(PsdError):
        welch_psd(_tone(1.0, 50.0), FS, segment_length=256, overlap=1.0)


def test_more_overlap_yields_more_segments() -> None:
    counts = [
        welch_psd(_tone(1.0, 50.0), FS, segment_length=256, overlap=value).segment_count
        for value in (0.0, 0.5, 0.75)
    ]
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]


def test_zero_overlap_segments_do_not_share_samples() -> None:
    starts = segment_starts(LENGTH, 256, 0.0)
    assert segment_step(256, 0.0) == 256
    assert all(later - earlier >= 256 for earlier, later in zip(starts, starts[1:]))


def test_the_reported_overlap_is_the_requested_one() -> None:
    result = welch_psd(_tone(1.0, 50.0), FS, segment_length=256, overlap=0.25)
    assert result.overlap == 0.25


# --------------------------------------------------------------------------- #
# pencere
# --------------------------------------------------------------------------- #


def test_an_unknown_window_is_rejected_as_a_psd_error() -> None:
    with pytest.raises(PsdError, match="bilinmeyen pencere"):
        welch_psd(_tone(1.0, 50.0), FS, segment_length=256, window="gaussian")


@pytest.mark.parametrize("window", list(WindowKind))
def test_every_known_window_is_accepted_and_reported(window: WindowKind) -> None:
    result = welch_psd(_tone(1.0, 50.0), FS, segment_length=256, window=window)
    assert result.window_kind == window.value


def test_a_window_given_as_text_is_accepted() -> None:
    assert welch_psd(_tone(1.0, 50.0), FS, segment_length=256, window="blackman").window_kind == (
        "blackman"
    )


# --------------------------------------------------------------------------- #
# parça uzunluğu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", [0, -1, -256])
def test_a_nonpositive_segment_length_is_rejected(bad: int) -> None:
    with pytest.raises(PsdError, match="parça uzunluğu"):
        welch_psd(_tone(1.0, 50.0), FS, segment_length=bad)


def test_a_segment_longer_than_the_signal_is_rejected_not_truncated() -> None:
    with pytest.raises(PsdError, match="uzun olamaz"):
        welch_psd(np.zeros(100), FS, segment_length=101)


def test_a_segment_equal_to_the_signal_is_a_single_periodogram() -> None:
    result = welch_psd(_tone(1.0, 50.0), FS, segment_length=LENGTH, overlap=0.5)
    assert result.segment_count == 1


def test_a_single_sample_segment_gives_one_bin() -> None:
    result = welch_psd(np.array([2.0]), FS, segment_length=1, overlap=0.0)
    assert len(result) == 1
    assert result.frequencies_hz[0] == 0.0


def test_the_default_segment_length_never_exceeds_the_signal() -> None:
    short = welch_psd(_tone(1.0, 10.0, 100), FS)
    assert short.segment_length == 100
    long = welch_psd(_tone(1.0, 10.0, 4_096), FS)
    assert long.segment_length == 256


# --------------------------------------------------------------------------- #
# birim: güç / Hz
# --------------------------------------------------------------------------- #


def test_density_scales_quadratically_with_the_signal() -> None:
    base = welch_psd(_tone(1.0, 50.0), FS, segment_length=LENGTH, overlap=0.0)
    scaled = welch_psd(_tone(3.0, 50.0), FS, segment_length=LENGTH, overlap=0.0)
    assert abs(scaled.integrated_power - 9.0 * base.integrated_power) < 1e-9
    assert np.allclose(scaled.density, 9.0 * base.density, atol=1e-12)


def test_a_higher_sample_rate_halves_the_density_but_keeps_the_power() -> None:
    samples = _tone(2.0, 50.0)
    slow = welch_psd(samples, FS, segment_length=LENGTH, overlap=0.0)
    fast = welch_psd(samples, 2.0 * FS, segment_length=LENGTH, overlap=0.0)

    # df iki katına çıkar, yoğunluk yarıya iner -> entegre güç değişmez.
    assert abs(fast.resolution_hz - 2.0 * slow.resolution_hz) < 1e-12
    assert np.allclose(fast.density, slow.density / 2.0, atol=1e-15)
    assert abs(fast.integrated_power - slow.integrated_power) < 1e-9


def test_integrated_power_is_the_density_times_the_bin_width() -> None:
    result = welch_psd(_tone(1.5, 70.0), FS, segment_length=LENGTH, overlap=0.0)
    manual = float(np.sum(result.density)) * result.resolution_hz
    assert abs(result.integrated_power - manual) < 1e-15
    assert abs(result.integrated_power - 1.5**2 / 2.0) < 1e-9


def test_dc_and_nyquist_bins_are_not_doubled() -> None:
    # Sabit sinyal yalnız DC'yi doldurur; entegre güç c^2 olmalı.
    dc = welch_psd(np.full(LENGTH, 2.0), FS, segment_length=LENGTH, overlap=0.0)
    assert abs(dc.integrated_power - 4.0) < 1e-9

    # (-1)^n tam Nyquist'te genliği 1 olan ton -> gücü 1.
    alternating = np.power(-1.0, np.arange(LENGTH, dtype=np.float64))
    nyquist = welch_psd(
        alternating, FS, segment_length=LENGTH, overlap=0.0, window=WindowKind.RECTANGULAR
    )
    assert abs(nyquist.integrated_power - 1.0) < 1e-9


def test_a_zero_signal_has_zero_density_everywhere() -> None:
    result = welch_psd(np.zeros(LENGTH), FS, segment_length=LENGTH, overlap=0.0)
    assert np.array_equal(result.density, np.zeros(len(result)))
    assert result.integrated_power == 0.0


# --------------------------------------------------------------------------- #
# dB dönüşümü
# --------------------------------------------------------------------------- #


def test_power_db_is_half_of_amplitude_db_for_the_same_quantity() -> None:
    amplitudes = np.array([0.1, 0.5, 1.0, 4.0])
    assert np.allclose(power_to_db(amplitudes**2), amplitude_to_db(amplitudes))


def test_doubling_the_power_adds_three_db() -> None:
    db = power_to_db(np.array([1.0, 2.0]))
    assert abs((db[1] - db[0]) - 10.0 * math.log10(2.0)) < 1e-12
    assert abs((db[1] - db[0]) - 3.0103) < 1e-4


def test_power_db_is_monotonic() -> None:
    db = power_to_db(np.array([0.0, 1e-9, 1e-3, 1.0, 1e3]))
    assert np.all(np.diff(db) > 0.0)


def test_the_default_power_floor_is_minus_200_db() -> None:
    assert DEFAULT_DB_FLOOR == -200.0
    assert power_to_db(np.array([0.0]))[0] == -200.0


def test_a_power_reference_shifts_the_scale_by_its_own_db() -> None:
    density = np.array([0.25, 1.0, 16.0])
    plain = power_to_db(density)
    shifted = power_to_db(density, reference=4.0)
    assert np.allclose(shifted, plain - 10.0 * math.log10(4.0))


def test_power_db_preserves_shape_and_handles_an_empty_array() -> None:
    assert power_to_db(np.zeros(5)).shape == (5,)
    assert power_to_db(np.empty(0, dtype=np.float64)).shape == (0,)


def test_a_psd_in_db_peaks_at_the_tone() -> None:
    result = welch_psd(_tone(1.0, 90.0), FS, segment_length=LENGTH, overlap=0.0)
    db = power_to_db(result.density)
    assert int(np.argmax(db)) == result.peak_index
    assert abs(result.frequencies_hz[int(np.argmax(db))] - 90.0) < 1e-9

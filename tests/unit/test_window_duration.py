"""Pencere süresi ↔ örnek sayısı dönüşümü — `F4-022`.

Kabul: pencere süresi sample rate üzerinden doğru örnek sayısına dönüşür.
"""

from __future__ import annotations

import math

import pytest

from sonar_analyzer.processing.windowing import (
    WindowingError,
    duration_for_samples,
    samples_for_duration,
)


def test_one_second_at_8hz_is_eight_samples() -> None:
    assert samples_for_duration(1.0, 8.0) == 8


def test_ten_milliseconds_at_48khz_is_480_samples() -> None:
    assert samples_for_duration(0.01, 48_000.0) == 480


def test_rounds_to_the_nearest_sample() -> None:
    # 0.18 s * 8 Hz = 1.44 -> 1 ;  0.19 s * 8 Hz = 1.52 -> 2
    assert samples_for_duration(0.18, 8.0) == 1
    assert samples_for_duration(0.19, 8.0) == 2


def test_sub_sample_duration_clamps_to_the_minimum() -> None:
    assert samples_for_duration(1e-6, 8.0) == 1
    assert samples_for_duration(0.001, 8.0, minimum=3) == 3


def test_no_upper_clamp_here() -> None:
    # Üst sınır ProcessingStep / validate_window işidir.
    assert samples_for_duration(1_000.0, 48_000.0) == 48_000_000


def test_rejects_nonpositive_duration() -> None:
    for bad in (0.0, -1.0):
        with pytest.raises(WindowingError, match="süre"):
            samples_for_duration(bad, 48_000.0)


def test_rejects_nonpositive_or_nonfinite_sample_rate() -> None:
    with pytest.raises(WindowingError, match="sample rate"):
        samples_for_duration(0.01, 0.0)
    with pytest.raises(WindowingError, match="sample rate"):
        samples_for_duration(0.01, -48_000.0)
    with pytest.raises(WindowingError, match="süre"):
        samples_for_duration(math.inf, 48_000.0)


def test_duration_for_samples_is_the_inverse() -> None:
    assert duration_for_samples(480, 48_000.0) == 0.01
    assert duration_for_samples(8, 8.0) == 1.0


def test_round_trip_for_exact_windows() -> None:
    for window, rate in ((480, 48_000.0), (8, 8.0), (1024, 44_100.0), (3, 10_000.0)):
        seconds = duration_for_samples(window, rate)
        assert samples_for_duration(seconds, rate) == window


def test_duration_for_samples_rejects_bad_rate() -> None:
    with pytest.raises(WindowingError, match="sample rate"):
        duration_for_samples(480, 0.0)

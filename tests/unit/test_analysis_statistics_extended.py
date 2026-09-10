"""Median, RMS, std, peak-to-peak — `F3-038`.

Kabul: referans dizi sonuçlarıyla eşleşir; boş aralık tanımlı gösterilir.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.statistics import summarize


def _arr(values: list[float]) -> NDArray[np.float64]:
    return np.array(values, dtype=np.float64)


def test_reference_short_array_matches_hand_computed_values() -> None:
    result = summarize(_arr([1.0, 2.0, 3.0, 4.0]))

    assert result.median == 2.5
    # rms = sqrt((1 + 4 + 9 + 16) / 4) = sqrt(7.5)
    assert abs(result.rms - math.sqrt(7.5)) < 1e-12
    # populasyon std = sqrt(((1.5)^2 + (0.5)^2 + (0.5)^2 + (1.5)^2) / 4) = sqrt(1.25)
    assert abs(result.std - math.sqrt(1.25)) < 1e-12
    assert result.peak_to_peak == 3.0


def test_symmetric_pair() -> None:
    result = summarize(_arr([-3.0, 3.0]))

    assert result.median == 0.0
    assert result.rms == 3.0
    assert result.std == 3.0
    assert result.peak_to_peak == 6.0


def test_odd_length_median_is_the_middle_value() -> None:
    result = summarize(_arr([5.0, 1.0, 3.0]))  # sirali: 1, 3, 5

    assert result.median == 3.0
    assert result.peak_to_peak == 4.0


def test_constant_array_has_zero_std_and_ptp() -> None:
    result = summarize(_arr([9.0] * 5))

    assert result.std == 0.0
    assert result.peak_to_peak == 0.0
    assert result.rms == 9.0
    assert result.median == 9.0


def test_rms_differs_from_mean_when_signal_is_centred() -> None:
    result = summarize(_arr([-2.0, -1.0, 1.0, 2.0]))

    assert result.mean == 0.0
    assert abs(result.rms - math.sqrt(2.5)) < 1e-12


def test_std_is_population_not_sample() -> None:
    data = _arr([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    result = summarize(data)

    assert abs(result.std - float(np.std(data))) < 1e-12
    # numune (ddof=1) std'den farkli olmali
    assert abs(result.std - float(np.std(data, ddof=1))) > 1e-6


def test_empty_extended_fields_are_nan() -> None:
    result = summarize(_arr([]))

    assert math.isnan(result.median)
    assert math.isnan(result.rms)
    assert math.isnan(result.std)
    assert math.isnan(result.peak_to_peak)


def test_single_sample_extended_fields() -> None:
    result = summarize(_arr([4.0]))

    assert result.median == 4.0
    assert result.rms == 4.0
    assert result.std == 0.0
    assert result.peak_to_peak == 0.0

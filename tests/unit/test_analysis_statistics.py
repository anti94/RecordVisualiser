"""Örnek dizisi temel istatistikleri — `F3-037`.

Kabul: bilinen kısa dizi beklenen istatistikleri üretir.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.statistics import SampleStatistics, summarize


def _arr(values: list[float]) -> NDArray[np.float64]:
    return np.array(values, dtype=np.float64)


def test_known_short_array_produces_expected_stats() -> None:
    result = summarize(_arr([1.0, 2.0, 3.0, 4.0]))

    assert result == SampleStatistics(count=4, minimum=1.0, maximum=4.0, mean=2.5)


def test_negative_and_positive_values() -> None:
    result = summarize(_arr([-2.0, 0.0, 2.0]))

    assert result.count == 3
    assert result.minimum == -2.0
    assert result.maximum == 2.0
    assert result.mean == 0.0


def test_single_element_array() -> None:
    result = summarize(_arr([5.0]))

    assert result == SampleStatistics(count=1, minimum=5.0, maximum=5.0, mean=5.0)


def test_constant_array_has_zero_spread() -> None:
    result = summarize(_arr([7.0] * 6))

    assert result.count == 6
    assert result.minimum == result.maximum == result.mean == 7.0


def test_mean_of_a_longer_ramp() -> None:
    result = summarize(_arr([float(n) for n in range(101)]))  # 0..100

    assert result.count == 101
    assert result.minimum == 0.0
    assert result.maximum == 100.0
    assert result.mean == 50.0


def test_empty_array_is_defined_not_an_error() -> None:
    result = summarize(_arr([]))

    assert result.count == 0
    assert result.is_empty
    assert math.isnan(result.minimum)
    assert math.isnan(result.maximum)
    assert math.isnan(result.mean)


def test_summarize_accepts_a_plain_list_like_input() -> None:
    result = summarize(_arr([10.0, 20.0, 30.0]))

    assert result.mean == 20.0
    assert result.count == 3


def test_non_empty_result_is_not_flagged_empty() -> None:
    assert not summarize(_arr([1.0])).is_empty


def test_float_mean_is_exact_for_representable_values() -> None:
    result = summarize(_arr([0.25, 0.75]))

    assert result.mean == 0.5

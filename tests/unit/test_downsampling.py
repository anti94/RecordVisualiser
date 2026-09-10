"""Min/max azaltımı dar darbeleri ve orijinal zamanları korur."""

import numpy as np
import pytest

from sonar_analyzer.analysis.downsampling import downsample_chunk, envelope_indices
from sonar_analyzer.domain.data_chunk import DataChunk, Quality


@pytest.mark.parametrize("budget", [4, 20, 201])
def test_single_sample_impulses_survive_in_source_order(budget: int) -> None:
    values = np.zeros(10_000)
    values[233] = 123
    values[9876] = -456
    indices = envelope_indices(values, budget)
    assert 233 in indices and 9876 in indices
    assert np.all(np.diff(indices) > 0)
    assert len(indices) <= budget


def test_each_bucket_matches_independent_extrema() -> None:
    values = np.random.default_rng(123).normal(size=1003)
    indices = envelope_indices(values, 100)
    for bucket in range(50):
        start, stop = bucket * 1003 // 50, (bucket + 1) * 1003 // 50
        chosen = indices[(indices >= start) & (indices < stop)]
        assert values[chosen].min() == values[start:stop].min()
        assert values[chosen].max() == values[start:stop].max()


def test_flat_trace_keeps_time_extent() -> None:
    indices = envelope_indices(np.ones(1000), 20)
    assert indices[0] == 0 and indices[-1] == 999
    assert len(indices) == 20


def test_nan_extrema_quality_and_irregular_timestamps_stay_aligned() -> None:
    values = np.array([0.0, 1.0, np.nan, -9.0, 8.0, 0.0, 0.0, 0.0])
    times = np.array([1, 4, 8, 10, 11, 15, 18, 20], dtype=np.int64) + 1_789_000_000_000_000_000
    flags = np.zeros(8, dtype=np.uint8)
    flags[2] = Quality.CRC_ERROR
    chunk = DataChunk("a", times, values, flags)
    result = downsample_chunk(chunk, 3)
    assert np.array_equal(result.timestamps_ns, times[[2, 3, 4]])
    assert np.array_equal(result.values, values[[2, 3, 4]], equal_nan=True)
    assert result.quality is not None
    assert np.array_equal(result.quality, flags[[2, 3, 4]])
    assert np.isnan(chunk.values[2]) and len(chunk) == 8


@pytest.mark.parametrize("budget", [1, 2, 3, 7, 100])
def test_small_and_nonfinite_inputs_respect_budget(budget: int) -> None:
    for values in (np.array([]), np.full(20, np.nan), np.array([1.0, np.nan, -3.0, 9.0])):
        indices = envelope_indices(values, budget)
        assert len(indices) <= budget
        assert np.all(np.diff(indices) > 0)


@pytest.mark.parametrize("budget", [0, -1, True, 1.5])
def test_invalid_budgets_fail(budget: int) -> None:
    with pytest.raises(ValueError, match="max_points"):
        envelope_indices(np.ones(100), budget)

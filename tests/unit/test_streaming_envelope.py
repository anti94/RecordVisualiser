"""Akış özeti ham zaman kovası referansıyla, farklı parça sınırlarında eşleşir."""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.analysis.downsampling import downsample_chunk, extrema_indices
from sonar_analyzer.analysis.streaming_envelope import streaming_envelope
from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.time_range import TimeRange


@pytest.mark.parametrize("budget", [1, 2, 3, 17, 120, 999])
@pytest.mark.parametrize("piece_size", [1, 37, 4096])
def test_stream_matches_raw_time_bin_reference(budget: int, piece_size: int) -> None:
    times = 1_788_901_200_000_000_000 + np.arange(513, dtype=np.int64) * 20_833
    values = np.random.default_rng(95).integers(-10, 10, len(times)).astype(np.float64)
    values[[0, 37, 255, 256, 511]] = [np.nan, 1e6, -1e6, np.inf, np.nan]
    flags = np.zeros(len(times), dtype=np.uint8)
    flags[~np.isfinite(values)] = int(Quality.CRC_ERROR)
    span = TimeRange(int(times[7]), int(times[-9]))
    count = max(1, budget // 3)
    selected: list[int] = []
    for bucket in range(count):
        start = span.start_ns + (span.end_ns - span.start_ns) * bucket // count
        stop = span.start_ns + (span.end_ns - span.start_ns) * (bucket + 1) // count
        indices = np.flatnonzero((times >= start) & (times < stop))
        selected.extend(indices[extrema_indices(values[indices])].tolist())
    keep = np.array(selected, dtype=np.int64)
    expected = downsample_chunk(DataChunk("0", times[keep], values[keep], flags[keep]), budget)
    chunks = [
        DataChunk(
            "0", times[i : i + piece_size], values[i : i + piece_size], flags[i : i + piece_size]
        )
        for i in range(0, len(times), piece_size)
    ]
    actual = streaming_envelope(chunks, "0", span, budget)
    np.testing.assert_array_equal(actual.timestamps_ns, expected.timestamps_ns)
    np.testing.assert_array_equal(actual.values, expected.values)
    assert actual.quality is not None and expected.quality is not None
    np.testing.assert_array_equal(actual.quality, expected.quality)


def test_overlapping_chunks_sort_ties_and_keep_nan_flags() -> None:
    first = DataChunk(
        "0",
        np.array([0, 10, 20]),
        np.array([5.0, 5.0, np.nan]),
        np.array([0, 0, 2], dtype=np.uint8),
    )
    second = DataChunk("0", np.array([5, 10, 15]), np.array([5.0, 5.0, -10.0]))
    result = streaming_envelope([first, second], "0", TimeRange(0, 30), 3)
    np.testing.assert_array_equal(result.timestamps_ns, [10, 15, 20])
    np.testing.assert_array_equal(result.values, [5.0, -10.0, np.nan])
    assert result.quality is not None
    np.testing.assert_array_equal(result.quality, [0, 0, 2])


def test_empty_stream_and_invalid_budget() -> None:
    assert len(streaming_envelope([], "0", TimeRange(0, 10), 10)) == 0
    assert len(streaming_envelope([], "0", TimeRange(0, 0), 10)) == 0
    with pytest.raises(ValueError):
        streaming_envelope([], "0", TimeRange(0, 0), 0)

"""Viewport sınırları, seviye seçimi ve tekrar sorgu davranışı — F4-058."""

import numpy as np

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.display_query import DisplayQuery, ViewportSummary


def test_zoom_selects_finer_levels_and_small_windows_are_exact() -> None:
    values = np.zeros(10_000)
    values[137] = 100
    values[8171] = -100
    chunk = DataChunk("a", np.arange(10_000, dtype=np.int64), values)
    summary = ViewportSummary(chunk)
    coarse = summary.choose_level(0, 10_000, 60)
    fine = summary.choose_level(0, 1_000, 60)
    assert coarse is not None and fine is not None
    assert coarse.block_size > fine.block_size
    result = summary.query(TimeRange(0, 10_000), 60)
    assert result.values.max() == 100 and result.values.min() == -100
    assert len(result) <= 60
    exact = summary.query(TimeRange(120, 160), 60)
    assert np.array_equal(exact.values, values[120:160])
    assert np.array_equal(exact.timestamps_ns, np.arange(120, 160))


def test_partial_blocks_do_not_leak_outside_peaks() -> None:
    values = np.ones(2000)
    values[10], values[11], values[888], values[889] = 1000, 20, -20, -1000
    summary = ViewportSummary(DataChunk("a", np.arange(2000, dtype=np.int64), values))
    result = summary.query(TimeRange(11, 889), 30)
    assert 0 < len(result) <= 30
    assert result.values.max() == 20 and result.values.min() == -20
    assert np.all(result.timestamps_ns >= 11) and np.all(result.timestamps_ns < 889)
    assert result.is_monotonic


def test_contained_display_queries_reuse_summary_but_analysis_reads_full_data() -> None:
    calls: list[TimeRange] = []

    def read(channel_id: str, span: TimeRange) -> DataChunk:
        calls.append(span)
        times = np.arange(span.start_ns, span.end_ns, dtype=np.int64)
        return DataChunk(channel_id, times, np.sin(times))

    query = DisplayQuery(read)
    query.query("a", TimeRange(0, 2000), 60)
    query.query("a", TimeRange(100, 1000), 100)
    assert len(calls) == 1
    full = query.query("a", TimeRange(100, 1000), None)
    assert len(calls) == 2 and len(full) == 900
    query.clear()
    query.query("a", TimeRange(100, 1000), 100)
    assert len(calls) == 3

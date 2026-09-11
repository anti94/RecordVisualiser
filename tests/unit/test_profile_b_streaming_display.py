"""Tam kayıt çizimi ham diziyi biriktirmez; analiz ve zoom ayrıntıları korunur."""

from __future__ import annotations

import tracemalloc
from unittest.mock import patch

import numpy as np
import pytest
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b_indexed_query import AcousticQuery
from sonar_analyzer.repository.display_query import DisplayQuery


@pytest.mark.parametrize("records", [64, 512])
def test_full_display_has_bounded_peak_allocation(records: int) -> None:
    reader = AcousticQuery(build_acoustic_fixture(records))
    span = reader.span(0)
    assert span is not None
    with patch.object(reader, "query", side_effect=AssertionError("full decode forbidden")):
        tracemalloc.start()
        try:
            result = reader.query_display(0, span, 2000)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
    assert result is not None and 0 < len(result) <= 2000
    assert result.is_monotonic
    assert reader.last_records_read == records
    assert peak < 2_000_000


def test_crc_error_survives_full_display_reduction() -> None:
    data = bytearray(build_acoustic_fixture(64))
    original = AcousticQuery(data)
    record = original.index.records[31]
    block = record.sensor_block(0)
    assert block is not None
    data[block.payload_offset + 3] ^= 1
    reader = AcousticQuery(data)
    span = reader.span(0)
    assert span is not None
    result = reader.query_display(0, span, 300)
    assert result is not None and result.quality is not None
    invalid = np.isnan(result.values)
    assert invalid.any()
    assert np.all(result.quality[invalid] == int(Quality.CRC_ERROR))
    assert np.all(result.quality[~invalid] == 0)


def test_bounded_cache_is_exact_and_zoom_and_analysis_read_full_source() -> None:
    reader = AcousticQuery(build_acoustic_fixture(64))
    span = reader.span(0)
    assert span is not None
    with (
        patch.object(reader, "query", wraps=reader.query) as raw,
        patch.object(reader, "query_display", wraps=reader.query_display) as bounded,
    ):
        display = DisplayQuery(
            lambda key, window: reader.query(int(key), window),
            read_large=lambda key, window, budget: reader.query_display(int(key), window, budget),
            max_bytes=1_000_000,
        )
        first = display.query("0", span, 100)
        original = first.values.copy()
        first.values[:] = 0
        np.testing.assert_array_equal(display.query("0", span, 100).values, original)
        assert raw.call_count == 0 and bounded.call_count == 1
        display.query("0", span, 200)
        assert bounded.call_count == 2
        narrow = TimeRange(span.start_ns + 50_000, span.start_ns + 100_000)
        zoom = display.query("0", narrow, 100)
        expected = reader.query(0, narrow)
        np.testing.assert_array_equal(zoom.timestamps_ns, expected.timestamps_ns)
        np.testing.assert_array_equal(zoom.values, expected.values)
        count = raw.call_count
        analysis = display.query("0", span, None)
        assert raw.call_count == count + 1
        assert len(analysis) == 64 * 6000
        assert display.cache_stats().used_bytes <= 1_000_000

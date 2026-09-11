"""Dar sorgu tüm örnekleri çözmez; sayısal çıktı tam referansla eşleşir."""

from __future__ import annotations

import struct
import tracemalloc
from unittest.mock import patch

import numpy as np
import pytest
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders import profile_b_indexed_query
from sonar_analyzer.io.decoders.profile_b import ProfileBFormatError, channel_samples
from sonar_analyzer.io.decoders.profile_b_indexed_query import AcousticQuery
from sonar_analyzer.io.decoders.profile_b_timing import channel_sample_times_ns
from sonar_analyzer.io.profile_b_format import RECORD_HEADER_SIZE, RECORD_PERIOD_NS


@pytest.mark.parametrize("rate", [48000, 44100, 8000])
def test_random_half_open_windows_match_full_resolution_reference(rate: int) -> None:
    data = build_acoustic_fixture(8)
    reader = AcousticQuery(data, rate)
    random = np.random.default_rng(92)
    for channel in range(4):
        times = channel_sample_times_ns(data, channel, rate)
        values = channel_samples(data, channel).astype(np.float64)
        order = np.argsort(times, kind="stable")
        times, values = times[order], values[order]
        for left, width in random.integers(0, 1_000_000_000, size=(12, 2)):
            start = int(times[0]) + int(left)
            span = TimeRange(start, start + int(width))
            expected = (times >= span.start_ns) & (times < span.end_ns)
            result = reader.query(channel, span)
            assert np.array_equal(result.timestamps_ns, times[expected])
            assert np.array_equal(result.values, values[expected])
            assert result.quality is None


@pytest.mark.parametrize("records", [8, 512])
def test_only_two_overlapping_records_are_read_regardless_of_source_size(records: int) -> None:
    data = build_acoustic_fixture(records)
    reader = AcousticQuery(data)
    start = reader.index.header.t0_utc_ns + 2 * RECORD_PERIOD_NS + 40_000_000
    with (
        patch.object(profile_b_indexed_query, "crc32", wraps=profile_b_indexed_query.crc32) as crc,
        patch.object(np, "frombuffer", wraps=np.frombuffer) as read,
    ):
        tracemalloc.start()
        try:
            result = reader.query(0, TimeRange(start, start + RECORD_PERIOD_NS))
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert len(result) == 6000
        assert reader.last_records_read == 2
        assert read.call_count == crc.call_count == 2
        low = reader.index.records[2].byte_offset
        high = reader.index.records[4].byte_offset
        assert all(low <= call.kwargs["offset"] < high for call in read.call_args_list)
        assert peak < 1_000_000


def test_empty_and_missing_channel_queries_do_not_touch_payload() -> None:
    reader = AcousticQuery(build_acoustic_fixture(8))
    span = reader.span(0)
    assert span is not None
    for channel, window in (
        (0, TimeRange(span.start_ns, span.start_ns)),
        (0, TimeRange(0, 100)),
        (0, TimeRange(span.end_ns, span.end_ns + 100)),
        (999, span),
    ):
        assert len(reader.query(channel, window)) == 0
        assert reader.last_records_read == 0


def test_out_of_order_and_overlapping_records_are_sorted_without_losing_samples() -> None:
    data = bytearray(build_acoustic_fixture(4))
    original = AcousticQuery(data)
    for entry, time_ns in zip(original.index.records, (250_000_000, 0, 0, 125_000_000)):
        struct.pack_into("<q", data, entry.byte_offset + 24, time_ns)
    reader = AcousticQuery(data)
    times = channel_sample_times_ns(data, 0)
    values = channel_samples(data, 0).astype(np.float64)
    order = np.argsort(times, kind="stable")
    window = TimeRange(int(times.min()) + 1, int(times.max()))
    selected = (times[order] >= window.start_ns) & (times[order] < window.end_ns)
    result = reader.query(0, window)
    assert np.array_equal(result.timestamps_ns, times[order][selected])
    assert np.array_equal(result.values, values[order][selected])


def test_crc_error_marks_only_the_affected_record_and_preserves_timestamps() -> None:
    data = bytearray(build_acoustic_fixture(4))
    good = AcousticQuery(data)
    span = good.span(0)
    assert span is not None
    before = good.query(0, span)
    record = good.index.records[1]
    data[record.byte_offset + RECORD_HEADER_SIZE + 20] ^= 1
    damaged = AcousticQuery(data)
    after = damaged.query(0, span)
    assert np.array_equal(after.timestamps_ns, before.timestamps_ns)
    assert np.isnan(after.values[6000:12000]).all()
    assert np.array_equal(after.values[:6000], before.values[:6000])
    assert np.array_equal(after.values[12000:], before.values[12000:])
    assert after.quality is not None
    assert np.all(after.quality[6000:12000] == int(Quality.CRC_ERROR))
    assert np.all(after.quality[:6000] == 0)


def test_bad_file_header_crc_is_rejected_before_queries() -> None:
    data = bytearray(build_acoustic_fixture(2))
    data[100] ^= 1
    with pytest.raises(ProfileBFormatError, match="FileHeader CRC"):
        AcousticQuery(data)

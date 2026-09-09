"""125 ms kayıt zamanı → kanonik ns dönüşümü — `F2-007`.

Kabul: ilk üç kayıt 0, 125 ve 250 ms üretir; UTC başlangıcı doğru eklenir.
"""

from __future__ import annotations

from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture

from sonar_analyzer.io.decoders.profile_a import iter_records
from sonar_analyzer.io.decoders.timing import (
    elapsed_us_for_sequence,
    record_timestamp_ns,
)
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

SECOND_NS = 1_000_000_000


def test_first_three_records_produce_0_125_250_ms() -> None:
    """Kabul kriteri birebir: ilk üç kayıt 0, 125, 250 ms üretir."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))[:3]

    timestamps = [record_timestamp_ns(header, r) for r in records]
    elapsed_from_start = [t - START_TIME_UTC_NS for t in timestamps]

    assert elapsed_from_start == [0, 125_000_000, 250_000_000]


def test_utc_start_is_correctly_added() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    first_record = next(iter_records(buffer))

    assert record_timestamp_ns(header, first_record) == START_TIME_UTC_NS


def test_all_eight_records_advance_by_exactly_125ms() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    timestamps = [record_timestamp_ns(header, r) for r in iter_records(buffer)]

    diffs = [b - a for a, b in zip(timestamps, timestamps[1:])]
    assert diffs == [125_000_000] * 7


def test_last_record_is_at_875ms() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))

    last_ts = record_timestamp_ns(header, records[-1])
    assert last_ts - START_TIME_UTC_NS == 875_000_000


def test_timestamp_is_int64_safe_range() -> None:
    """Sonuç Python int'tir; int64 sınırları içinde kalmalı (ADR-003)."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    for record in iter_records(buffer):
        ts = record_timestamp_ns(header, record)
        assert -(2**63) <= ts < 2**63


def test_elapsed_us_for_sequence_matches_nominal_grid() -> None:
    period_us = 125_000
    assert elapsed_us_for_sequence(0, period_us) == 0
    assert elapsed_us_for_sequence(1, period_us) == 125_000
    assert elapsed_us_for_sequence(8, period_us) == 1_000_000


def test_elapsed_us_matches_actual_record_field_in_gapless_file() -> None:
    """Kayıpsız dosyada nominal ızgara ile gerçek `elapsed_us` aynı olmalı."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    for record in iter_records(buffer):
        expected = elapsed_us_for_sequence(record.sequence_no, header.period_us)
        assert record.elapsed_us == expected


def test_no_floating_point_is_used_for_the_conversion() -> None:
    """Tamsayı aritmetiği: sonuç her zaman int, float değil (ulp kaybı olmaz)."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    record = next(iter_records(buffer))
    assert isinstance(record_timestamp_ns(header, record), int)

"""Kayıt offseti ve zaman indeksini oluşturma — `F2-028`.

Kabul: indeks konumları tam kayıt sınırlarına işaret eder.
"""

from __future__ import annotations

from tests.golden_bytes import (
    START_TIME_UTC_NS,
    build_duplicate_sequence_fixture,
    build_gap_fixture,
    build_valid_fixture,
)

from sonar_analyzer.io.decoders.profile_a import decode_record_at_index
from sonar_analyzer.io.index.record_index import RecordIndexEntry, build_record_index
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

PERIOD_NS = 125_000_000
HEADER_SIZE = 32
RECORD_SIZE = 64


def test_index_has_one_entry_per_physical_record() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)

    entries = build_record_index(buffer, header)

    assert len(entries) == 8


def test_index_positions_point_exactly_to_record_boundaries() -> None:
    """Kabul kriteri birebir: indeks konumları tam kayıt sınırlarına işaret eder."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)

    entries = build_record_index(buffer, header)

    for index, entry in enumerate(entries):
        expected_offset = HEADER_SIZE + index * RECORD_SIZE
        assert entry.byte_offset == expected_offset
        assert (entry.byte_offset - header.header_size) % header.record_size == 0


def test_index_offsets_round_trip_to_the_same_record() -> None:
    """Bir indeks girdisinin offsetinden kaydı yeniden çözmek aynı sequence_no'yu verir."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    entries = build_record_index(buffer, header)

    for physical_index, entry in enumerate(entries):
        record = decode_record_at_index(buffer, physical_index)
        assert record.sequence_no == entry.sequence_no


def test_index_timestamps_match_the_documented_formula() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    entries = build_record_index(buffer, header)

    for index, entry in enumerate(entries):
        assert entry.timestamp_ns == START_TIME_UTC_NS + index * PERIOD_NS


def test_index_offsets_strictly_increase_by_record_size() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    entries = build_record_index(buffer, header)

    offsets = [entry.byte_offset for entry in entries]
    deltas = [b - a for a, b in zip(offsets, offsets[1:])]
    assert all(delta == RECORD_SIZE for delta in deltas)


def test_index_preserves_physical_order_even_with_gap() -> None:
    """Sıra fiziksel sıradır; sequence_no boşluklu olsa da offsetler hâlâ tam sınırdadır."""
    buffer = build_gap_fixture()
    header = read_file_header_v1(buffer)

    entries = build_record_index(buffer, header)

    assert len(entries) == 8
    assert [e.sequence_no for e in entries] == [0, 1, 2, 3, 4, 6, 7, 8]
    for index, entry in enumerate(entries):
        assert entry.byte_offset == HEADER_SIZE + index * RECORD_SIZE


def test_index_preserves_physical_order_even_with_duplicate_sequence() -> None:
    """Tekrarlı sequence_no'lar bile ayrı, fiziksel-sıradaki girdiler olarak kalır."""
    buffer = build_duplicate_sequence_fixture()
    header = read_file_header_v1(buffer)

    entries = build_record_index(buffer, header)

    assert len(entries) == 8
    assert entries[2].sequence_no == 2
    assert entries[3].sequence_no == 2  # tekrar, ama ayri fiziksel konum
    assert entries[2].byte_offset != entries[3].byte_offset


def test_empty_index_for_header_only_buffer() -> None:
    buffer = build_valid_fixture(record_count=0)
    header = read_file_header_v1(buffer)
    assert build_record_index(buffer, header) == []


def test_record_index_entry_is_immutable() -> None:
    import dataclasses

    import pytest

    entry = RecordIndexEntry(sequence_no=0, byte_offset=32, timestamp_ns=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.byte_offset = 64  # type: ignore[misc]

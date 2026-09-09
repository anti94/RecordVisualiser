"""Kayıtlı BIT/TX ve parser olay sorguları — F2-035."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from tests.golden_bytes import (
    START_TIME_UTC_NS,
    build_gap_fixture,
    build_name_mismatch_fixture,
    build_unknown_packet_fixture,
    build_valid_fixture,
    build_valid_v2_fixture,
)

from sonar_analyzer.domain.event import BitState, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository


def open_bytes(tmp_path: Path, data: bytes) -> FileRecordingRepository:
    path = tmp_path / "record.bin"
    path.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(path)
    return repository


@pytest.mark.parametrize("version", [1, 2])
def test_bit_tx_reference_events_and_protocol(tmp_path: Path, version: int) -> None:
    repository = open_bytes(
        tmp_path, build_valid_fixture() if version == 1 else build_valid_v2_fixture()
    )
    assert isinstance(repository, RecordingRepository)
    span = repository.metadata().time_range
    events = repository.events(span)
    assert [
        (item.code, (item.timestamp_ns - START_TIME_UTC_NS) // 1_000_000) for item in events
    ] == [
        ("TX_START", 250),
        ("BIT_FAIL", 500),
        ("BIT_PASS", 625),
        ("TX_STOP", 750),
    ]
    assert len(repository.bit_results(span)) == 24
    assert sum(item.state is BitState.FAIL for item in repository.bit_results(span)) == 1
    (interval,) = repository.transmissions(span)
    assert interval.duration_seconds == 0.5
    assert interval.closed


def test_combined_event_filters_and_exclusive_end(tmp_path: Path) -> None:
    repository = open_bytes(tmp_path, build_valid_fixture())
    span = repository.metadata().time_range
    filters = EventFilter(
        sources=["BIT"], categories=["BIT"], min_severity=Severity.ERROR, text="thermal"
    )
    events = repository.events(span, filters)
    assert len(events) == 1
    assert events[0].code == "BIT_FAIL"
    assert repository.events(TimeRange(START_TIME_UTC_NS, events[0].timestamp_ns), filters) == ()
    assert repository.transmissions(TimeRange(events[0].timestamp_ns, events[0].timestamp_ns)) == ()


def test_crc_error_does_not_create_false_bit_failure(tmp_path: Path) -> None:
    data = bytearray(build_valid_v2_fixture())
    data[36 + 3 * 68 + 56] ^= 255
    repository = open_bytes(tmp_path, bytes(data))
    bad = TimeRange(START_TIME_UTC_NS + 375_000_000, START_TIME_UTC_NS + 500_000_000)
    events = repository.events(bad)
    assert any(item.code == "CRC_ERROR" and item.source_offset == 36 + 3 * 68 for item in events)
    assert not any(item.code == "BIT_FAIL" for item in events)
    assert all(item.state is BitState.UNKNOWN for item in repository.bit_results(bad))
    intervals = repository.transmissions(repository.metadata().time_range)
    assert len(intervals) == 2
    assert not intervals[0].closed


@pytest.mark.parametrize("case", ["gap", "name", "unknown", "truncated"])
def test_parser_diagnostics_keep_offsets(tmp_path: Path, case: str) -> None:
    data, code, offset = {
        "gap": (build_gap_fixture(), "GAP", 352),
        "name": (build_name_mismatch_fixture(), "NAME_MISMATCH", 160),
        "unknown": (build_unknown_packet_fixture(), "UNKNOWN_PACKET", 224),
        "truncated": (build_valid_fixture()[:-3], "TRUNCATED_TAIL", 480),
    }[case]
    repository = open_bytes(tmp_path, data)
    events = repository.events(TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + 2_000_000_000))
    assert any(item.code == code and item.source_offset == offset for item in events)


def test_events_require_open_and_are_cleared_on_reopen(tmp_path: Path) -> None:
    repository = open_bytes(tmp_path, build_valid_fixture())
    assert repository.events(repository.metadata().time_range)
    path = tmp_path / "empty.bin"
    path.write_bytes(build_valid_fixture(0))
    repository.open(path)
    assert repository.events(TimeRange(0, START_TIME_UTC_NS + 1_000_000_000)) == ()
    repository.close()
    with pytest.raises(RuntimeError):
        repository.events(TimeRange(0, 1))


def test_fault_ending_transmission_is_not_reported_as_idle(tmp_path: Path) -> None:
    data = bytearray(build_valid_fixture())
    struct.pack_into("<I", data, 32 + 6 * 64 + 60, 2)
    repository = open_bytes(tmp_path, bytes(data))
    stopped = [
        item
        for item in repository.events(repository.metadata().time_range)
        if item.code == "TX_STOP"
    ]
    assert len(stopped) == 1
    assert stopped[0].state == "fault"

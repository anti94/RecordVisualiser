"""Decoded olaydan gerçek kaynak byte konumuna dönüş — F2-037."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.golden_bytes import build_valid_fixture, build_valid_v2_fixture

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.repository.file_repository import FileRecordingRepository


@pytest.mark.parametrize("version,header_size,record_size", [(1, 32, 64), (2, 36, 68)])
def test_event_offset_matches_source_bytes(
    tmp_path: Path,
    version: int,
    header_size: int,
    record_size: int,
) -> None:
    data = build_valid_fixture() if version == 1 else build_valid_v2_fixture()
    path = tmp_path / "record.bin"
    path.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(path)
    event = next(
        item
        for item in repository.events(repository.metadata().time_range)
        if item.code == "BIT_FAIL"
    )
    assert event.source_offset == header_size + 4 * record_size
    assert event.source_offset is not None
    inspection = repository.inspect_record(event.source_offset)
    assert inspection.raw_bytes == data[event.source_offset : event.source_offset + record_size]
    assert dict(inspection.fields)["sequence_no"] == "4"
    assert dict(inspection.fields)["name"] == "Data00004"
    assert inspection.timestamp_ns == event.timestamp_ns
    assert inspection.source_path == str(path.resolve())


def test_crc_error_raw_bytes_remain_inspectable(tmp_path: Path) -> None:
    path = tmp_path / "record.bin"
    data = bytearray(build_valid_v2_fixture())
    data[36 + 24] ^= 1
    path.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(path)
    inspection = repository.inspect_record(36)
    assert inspection.quality & Quality.CRC_ERROR
    assert inspection.raw_bytes == bytes(data[36:104])


@pytest.mark.parametrize("offset", [-1, 0, 33, 544])
def test_invalid_offsets_are_rejected(tmp_path: Path, offset: int) -> None:
    path = tmp_path / "record.bin"
    path.write_bytes(build_valid_fixture())
    repository = FileRecordingRepository()
    repository.open(path)
    with pytest.raises(ValueError, match="offset"):
        repository.inspect_record(offset)

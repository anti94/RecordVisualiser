"""İndeksli zaman aralığı sorgusu, kalite ve dar aralık okuma — F2-034."""

from __future__ import annotations

import struct
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from tests.golden_bytes import (
    START_TIME_UTC_NS,
    build_duplicate_sequence_fixture,
    build_gap_fixture,
    build_out_of_order_fixture,
    build_unknown_packet_fixture,
    build_valid_fixture,
    build_valid_v2_fixture,
)

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.profile_a_format import DataRecordV1
from sonar_analyzer.repository import file_repository
from sonar_analyzer.repository.file_repository import FileRecordingRepository

PERIOD = 125_000_000


def open_bytes(tmp_path: Path, data: bytes) -> FileRecordingRepository:
    path = tmp_path / "record.bin"
    path.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(path)
    return repository


@pytest.mark.parametrize("version", [1, 2])
def test_half_open_boundaries(tmp_path: Path, version: int) -> None:
    repository = open_bytes(
        tmp_path, build_valid_fixture() if version == 1 else build_valid_v2_fixture()
    )
    chunk = repository.query(
        "ch0", TimeRange(START_TIME_UTC_NS + 2 * PERIOD, START_TIME_UTC_NS + 4 * PERIOD)
    )
    assert chunk.timestamps_ns.tolist() == [
        START_TIME_UTC_NS + 2 * PERIOD,
        START_TIME_UTC_NS + 3 * PERIOD,
    ]
    np.testing.assert_array_equal(chunk.values, [101.0, 101.5])


def test_empty_and_outside_ranges(tmp_path: Path) -> None:
    repository = open_bytes(tmp_path, build_valid_fixture())
    assert repository.query("ch0", TimeRange(0, START_TIME_UTC_NS)).is_empty
    assert repository.query("ch0", TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS)).is_empty
    assert repository.query(
        "ch0", TimeRange(START_TIME_UTC_NS + 8 * PERIOD, START_TIME_UTC_NS + 9 * PERIOD)
    ).is_empty


def test_only_selected_records_are_decoded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = open_bytes(tmp_path, build_valid_fixture())
    original = file_repository.read_data_record_v1
    offsets: list[int] = []

    def traced(data: bytes, offset: int) -> DataRecordV1:
        offsets.append(offset)
        return original(data, offset)

    monkeypatch.setattr(file_repository, "read_data_record_v1", traced)
    repository.query(
        "ch1", TimeRange(START_TIME_UTC_NS + 3 * PERIOD, START_TIME_UTC_NS + 5 * PERIOD)
    )
    assert offsets == [32 + 3 * 64, 32 + 4 * 64]


def test_gap_does_not_shift_following_sample(tmp_path: Path) -> None:
    repository = open_bytes(tmp_path, build_gap_fixture())
    chunk = repository.query("ch0", repository.metadata().time_range)
    assert chunk.timestamps_ns[5] == START_TIME_UTC_NS + 6 * PERIOD
    assert chunk.has_flag(Quality.GAP_BEFORE)


@pytest.mark.parametrize("builder", [build_duplicate_sequence_fixture, build_out_of_order_fixture])
def test_out_of_order_and_duplicate_samples_remain_visible(
    tmp_path: Path, builder: Callable[[], bytes]
) -> None:
    repository = open_bytes(tmp_path, builder())
    chunk = repository.query("ch0", repository.metadata().time_range)
    assert len(chunk) == 8
    assert chunk.is_monotonic
    assert chunk.has_flag(Quality.SUSPECT)


def test_bad_record_crc_is_nan_with_quality(tmp_path: Path) -> None:
    data = bytearray(build_valid_v2_fixture())
    data[36 + 3 * 68 + 24] ^= 1
    repository = open_bytes(tmp_path, bytes(data))
    chunk = repository.query("ch0", repository.metadata().time_range)
    assert len(chunk) == 8
    assert np.isnan(chunk.values[3])
    assert chunk.flagged_indices(Quality.CRC_ERROR).tolist() == [3]
    assert chunk.values[4] == 102.0


def test_point_budget_preserves_narrow_impulse(tmp_path: Path) -> None:
    data = bytearray(build_valid_fixture(64))
    struct.pack_into("<f", data, 32 + 17 * 64 + 24, 9000.0)
    repository = open_bytes(tmp_path, bytes(data))
    chunk = repository.query("ch0", repository.metadata().time_range, max_points=8)
    assert len(chunk) <= 8
    assert chunk.is_monotonic
    assert 9000.0 in chunk.values


def test_query_requires_open_and_known_channel(tmp_path: Path) -> None:
    repository = FileRecordingRepository()
    with pytest.raises(RuntimeError):
        repository.query("ch0", TimeRange(0, 1))
    repository = open_bytes(tmp_path, build_valid_fixture())
    with pytest.raises(KeyError):
        repository.query("missing", repository.metadata().time_range)
    with pytest.raises(ValueError, match="max_points"):
        repository.query("ch0", repository.metadata().time_range, max_points=0)


def test_unknown_packet_does_not_hide_valid_records(tmp_path: Path) -> None:
    repository = open_bytes(tmp_path, build_unknown_packet_fixture())
    chunk = repository.query("ch0", repository.metadata().time_range)
    assert len(chunk) == 7
    assert chunk.is_monotonic
    assert chunk.values[-1] == 103.5


def test_nan_is_preserved_and_query_results_are_independent(tmp_path: Path) -> None:
    data = bytearray(build_valid_fixture())
    struct.pack_into("<f", data, 32 + 2 * 64 + 24, float("nan"))
    repository = open_bytes(tmp_path, bytes(data))
    chunk = repository.query("ch0", repository.metadata().time_range)
    assert np.isnan(chunk.values[2])
    assert chunk.has_flag(Quality.SUSPECT)
    chunk.values[0] = -123.0
    assert repository.query("ch0", repository.metadata().time_range).values[0] == 100.0

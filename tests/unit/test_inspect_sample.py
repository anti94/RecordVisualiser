"""Örnek başına ham/ölçeklenmiş inceleme — `F3-040`.

Kabul: seçim kaynak offsetini ve ham/ölçeklenmiş değeri gösterir.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.golden_bytes import START_TIME_UTC_NS

from sonar_analyzer.repository.file_repository import FileRecordingRepository

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"

HEADER_SIZE = 32
RECORD_SIZE = 64
PERIOD_NS = 125_000_000


@pytest.fixture()
def repo(tmp_path: Path) -> Iterator[FileRecordingRepository]:
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    repository = FileRecordingRepository()
    repository.open(target)
    yield repository
    repository.close()


def test_inspect_sample_reports_offset_and_values(repo: FileRecordingRepository) -> None:
    inspection = repo.inspect_sample("ch0", START_TIME_UTC_NS + 3 * PERIOD_NS)

    assert inspection.channel_id == "ch0"
    assert inspection.byte_offset == HEADER_SIZE + 3 * RECORD_SIZE
    assert inspection.timestamp_ns == START_TIME_UTC_NS + 3 * PERIOD_NS
    # CH0 (Pressure) = 100.0 + 0.5*n ; katalog kimlik kazanci -> ham == olcekli
    assert inspection.raw_value == 101.5
    assert inspection.scaled_value == 101.5


def test_consecutive_samples_advance_by_one_record(repo: FileRecordingRepository) -> None:
    first = repo.inspect_sample("ch0", START_TIME_UTC_NS)
    second = repo.inspect_sample("ch0", START_TIME_UTC_NS + PERIOD_NS)

    assert second.byte_offset - first.byte_offset == RECORD_SIZE
    assert first.raw_value == 100.0
    assert second.raw_value == 100.5


def test_inspect_sample_snaps_to_the_nearest_record(repo: FileRecordingRepository) -> None:
    # 2. ve 3. örnek arası, 3'e daha yakın
    near_third = START_TIME_UTC_NS + 2 * PERIOD_NS + int(PERIOD_NS * 0.7)

    inspection = repo.inspect_sample("ch0", near_third)

    assert inspection.timestamp_ns == START_TIME_UTC_NS + 3 * PERIOD_NS


def test_inspect_sample_clamps_before_first_and_after_last(repo: FileRecordingRepository) -> None:
    before = repo.inspect_sample("ch0", START_TIME_UTC_NS - 10 * PERIOD_NS)
    after = repo.inspect_sample("ch0", START_TIME_UTC_NS + 999 * PERIOD_NS)

    assert before.timestamp_ns == START_TIME_UTC_NS
    assert after.timestamp_ns == START_TIME_UTC_NS + 7 * PERIOD_NS


def test_a_different_channel_has_its_own_raw_value(repo: FileRecordingRepository) -> None:
    # CH1 (Temperature) sabit 25.0
    inspection = repo.inspect_sample("ch1", START_TIME_UTC_NS + 5 * PERIOD_NS)

    assert inspection.raw_value == 25.0
    assert inspection.scaled_value == 25.0


def test_unknown_channel_raises_key_error(repo: FileRecordingRepository) -> None:
    with pytest.raises(KeyError):
        repo.inspect_sample("chZZ", START_TIME_UTC_NS)

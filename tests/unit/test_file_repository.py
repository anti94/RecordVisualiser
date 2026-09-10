"""Dosyadan metadata/kanal erişimi ve format doğrulaması — F2-033."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture, build_valid_v2_fixture

from sonar_analyzer.io.decoders.crc_validation import HeaderCrcMismatchError
from sonar_analyzer.io.decoders.errors import FormatError, HeaderContractError
from sonar_analyzer.repository.file_repository import FileRecordingRepository


def test_access_requires_open_recording() -> None:
    repository = FileRecordingRepository()
    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        repository.metadata()
    with pytest.raises(RuntimeError):
        repository.channels()


@pytest.mark.parametrize("version", [1, 2])
def test_metadata_and_channels_for_both_versions(tmp_path: Path, version: int) -> None:
    source = tmp_path / "record.bin"
    data = build_valid_fixture() if version == 1 else build_valid_v2_fixture()
    source.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(source)
    metadata = repository.metadata()
    assert metadata.format_version == version
    assert metadata.record_count == 8
    assert metadata.channel_count == 8
    assert metadata.start_ns == START_TIME_UTC_NS
    assert metadata.duration_seconds == 1.0
    assert metadata.file_size_bytes == len(data)
    assert len(repository.channels()) == 8
    assert repository.channels()[0].unit == "bar"
    assert all(channel.sample_rate_hz == 8.0 for channel in repository.channels())
    assert not repository.cache_reused
    repository.open(source)
    assert repository.cache_reused


@pytest.mark.parametrize("data", [b"", b"x" * 32, b"SONARBIN" + bytes(25)])
def test_invalid_header_does_not_open_or_write_cache(tmp_path: Path, data: bytes) -> None:
    source = tmp_path / "bad.bin"
    source.write_bytes(data)
    repository = FileRecordingRepository()
    with pytest.raises(FormatError):
        repository.open(source)
    assert not source.with_suffix(".bin.sidx").exists()
    with pytest.raises(RuntimeError):
        repository.metadata()


def test_v2_header_crc_is_checked(tmp_path: Path) -> None:
    source = tmp_path / "bad-crc.bin"
    data = bytearray(build_valid_v2_fixture())
    data[24] ^= 1
    source.write_bytes(data)
    with pytest.raises(HeaderCrcMismatchError):
        FileRecordingRepository().open(source)


def test_zero_period_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "zero-period.bin"
    data = bytearray(build_valid_fixture())
    struct.pack_into("<I", data, 16, 0)
    source.write_bytes(data)
    with pytest.raises(HeaderContractError, match="period_us"):
        FileRecordingRepository().open(source)


def test_header_period_drives_channel_sample_rate(tmp_path: Path) -> None:
    source = tmp_path / "period.bin"
    data = bytearray(build_valid_fixture())
    struct.pack_into("<I", data, 16, 250_000)
    source.write_bytes(data)
    repository = FileRecordingRepository()
    repository.open(source)
    assert repository.channels()[0].sample_rate_hz == 4.0
    assert any("250000" in note for note in repository.metadata().diagnostics)


def test_empty_and_truncated_recordings(tmp_path: Path) -> None:
    source = tmp_path / "record.bin"
    repository = FileRecordingRepository()
    source.write_bytes(build_valid_fixture(record_count=0))
    repository.open(source)
    assert repository.metadata().time_range.is_empty
    # `F4-054`: kaynak bellek esleniyor; degistirmeden once birakilmali.
    repository.close()
    source.write_bytes(build_valid_fixture()[:-3])
    repository.open(source)
    assert repository.metadata().record_count == 7
    assert any("Kesik" in note for note in repository.metadata().diagnostics)


def test_cache_cannot_overwrite_source(tmp_path: Path) -> None:
    source = tmp_path / "record.bin"
    data = build_valid_fixture()
    source.write_bytes(data)
    with pytest.raises(ValueError, match="kaynak"):
        FileRecordingRepository().open(source, cache_path=source)
    assert source.read_bytes() == data


def test_unwritable_cache_does_not_prevent_reading(tmp_path: Path) -> None:
    source = tmp_path / "record.bin"
    source.write_bytes(build_valid_fixture())
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("file", encoding="utf-8")
    repository = FileRecordingRepository()
    repository.open(source, cache_path=blocked / "index.sidx")
    assert repository.metadata().record_count == 8
    assert any("cache" in note for note in repository.metadata().diagnostics)


def test_failed_open_preserves_previous_recording(tmp_path: Path) -> None:
    source = tmp_path / "good.bin"
    source.write_bytes(build_valid_fixture())
    repository = FileRecordingRepository()
    repository.open(source)
    with pytest.raises(FileNotFoundError):
        repository.open(tmp_path / "missing.bin")
    assert repository.metadata().source_path == str(source.resolve())

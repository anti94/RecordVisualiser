"""Aç/kapat, hata ve Windows dosya kilidi davranışı — F2-038."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.errors import FormatError
from sonar_analyzer.repository.file_repository import FileRecordingRepository


def test_context_manager_closes_on_exception(tmp_path: Path) -> None:
    path = tmp_path / "record.bin"
    path.write_bytes(build_valid_fixture())
    repository = FileRecordingRepository()
    with pytest.raises(RuntimeError, match="caller"), repository:
        repository.open(path)
        repository.events(repository.metadata().time_range)
        raise RuntimeError("caller failed")
    span = TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + 1_000_000_000)
    for operation in (
        repository.metadata,
        repository.channels,
        lambda: repository.query("ch0", span),
        lambda: repository.events(span),
        lambda: repository.bit_results(span),
        lambda: repository.transmissions(span),
        lambda: repository.inspect_record(32),
    ):
        with pytest.raises(RuntimeError, match="dosyasi acilmali"):
            operation()
    repository.close()  # Tekrarlı close güvenlidir.


def test_closed_reader_does_not_hold_windows_file_lock(tmp_path: Path) -> None:
    path = tmp_path / "record.bin"
    path.write_bytes(build_valid_fixture())
    with FileRecordingRepository() as repository:
        repository.open(path)
        assert len(repository.query("ch0", repository.metadata().time_range)) == 8
    renamed = path.rename(tmp_path / "renamed.bin")
    renamed.unlink()
    assert not renamed.exists()


def test_failed_open_leaves_no_file_lock(tmp_path: Path) -> None:
    path = tmp_path / "bad.bin"
    path.write_bytes(b"invalid")
    with FileRecordingRepository() as repository, pytest.raises(FormatError):
        repository.open(path)
    renamed = path.rename(tmp_path / "bad-renamed.bin")
    renamed.unlink()


def test_repeated_open_close_and_snapshot_isolation(tmp_path: Path) -> None:
    path = tmp_path / "record.bin"
    original = build_valid_fixture()
    path.write_bytes(original)
    repository = FileRecordingRepository()
    for _ in range(20):
        repository.open(path)
        repository.events(repository.metadata().time_range)
        repository.close()
    repository.open(path)
    # Acik snapshot kendi kaydini gorur.
    assert len(repository.query("ch0", repository.metadata().time_range)) == 8
    # `F4-054`: kaynak bellek esleniyor; degistirmeden once birakilmali.
    repository.close()
    path.write_bytes(build_valid_fixture(2))
    repository.open(path)
    assert repository.metadata().record_count == 2
    repository.close()

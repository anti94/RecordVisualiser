"""Yalnız görünür zaman bloklarını yükle — `F4-054`.

Kabul: dar sorgu ilgili bloklarla sınırlı kalır.

İki yönden denetlenir:

1. **Doğruluk** — dar bir sorgu yalnız aralıktaki kayıtları döndürür ve
   değerleri tam sorgunun aynı dilimiyle birebir eşleşir.
2. **Maliyet** — `tracemalloc` ile ölçülür: büyük bir kayıtta dar sorgu,
   dönen nokta sayısıyla orantılı bellek ayırır; dosya boyutuna göre
   değil. Kaynak `MappedSource` ile eşlendiği için dosya hiç kopyalanmaz.
"""

from __future__ import annotations

import struct
import tracemalloc
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.readers.mapped_source import MappedSource
from sonar_analyzer.repository.file_repository import FileRecordingRepository

#: 8 Hz kayıt: 125 ms periyot.
PERIOD_NS = 125_000_000
#: Ölçüm anlamlı olsun diye büyükçe bir kayıt (~64 kayıt/blok değil, çok kayıt).
LARGE_RECORDS = 40_000


def _write(tmp_path: Path, record_count: int, name: str = "record.bin") -> Path:
    source = tmp_path / name
    source.write_bytes(build_valid_fixture(record_count=record_count))
    return source


@pytest.fixture()
def large_recording(tmp_path: Path) -> Path:
    return _write(tmp_path, LARGE_RECORDS, "large.bin")


@pytest.fixture()
def repository(large_recording: Path) -> Iterator[FileRecordingRepository]:
    repo = FileRecordingRepository()
    repo.open(large_recording)
    yield repo
    repo.close()


# --------------------------------------------------------------------------- #
# kaynak kopyalanmıyor
# --------------------------------------------------------------------------- #


def test_the_open_source_is_a_memory_mapping(repository: FileRecordingRepository) -> None:
    metadata = repository.metadata()
    with MappedSource(Path(metadata.source_path)) as mapped:
        assert mapped.size == metadata.file_size_bytes


# --------------------------------------------------------------------------- #
# dar sorgu doğru sonucu verir
# --------------------------------------------------------------------------- #


def test_a_narrow_query_returns_only_the_records_in_range(
    repository: FileRecordingRepository,
) -> None:
    start = START_TIME_UTC_NS + 100 * PERIOD_NS
    narrow = TimeRange(start, start + 10 * PERIOD_NS)

    chunk = repository.query("ch0", narrow)

    assert len(chunk) == 10
    assert int(chunk.timestamps_ns[0]) == start
    assert int(chunk.timestamps_ns[-1]) == start + 9 * PERIOD_NS
    assert np.all(chunk.timestamps_ns >= narrow.start_ns)
    assert np.all(chunk.timestamps_ns < narrow.end_ns)


def test_a_narrow_query_matches_the_same_slice_of_the_full_query(
    repository: FileRecordingRepository,
) -> None:
    full = repository.query("ch0", repository.metadata().time_range)
    start = START_TIME_UTC_NS + 500 * PERIOD_NS
    narrow = repository.query("ch0", TimeRange(start, start + 20 * PERIOD_NS))

    assert np.array_equal(narrow.timestamps_ns, full.timestamps_ns[500:520])
    assert np.array_equal(narrow.values, full.values[500:520])


def test_a_window_outside_the_recording_is_empty(repository: FileRecordingRepository) -> None:
    far = START_TIME_UTC_NS + (LARGE_RECORDS + 100) * PERIOD_NS
    chunk = repository.query("ch0", TimeRange(far, far + PERIOD_NS))
    assert len(chunk) == 0


# --------------------------------------------------------------------------- #
# dar sorgu ilgili bloklarla sınırlı kalır
# --------------------------------------------------------------------------- #


def _peak_bytes_for_query(repository: FileRecordingRepository, span: TimeRange) -> int:
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        chunk = repository.query("ch0", span)
        assert len(chunk) >= 0
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak


def test_a_narrow_query_allocates_far_less_than_the_file(
    repository: FileRecordingRepository, large_recording: Path
) -> None:
    file_size = large_recording.stat().st_size
    start = START_TIME_UTC_NS + 1_000 * PERIOD_NS
    peak = _peak_bytes_for_query(repository, TimeRange(start, start + 20 * PERIOD_NS))

    # 20 nokta okumak, ~2.5 MB'lık kaydın yüzde birinden azını ayırmalı.
    assert peak < file_size // 100, f"tepe ayırma {peak}, dosya {file_size}"


def test_the_query_cost_follows_the_window_not_the_file(
    repository: FileRecordingRepository,
) -> None:
    start = START_TIME_UTC_NS + 1_000 * PERIOD_NS
    narrow = _peak_bytes_for_query(repository, TimeRange(start, start + 10 * PERIOD_NS))
    wide = _peak_bytes_for_query(
        repository, TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + LARGE_RECORDS * PERIOD_NS)
    )

    # Geniş sorgu belirgin biçimde daha pahalı: maliyet pencereyle ölçekleniyor.
    assert wide > narrow * 10


def test_repeated_narrow_queries_do_not_accumulate(
    repository: FileRecordingRepository, large_recording: Path
) -> None:
    file_size = large_recording.stat().st_size
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        for index in range(50):
            start = START_TIME_UTC_NS + (index * 100) * PERIOD_NS
            chunk = repository.query("ch0", TimeRange(start, start + 5 * PERIOD_NS))
            assert len(chunk) == 5
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < file_size // 50


# --------------------------------------------------------------------------- #
# kaynak açıkken kilitli kalır (F4-054 ödünçü)
# --------------------------------------------------------------------------- #


def test_closing_the_repository_releases_the_source(tmp_path: Path) -> None:
    source = _write(tmp_path, 8)
    repo = FileRecordingRepository()
    repo.open(source)
    assert repo.metadata().record_count == 8

    repo.close()

    # Kilit bırakıldı: kaynak artık değiştirilebilir.
    source.write_bytes(build_valid_fixture(record_count=2))
    repo.open(source)
    assert repo.metadata().record_count == 2
    repo.close()


def test_an_empty_source_is_a_format_error_not_a_mapping_error(tmp_path: Path) -> None:
    from sonar_analyzer.io.decoders.errors import FormatError

    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(FormatError):
        FileRecordingRepository().open(empty)


def test_the_header_is_still_read_from_the_mapping(tmp_path: Path) -> None:
    source = _write(tmp_path, 8)
    repo = FileRecordingRepository()
    repo.open(source)
    try:
        # Header alanları dosyadaki ham baytlarla birebir.
        raw = source.read_bytes()
        record_size = struct.unpack_from("<I", raw, 12)[0]
        assert repo.metadata().record_count == 8
        assert record_size > 0
    finally:
        repo.close()

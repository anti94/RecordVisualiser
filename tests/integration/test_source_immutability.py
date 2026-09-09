"""Kaynak dosyanın değişmediğini doğrulama — `F2-040`.

Kabul: geçerli ve bozuk dosya aç/kapat öncesi ve sonrası hash aynıdır.

Plan Bölüm 10.1: "Ham veri immutable kabul edilir." Bu test o sözü
ölçülebilir hâle getirir — okuyucu kaynak `.bin`'e **hiçbir koşulda**
yazmaz: ne başarılı açılışta, ne sorgu sırasında, ne de açılış hata
verdiğinde. Türetilmiş indeks (`.sidx`) ayrı bir dosyadır ve kaynağın
yanına yazılır; kaynağın kendisine dokunulmaz.

Her fixture `tmp_path`'e kopyalanarak açılır; böylece indeks cache'i
depo içindeki fixture dizinine değil geçici dizine yazılır.
"""

from __future__ import annotations

import hashlib
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

import pytest

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.errors import FormatError
from sonar_analyzer.repository.file_repository import FileRecordingRepository

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

#: docs/format/fixture-corrupt.md K-01..K-06 + gecerli v1/v2 dosyalari.
#: (dosya adi, acilis basarili mi) — K-01 ve K-05 dosyayi acmayi reddeder.
FIXTURE_CASES = (
    ("valid_8records.bin", True),
    ("valid_8records_v2.bin", True),
    ("truncated_header.bin", False),  # K-01
    ("truncated_last_record.bin", True),  # K-02
    ("gap_missing_record.bin", True),  # K-03
    ("crc_error.bin", True),  # K-04
    ("unsupported_version.bin", False),  # K-05
    ("name_index_mismatch.bin", True),  # K-06
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: docs/format/profile-a.md / ADR-011 §2.3: v1 header 32 byte, v2 (CRC'li) 36 byte.
_HEADER_SIZE_BY_VERSION = {1: 32, 2: 36}


def _exercise_all_queries(repository: FileRecordingRepository) -> None:
    """Açık bir kayıt üzerinde okuma yollarının tamamını dolaşır."""
    metadata = repository.metadata()
    span = metadata.time_range
    for channel in repository.channels():
        repository.query(channel.id, span)
        repository.query(channel.id, span, max_points=4)
    repository.events(span)
    repository.bit_results(span)
    repository.transmissions(span)
    if metadata.record_count:
        # Ilk kaydin offseti = header boyutu; kesik kuyruklu dosyada da gecerli.
        repository.inspect_record(_HEADER_SIZE_BY_VERSION[metadata.format_version])


@pytest.mark.parametrize(("filename", "opens_successfully"), FIXTURE_CASES)
def test_hash_is_identical_before_and_after_open_close(
    tmp_path: Path, filename: str, opens_successfully: bool
) -> None:
    """Kabul kriteri birebir: geçerli ve bozuk dosyada aç/kapat hash'i değiştirmez."""
    source = tmp_path / filename
    shutil.copyfile(FIXTURES_DIR / filename, source)
    hash_before = _sha256(source)
    size_before = source.stat().st_size

    repository = FileRecordingRepository()
    with repository:
        if opens_successfully:
            repository.open(source)
            _exercise_all_queries(repository)
        else:
            with pytest.raises(FormatError):
                repository.open(source)

    assert _sha256(source) == hash_before
    assert source.stat().st_size == size_before


@pytest.mark.parametrize(("filename", "opens_successfully"), FIXTURE_CASES)
def test_repeated_open_close_cycles_never_touch_the_source(
    tmp_path: Path, filename: str, opens_successfully: bool
) -> None:
    """Cache yeniden kullanımı (F2-032) devreye girdiğinde de kaynak değişmez."""
    source = tmp_path / filename
    shutil.copyfile(FIXTURES_DIR / filename, source)
    hash_before = _sha256(source)

    repository = FileRecordingRepository()
    for _ in range(3):
        with repository:
            if opens_successfully:
                repository.open(source)
                _exercise_all_queries(repository)
            else:
                with pytest.raises(FormatError):
                    repository.open(source)
        assert _sha256(source) == hash_before


def test_derived_index_is_a_separate_sidecar_file(tmp_path: Path) -> None:
    """Türetilmiş indeks kaynağın içine değil yanındaki `.sidx` dosyasına yazılır."""
    source = tmp_path / "valid_8records.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", source)
    hash_before = _sha256(source)

    with FileRecordingRepository() as repository:
        repository.open(source)
        _exercise_all_queries(repository)

    sidecar = source.with_suffix(source.suffix + ".sidx")
    assert sidecar.exists()
    assert sidecar != source
    assert _sha256(source) == hash_before


def test_explicit_cache_path_keeps_source_untouched(tmp_path: Path) -> None:
    """`cache_path` başka bir dizine verilse de kaynak yine değişmez."""
    source = tmp_path / "valid_8records.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", source)
    hash_before = _sha256(source)
    cache_dir = tmp_path / "cache"

    with FileRecordingRepository() as repository:
        repository.open(source, cache_path=cache_dir / "record.sidx")
        _exercise_all_queries(repository)

    assert (cache_dir / "record.sidx").exists()
    assert _sha256(source) == hash_before


def test_read_only_source_can_still_be_opened_and_queried(tmp_path: Path) -> None:
    """Salt okunur dosya açılabiliyorsa okuyucu kaynağa yazmaya hiç kalkışmıyor."""
    source = tmp_path / "valid_8records.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", source)
    hash_before = _sha256(source)
    source.chmod(stat.S_IREAD)
    try:
        with FileRecordingRepository() as repository:
            repository.open(source)
            _exercise_all_queries(repository)
            assert repository.metadata().record_count == 8
        assert _sha256(source) == hash_before
    finally:
        # Windows'ta salt okunur dosya silinemez; tmp_path temizligi icin geri al.
        source.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_query_paths_do_not_mutate_the_in_memory_snapshot(tmp_path: Path) -> None:
    """Aynı sorgu iki kez aynı sonucu verir — okuma yolu durum bozmaz."""
    source = tmp_path / "valid_8records.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", source)

    with FileRecordingRepository() as repository:
        repository.open(source)
        span = repository.metadata().time_range
        first = repository.query("ch0", span)
        events_first = repository.events(span)
        second = repository.query("ch0", span)
        events_second = repository.events(span)

    assert first.values.tolist() == second.values.tolist()
    assert first.timestamps_ns.tolist() == second.timestamps_ns.tolist()
    assert events_first == events_second


def _corrupting_operations() -> tuple[Callable[[FileRecordingRepository], object], ...]:
    """Hata veren sorgular da kaynağa yazmamalı."""
    span = TimeRange(0, 1)
    return (
        lambda repo: repo.query("bilinmeyen-kanal", span),
        lambda repo: repo.query("ch0", span, max_points=0),
        lambda repo: repo.inspect_record(-1),
    )


@pytest.mark.parametrize("operation", _corrupting_operations())
def test_failing_queries_leave_the_source_unchanged(
    tmp_path: Path, operation: Callable[[FileRecordingRepository], object]
) -> None:
    source = tmp_path / "valid_8records.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", source)
    hash_before = _sha256(source)

    with FileRecordingRepository() as repository:
        repository.open(source)
        with pytest.raises((KeyError, ValueError)):
            operation(repository)

    assert _sha256(source) == hash_before

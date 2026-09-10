"""İndeks kesintisi ve cache kurtarma — `F4-066`.

Kabul: yarım indeks kullanılmaz; yeniden üretim kaynak veriyi değiştirmez.

`F2-031` atomik yazmayı, `F2-032` geçersiz cache'in yeniden üretilmesini
birim düzeyinde denetler. Burada aynı sözler **kesinti senaryolarıyla ve
uçtan uca** sınanır: indeks yazımı ortasında kesilen bir koşudan sonra
gerçek bir kayıt `FileRecordingRepository` ile açılır, kurtarılan indeksin
temiz bir yapıyla birebir aynı olduğu ve kaynak `.bin`'in **baytı baytına**
değişmediği gösterilir.

Kesinti biçimleri gerçek arıza kiplerini taklit eder: yarım yazılmış JSON,
geçerli JSON ama eksik kayıt listesi, tek bayt bozulması, yanlış kaynağa
ait indeks, sıfır uzunlukta dosya ve rename'e hiç gelinememiş `.tmp`
artığı.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sonar_analyzer.io.index.cache import load_or_build_record_index, records_digest
from sonar_analyzer.io.index.storage import save_index_atomic
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1
from sonar_analyzer.repository.file_repository import FileRecordingRepository

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    """Geçici dizine kopyalanmış gerçek bir kayıt; indeks yanına yazılır."""
    target = tmp_path / "record.bin"
    shutil.copyfile(FIXTURE, target)
    return target


@pytest.fixture()
def index_path(tmp_path: Path) -> Path:
    return tmp_path / "record.bin.sidx"


def _open_once(source: Path, index_path: Path) -> tuple[tuple[object, ...], bool]:
    """Kaydı bir kez açar; (indeks girdileri, cache yeniden kullanıldı mı)."""
    repository = FileRecordingRepository()
    try:
        repository.open(source, cache_path=index_path)
        metadata = repository.metadata()
        entries = tuple(
            repository.query(channel.id, metadata.time_range).timestamps_ns.tolist()
            for channel in repository.channels()
        )
        return entries, repository.cache_reused
    finally:
        repository.close()


def _clean_index(source: Path, index_path: Path) -> tuple[object, ...]:
    """Hiç kesinti olmamış bir koşunun ürettiği indeks girdileri."""
    data = source.read_bytes()
    header = read_file_header_v1(data)
    return load_or_build_record_index(data, header, index_path).entries


# --------------------------------------------------------------------------- #
# kesinti bicimleri
# --------------------------------------------------------------------------- #


def _valid_payload(source: Path, index_path: Path) -> dict[str, Any]:
    _clean_index(source, index_path)
    payload: dict[str, Any] = json.loads(index_path.read_text(encoding="utf-8"))
    return payload


def _damage_cases(source: Path, index_path: Path) -> Iterator[tuple[str, bytes]]:
    """Gerçek arıza kiplerini taklit eden yarım/bozuk indeks içerikleri."""
    payload = _valid_payload(source, index_path)
    complete = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")

    truncated_records = dict(payload)
    truncated_records["records"] = payload["records"][:3]

    flipped = json.loads(json.dumps(payload))
    flipped["records"][0][2] += 1  # tek bayt oynamis gibi

    foreign = dict(payload)
    foreign["source_sha256"] = "0" * 64

    # Zarfı tutarlı ama içeriği yanlış: yarım kalmış bir taramanın uydurma
    # offset'le tamamlanması gibi. Özet de yeniden hesaplanır ki reddin
    # nedeni özet değil, kaydın kendisinin doğrulanması olsun.
    shifted = json.loads(json.dumps(payload))
    shifted["records"][1][1] += 1
    shifted["records_sha256"] = records_digest(shifted["records"])

    yield "sifir-uzunluk", b""
    yield "yarim-json", complete[: len(complete) // 2]
    yield "eksik-kayit-listesi", json.dumps(truncated_records).encode("utf-8")
    yield "bozuk-tek-kayit", json.dumps(flipped).encode("utf-8")
    yield "baska-kaynagin-indeksi", json.dumps(foreign).encode("utf-8")
    yield "tutarli-zarf-yanlis-offset", json.dumps(shifted).encode("utf-8")
    yield "bos-nesne", b"{}"


def test_every_damaged_index_is_rebuilt_not_used(source: Path, index_path: Path) -> None:
    """Yarım indeks **kullanılmaz**: her biçim yeniden üretime düşer."""
    expected = _clean_index(source, index_path)
    for name, contents in list(_damage_cases(source, index_path)):
        index_path.write_bytes(contents)
        data = source.read_bytes()
        result = load_or_build_record_index(data, read_file_header_v1(data), index_path)
        assert not result.reused, f"{name}: yarim indeks kullanildi"
        assert result.entries == expected, f"{name}: kurtarilan indeks farkli"


def test_a_rebuilt_index_is_reused_on_the_next_open(source: Path, index_path: Path) -> None:
    """Kurtarma kalıcıdır: bir sonraki açılış yeniden taramaz."""
    index_path.write_bytes(b"{yarim")
    data = source.read_bytes()
    header = read_file_header_v1(data)

    first = load_or_build_record_index(data, header, index_path)
    second = load_or_build_record_index(data, header, index_path)

    assert not first.reused
    assert second.reused
    assert first.entries == second.entries


def test_a_stray_temp_file_is_never_adopted(source: Path, index_path: Path) -> None:
    """Rename'e hiç gelinememiş `.tmp` artığı indeks yerine geçmez."""
    expected = _clean_index(source, index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    index_path.unlink()
    stray = index_path.with_name(index_path.name + ".abc123.tmp")
    stray.write_text(json.dumps(payload), encoding="utf-8")

    data = source.read_bytes()
    result = load_or_build_record_index(data, read_file_header_v1(data), index_path)

    assert not result.reused  # artik dosya gecerli indeks sayilmadi
    assert result.entries == expected
    assert stray.exists()  # dokunulmadi da


def test_an_interrupted_write_keeps_the_previous_valid_index(
    source: Path, index_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yazma kesilirse var olan geçerli indeks bozulmaz."""
    expected = _clean_index(source, index_path)
    before = index_path.read_bytes()

    def interrupted(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk doldu")

    monkeypatch.setattr(Path, "replace", interrupted)
    with pytest.raises(OSError, match="disk doldu"):
        save_index_atomic(index_path, {"schema_version": 1, "records": []})
    monkeypatch.undo()

    assert index_path.read_bytes() == before
    data = source.read_bytes()
    result = load_or_build_record_index(data, read_file_header_v1(data), index_path)
    assert result.reused
    assert result.entries == expected
    assert not list(index_path.parent.glob("*.tmp"))  # yarim dosya birakilmadi


# --------------------------------------------------------------------------- #
# yeniden uretim kaynak veriyi degistirmez
# --------------------------------------------------------------------------- #


def test_rebuilding_after_every_damage_leaves_the_source_byte_identical(
    source: Path, index_path: Path
) -> None:
    digest = _sha256(source)
    size = source.stat().st_size
    mtime = source.stat().st_mtime_ns

    for _name, contents in list(_damage_cases(source, index_path)):
        index_path.write_bytes(contents)
        _open_once(source, index_path)

    assert _sha256(source) == digest
    assert source.stat().st_size == size
    assert source.stat().st_mtime_ns == mtime


def test_recovery_through_the_repository_produces_the_same_data(
    source: Path, index_path: Path
) -> None:
    """Kurtarılmış indeksle okunan veri, temiz indeksle okunanla aynıdır."""
    clean_values, clean_reused = _open_once(source, index_path)
    assert not clean_reused

    index_path.write_bytes(b"\xff\xfe yarim")
    recovered_values, recovered_reused = _open_once(source, index_path)

    assert not recovered_reused  # bozuk indeks kullanilmadi
    assert recovered_values == clean_values
    # Kurtarma kalicidir.
    _third, third_reused = _open_once(source, index_path)
    assert third_reused


def test_a_read_only_source_survives_index_recovery(source: Path, index_path: Path) -> None:
    """Kaynak salt okunursa da kurtarma çalışır ve dosyaya yazılmaz."""
    _clean_index(source, index_path)
    digest = _sha256(source)
    index_path.write_bytes(b"{}")
    source.chmod(0o444)
    try:
        values, reused = _open_once(source, index_path)
    finally:
        source.chmod(0o666)

    assert not reused
    assert values
    assert _sha256(source) == digest


def test_the_index_never_lands_on_the_source_itself(source: Path) -> None:
    """İndeks hedefi kaynak dosya olamaz — kurtarma kaynağı ezemez."""
    repository = FileRecordingRepository()
    try:
        with pytest.raises(ValueError, match="Indeks hedefi"):
            repository.open(source, cache_path=source)
    finally:
        repository.close()
    assert _sha256(source) == _sha256(FIXTURE)


def test_a_missing_index_directory_is_created_without_touching_the_source(
    source: Path, tmp_path: Path
) -> None:
    digest = _sha256(source)
    nested = tmp_path / "cache" / "nested" / "record.sidx"
    values, reused = _open_once(source, nested)

    assert not reused
    assert values
    assert nested.exists()
    assert _sha256(source) == digest

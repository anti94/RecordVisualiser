"""Klasör seviyesinde indeks — `F7-031`…`F7-035`.

Kabuller: dosya → zaman aralığı eşlemesi tek dosyada tutulur; indeks
dosya adı, boyut ve değişiklik zamanıyla geçersizleşir; yazım atomiktir;
salt okunur klasörde kayıt yine açılır.

Bir indeksin en tehlikeli hâli **eskimiş ama geçerli görünmesidir**.
Klasör değişmiş, indeks eski frame sayılarını taşıyor ve hiçbir hata
oluşmuyor — yalnız sayılar yanlış. Testlerin çoğunluğu bu yüzden
geçersizleşmenin gerçekten çalıştığını gösterir.

İkinci risk sessizce kaybolmaktır: yarıda kesilen bir yazım, sonraki
açılışta ayrıştırma hatası veren yarım bir JSON bırakırdı.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sonar_analyzer.io.decoders.profile_c_folder import Stream, discover
from sonar_analyzer.io.index.profile_c_index import (
    INDEX_FORMAT_VERSION,
    FileEntry,
    FolderIndex,
    folder_fingerprint,
    index_path,
    is_current,
    read_index,
    write_index,
)

SCHEMA_FP = "a01d251282fb50f8"


def _make(root: Path, name: str = "2026-09-12T14-30-00Z") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    return folder


def _write(folder: Path, stream: str, counters: list[int], size: int = 64) -> None:
    directory = folder / stream
    directory.mkdir(exist_ok=True)
    for counter in counters:
        (directory / f"{stream}Data{counter:05d}.bin").write_bytes(bytes(size))


def _index(folder_path: Path, *, schema_fp: str = SCHEMA_FP) -> FolderIndex:
    folder = discover(folder_path)
    entries: dict[str, tuple[FileEntry, ...]] = {}
    for stream in Stream:
        listing = folder.listing(stream)
        if not listing.present:
            continue
        entries[stream.value] = tuple(
            FileEntry(
                counter=item.counter,
                name=item.path.name,
                size_bytes=item.size_bytes,
                frame_count=10,
                start_ns=1_700_000_000_000_000_000 + item.counter * 1_000_000_000,
                end_ns=1_700_000_000_000_000_000 + (item.counter + 1) * 1_000_000_000,
            )
            for item in listing.files
        )
    return FolderIndex(
        fingerprint=folder_fingerprint(folder), schema_fingerprint=schema_fp, entries=entries
    )


# --------------------------------------------------------------------------- #
# F7-031 — INDEKS YAPISI
# --------------------------------------------------------------------------- #


def test_the_index_maps_files_to_time_ranges(tmp_path: Path) -> None:
    """Asıl kabul: dosya → zaman aralığı eşlemesi tek yerde."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1, 2])

    index = _index(folder_path)

    assert index.file_count == 3
    assert index.frame_count == 30
    assert index.stream(Stream.RX)[0].start_ns == 1_700_000_000_000_000_000


def test_the_time_range_spans_every_stream(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Tx", [0, 1])
    _write(folder_path, "Rx", [0, 1, 2])

    span = _index(folder_path).time_range_ns

    assert span is not None
    assert span[1] - span[0] == 3_000_000_000


def test_an_index_without_timestamps_has_no_range(tmp_path: Path) -> None:
    """Çözülmemiş bir dosya için zaman uydurulmaz."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    index = FolderIndex(
        fingerprint="x",
        schema_fingerprint=SCHEMA_FP,
        entries={
            "Rx": (FileEntry(counter=0, name="RxData00000.bin", size_bytes=64, frame_count=0),)
        },
    )

    assert index.time_range_ns is None


def test_a_round_trip_preserves_every_field(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Tx", [0])
    _write(folder_path, "Rx", [0, 1])
    original = _index(folder_path)

    write_index(discover(folder_path), original)
    restored = read_index(discover(folder_path))

    assert restored is not None
    assert restored.fingerprint == original.fingerprint
    assert restored.schema_fingerprint == original.schema_fingerprint
    assert restored.file_count == original.file_count
    assert restored.stream(Stream.RX)[1].end_ns == original.stream(Stream.RX)[1].end_ns


# --------------------------------------------------------------------------- #
# F7-032 — GECERSIZLESME
# --------------------------------------------------------------------------- #


def test_an_unchanged_folder_keeps_its_index(tmp_path: Path) -> None:
    """Karşı yön: değişmemiş klasörde indeks yeniden kurulmamalı."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1])
    index = _index(folder_path)

    assert is_current(index, discover(folder_path), SCHEMA_FP) is True


def test_adding_a_file_invalidates_the_index(tmp_path: Path) -> None:
    """Asıl kabul: yeni dosya indeksi geçersiz kılmalı."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1])
    index = _index(folder_path)

    _write(folder_path, "Rx", [2])

    assert is_current(index, discover(folder_path), SCHEMA_FP) is False


def test_removing_a_file_invalidates_the_index(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1, 2])
    index = _index(folder_path)

    (folder_path / "Rx" / "RxData00001.bin").unlink()

    assert is_current(index, discover(folder_path), SCHEMA_FP) is False


def test_a_changed_file_size_invalidates_the_index(tmp_path: Path) -> None:
    """Aynı ad, farklı boyut: dosya yeniden yazılmış."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    index = _index(folder_path)

    (folder_path / "Rx" / "RxData00000.bin").write_bytes(bytes(128))

    assert is_current(index, discover(folder_path), SCHEMA_FP) is False


def test_a_changed_schema_invalidates_the_index(tmp_path: Path) -> None:
    """Asıl kabul: klasör değişmeden şema değişebilir.

    Aynı dosyalar farklı bir yerleşimle okunur ve indeksteki frame
    sayıları yanlış olur. Tek bir parmak iziyle bu ayrım kaybolurdu.
    """
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1])
    index = _index(folder_path)

    assert is_current(index, discover(folder_path), SCHEMA_FP) is True
    assert is_current(index, discover(folder_path), "baskabirsema") is False


def test_an_old_format_version_invalidates_the_index(tmp_path: Path) -> None:
    """İndeks biçimi değişince eski indeksler okunmamalı."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    stale = FolderIndex(
        fingerprint=folder_fingerprint(folder),
        schema_fingerprint=SCHEMA_FP,
        entries={},
        format_version=INDEX_FORMAT_VERSION - 1,
    )

    assert is_current(stale, folder, SCHEMA_FP) is False


def test_the_fingerprint_does_not_hash_file_contents(tmp_path: Path) -> None:
    """1,17 GiB'i hash'lemek indeksin kendisinden uzun sürerdi.

    Aynı boyutta ama farklı içerikli bir dosya, aynı `mtime` ile aynı
    parmak izini verir. Bu bilinçli bir takas: amaç kriptografik güvence
    değil, "bu klasör değişti mi" sorusuna ucuz cevap.
    """
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    target = folder_path / "Rx" / "RxData00000.bin"
    before = folder_fingerprint(discover(folder_path))

    info = target.stat()
    target.write_bytes(b"\xff" * 64)

    os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))

    assert folder_fingerprint(discover(folder_path)) == before


# --------------------------------------------------------------------------- #
# F7-033 — ATOMIK YAZIM
# --------------------------------------------------------------------------- #


def test_the_index_is_written_where_expected(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)

    written = write_index(folder, _index(folder_path))

    assert written == index_path(folder)
    assert written is not None and written.is_file()
    assert written.parent.name == ".sonar-index"


def test_no_temporary_file_survives_a_successful_write(tmp_path: Path) -> None:
    """Geçici dosya kalırsa, sonraki taramalar onu da görür."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)

    write_index(folder, _index(folder_path))

    leftovers = list(index_path(folder).parent.glob("*.tmp"))
    assert leftovers == []


def test_rewriting_replaces_the_previous_index(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))

    _write(folder_path, "Rx", [1])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))

    restored = read_index(folder)
    assert restored is not None
    assert restored.file_count == 2


def test_the_written_index_is_valid_json(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))

    raw = json.loads(index_path(folder).read_text(encoding="utf-8"))

    assert raw["format_version"] == INDEX_FORMAT_VERSION
    assert "Rx" in raw["entries"]


# --------------------------------------------------------------------------- #
# BOZUK INDEKS
# --------------------------------------------------------------------------- #


def test_a_missing_index_returns_none(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])

    assert read_index(discover(folder_path)) is None


def test_a_corrupt_index_returns_none_instead_of_raising(tmp_path: Path) -> None:
    """Asıl kabul: bozuk indeks veriyi okunamaz kılmamalı.

    İndeks türetilmiş veridir; yeniden kurmanın bedeli birkaç saniyedir.
    Kurtarmaya çalışmak yanlış zaman aralıklarıyla çalışmak olurdu.
    """
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))
    index_path(folder).write_text("{ yarim json", encoding="utf-8")

    assert read_index(folder) is None


def test_an_index_missing_a_required_key_returns_none(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))
    index_path(folder).write_text(
        json.dumps({"format_version": INDEX_FORMAT_VERSION}), encoding="utf-8"
    )

    assert read_index(folder) is None


def test_an_index_that_is_not_an_object_returns_none(tmp_path: Path) -> None:
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))
    index_path(folder).write_text("[1, 2, 3]", encoding="utf-8")

    assert read_index(folder) is None


# --------------------------------------------------------------------------- #
# F7-034 — SALT OKUNUR KLASOR
# --------------------------------------------------------------------------- #


def _block_index_directory(folder_path: Path) -> None:
    """İndeks dizininin yaratılmasını engeller.

    Adı `.sonar-index` olan bir **dosya** konur; `mkdir` o adı alamaz ve
    `OSError` verir. Windows'ta klasör izinlerini değiştirmek yönetici
    hakkı ve platforma özgü çağrı gerektirdiği için bu yol seçildi:
    sınanan davranış aynı, kurulumu taşınabilir.
    """
    (folder_path / ".sonar-index").write_bytes(b"bu bir dizin degil")


def test_a_read_only_folder_does_not_block_the_recording(tmp_path: Path) -> None:
    """Asıl kabul: indeks yazılamıyorsa kayıt yine açılır.

    Arşivdeki ya da salt okunur bir paylaşımdaki kaydı incelemek
    engellenmemeli. Kayıt klasörünü yazılabilir olmaya zorlamak, veriyi
    okumayı izinlere bağlamak olurdu.
    """
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1])
    _block_index_directory(folder_path)
    folder = discover(folder_path)

    written = write_index(folder, _index(folder_path))

    assert written is None, "yazilamadi ama hata atilmamali"
    assert folder.file_count == 2, "kayit yine okunabilmeli"


def test_a_blocked_index_reads_back_as_none(tmp_path: Path) -> None:
    """Yazılamayan indeks, sonraki açılışta yokmuş gibi davranır."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0])
    _block_index_directory(folder_path)
    folder = discover(folder_path)

    write_index(folder, _index(folder_path))

    assert read_index(folder) is None


def test_the_index_file_is_not_mistaken_for_a_recording_file(tmp_path: Path) -> None:
    """`.sonar-index` bir akım klasörü değildir; taramaya karışmamalı."""
    folder_path = _make(tmp_path)
    _write(folder_path, "Rx", [0, 1])
    folder = discover(folder_path)
    write_index(folder, _index(folder_path))

    rescanned = discover(folder_path)

    assert rescanned.file_count == 2

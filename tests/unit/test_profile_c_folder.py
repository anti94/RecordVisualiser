"""Profil C kayıt klasörü keşfi — `F7-028`…`F7-031`.

Kabuller: tarih klasörü altında `Tx/` ve `Rx/` bulunur, eksikse hangisi
olmadığı söylenir; dosya sayacı sırası doğrulanır ve boşluklar raporlanır;
manifest okunur, yoksa üretilir.

Bu katmanın sessiz hatası sıralamadır. Dosya sistemi `TxData10.bin`'i
`TxData9.bin`'den önce döndürebilir ve o sırayla okunan bir kayıt zamanda
geri gider. Testler bu yüzden dosyaları **kasten karışık** yaratır.

İkinci sessiz hata sarmadır: azalan bir sayacı sarma sayıp devam etmek,
karışmış iki kaydı tek kayıt gibi okutur.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.io.decoders.profile_c_folder import (
    COUNTER_CAPACITY,
    FolderError,
    Stream,
    aligned_counters,
    check_counter_sequence,
    discover,
)


def _make(root: Path, name: str = "2026-09-12T14-30-00Z") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    return folder


def _write(folder: Path, stream: str, counters: list[int], size: int = 64) -> None:
    directory = folder / stream
    directory.mkdir(exist_ok=True)
    for counter in counters:
        (directory / f"{stream}Data{counter:05d}.bin").write_bytes(bytes(size))


# --------------------------------------------------------------------------- #
# F7-028 — KLASOR DUZENI
# --------------------------------------------------------------------------- #


def test_a_well_formed_folder_is_discovered(tmp_path: Path) -> None:
    """Karşı yön: doğru bir klasör sorunsuz keşfedilmeli."""
    folder = _make(tmp_path)
    _write(folder, "Tx", [0, 1, 2])
    _write(folder, "Rx", [0, 1, 2])

    result = discover(folder)

    assert result.file_count == 6
    assert result.missing_streams == ()
    assert result.listing(Stream.TX).first_counter == 0
    assert result.listing(Stream.RX).last_counter == 2


def test_the_date_stamp_is_parsed_from_the_folder_name(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])

    assert discover(folder).stamp == "2026-09-12T14-30-00Z"


def test_a_collision_suffix_is_accepted(tmp_path: Path) -> None:
    """Aynı saniyede iki kayıt başlarsa `_2` soneki eklenir (§2.1)."""
    folder = _make(tmp_path, "2026-09-12T14-30-00Z_2")
    _write(folder, "Rx", [0])

    assert discover(folder).stamp == "2026-09-12T14-30-00Z"


def test_an_unparseable_folder_name_warns_but_does_not_fail(tmp_path: Path) -> None:
    """Ad kalıbı tutmuyorsa kayıt yine açılır; zaman dosyalardan okunur."""
    folder = _make(tmp_path, "eski-kayit")
    _write(folder, "Rx", [0])

    result = discover(folder)

    assert result.stamp is None
    assert any("tarih kalibina uymuyor" in w for w in result.warnings)


def test_a_missing_stream_is_not_an_error(tmp_path: Path) -> None:
    """Asıl kabul: yayın yapılmayan oturumda `Tx/` bulunmaz (§2.2)."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 1])

    result = discover(folder)

    assert result.missing_streams == (Stream.TX,)
    assert result.listing(Stream.RX).present is True
    assert result.file_count == 2


def test_a_folder_with_neither_stream_is_refused(tmp_path: Path) -> None:
    """İkisi de yoksa bu bir Profil C kaydı değildir."""
    folder = _make(tmp_path)
    (folder / "Tx").mkdir()

    with pytest.raises(FolderError, match="Profil C kayit klasoru degil"):
        discover(folder)


def test_a_path_that_is_not_a_directory_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "dosya.bin"
    target.write_bytes(b"x")

    with pytest.raises(FolderError, match="kayit klasoru degil"):
        discover(target)


def test_files_that_do_not_match_the_pattern_are_ignored(tmp_path: Path) -> None:
    """Klasörde başka dosyalar bulunabilir; kalıba uymayan atlanır."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 1])
    (folder / "Rx" / "notlar.txt").write_text("x", encoding="utf-8")
    (folder / "Rx" / "RxData9.bin").write_bytes(b"x")  # dolgusuz, kalip disi

    assert len(discover(folder).listing(Stream.RX).files) == 2


def test_a_tx_file_in_the_rx_folder_is_ignored(tmp_path: Path) -> None:
    """Yanlış klasördeki dosya, akıma ait sayılmaz."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])
    (folder / "Rx" / "TxData00005.bin").write_bytes(bytes(64))

    assert len(discover(folder).listing(Stream.RX).files) == 1
    assert discover(folder).listing(Stream.TX).present is False


# --------------------------------------------------------------------------- #
# F7-029 — SAYAC SIRASI
# --------------------------------------------------------------------------- #


def test_files_are_sorted_by_counter_not_by_name(tmp_path: Path) -> None:
    """Asıl kabul: dosya sistemi sırası bağlayıcı değildir.

    Dosyalar kasten karışık yaratılır. Sıralama sayaca göre yapılmazsa
    kayıt zamanda geri gider.
    """
    folder = _make(tmp_path)
    _write(folder, "Rx", [7, 2, 11, 0, 9])

    counters = [item.counter for item in discover(folder).listing(Stream.RX).files]

    assert counters == sorted(counters)
    assert counters == [0, 2, 7, 9, 11]


def test_a_gap_is_reported(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 1, 3, 4])

    listing = discover(folder).listing(Stream.RX)

    assert listing.gaps == (2,)
    assert any("eksik sayaclar" in issue for issue in check_counter_sequence(listing))


def test_multiple_gaps_are_all_reported(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 5, 10])

    assert discover(folder).listing(Stream.RX).gaps == (1, 2, 3, 4, 6, 7, 8, 9)


def test_a_gap_produces_a_warning_on_the_folder(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 2])

    assert any("sayac bosluk" in w for w in discover(folder).warnings)


def test_a_contiguous_sequence_reports_nothing(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", list(range(10)))

    assert check_counter_sequence(discover(folder).listing(Stream.RX)) == []


def test_a_counter_beyond_capacity_is_reported(tmp_path: Path) -> None:
    """Beş hane 100.000 saniyeyi kapsar; aşan bir sayaç tutarsızlıktır."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])
    (folder / "Rx" / "RxData99999.bin").write_bytes(bytes(64))

    listing = discover(folder).listing(Stream.RX)

    assert listing.last_counter == COUNTER_CAPACITY - 1
    assert check_counter_sequence(listing) != []  # bosluk raporlanir


def test_an_empty_stream_reports_nothing(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])

    assert check_counter_sequence(discover(folder).listing(Stream.TX)) == []


# --------------------------------------------------------------------------- #
# TX VE RX HIZALAMASI
# --------------------------------------------------------------------------- #


def test_matching_counters_mean_the_same_second(tmp_path: Path) -> None:
    """`TxData00042.bin` ile `RxData00042.bin` aynı saniyeye aittir (§2.3)."""
    folder = _make(tmp_path)
    _write(folder, "Tx", [0, 1, 2])
    _write(folder, "Rx", [0, 1, 2])

    assert aligned_counters(discover(folder)) == (0, 1, 2)


def test_a_second_without_a_transmission_is_normal(tmp_path: Path) -> None:
    """Yayın yapılmayan saniyede Tx dosyası üretilmez; kesişim küçülür."""
    folder = _make(tmp_path)
    _write(folder, "Tx", [0, 2])
    _write(folder, "Rx", [0, 1, 2, 3])

    result = discover(folder)

    assert aligned_counters(result) == (0, 2)
    assert len(result.listing(Stream.RX).files) == 4


def test_a_single_stream_aligns_with_itself(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 1])

    assert aligned_counters(discover(folder)) == (0, 1)


# --------------------------------------------------------------------------- #
# F7-030 — MANIFEST
# --------------------------------------------------------------------------- #


def test_a_manifest_is_read_when_present(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])
    (folder / "manifest.toml").write_text(
        'schema_id = "sonar-profile-c"\nsensor_count = 32\n', encoding="utf-8"
    )

    result = discover(folder)

    assert result.manifest is not None
    assert result.manifest["sensor_count"] == 32


def test_a_missing_manifest_is_a_warning_not_an_error(tmp_path: Path) -> None:
    """Manifest bulunmayabilir; bilgiler dosyalardan çıkarılır (§4)."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0])

    result = discover(folder)

    assert result.manifest is None
    assert any("manifest.toml bulunamadi" in w for w in result.warnings)


def test_a_broken_manifest_does_not_block_the_recording(tmp_path: Path) -> None:
    """Asıl kabul: bozuk bir özet yüzünden veri okunamaz olmamalı."""
    folder = _make(tmp_path)
    _write(folder, "Rx", [0, 1])
    (folder / "manifest.toml").write_text("bu = gecerli toml degil [[", encoding="utf-8")

    result = discover(folder)

    assert result.manifest is None
    assert result.file_count == 2
    assert any("okunamadi" in w for w in result.warnings)
    assert any("dosyalar esas alinacak" in w for w in result.warnings)


# --------------------------------------------------------------------------- #
# BOYUT VE OZET
# --------------------------------------------------------------------------- #


def test_the_total_byte_count_sums_both_streams(tmp_path: Path) -> None:
    folder = _make(tmp_path)
    _write(folder, "Tx", [0, 1], size=100)
    _write(folder, "Rx", [0, 1], size=200)

    result = discover(folder)

    assert result.listing(Stream.TX).total_bytes == 200
    assert result.listing(Stream.RX).total_bytes == 400
    assert result.total_bytes == 600


def test_the_ten_minute_ceiling_fits_the_counter(tmp_path: Path) -> None:
    """600 dosya, 100.000 kapasitenin çok altında (§2.4)."""
    assert COUNTER_CAPACITY > 600

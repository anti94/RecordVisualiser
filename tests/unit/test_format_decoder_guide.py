"""Format ve decoder kılavuzu — `F6-027`.

Kabul: **32/64 örnek, CRC'li ve akustik format sürümleri karıştırılmaz.**

Bir format belgesinin tek gerçek riski, koddan sessizce ayrılmasıdır:
yanlış bir bayt düzeni, olmayan bir garanti verir ve okuyanı yanlış
decoder yazmaya götürür. Bu yüzden testler kılavuzu **yalnız metin
olarak taramaz**; yazdığı sayıları üç bağımsız kaynağa karşı doğrular:

1. `io/profile_a_format.py` ve `io/profile_b_format.py` sabitleri,
2. `tests/fixtures/` altındaki **gerçek dosya baytları**,
3. decoder'ın çalışma zamanındaki davranışı (sürüm seçimi, ret kuralları).

Ayrıca kılavuzun asıl iddiası — "sürümleri karıştırmak sessizce yanlış
veri üretir" — prose olarak değil, yanlış sürümle okuyup sonucun
gerçekten bozuk çıktığı gösterilerek kanıtlanır.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from sonar_analyzer.io.decoders.crc import header_crc32
from sonar_analyzer.io.decoders.errors import (
    FormatError,
    HeaderContractError,
    UnsupportedVersionError,
)
from sonar_analyzer.io.decoders.version_dispatch import peek_version, select_decoder
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_HEADER_SIZE_V2,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    SUPPORTED_VERSIONS,
)
from sonar_analyzer.io.profile_a_format import (
    MAGIC as PROFILE_A_MAGIC,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_SAMPLE_RATE_HZ,
    SAMPLES_PER_BLOCK,
)
from sonar_analyzer.io.profile_b_format import (
    FILE_HEADER_SIZE as PROFILE_B_FILE_HEADER_SIZE,
)
from sonar_analyzer.io.profile_b_format import (
    MAGIC as PROFILE_B_MAGIC,
)
from sonar_analyzer.io.readers.binary_reader import read_data_record_v1, read_data_record_v2
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.header_writer import DEFAULT_FORMAT_VERSION

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "format" / "decoder-guide.md"
INVENTORY = ROOT / "docs" / "format" / "inventory.md"
FIXTURES = ROOT / "tests" / "fixtures"

V1_FIXTURE = FIXTURES / "valid_8records.bin"
V2_FIXTURE = FIXTURES / "valid_8records_v2.bin"
ACOUSTIC_FIXTURE = FIXTURES / "acoustic_8records.bin"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _inventory() -> str:
    return INVENTORY.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# BELGE VAR ve UC SURUMU AYIRIYOR
# --------------------------------------------------------------------------- #


def test_the_guide_exists() -> None:
    assert GUIDE.is_file()


def test_the_guide_names_all_three_versions_separately() -> None:
    """Üçü ayrı ayrı adlandırılmazsa zaten karıştırılmış olurlar."""
    text = _guide()
    for label in ("Profil A v1", "Profil A v2", "Profil B"):
        assert label in text, f"{label} ayri bir surum olarak adlandirilmamis"


def test_the_guide_states_the_consequence_of_mixing_versions() -> None:
    """Asıl tehlike hata değil, hatasız yanlıştır; belge bunu söylemeli."""
    text = _guide()
    assert "makul görünen yanlış veri" in text
    assert "hata vermez" in text


# --------------------------------------------------------------------------- #
# YAZILAN SAYILAR KOD SABITLERIYLE AYNI
# --------------------------------------------------------------------------- #


def test_the_documented_v1_sizes_match_the_code_constants() -> None:
    assert (EXPECTED_HEADER_SIZE_V1, EXPECTED_RECORD_SIZE_V1) == (32, 64)
    text = _guide()
    assert f"**{EXPECTED_HEADER_SIZE_V1} bayt**" in text
    assert f"**{EXPECTED_RECORD_SIZE_V1} bayt**" in text


def test_the_documented_v2_sizes_match_the_code_constants() -> None:
    assert (EXPECTED_HEADER_SIZE_V2, EXPECTED_RECORD_SIZE_V2) == (36, 68)
    text = _guide()
    assert f"**{EXPECTED_HEADER_SIZE_V2} bayt**" in text
    assert f"**{EXPECTED_RECORD_SIZE_V2} bayt**" in text


def test_the_documented_magics_match_the_code_constants() -> None:
    """İki profil ayrı magic taşır; belge ikisini de doğru yazmalı."""
    assert PROFILE_A_MAGIC == b"SONARBIN"
    assert PROFILE_B_MAGIC == b"SNRBIN\x1a\x00"
    text = _guide()
    assert "`SONARBIN`" in text
    assert r"`SNRBIN\x1a\x00`" in text


def test_the_documented_channel_count_matches_the_constant() -> None:
    assert EXPECTED_CHANNEL_COUNT == 8
    assert f"sabit **{EXPECTED_CHANNEL_COUNT}**" in _guide()


def test_the_documented_acoustic_numbers_match_the_constants() -> None:
    """48 kHz ve 6000 örnek, taslaktaki 96 kHz ile karıştırılmamalı."""
    assert ACOUSTIC_SAMPLE_RATE_HZ == 48_000
    assert SAMPLES_PER_BLOCK == 6_000
    text = _guide()
    assert "48 kHz" in text
    assert "6000 örnek" in text
    assert "96 kHz" not in text


def test_the_documented_profile_b_header_size_matches_the_constant() -> None:
    assert PROFILE_B_FILE_HEADER_SIZE == 256
    assert f"{PROFILE_B_FILE_HEADER_SIZE} bayt" in _guide()


def test_the_guide_names_the_written_version_and_it_is_v2() -> None:
    """Uygulamanın hangi sürümü *yazdığı* belirsiz kalmamalı."""
    assert DEFAULT_FORMAT_VERSION == 2
    text = _guide()
    assert "DEFAULT_FORMAT_VERSION = 2" in text
    assert "yalnız v2 yazar" in text


# --------------------------------------------------------------------------- #
# YAZILAN SAYILAR GERCEK FIXTURE BAYTLARIYLA AYNI
# --------------------------------------------------------------------------- #


def _header_fields(data: bytes) -> tuple[int, int, int]:
    """`(version, header_size, record_size)` — ham baytlardan, decoder'sız."""
    version, header_size = struct.unpack_from("<HH", data, 8)
    (record_size,) = struct.unpack_from("<I", data, 12)
    return int(version), int(header_size), int(record_size)


def test_the_v1_fixture_really_is_32_64_and_the_guide_says_so() -> None:
    data = V1_FIXTURE.read_bytes()
    assert _header_fields(data) == (1, 32, 64)
    assert len(data) == 32 + 8 * 64 == 544
    assert "544 bayt" in _guide()


def test_the_v2_fixture_really_is_36_68_and_the_guide_says_so() -> None:
    data = V2_FIXTURE.read_bytes()
    assert _header_fields(data) == (2, 36, 68)
    assert len(data) == 36 + 8 * 68 == 580
    assert "580 bayt" in _guide()


def test_the_acoustic_fixture_really_carries_the_profile_b_magic() -> None:
    data = ACOUSTIC_FIXTURE.read_bytes()
    assert data[:8] == PROFILE_B_MAGIC
    assert data[:8] != PROFILE_A_MAGIC
    assert "385 472 bayt" in _guide()
    assert len(data) == 385_472


def test_the_two_profile_a_fixtures_differ_by_exactly_the_crc_fields() -> None:
    """v2, v1'e 1 header + 8 kayıt CRC'si ekler: 4 × 9 = 36 bayt."""
    grew = len(V2_FIXTURE.read_bytes()) - len(V1_FIXTURE.read_bytes())
    assert grew == 4 * (1 + 8) == 36


# --------------------------------------------------------------------------- #
# KARISTIRMA GERCEKTEN SESSIZCE BOZUYOR (kilavuzun iddiasinin kaniti)
# --------------------------------------------------------------------------- #


def test_reading_a_v2_file_with_the_v1_record_layout_silently_corrupts() -> None:
    """Kılavuzun "hata vermez, sadece yanlış olur" iddiasının kanıtı.

    v2 dosyasının ikinci kaydını v1 yerleşimiyle (4 bayt eksik adım)
    okumak `struct` hatası vermez; sonuç yalnız *yanlış* olur.
    """
    data = V2_FIXTURE.read_bytes()

    correct = read_data_record_v2(data, 36 + 68)
    assert correct.name.split(b"\x00", 1)[0] == b"Data00001"

    # v1 gibi davranmak: 32 baytlik header + 64 baytlik adim varsaymak.
    wrong = read_data_record_v1(data, 32 + 64)
    assert wrong.name.split(b"\x00", 1)[0] != b"Data00001"


def test_the_version_field_is_readable_without_knowing_the_version() -> None:
    """Sürüm alanı her iki sürümde de aynı offsette; belge bunu söyler."""
    assert peek_version(V1_FIXTURE.read_bytes()) == 1
    assert peek_version(V2_FIXTURE.read_bytes()) == 2
    assert "offset 8" in _guide()


# --------------------------------------------------------------------------- #
# RET KURALLARI GERCEKTEN VAR
# --------------------------------------------------------------------------- #


def test_flipping_only_the_version_field_is_rejected() -> None:
    """v1 dosyasının sürümünü 2 yapmak onu v2 yapmaz; dosya açılmamalı.

    Bu durumda **CRC denetimi önce** çalışır: sürüm 2 iddia eden bir
    dosyada, header'ın son dört baytı CRC sanılır ve tutmaz. Hata türü
    `HeaderCrcMismatchError`'dir — sözleşme hatası değil, ama ikisi de
    `FormatError` ailesindendir ve sonuç aynıdır: dosya açılmaz.
    """
    data = bytearray(V1_FIXTURE.read_bytes())
    struct.pack_into("<H", data, 8, 2)  # yalnizca surum alanini 2 yap

    with pytest.raises(FormatError):
        read_validated_header(bytes(data))


def test_a_version_size_mismatch_is_rejected_not_guessed() -> None:
    """CRC'si doğru ama `record_size`'ı yanlış bir v2 dosyası da açılmamalı.

    Önceki test CRC kapısında duruyordu; burada CRC **kasten yeniden
    hesaplanır**, böylece denetlenen şey gerçekten boyut sözleşmesidir:
    "sürüm 2 diyor ama 64 baytlık kayıt bildiriyor" tahminle
    çözülmez.
    """
    data = bytearray(V2_FIXTURE.read_bytes())
    struct.pack_into("<I", data, 12, EXPECTED_RECORD_SIZE_V1)  # 68 -> 64
    struct.pack_into("<I", data, 32, header_crc32(bytes(data[:32])))  # CRC'yi gecerli kil

    with pytest.raises(HeaderContractError) as excinfo:
        read_validated_header(bytes(data))
    assert excinfo.value.byte_offset == 12  # record_size alani


def test_an_unsupported_version_is_rejected_not_downgraded() -> None:
    """Bilinmeyen sürüm en yakın sürüme düşürülmez."""
    assert 99 not in SUPPORTED_VERSIONS
    with pytest.raises(UnsupportedVersionError):
        select_decoder(99)


def test_the_guide_documents_both_rejection_rules() -> None:
    text = _guide()
    assert "HeaderContractError" in text
    assert "UnsupportedVersionError" in text
    assert "en yakın sürüme düşülmez" in text


def test_the_guide_distinguishes_header_crc_from_record_crc() -> None:
    """İkisini aynı sertlikte ele almak ya veri kaybettirir ya bozuk geçirir."""
    text = _guide()
    assert "Header CRC hatası" in text
    assert "Kayıt CRC hatası" in text
    assert "Fatal" in text and "değil" in text


def test_the_guide_rules_out_silent_version_conversion() -> None:
    text = _guide()
    assert "dönüştürme" in text.lower()
    assert "yapılmaz" in text


# --------------------------------------------------------------------------- #
# ENVANTER ARTIK ESKI DEGIL
# --------------------------------------------------------------------------- #


def test_the_inventory_no_longer_claims_profile_a_has_no_crc() -> None:
    """Eski satır "CRC alanı yok" diyordu; v2 CRC'lidir ve sevk edilen sürümdür."""
    assert "CRC alanı yok; `F0-008` ayrı sürüm tanımlar" not in _inventory()


def test_the_inventory_no_longer_marks_implemented_profiles_as_draft() -> None:
    text = _inventory()
    assert "| Bölüm 8.2 | Taslak |" not in text
    assert "| Bölüm 8.3 | Taslak |" not in text


def test_the_inventory_lists_all_three_versions_with_their_sizes() -> None:
    text = _inventory()
    assert "**Profil A v1**" in text
    assert "**Profil A v2**" in text
    assert "32 B header + 64 B kayıt" in text
    assert "36 B header + 68 B kayıt" in text


def test_the_inventory_fixture_table_matches_the_files_on_disk() -> None:
    """Tabloda adı geçen her fixture gerçekten var olmalı."""
    text = _inventory()
    for path in (V1_FIXTURE, V2_FIXTURE, ACOUSTIC_FIXTURE):
        assert path.is_file(), f"{path.name} diskte yok"
        assert f"`{path.name}`" in text, f"{path.name} envanterde yok"


def test_the_inventory_no_longer_lists_fixtures_that_were_never_produced() -> None:
    """Üretilmemiş dosyaları listelemek, var sanılmalarına yol açar."""
    text = _inventory()
    for stale in ("acoustic_5s_4ch.bin", "large_1h.bin"):
        assert stale not in text
        assert not (FIXTURES / stale).exists()


def test_the_inventory_and_the_guide_point_at_each_other() -> None:
    assert "decoder-guide.md" in _inventory()
    assert "inventory.md" in _guide()

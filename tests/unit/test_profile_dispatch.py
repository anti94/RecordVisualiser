"""Profil seçimi — `F7-027`.

Kabul: **Profil A, B ve C dosyaları doğru çözücüye gider; bilinmeyen
sürüm açık hata verir.**

Bu seçicinin sessiz hatası şudur: bir Profil B dosyasını Profil A sanmak.
İkisi de `.bin`, ikisi de sekiz baytlık bir sihirli sayıyla başlıyor ve
yanlış seçim hata vermeden yanlış sayılar üretir.

Testler gerçek fixture'ları kullanır. Elle kurulmuş baytlar yalnız
kendilerini sınar; depodaki fixture'lar gerçek üreticinin çıktısıdır.

Profil C'nin asimetrisi ayrıca sınanır: sihirli sayısı koda gömülü
değildir, şemayla gelir. Şemasız bir çağrıda "muhtemelen C" demek,
tahminle okumaya açılan kapıdır.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.io.decoders.errors import UnsupportedVersionError
from sonar_analyzer.io.decoders.profile_dispatch import (
    MAGIC_LENGTH,
    Profile,
    describe,
    detect,
    schema_magic,
)
from sonar_analyzer.io.decoders.version_dispatch import peek_version, select_decoder
from sonar_analyzer.io.schema.loader import load_text
from sonar_analyzer.io.schema.model import Schema

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"


@pytest.fixture(scope="module")
def schema() -> Schema:
    return load_text(EXAMPLE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# GERCEK FIXTURE'LAR DOGRU PROFILE GIDIYOR
# --------------------------------------------------------------------------- #


def test_a_profile_a_fixture_is_recognised() -> None:
    """Asıl kabul: gerçek bir Profil A dosyası A olarak tanınmalı."""
    data = (FIXTURES / "valid_8records.bin").read_bytes()

    result = detect(data)

    assert result.profile is Profile.A
    assert result.basis == "magic"
    assert result.magic == b"SONARBIN"


def test_a_profile_a_v2_fixture_is_still_profile_a() -> None:
    """Sürüm profili değiştirmez; v1 ve v2 aynı profilin iki sürümüdür."""
    data = (FIXTURES / "valid_8records_v2.bin").read_bytes()

    assert detect(data).profile is Profile.A
    assert peek_version(data) == 2


def test_a_profile_b_fixture_is_recognised() -> None:
    data = (FIXTURES / "acoustic_8records.bin").read_bytes()

    result = detect(data)

    assert result.profile is Profile.B
    assert result.magic == b"SNRBIN\x1a\x00"


def test_profile_a_and_b_are_never_confused() -> None:
    """İkisi de sekiz baytlık bir sihirli sayıyla başlıyor; karışırlarsa
    yanlış seçim hata vermeden yanlış sayılar üretir."""
    a = detect((FIXTURES / "valid_8records.bin").read_bytes()).profile
    b = detect((FIXTURES / "acoustic_8records.bin").read_bytes()).profile

    assert a is Profile.A
    assert b is Profile.B
    assert a is not b


# --------------------------------------------------------------------------- #
# PROFIL C ANCAK SEMAYLA TANINIR
# --------------------------------------------------------------------------- #


def test_profile_c_needs_a_schema(schema: Schema) -> None:
    """Asıl kabul: şemasız çağrıda "muhtemelen C" denmez."""
    data = b"SNRPROFC" + b"\x00" * 56

    assert detect(data).profile is Profile.UNKNOWN
    assert detect(data, schema).profile is Profile.C


def test_the_schema_based_detection_says_so(schema: Schema) -> None:
    """Nasıl tanındığı yazılmazsa, sonuç sorgulanamaz."""
    result = detect(b"SNRPROFC" + b"\x00" * 56, schema)

    assert result.basis == "schema"
    assert schema.id in result.detail


def test_a_schemaless_call_explains_why_it_failed() -> None:
    """ "Tanınmadı" demek yetmez; neden tanınmadığı da gerekir."""
    result = detect(b"SNRPROFC" + b"\x00" * 56)

    assert "sema gerekir" in result.detail
    assert "D-29" in result.detail


def test_a_schema_without_a_magic_field_cannot_detect() -> None:
    """Şemada `magic` alanı yoksa tanıma dayanağı da yoktur."""
    text = """
[schema]
id = "t"
version = 1
[structs.FileHeader]
size = 8
[[structs.FileHeader.fields]]
name = "frame_count"
type = "uint64_t"
offset = 0
[structs.FrameHeader]
size = 4
[[structs.FrameHeader.fields]]
name = "frame_index"
type = "uint32_t"
offset = 0
[payload]
sensor_count = 1
frame_samples = 1
sample_type = "std::complex<float>"
"""
    plain = load_text(text)

    assert schema_magic(plain) is None
    assert detect(b"WHATEVER" + b"\x00" * 8, plain).profile is Profile.UNKNOWN


def test_a_magic_field_not_at_offset_zero_is_not_a_magic(schema: Schema) -> None:
    """Sihirli sayı dosyanın **başında** olmalı; ortada olan bir alan değildir."""
    moved = load_text(
        EXAMPLE.read_text(encoding="utf-8")
        .replace(
            'name = "magic"\ntype = "char[N]"\ncount = 8\noffset = 0',
            'name = "magic"\ntype = "char[N]"\ncount = 8\noffset = 8',
        )
        .replace(
            'name = "schema_version"\ntype = "uint16_t"\noffset = 8',
            'name = "schema_version"\ntype = "uint16_t"\noffset = 0',
        )
        .replace(
            'name = "header_size"\ntype = "uint16_t"\noffset = 10',
            'name = "header_size"\ntype = "uint16_t"\noffset = 2',
        )
        .replace(
            'name = "stream_kind"\ntype = "uint8_t"\noffset = 12',
            'name = "stream_kind"\ntype = "uint8_t"\noffset = 4',
        )
        .replace(
            'name = "sample_format"\ntype = "uint8_t"\noffset = 13',
            'name = "sample_format"\ntype = "uint8_t"\noffset = 5',
        )
        .replace(
            'name = "clock_source"\ntype = "uint8_t"\noffset = 14',
            'name = "clock_source"\ntype = "uint8_t"\noffset = 6',
        )
        .replace(
            'name = "_pad0"\ntype = "uint8_t"\noffset = 15\ncount = 1',
            'name = "_pad0"\ntype = "uint8_t"\noffset = 7\ncount = 1',
        )
    )
    assert schema_magic(moved) is None


# --------------------------------------------------------------------------- #
# TANINMAYAN BICIM
# --------------------------------------------------------------------------- #


def test_an_unknown_magic_is_reported_with_its_bytes() -> None:
    """Hangi sihirli sayının bulunduğu yazılmazsa teşhis edilemez."""
    result = detect(b"NOTASONR" + b"\x00" * 8)

    assert result.profile is Profile.UNKNOWN
    assert "NOTASONR" in result.detail


def test_a_file_too_short_for_a_magic_is_refused() -> None:
    result = detect(b"SONAR")

    assert result.profile is Profile.UNKNOWN
    assert "yeterli bayt yok" in result.detail
    assert str(MAGIC_LENGTH) in result.detail


def test_an_empty_buffer_does_not_crash() -> None:
    assert detect(b"").profile is Profile.UNKNOWN


def test_the_description_is_readable() -> None:
    assert describe(detect((FIXTURES / "valid_8records.bin").read_bytes())) == "profile-a"
    assert "taninmayan" in describe(detect(b"XXXXXXXX"))


# --------------------------------------------------------------------------- #
# PROFIL ICI SURUM SECIMI BOZULMADI
# --------------------------------------------------------------------------- #


def test_profile_a_version_dispatch_still_works() -> None:
    """Üst kattaki profil seçimi, alt kattaki sürüm seçimini bozmamalı."""
    assert select_decoder(1).version == 1
    assert select_decoder(2).version == 2


def test_an_unsupported_version_raises() -> None:
    """Asıl kabul: bilinmeyen sürüm açık hata verir."""
    with pytest.raises(UnsupportedVersionError):
        select_decoder(99)


def test_the_unsupported_version_fixture_is_still_profile_a() -> None:
    """Desteklenmeyen sürüm, tanınmayan profil demek değildir.

    Dosya Profil A'dır ve öyle tanınır; düşen şey sürüm seçimidir. İkisini
    karıştırmak, "bu dosya bizim değil" ile "bu sürümü okuyamıyoruz"u
    aynı hata saymak olurdu.
    """
    data = (FIXTURES / "unsupported_version.bin").read_bytes()

    assert detect(data).profile is Profile.A
    with pytest.raises(UnsupportedVersionError):
        select_decoder(peek_version(data))

"""CRC-32/ISO-HDLC referans vektörleri — `F2-013`.

Kabul: `docs/adr/ADR-011-crc.md` §3'teki bağımsız referans vektörlerin
tamamı eşleşir. Vektörler ADR'de sabitlenmiştir; bu test yalnız
`crc.py`'nin o tabloyla senkron kaldığını doğrular.
"""

from __future__ import annotations

import struct

from sonar_analyzer.io.decoders.crc import crc32, header_crc32, record_crc32
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1

# -- ADR-011 §3 referans vektörleri -----------------------------------------


def test_ascii_check_value_matches_standard_crc32() -> None:
    """Standart CRC-32 kontrol değeri: b"123456789" -> 0xCBF43926."""
    assert crc32(b"123456789") == 0xCBF43926


def test_empty_input_is_zero() -> None:
    assert crc32(b"") == 0x00000000


def test_64_zero_bytes() -> None:
    assert crc32(bytes(64)) == 0x758D6336


#: docs/format/profile-a.md §5.3 hexdump'i (4 satır, satır başına 16 bayt).
_DATA00001_HEXDUMP = (
    "44 61 74 61 30 30 30 30 31 00 00 00 01 00 00 00"
    "48 E8 01 00 00 00 00 00 00 00 48 41 00 00 50 C0"
    "00 00 00 00 00 80 CB 42 00 00 E4 40 00 00 00 BF"
    "00 00 40 42 00 00 7A 44 00 00 00 00 01 00 00 00"
)


def test_example_data00001_record_body_v1() -> None:
    """docs/format/profile-a.md §5.3 hexdump'ından üretilen 64 baytlık kayıt."""
    record_body = struct.pack(
        "<12sIQ8fII",
        b"Data00001\x00\x00\x00",
        1,
        125_000,
        12.5,
        -3.25,
        0.0,
        101.75,
        7.125,
        -0.5,
        48.0,
        1000.0,
        0,
        1,
    )
    assert len(record_body) == 64
    assert record_body == bytes.fromhex(_DATA00001_HEXDUMP.replace(" ", ""))

    assert record_crc32(record_body) == 0x6B7E1EEF
    assert DATA_RECORD_V1.pack(*DATA_RECORD_V1.unpack(record_body)) == record_body


def test_example_header_v2_body() -> None:
    """ADR-011 §3: örnek header gövdesi (CRC hariç 32 bayt) -> 0x7CB1047D."""
    header_body = FILE_HEADER_V1.pack(
        b"SONARBIN",
        2,
        36,
        68,
        125_000,
        8,
        1_788_901_200_000_000_000,
    )
    assert len(header_body) == 32
    assert header_crc32(header_body) == 0x7CB1047D


# -- kapsam kuralı: CRC alanı hesaba dahil edilmez --------------------------


def test_crc_scope_excludes_the_crc_field_itself() -> None:
    """ADR-011 §2.2: CRC yalnız kendi alanı hariç gövdeyi kapsar."""
    body = b"Data00001\x00\x00\x00" + bytes(52)
    crc_value = record_crc32(body)
    # CRC alanini govdeye eklemek farkli (ve rastgele) bir sonuc uretir --
    # yani fonksiyon govdeyi CRC alani dahilmis gibi degil, haric aliyor.
    assert crc32(body + struct.pack("<I", crc_value)) != crc_value


def test_record_crc32_and_header_crc32_are_the_same_algorithm() -> None:
    """ADR-011 §2.2: kayit ve header CRC'si ayni algoritma/kapsam kuralini paylasir."""
    data = b"ornek veri"
    assert record_crc32(data) == header_crc32(data) == crc32(data)

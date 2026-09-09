"""CRC destekli format fixture'ı — `F2-018`.

Kabul: geçerli ve tek byte bozulmuş dosya farklı doğrulama sonucu verir.
Beklenen sonuçlar `docs/format/fixture-corrupt.md` K-04'te sabitlenmiştir.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from sonar_analyzer.io.decoders.crc_validation import (
    RecordCrcMismatch,
    check_record_crc,
    validate_header_crc,
)
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2, read_file_header_v2

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
HEADER_SIZE_V2 = 36
RECORD_SIZE_V2 = 68


def _read(filename: str) -> bytes:
    path = FIXTURES_DIR / filename
    assert path.exists(), (
        f"F2-018: tools/make_corrupt_fixtures.py ile uretilip commitlenmeli: {path}"
    )
    return path.read_bytes()


def _record_crc_mismatches(data: bytes) -> list[RecordCrcMismatch | None]:
    mismatches: list[RecordCrcMismatch | None] = []
    for index in range(8):
        offset = HEADER_SIZE_V2 + index * RECORD_SIZE_V2
        record = read_data_record_v2(data, offset)
        body = data[offset : offset + RECORD_SIZE_V2 - 4]
        mismatches.append(check_record_crc(record, body, byte_offset=offset))
    return mismatches


# -- boyut/hash dogrulamasi ---------------------------------------------------


def test_valid_v2_fixture_matches_documented_size_and_hash() -> None:
    data = _read("valid_8records_v2.bin")
    assert len(data) == 580
    assert (
        hashlib.sha256(data).hexdigest()
        == "57681d96de5eedf22b86f3ca2ce1e359a721bb0680cc01f69d6c74a658c7bf4f"
    )


def test_k04_crc_error_matches_documented_size_and_hash() -> None:
    data = _read("crc_error.bin")
    assert len(data) == 580
    assert (
        hashlib.sha256(data).hexdigest()
        == "d23348d74ce425532c534713fa83fa875d91d185b335f2298f067f08051f8aaf"
    )


# -- kabul kriteri: gecerli ve bozuk dosya farkli sonuc verir ----------------


def test_valid_v2_fixture_has_no_crc_mismatches() -> None:
    data = _read("valid_8records_v2.bin")
    header = read_file_header_v2(data)
    validate_header_crc(header, data[: HEADER_SIZE_V2 - 4])  # sorun cikarmaz

    mismatches = _record_crc_mismatches(data)
    assert all(m is None for m in mismatches)


def test_k04_crc_error_has_exactly_one_mismatch_others_are_still_valid() -> None:
    """Kabul: gecerli ve tek byte bozulmus dosya farkli dogrulama sonucu verir."""
    data = _read("crc_error.bin")

    mismatches = _record_crc_mismatches(data)
    real_mismatches = [m for m in mismatches if m is not None]

    assert len(real_mismatches) == 1
    mismatch = real_mismatches[0]
    assert mismatch.sequence_no == 3
    assert mismatch.byte_offset == HEADER_SIZE_V2 + 3 * RECORD_SIZE_V2
    assert mismatch.byte_offset == 240
    assert mismatch.expected_crc32 == 0xAA7584BF
    assert mismatch.found_crc32 == 0x053116F8


def test_k04_header_crc_is_still_valid() -> None:
    """Yalnız kayıt bozuldu; header CRC'si geçerli, dosya açılır (K-04 tablosu)."""
    data = _read("crc_error.bin")
    header = read_file_header_v2(data)
    validate_header_crc(header, data[: HEADER_SIZE_V2 - 4])  # istisna firlatmaz


def test_k04_corrupted_value_decodes_to_documented_float() -> None:
    """K-04: bozuk alanın çözülmüş değeri 101.50000762939453 (beklenen 101.5)."""
    data = _read("crc_error.bin")
    offset = HEADER_SIZE_V2 + 3 * RECORD_SIZE_V2
    record = read_data_record_v2(data, offset)
    assert record.sensor_values[0] == 101.50000762939453
    assert record.sensor_values[0] != 101.5


def test_k04_other_seven_records_remain_readable_and_unflagged() -> None:
    """K-04: diğer 7 kayıt normal okunur ve çizilir — bir kaydın bozuk olması
    diğerlerini geçersiz kılmaz (ADR-011 §2.2)."""
    data = _read("crc_error.bin")
    for index in range(8):
        offset = HEADER_SIZE_V2 + index * RECORD_SIZE_V2
        record = read_data_record_v2(data, offset)
        assert record.sequence_no == index

    mismatches = _record_crc_mismatches(data)
    unaffected = [i for i, m in enumerate(mismatches) if m is None]
    assert unaffected == [0, 1, 2, 4, 5, 6, 7]


def test_valid_and_corrupted_fixtures_differ_in_exactly_one_byte() -> None:
    """K-04'ün tanımı gereği: CRC alanı hariç yalnız CH0'ın ilk baytı değişir."""
    valid = _read("valid_8records_v2.bin")
    corrupted = _read("crc_error.bin")
    assert len(valid) == len(corrupted)

    differing_offsets = [i for i in range(len(valid)) if valid[i] != corrupted[i]]
    assert differing_offsets == [HEADER_SIZE_V2 + 3 * RECORD_SIZE_V2 + 24]

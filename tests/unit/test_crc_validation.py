"""CRC alanlı format doğrulaması — `F2-014`.

Kabul: tek byte bozulması yakalanır; CRC'siz örnek dosya doğrulanmış
sayılmaz.
"""

from __future__ import annotations

import pytest
from tests.golden_bytes import build_valid_fixture, build_valid_v2_fixture

from sonar_analyzer.io.decoders.crc_validation import (
    HeaderCrcMismatchError,
    RecordCrcMismatch,
    check_record_crc,
    is_crc_validated,
    validate_header_crc,
)
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2, read_file_header_v2

HEADER_SIZE_V2 = 36
RECORD_SIZE_V2 = 68


def test_valid_v2_header_crc_passes() -> None:
    buffer = build_valid_v2_fixture()
    header = read_file_header_v2(buffer)
    validate_header_crc(header, buffer[: HEADER_SIZE_V2 - 4])  # sorun cikarmaz


def test_valid_v2_records_have_no_crc_mismatch() -> None:
    buffer = build_valid_v2_fixture()
    for index in range(8):
        offset = HEADER_SIZE_V2 + index * RECORD_SIZE_V2
        record = read_data_record_v2(buffer, offset)
        body = buffer[offset : offset + RECORD_SIZE_V2 - 4]
        assert check_record_crc(record, body, byte_offset=offset) is None


def test_single_byte_corruption_in_record_is_caught() -> None:
    """Kabul kriteri: tek byte bozulması yakalanır."""
    buffer = bytearray(build_valid_v2_fixture())
    target_index = 3
    offset = HEADER_SIZE_V2 + target_index * RECORD_SIZE_V2
    # Sensor_values alani icinde tek bayti boz (CRC alanina dokunma).
    corrupt_at = offset + 20
    buffer[corrupt_at] ^= 0xFF

    frozen = bytes(buffer)
    record = read_data_record_v2(frozen, offset)
    body = frozen[offset : offset + RECORD_SIZE_V2 - 4]

    mismatch = check_record_crc(record, body, byte_offset=offset)

    assert mismatch is not None
    assert isinstance(mismatch, RecordCrcMismatch)
    assert mismatch.byte_offset == offset
    assert mismatch.sequence_no == target_index
    assert mismatch.expected_crc32 == record.record_crc32
    assert mismatch.found_crc32 != mismatch.expected_crc32


def test_corrupted_record_is_still_readable_not_dropped() -> None:
    """ADR-011 §2.4: kayıt CRC hatasında atılmaz, yalnız işaretlenir."""
    buffer = bytearray(build_valid_v2_fixture())
    offset = HEADER_SIZE_V2 + 2 * RECORD_SIZE_V2
    buffer[offset + 5] ^= 0x01
    frozen = bytes(buffer)

    # Kayit yine sorunsuz cozulebilir; check_record_crc bunu engellemez.
    record = read_data_record_v2(frozen, offset)
    assert record.sequence_no == 2


def test_other_records_are_unaffected_by_one_corrupted_record() -> None:
    """Bir kaydın bozuk olması diğerlerini geçersiz kılmaz (ADR-011 §2.2)."""
    buffer = bytearray(build_valid_v2_fixture())
    offset = HEADER_SIZE_V2 + 3 * RECORD_SIZE_V2
    buffer[offset + 10] ^= 0xFF
    frozen = bytes(buffer)

    mismatches: list[RecordCrcMismatch | None] = []
    for index in range(8):
        rec_offset = HEADER_SIZE_V2 + index * RECORD_SIZE_V2
        record = read_data_record_v2(frozen, rec_offset)
        body = frozen[rec_offset : rec_offset + RECORD_SIZE_V2 - 4]
        mismatches.append(check_record_crc(record, body, byte_offset=rec_offset))

    real_mismatches = [m for m in mismatches if m is not None]
    assert len(real_mismatches) == 1
    assert real_mismatches[0].sequence_no == 3


def test_corrupted_header_crc_raises_fatal_error() -> None:
    """ADR-011 §2.4: header CRC hatasında boyut alanları güvenilmez, dosya açılmaz."""
    buffer = bytearray(build_valid_v2_fixture())
    buffer[10] ^= 0xFF  # header govdesi icinde, header_crc32 alanina dokunmadan
    frozen = bytes(buffer)

    header = read_file_header_v2(frozen)
    with pytest.raises(HeaderCrcMismatchError) as excinfo:
        validate_header_crc(header, frozen[: HEADER_SIZE_V2 - 4])
    assert excinfo.value.expected == header.header_crc32
    assert excinfo.value.found != header.header_crc32


def test_v1_sample_file_is_not_considered_crc_validated() -> None:
    """Kabul kriteri: CRC'siz örnek dosya doğrulanmış sayılmaz."""
    buffer = build_valid_fixture()
    from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

    header = read_file_header_v1(buffer)
    assert header.version == 1
    assert is_crc_validated(header.version) is False


def test_v2_sample_file_is_crc_validated() -> None:
    buffer = build_valid_v2_fixture()
    header = read_file_header_v2(buffer)
    assert is_crc_validated(header.version) is True


def test_record_crc_mismatch_str_shape() -> None:
    mismatch = RecordCrcMismatch(
        byte_offset=240, sequence_no=3, expected_crc32=0x11223344, found_crc32=0x55667788
    )
    assert str(mismatch) == (
        "CRC_ERROR: seq 3, offset 240, beklenen 0x11223344, bulunan 0x55667788"
    )

"""Profil A alan sabitleri ve veri modeli — `F2-001`.

Kabul: örnek alan offsetleri toplam 32 byte ile eşleşir.
"""

from __future__ import annotations

import dataclasses
import struct

import pytest

from sonar_analyzer.io.profile_a_format import (
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_HEADER_SIZE_V2,
    EXPECTED_PERIOD_US,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    FILE_HEADER_V1,
    FILE_HEADER_V2,
    MAGIC,
    RECORD_PERIOD_NS,
    SUPPORTED_VERSIONS,
    DataRecordV1,
    FileHeaderV1,
    record_name,
)


def test_header_v1_struct_is_32_bytes() -> None:
    """Kabul kriteri: örnek alan offsetleri toplam 32 byte ile eşleşir."""
    assert FILE_HEADER_V1.size == 32 == EXPECTED_HEADER_SIZE_V1


def test_record_v1_struct_is_64_bytes() -> None:
    assert DATA_RECORD_V1.size == 64 == EXPECTED_RECORD_SIZE_V1


def test_header_v2_struct_is_36_bytes() -> None:
    assert FILE_HEADER_V2.size == 36 == EXPECTED_HEADER_SIZE_V2


def test_record_v2_struct_is_68_bytes() -> None:
    assert DATA_RECORD_V2.size == 68 == EXPECTED_RECORD_SIZE_V2


def test_v2_is_v1_body_plus_crc_field() -> None:
    """ADR-011: v2 = v1 gövdesi + crc32 alanı."""
    assert FILE_HEADER_V2.size == FILE_HEADER_V1.size + 4
    assert DATA_RECORD_V2.size == DATA_RECORD_V1.size + 4


def test_constants_match_documented_contract() -> None:
    assert MAGIC == b"SONARBIN"
    assert frozenset({1, 2}) == SUPPORTED_VERSIONS
    assert EXPECTED_PERIOD_US == 125_000
    assert EXPECTED_CHANNEL_COUNT == 8
    assert RECORD_PERIOD_NS == 125_000_000


def test_header_v1_offsets_match_profile_a_md() -> None:
    """docs/format/profile-a.md §2 offset tablosuyla birebir."""
    offsets: dict[str, int] = {}
    offset = 0
    for name, fmt in (
        ("magic", "8s"),
        ("version", "H"),
        ("header_size", "H"),
        ("record_size", "I"),
        ("period_us", "I"),
        ("channel_count", "I"),
        ("start_time_utc_ns", "Q"),
    ):
        offsets[name] = offset
        offset += struct.calcsize("<" + fmt)

    assert offsets == {
        "magic": 0,
        "version": 8,
        "header_size": 10,
        "record_size": 12,
        "period_us": 16,
        "channel_count": 20,
        "start_time_utc_ns": 24,
    }
    assert offset == 32


def test_record_v1_offsets_match_profile_a_md() -> None:
    """docs/format/profile-a.md §5 offset tablosuyla birebir."""
    offsets: dict[str, int] = {}
    offset = 0
    for name, fmt in (
        ("name", "12s"),
        ("sequence_no", "I"),
        ("elapsed_us", "Q"),
        ("sensor_values", "8f"),
        ("bit_status", "I"),
        ("tx_status", "I"),
    ):
        offsets[name] = offset
        offset += struct.calcsize("<" + fmt)

    assert offsets == {
        "name": 0,
        "sequence_no": 12,
        "elapsed_us": 16,
        "sensor_values": 24,
        "bit_status": 56,
        "tx_status": 60,
    }
    assert offset == 64


def test_data00001_hexdump_matches_profile_a_md() -> None:
    """docs/format/profile-a.md §5.3'teki Data00001 hexdump'ı yeniden üretir."""
    values = (12.5, -3.25, 0.0, 101.75, 7.125, -0.5, 48.0, 1000.0)
    packed = DATA_RECORD_V1.pack(b"Data00001", 1, 125_000, *values, 0, 1)
    expected = bytes.fromhex(
        "446174613030303031000000"
        "01000000"
        "48e801000000000000004841"
        "000050c0"
        "0000000000 80cb4200 00e440"
        "000000bf"
        "00004042"
        "00007a44"
        "00000000"
        "01000000".replace(" ", "")
    )
    assert packed == expected


def test_record_name_does_not_wrap() -> None:
    """docs/format/timing-and-naming.md §2: ad sarmaz."""
    assert record_name(0) == "Data00000"
    assert record_name(1) == "Data00001"
    assert record_name(99_999) == "Data99999"
    assert record_name(100_000) == "Data100000"


def test_file_header_v1_is_immutable() -> None:
    header = FileHeaderV1(
        magic=b"SONARBIN",
        version=1,
        header_size=32,
        record_size=64,
        period_us=125_000,
        channel_count=8,
        start_time_utc_ns=0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        header.version = 2  # type: ignore[misc]


def test_data_record_v1_is_immutable() -> None:
    record = DataRecordV1(
        name=b"Data00000",
        sequence_no=0,
        elapsed_us=0,
        sensor_values=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        bit_status=0,
        tx_status=0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.sequence_no = 1  # type: ignore[misc]

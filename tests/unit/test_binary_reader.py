"""Little-endian header/kayıt okuyucusu — `F2-002`.

Kabul: bilinen header tüm beklenen sayısal değerleri üretir.

Golden bayt dizisi `docs/format/fixture-valid-8records.md` §1'deki
deterministik formüllerden üretilir; belgedeki SHA-256 ile çapraz kontrol
edilir, böylece formül belgeyle senkron kalır.
"""

from __future__ import annotations

import hashlib
import struct

import pytest

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1
from sonar_analyzer.io.readers.binary_reader import (
    read_data_record_v1,
    read_file_header_v1,
)

START_TIME_UTC_NS = 1_788_901_200_000_000_000
CHANNEL_COUNT = 8

#: docs/format/fixture-valid-8records.md §6.
EXPECTED_SHA256 = "5094b9b0bc585518cf7fa9dc372d3e997f32b59caeb156cb4c0f9ab9d039fce9"


def _sensor_values(n: int) -> tuple[float, float, float, float, float, float, float, float]:
    return (
        100.0 + 0.5 * n,
        25.0,
        0.125 * n,
        0.0 - 0.125 * n,  # negatif sifir uretmeyen bicim (belgedeki uyari)
        1.0,
        2.5 if n % 2 == 0 else -2.5,
        10.0 + 0.25 * n,
        48.0,
    )


def build_valid_fixture() -> bytes:
    """`docs/format/fixture-valid-8records.md` §1'deki formüllerden dosyayı üretir."""
    header = FILE_HEADER_V1.pack(b"SONARBIN", 1, 32, 64, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS)
    body = bytearray(header)
    for n in range(8):
        bit_status = 0x00000100 if n == 4 else 0
        tx_status = 1 if 2 <= n <= 5 else 0
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *_sensor_values(n),
            bit_status,
            tx_status,
        )
    return bytes(body)


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return build_valid_fixture()


def test_fixture_matches_documented_hash(fixture_bytes: bytes) -> None:
    """Formül belgeyle senkron değilse bu test en önce kırılır."""
    assert len(fixture_bytes) == 544
    assert hashlib.sha256(fixture_bytes).hexdigest() == EXPECTED_SHA256


# -- header ------------------------------------------------------------


def test_header_fields_are_all_present(fixture_bytes: bytes) -> None:
    """Kabul kriteri: bilinen header tüm beklenen sayısal değerleri üretir."""
    header = read_file_header_v1(fixture_bytes)

    assert header.magic == b"SONARBIN"
    assert header.version == 1
    assert header.header_size == 32
    assert header.record_size == 64
    assert header.period_us == 125_000
    assert header.channel_count == 8
    assert header.start_time_utc_ns == START_TIME_UTC_NS


def test_header_read_at_nonzero_offset() -> None:
    """Buffer'ın başında dolgu olsa da doğru offsetten okunur."""
    padding = b"\x00" * 16
    header = read_file_header_v1(padding + build_valid_fixture(), offset=len(padding))
    assert header.magic == b"SONARBIN"
    assert header.start_time_utc_ns == START_TIME_UTC_NS


def test_short_buffer_raises_struct_error() -> None:
    """Doğrulama F2-004'te; burada yalnız 'kısa buffer okunamaz' garanti edilir."""
    with pytest.raises(struct.error):
        read_file_header_v1(b"\x00" * 10)


# -- kayit -----------------------------------------------------------------


def test_record_zero_matches_formula(fixture_bytes: bytes) -> None:
    record = read_data_record_v1(fixture_bytes, offset=32)

    assert record.name == b"Data00000\x00\x00\x00"
    assert record.sequence_no == 0
    assert record.elapsed_us == 0
    assert record.sensor_values == (100.0, 25.0, 0.0, 0.0, 1.0, 2.5, 10.0, 48.0)
    assert record.bit_status == 0
    assert record.tx_status == 0


def test_record_one_matches_formula(fixture_bytes: bytes) -> None:
    record = read_data_record_v1(fixture_bytes, offset=32 + 64)

    assert record.name == b"Data00001\x00\x00\x00"
    assert record.sequence_no == 1
    assert record.elapsed_us == 125_000
    assert record.sensor_values == (
        100.5,
        25.0,
        0.125,
        -0.125,
        1.0,
        -2.5,
        10.25,
        48.0,
    )


def test_record_four_carries_the_bit_failure(fixture_bytes: bytes) -> None:
    """`docs/format/fixture-valid-8records.md`: yalnız n=4'te bit_status != 0."""
    record = read_data_record_v1(fixture_bytes, offset=32 + 4 * 64)

    assert record.sequence_no == 4
    assert record.bit_status == 0x00000100
    assert record.tx_status == 1


def test_all_eight_records_are_readable(fixture_bytes: bytes) -> None:
    records = [read_data_record_v1(fixture_bytes, offset=32 + n * 64) for n in range(8)]

    assert [r.sequence_no for r in records] == list(range(8))
    assert [r.name.rstrip(b"\x00").decode("ascii") for r in records] == [
        f"Data{n:05d}" for n in range(8)
    ]
    tx_statuses = [r.tx_status for r in records]
    assert tx_statuses == [0, 0, 1, 1, 1, 1, 0, 0], "n=2..5 ACTIVE olmali"

"""Kesik, bozuk ve sıra boşluklu fixture'ları — `F2-017`.

Kabul: her fixture önceden belirlenen hata sonucunu üretir. Beklenen
sonuçlar `docs/format/fixture-corrupt.md`'de sabitlenmiştir (K-01, K-02,
K-03, K-05, K-06 — K-04 CRC hatası `F2-018`'in kapsamındadır).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from sonar_analyzer.io.decoders.errors import TruncatedHeaderError, UnsupportedVersionError
from sonar_analyzer.io.decoders.gaps import detect_gaps
from sonar_analyzer.io.decoders.limits import validate_buffer_has_header
from sonar_analyzer.io.decoders.naming import check_name_consistency
from sonar_analyzer.io.decoders.profile_a import iter_records, validate_version
from sonar_analyzer.io.decoders.truncation import TruncatedTail, find_truncated_tail
from sonar_analyzer.io.profile_a_format import EXPECTED_PERIOD_US
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _read(filename: str) -> bytes:
    path = FIXTURES_DIR / filename
    assert path.exists(), (
        f"F2-017: tools/make_corrupt_fixtures.py ile uretilip commitlenmeli: {path}"
    )
    return path.read_bytes()


# -- boyut/hash dogrulamasi: her fixture belgedeki degerle birebir eslesir --


@pytest.mark.parametrize(
    ("filename", "expected_size", "expected_sha256"),
    [
        (
            "truncated_header.bin",
            20,
            "49c4c7a46803a28007700129a74544351fc0c6a14bc7dc89cf3930f4bff74651",
        ),
        (
            "truncated_last_record.bin",
            524,
            "ea294eba3f1f5ffcbf2fcdfd13c2fec9f4d3163bb7084122732c90a01fbd28ad",
        ),
        (
            "gap_missing_record.bin",
            544,
            "0ddd96308c58d7807004029fa4dcf19f20034eb2294ab2ec5274210c336bcaab",
        ),
        (
            "unsupported_version.bin",
            544,
            "cc1f6eeb520486415e13b1e8f2c00a669ea1a5a712630d6abc2e4596ebd27bfe",
        ),
        (
            "name_index_mismatch.bin",
            544,
            "b1f807cf1bbea070273ce48d9d2b45d06a402a46241cd1bd576b290e0cb14a84",
        ),
    ],
)
def test_fixture_matches_documented_size_and_hash(
    filename: str, expected_size: int, expected_sha256: str
) -> None:
    data = _read(filename)
    assert len(data) == expected_size
    assert hashlib.sha256(data).hexdigest() == expected_sha256


# -- K-01: kesik header, dosya acilmaz -------------------------------------


def test_k01_truncated_header_is_rejected_before_reading_records() -> None:
    """Kabul: dosya acilmaz; hata 32/20 bayt ayrintisini tasir."""
    data = _read("truncated_header.bin")

    with pytest.raises(TruncatedHeaderError) as excinfo:
        validate_buffer_has_header(len(data))

    assert excinfo.value.available_bytes == 20
    assert excinfo.value.required_bytes == 32


# -- K-02: kesik son kayit, 7 saglam kayit okunur ---------------------------


def test_k02_truncated_last_record_reads_seven_records() -> None:
    """Kabul: 7 kayit (Data00000-Data00006), kesik kayit uretilmez."""
    data = _read("truncated_last_record.bin")

    records = list(iter_records(data))

    assert len(records) == 7
    assert [r.sequence_no for r in records] == list(range(7))


def test_k02_truncated_tail_diagnostic_matches_documented_offset() -> None:
    data = _read("truncated_last_record.bin")

    tail = find_truncated_tail(len(data))

    assert tail is not None
    assert isinstance(tail, TruncatedTail)
    assert tail.byte_offset == 480
    assert tail.available_bytes == 44
    assert tail.required_bytes == 64
    assert str(tail) == "Kesik kayit: offset 480, 44/64 byte"


# -- K-03: sira boslugu ------------------------------------------------------


def test_k03_gap_reads_all_eight_physical_records() -> None:
    data = _read("gap_missing_record.bin")

    records = list(iter_records(data))

    assert len(records) == 8
    assert [r.sequence_no for r in records] == [0, 1, 2, 3, 4, 6, 7, 8]


def test_k03_gap_is_detected_as_single_missing_period() -> None:
    """Kabul: kayip periyot 1, 125 ms (sequence_no=5)."""
    data = _read("gap_missing_record.bin")
    records = list(iter_records(data))

    gaps = list(detect_gaps(records, period_us=EXPECTED_PERIOD_US))

    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.before_sequence_no == 4
    assert gap.after_sequence_no == 6
    assert gap.missing_count == 1
    assert gap.gap_us == 125_000
    assert gap.first_missing_sequence_no == 5
    assert gap.last_missing_sequence_no == 5


def test_k03_sequence_no_six_is_not_at_naive_offset() -> None:
    """docs/format/fixture-corrupt.md ek kontrol: 32 + 6*64 = 416, Data00006'yi
    gostermez (gercek fiziksel offset 352) — dogrudan sequence_no ile seek
    yapan bir uygulamayi yakalar."""
    data = _read("gap_missing_record.bin")
    records = list(iter_records(data))

    # Fiziksel index 5 (0 tabanli) = offset 32 + 5*64 = 352, sequence_no=6.
    physical_index_5 = records[5]
    assert physical_index_5.sequence_no == 6

    naive_offset = 32 + 6 * 64
    real_offset = 32 + 5 * 64
    assert naive_offset == 416
    assert real_offset == 352
    assert naive_offset != real_offset


# -- K-05: desteklenmeyen surum, dosya acilmaz ------------------------------


def test_k05_unsupported_version_is_rejected() -> None:
    """Kabul: dosya acilmaz; hata surum numarasini tasir (99, desteklenen 1,2)."""
    data = _read("unsupported_version.bin")
    header = read_file_header_v1(data)
    assert header.version == 99

    with pytest.raises(UnsupportedVersionError) as excinfo:
        validate_version(header)

    assert excinfo.value.found == 99
    assert excinfo.value.supported == frozenset({1, 2})


# -- K-06: ad / sequence_no uyumsuzlugu -------------------------------------


def test_k06_all_eight_records_are_still_readable() -> None:
    data = _read("name_index_mismatch.bin")
    records = list(iter_records(data))
    assert len(records) == 8
    assert [r.sequence_no for r in records] == list(range(8))


def test_k06_exactly_one_name_mismatch_at_documented_offset() -> None:
    data = _read("name_index_mismatch.bin")
    records = list(iter_records(data))

    mismatches = [
        check_name_consistency(record, byte_offset=32 + index * 64)
        for index, record in enumerate(records)
    ]
    real_mismatches = [m for m in mismatches if m is not None]

    assert len(real_mismatches) == 1
    mismatch = real_mismatches[0]
    assert mismatch.byte_offset == 160
    assert mismatch.found_name == "Data00099"
    assert mismatch.expected_name == "Data00002"
    assert mismatch.sequence_no == 2

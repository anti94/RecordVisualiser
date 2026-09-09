"""Kayıt adı ve sıra numarası tutarlılığı — `F2-010`.

Kabul: `Data99999` sonrası `Data100000` kabul edilir; uyumsuz isim raporlanır.
"""

from __future__ import annotations

from tests.golden_bytes import build_name_mismatch_fixture, build_valid_fixture

from sonar_analyzer.io.decoders.naming import NameMismatch, check_name_consistency
from sonar_analyzer.io.decoders.profile_a import decode_record_at_index, iter_records
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, record_name

#: docs/format/fixture-corrupt.md K-06.
K06_EXPECTED_DIAGNOSTIC = 'Ad tutarsizligi: "Data00099" beklenen "Data00002" (seq 2), offset 160'


def test_matching_names_report_no_mismatch() -> None:
    buffer = build_valid_fixture()
    for index, record in enumerate(iter_records(buffer)):
        offset = 32 + index * 64
        assert check_name_consistency(record, offset) is None


def test_k06_mismatch_matches_documented_diagnostic() -> None:
    """Kabul kriteri: uyumsuz isim raporlanır."""
    buffer = build_name_mismatch_fixture()
    record = decode_record_at_index(buffer, 2)

    mismatch = check_name_consistency(record, byte_offset=32 + 2 * 64)

    assert mismatch is not None
    assert mismatch.byte_offset == 160
    assert mismatch.found_name == "Data00099"
    assert mismatch.expected_name == "Data00002"
    assert mismatch.sequence_no == 2
    assert str(mismatch) == K06_EXPECTED_DIAGNOSTIC


def test_used_value_is_always_sequence_no() -> None:
    """Kabul kriteri: kullanılan değer sequence_no'dur, ad değil."""
    buffer = build_name_mismatch_fixture()
    record = decode_record_at_index(buffer, 2)

    # Zaman ve sira icin sequence_no kullanilir; ad yalniz etikettir.
    assert record.sequence_no == 2
    assert record.elapsed_us == 2 * 125_000


def test_mismatched_record_is_not_dropped() -> None:
    """K-06: veri normal okunur, kayıt atılmaz."""
    buffer = build_name_mismatch_fixture()
    records = list(iter_records(buffer))

    assert len(records) == 8
    assert [r.sequence_no for r in records] == list(range(8))


def test_only_one_mismatch_is_found_in_k06() -> None:
    buffer = build_name_mismatch_fixture()
    mismatches = [
        check_name_consistency(decode_record_at_index(buffer, i), byte_offset=32 + i * 64)
        for i in range(8)
    ]
    real_mismatches = [m for m in mismatches if m is not None]
    assert len(real_mismatches) == 1
    assert real_mismatches[0].sequence_no == 2


def test_data99999_is_followed_by_data100000_without_wrapping() -> None:
    """Kabul kriteri birebir: Data99999 sonrası Data100000 kabul edilir."""
    assert record_name(99_999) == "Data99999"
    assert record_name(100_000) == "Data100000"

    record_99999 = DATA_RECORD_V1.pack(
        b"Data99999\x00\x00\x00", 99_999, 99_999 * 125_000, *([0.0] * 8), 0, 0
    )
    record_100000 = DATA_RECORD_V1.pack(
        b"Data100000\x00\x00", 100_000, 100_000 * 125_000, *([0.0] * 8), 0, 0
    )
    from sonar_analyzer.io.readers.binary_reader import read_data_record_v1

    r1 = read_data_record_v1(record_99999, 0)
    r2 = read_data_record_v1(record_100000, 0)

    assert check_name_consistency(r1, byte_offset=0) is None
    assert check_name_consistency(r2, byte_offset=0) is None


def test_name_mismatch_is_immutable() -> None:
    import dataclasses

    import pytest

    mismatch = NameMismatch(
        byte_offset=160, found_name="Data00099", expected_name="Data00002", sequence_no=2
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        mismatch.sequence_no = 3  # type: ignore[misc]

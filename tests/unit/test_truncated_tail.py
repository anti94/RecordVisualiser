"""Kesik son kaydı raporlama — `F2-009`.

Kabul: önceki tam kayıtlar erişilebilir kalır.

Referans senaryo `docs/format/fixture-corrupt.md` K-02: `valid_8records.bin`
ilk 524 baytı (son kayıttan 20 bayt eksik).
"""

from __future__ import annotations

from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.io.decoders.profile_a import iter_records, record_count_in_buffer
from sonar_analyzer.io.decoders.truncation import TruncatedTail, find_truncated_tail

#: docs/format/fixture-corrupt.md K-02.
K02_TRUNCATED_LENGTH = 524
K02_EXPECTED_DIAGNOSTIC = "Kesik kayit: offset 480, 44/64 byte"


def truncated_524() -> bytes:
    return build_valid_fixture()[:K02_TRUNCATED_LENGTH]


def test_full_file_has_no_truncated_tail() -> None:
    assert find_truncated_tail(len(build_valid_fixture())) is None


def test_k02_scenario_matches_documented_values() -> None:
    """Kabul kriteri: 524 bayt -> 7 tam kayıt, 44/64 bayt artık, offset 480."""
    tail = find_truncated_tail(K02_TRUNCATED_LENGTH)

    assert tail is not None
    assert tail.byte_offset == 480
    assert tail.available_bytes == 44
    assert tail.required_bytes == 64
    assert str(tail) == K02_EXPECTED_DIAGNOSTIC


def test_previous_full_records_remain_accessible() -> None:
    """Kabul kriteri birebir: önceki tam kayıtlar erişilebilir kalır."""
    buffer = truncated_524()

    assert record_count_in_buffer(len(buffer)) == 7
    records = list(iter_records(buffer))
    assert len(records) == 7
    assert [r.sequence_no for r in records] == list(range(7))
    assert [r.name.rstrip(b"\x00").decode("ascii") for r in records] == [
        f"Data{n:05d}" for n in range(7)
    ]


def test_covered_range_is_0_to_750ms() -> None:
    """Kabul kriteri: kapsanan aralık 0 ms - 750 ms."""
    from sonar_analyzer.io.decoders.timing import record_timestamp_ns
    from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

    buffer = truncated_524()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))

    first_ms = (record_timestamp_ns(header, records[0]) - header.start_time_utc_ns) // 1_000_000
    last_ms = (record_timestamp_ns(header, records[-1]) - header.start_time_utc_ns) // 1_000_000
    assert first_ms == 0
    assert last_ms == 750


def test_partial_record_never_enters_the_domain_model() -> None:
    """Kabul kriteri: Data00007 hiç üretilmez, kısmi veri domain modeline girmez."""
    buffer = truncated_524()
    records = list(iter_records(buffer))
    assert all(r.sequence_no != 7 for r in records)
    assert len(records) == 7  # 8. kayit (indeks 7) yok


def test_severity_is_warning_not_error() -> None:
    """K-02: şiddet uyarı, hata değil — find_truncated_tail istisna atmaz."""
    tail = find_truncated_tail(K02_TRUNCATED_LENGTH)  # istisna firlatmamali
    assert tail is not None


def test_exactly_one_byte_short_is_detected() -> None:
    full = build_valid_fixture()
    tail = find_truncated_tail(len(full) - 1)
    assert tail is not None
    assert tail.available_bytes == 63


def test_header_only_buffer_has_no_tail_to_report() -> None:
    """Header'dan sonra hiç bayt yoksa "kesik kayıt" değil, "kayıt yok"tur."""
    assert find_truncated_tail(32) is None


def test_too_short_for_header_returns_none() -> None:
    """Kesik header ayrı bir durumdur (F2-004); burada None döner, hata değil."""
    assert find_truncated_tail(10) is None


def test_truncated_tail_is_immutable() -> None:
    import dataclasses

    import pytest

    tail = TruncatedTail(byte_offset=480, available_bytes=44, required_bytes=64)
    with pytest.raises(dataclasses.FrozenInstanceError):
        tail.available_bytes = 0  # type: ignore[misc]

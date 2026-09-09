"""Ardışık kayıt iterator'ü — `F2-006`.

Kabul: sekiz kayıt sırayla okunur; offsetler `32 + n × 64` olur.
"""

from __future__ import annotations

import struct

from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.io.decoders.profile_a import iter_records, record_count_in_buffer
from sonar_analyzer.io.profile_a_format import EXPECTED_HEADER_SIZE_V1, EXPECTED_RECORD_SIZE_V1


def test_record_count_for_the_golden_fixture() -> None:
    assert record_count_in_buffer(len(build_valid_fixture())) == 8


def test_offsets_follow_32_plus_n_times_64() -> None:
    """Kabul kriteri: offsetler 32 + n * 64 olur."""
    for n in range(8):
        assert EXPECTED_HEADER_SIZE_V1 + n * EXPECTED_RECORD_SIZE_V1 == 32 + n * 64


def test_all_eight_records_are_read_in_order() -> None:
    records = list(iter_records(build_valid_fixture()))

    assert len(records) == 8
    assert [r.sequence_no for r in records] == list(range(8))
    assert [r.name.rstrip(b"\x00").decode("ascii") for r in records] == [
        f"Data{n:05d}" for n in range(8)
    ]


def test_iterator_is_lazy_and_reusable() -> None:
    """`iter_records` bir generator'dır: her çağrı taze bir akış üretir."""
    buffer = build_valid_fixture()
    first_pass = list(iter_records(buffer))
    second_pass = list(iter_records(buffer))
    assert first_pass == second_pass


def test_record_count_handles_empty_and_header_only_buffers() -> None:
    assert record_count_in_buffer(0) == 0
    assert record_count_in_buffer(EXPECTED_HEADER_SIZE_V1) == 0  # header var, kayit yok


def test_record_count_ignores_trailing_partial_bytes() -> None:
    """Son kaydın kesik olması F2-009'da raporlanır; burada yok sayılır."""
    full = build_valid_fixture()
    truncated = full[:-20]  # son kaydin 44/64 bayti
    assert record_count_in_buffer(len(truncated)) == 7


def test_iterating_a_truncated_buffer_yields_only_full_records() -> None:
    full = build_valid_fixture()
    truncated = full[:-20]
    records = list(iter_records(truncated))
    assert len(records) == 7
    assert [r.sequence_no for r in records] == list(range(7))


def test_iterating_beyond_a_completely_empty_buffer_is_safe() -> None:
    assert list(iter_records(b"")) == []


def test_custom_sizes_are_respected() -> None:
    from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1

    header = b"\x00" * 40
    two_records = (
        header
        + DATA_RECORD_V1.pack(b"Data00000", 0, 0, *([1.0] * 8), 0, 0)
        + DATA_RECORD_V1.pack(b"Data00001", 1, 125_000, *([2.0] * 8), 0, 0)
    )

    records = list(iter_records(two_records, header_size=40))
    assert [r.sequence_no for r in records] == [0, 1]
    assert records[1].sensor_values == (2.0,) * 8


def test_struct_module_never_reads_past_buffer_bounds() -> None:
    """iter_records sadece TAM kayıtları hesaba katar; struct.error asla
    fırlatılmamalı — kabul kriteri: sınır dışı okuma yok."""
    for cut in range(0, 200, 7):
        buffer = build_valid_fixture()[: len(build_valid_fixture()) - cut]
        try:
            list(iter_records(buffer))
        except struct.error:  # pragma: no cover - hicbir kesimde olmamali
            raise AssertionError(f"struct.error at cut={cut}") from None

"""Tekrarlı ve sıra dışı kayıtları raporlama — `F2-011`.

`docs/adr/ADR-003-time-base.md` §2.7: aynı zaman iki kez görülürse ikisi de
saklanır (`duplicate` işaretlenir); geri giden `sequence_no` reset/bozulma
sayılır, sıralama düzeltmesiyle gizlenmez. Kabul: her durum kaynak offseti
ve zamanıyla ayrılır.
"""

from __future__ import annotations

from tests.golden_bytes import (
    START_TIME_UTC_NS,
    build_duplicate_sequence_fixture,
    build_out_of_order_fixture,
    build_valid_fixture,
)

from sonar_analyzer.io.decoders.anomalies import (
    DuplicateSequence,
    OutOfOrderSequence,
    detect_anomalies,
)
from sonar_analyzer.io.decoders.profile_a import decode_record_at_index, record_count_in_buffer
from sonar_analyzer.io.profile_a_format import DataRecordV1
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

HEADER_SIZE = 32
RECORD_SIZE = 64


def _indexed_records(buffer: bytes) -> list[tuple[int, DataRecordV1]]:
    count = record_count_in_buffer(len(buffer))
    return [
        (HEADER_SIZE + i * RECORD_SIZE, decode_record_at_index(buffer, i)) for i in range(count)
    ]


def test_valid_fixture_has_no_anomalies() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    anomalies = list(detect_anomalies(_indexed_records(buffer), header))
    assert anomalies == []


def test_duplicate_sequence_is_reported_with_offset_and_timestamp() -> None:
    buffer = build_duplicate_sequence_fixture()
    header = read_file_header_v1(buffer)

    anomalies = list(detect_anomalies(_indexed_records(buffer), header))

    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert isinstance(anomaly, DuplicateSequence)
    # Fiziksel index 3, offset = 32 + 3*64 = 224.
    assert anomaly.byte_offset == 224
    assert anomaly.sequence_no == 2
    # elapsed_us index 3'ün kendi kaydindan (n=3) degil, sequence_no=2'nin
    # yazildigi elapsed_us'tan gelir (fixture n=2 formuluyle yazildi).
    assert anomaly.timestamp_ns == START_TIME_UTC_NS + 2 * 125_000 * 1_000


def test_duplicated_records_are_both_kept_not_deduplicated() -> None:
    """Politika: ikisi de saklanır, sessizce ilki/sonuncusu seçilmez."""
    buffer = build_duplicate_sequence_fixture()
    records = [decode_record_at_index(buffer, i) for i in range(8)]

    sequence_numbers = [r.sequence_no for r in records]
    assert sequence_numbers.count(2) == 2
    assert len(records) == 8, "Kayit sayisi degismez; tekrar eden kayit atilmaz"


def test_out_of_order_sequence_is_reported_with_offset_and_timestamp() -> None:
    buffer = build_out_of_order_fixture()
    header = read_file_header_v1(buffer)

    anomalies = list(detect_anomalies(_indexed_records(buffer), header))

    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert isinstance(anomaly, OutOfOrderSequence)
    # Fiziksel index 4, offset = 32 + 4*64 = 288.
    assert anomaly.byte_offset == 288
    assert anomaly.sequence_no == 1
    assert anomaly.previous_sequence_no == 3
    assert anomaly.timestamp_ns == START_TIME_UTC_NS + 1 * 125_000 * 1_000


def test_backward_sequence_is_not_silently_hidden_by_sorting() -> None:
    """Politika: geri giden sequence_no reset/bozulma sayilir, sirala-ve-
    gizle davranisi yok — fiziksel sirada tespit edilir."""
    buffer = build_out_of_order_fixture()
    header = read_file_header_v1(buffer)
    records = [decode_record_at_index(buffer, i) for i in range(8)]

    # Fiziksel sirada gercekten geri gidis var (sort edilmemis girdi).
    assert [r.sequence_no for r in records] == [0, 1, 2, 3, 1, 5, 6, 7]

    anomalies = list(detect_anomalies(_indexed_records(buffer), header))
    assert any(isinstance(a, OutOfOrderSequence) for a in anomalies)


def test_duplicate_str_matches_expected_shape() -> None:
    anomaly = DuplicateSequence(byte_offset=224, sequence_no=2, timestamp_ns=1_000)
    assert str(anomaly) == "Tekrarli sira: seq 2, offset 224, t=1000"


def test_out_of_order_str_matches_expected_shape() -> None:
    anomaly = OutOfOrderSequence(
        byte_offset=288, sequence_no=1, previous_sequence_no=3, timestamp_ns=2_000
    )
    assert str(anomaly) == "Sira disi kayit: seq 1 (onceki 3), offset 288, t=2000"


def test_anomalies_are_immutable() -> None:
    import dataclasses

    import pytest

    dup = DuplicateSequence(byte_offset=1, sequence_no=1, timestamp_ns=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        dup.sequence_no = 2  # type: ignore[misc]

    ooo = OutOfOrderSequence(byte_offset=1, sequence_no=1, previous_sequence_no=2, timestamp_ns=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ooo.sequence_no = 3  # type: ignore[misc]


def test_empty_and_single_record_streams_produce_no_anomalies() -> None:
    buffer = build_valid_fixture(record_count=1)
    header = read_file_header_v1(buffer)
    assert list(detect_anomalies(_indexed_records(buffer), header)) == []
    assert list(detect_anomalies([], header)) == []

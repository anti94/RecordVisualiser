"""Sıra ve zaman boşluklarını raporlama — `F2-008`.

Kabul: atlanan sıra boşluk olarak gösterilir; sonraki kaydın zamanı
kaydırılmaz.
"""

from __future__ import annotations

from tests.golden_bytes import build_gap_fixture, build_valid_fixture

from sonar_analyzer.io.decoders.gaps import SequenceGap, detect_gaps
from sonar_analyzer.io.decoders.profile_a import iter_records
from sonar_analyzer.io.decoders.timing import record_timestamp_ns
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1


class _FakeRecord:
    """`detect_gaps` yalnız `sequence_no` alanına bakar; sentetik dizilerde
    tam bir `DataRecordV1` üretmek yerine bu kullanılır."""

    def __init__(self, sequence_no: int) -> None:
        self.sequence_no = sequence_no


def test_gapless_file_reports_no_gaps() -> None:
    records = list(iter_records(build_valid_fixture()))
    assert list(detect_gaps(records)) == []


def test_missing_sequence_5_is_reported() -> None:
    """Kabul kriteri: atlanan sıra boşluk olarak gösterilir."""
    records = list(iter_records(build_gap_fixture()))
    gaps = list(detect_gaps(records))

    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.before_sequence_no == 4
    assert gap.after_sequence_no == 6
    assert gap.missing_count == 1
    assert gap.gap_us == 125_000
    assert gap.first_missing_sequence_no == 5
    assert gap.last_missing_sequence_no == 5


def test_next_records_timestamp_is_not_shifted() -> None:
    """Kabul kriteri: sonraki kaydın zamanı kaydırılmaz.

    docs/format/timing-and-naming.md §4: fiziksel 5. kayıt (sequence_no=6)
    beklenen elapsed_us=625000 yerine 750000 gösterir — kaydırılıp
    625000'e "düzeltilmez".
    """
    buffer = build_gap_fixture()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))

    physical_fifth = records[5]  # fiziksel sira 5, sequence_no=6
    assert physical_fifth.sequence_no == 6
    assert physical_fifth.elapsed_us == 750_000, "elapsed_us kaydirilmamis olmali"

    timestamp = record_timestamp_ns(header, physical_fifth)
    assert timestamp - header.start_time_utc_ns == 750_000_000


def test_gap_does_not_affect_surrounding_records() -> None:
    """Boşluğun öncesi ve sonrasındaki kayıtlar normal okunur."""
    records = list(iter_records(build_gap_fixture()))
    assert len(records) == 8
    assert [r.sequence_no for r in records] == [0, 1, 2, 3, 4, 6, 7, 8]


def test_multi_period_gap_reports_correct_missing_count() -> None:
    """Birden fazla ardışık periyodun kaybı da tek boşluk olarak sayılır."""

    records = [_FakeRecord(0), _FakeRecord(1), _FakeRecord(5)]  # seq 2,3,4 kayip
    gaps = list(detect_gaps(records))  # type: ignore[arg-type]

    assert len(gaps) == 1
    assert gaps[0].missing_count == 3
    assert gaps[0].gap_us == 3 * 125_000
    assert gaps[0].first_missing_sequence_no == 2
    assert gaps[0].last_missing_sequence_no == 4


def test_multiple_separate_gaps_are_all_reported() -> None:
    records = [
        _FakeRecord(0),
        _FakeRecord(2),
        _FakeRecord(3),
        _FakeRecord(6),
    ]  # kayip: 1, sonra 4-5
    gaps = list(detect_gaps(records))  # type: ignore[arg-type]

    assert len(gaps) == 2
    assert gaps[0].missing_count == 1
    assert gaps[1].missing_count == 2


def test_backward_sequence_is_not_reported_as_a_gap() -> None:
    """docs/format/timing-and-naming.md §4.2: geri giden sequence_no boşluk
    değildir — F2-011'in konusu, burada sessizce yok sayılır."""

    records = [_FakeRecord(5), _FakeRecord(3)]  # geri gidiyor
    assert list(detect_gaps(records)) == []  # type: ignore[arg-type]


def test_single_record_has_no_gaps() -> None:
    assert list(detect_gaps([_FakeRecord(0)])) == []  # type: ignore[arg-type]


def test_empty_iterable_has_no_gaps() -> None:
    assert list(detect_gaps([])) == []


def test_sequence_gap_is_immutable() -> None:
    import dataclasses

    import pytest

    gap = SequenceGap(before_sequence_no=4, after_sequence_no=6, missing_count=1, gap_us=125_000)
    with pytest.raises(dataclasses.FrozenInstanceError):
        gap.missing_count = 2  # type: ignore[misc]

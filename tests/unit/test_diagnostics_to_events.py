"""Parser teşhislerini sistem olaylarına çevirme — `F2-024`.

Kabul: hata zamanı, kaynak offseti, kategori ve severity korunur.
"""

from __future__ import annotations

from tests.golden_bytes import START_TIME_UTC_NS

from sonar_analyzer.domain.event import Severity
from sonar_analyzer.io.decoders.anomalies import DuplicateSequence, OutOfOrderSequence
from sonar_analyzer.io.decoders.crc_validation import RecordCrcMismatch
from sonar_analyzer.io.decoders.diagnostics_to_events import (
    crc_mismatch_to_event,
    duplicate_sequence_to_event,
    gap_to_event,
    name_mismatch_to_event,
    out_of_order_to_event,
    truncated_tail_to_event,
    unknown_packet_to_event,
)
from sonar_analyzer.io.decoders.gaps import SequenceGap
from sonar_analyzer.io.decoders.naming import NameMismatch
from sonar_analyzer.io.decoders.truncation import TruncatedTail
from sonar_analyzer.io.decoders.unknown_packet import UnknownPacket
from sonar_analyzer.io.profile_a_format import FileHeaderV1

PERIOD_NS = 125_000_000

HEADER = FileHeaderV1(
    magic=b"SONARBIN",
    version=1,
    header_size=32,
    record_size=64,
    period_us=125_000,
    channel_count=8,
    start_time_utc_ns=START_TIME_UTC_NS,
)


def _timestamp(n: int) -> int:
    return START_TIME_UTC_NS + n * PERIOD_NS


# -- SequenceGap ----------------------------------------------------------


def test_gap_to_event_preserves_time_offset_category_severity() -> None:
    gap = SequenceGap(before_sequence_no=4, after_sequence_no=6, missing_count=1, gap_us=125_000)

    event = gap_to_event(gap, HEADER, after_record_byte_offset=352)

    assert event.timestamp_ns == _timestamp(5)  # first_missing_sequence_no
    assert event.source_offset == 352
    assert event.category == "sequence_gap"
    assert event.severity == Severity.WARNING
    assert "1" in event.message


# -- NameMismatch -----------------------------------------------------------


def test_name_mismatch_to_event_preserves_time_offset_category_severity() -> None:
    mismatch = NameMismatch(
        byte_offset=160, found_name="Data00099", expected_name="Data00002", sequence_no=2
    )

    event = name_mismatch_to_event(mismatch, HEADER)

    assert event.timestamp_ns == _timestamp(2)
    assert event.source_offset == 160
    assert event.category == "name_mismatch"
    assert event.severity == Severity.WARNING
    assert event.message == str(mismatch)


# -- DuplicateSequence / OutOfOrderSequence ----------------------------------


def test_duplicate_sequence_to_event_preserves_fields() -> None:
    duplicate = DuplicateSequence(byte_offset=224, sequence_no=2, timestamp_ns=_timestamp(2))

    event = duplicate_sequence_to_event(duplicate)

    assert event.timestamp_ns == _timestamp(2)
    assert event.source_offset == 224
    assert event.category == "duplicate_sequence"
    assert event.severity == Severity.WARNING


def test_out_of_order_to_event_uses_error_severity() -> None:
    """ADR-003 §2.7: geri giden sequence_no reset/bozulma sayilir -> ERROR."""
    out_of_order = OutOfOrderSequence(
        byte_offset=288, sequence_no=1, previous_sequence_no=3, timestamp_ns=_timestamp(1)
    )

    event = out_of_order_to_event(out_of_order)

    assert event.timestamp_ns == _timestamp(1)
    assert event.source_offset == 288
    assert event.category == "out_of_order_sequence"
    assert event.severity == Severity.ERROR


# -- TruncatedTail ------------------------------------------------------


def test_truncated_tail_to_event_uses_warning_not_error() -> None:
    """K-02: 'Siddet: Uyari (hata degil)'."""
    tail = TruncatedTail(byte_offset=480, available_bytes=44, required_bytes=64)

    event = truncated_tail_to_event(tail, HEADER)

    assert event.timestamp_ns == _timestamp(7)  # (480-32)//64 = 7
    assert event.source_offset == 480
    assert event.category == "truncated_tail"
    assert event.severity == Severity.WARNING
    assert event.message == str(tail)


# -- RecordCrcMismatch ----------------------------------------------------


def test_crc_mismatch_to_event_uses_error_severity() -> None:
    mismatch = RecordCrcMismatch(
        byte_offset=240, sequence_no=3, expected_crc32=0xAA7584BF, found_crc32=0x053116F8
    )

    event = crc_mismatch_to_event(mismatch, HEADER)

    assert event.timestamp_ns == _timestamp(3)
    assert event.source_offset == 240
    assert event.category == "crc_error"
    assert event.severity == Severity.ERROR


# -- UnknownPacket ------------------------------------------------------


def test_unknown_packet_to_event_uses_error_severity() -> None:
    packet = UnknownPacket(byte_offset=224, reason="beklenmeyen onek b'XXXX'", skipped_bytes=64)

    event = unknown_packet_to_event(packet, HEADER)

    assert event.timestamp_ns == _timestamp(3)  # (224-32)//64 = 3
    assert event.source_offset == 224
    assert event.category == "unknown_packet"
    assert event.severity == Severity.ERROR
    assert event.message == str(packet)


# -- ortak alanlar ---------------------------------------------------------


def test_all_converters_use_the_parser_source() -> None:
    mismatch = NameMismatch(
        byte_offset=160, found_name="Data00099", expected_name="Data00002", sequence_no=2
    )
    event = name_mismatch_to_event(mismatch, HEADER)
    assert event.source == "parser"

"""Parser teşhislerini sistem olaylarına çevirme — `F2-024`.

`F2-008`'den `F2-015`'e kadar üretilen teşhis dataclass'larının (`SequenceGap`,
`TruncatedTail`, `NameMismatch`, `DuplicateSequence`, `OutOfOrderSequence`,
`RecordCrcMismatch`, `UnknownPacket`) her biri kendi alanlarını taşır; bu
modül hepsini ortak `domain.event.Event` tablosuna çevirir — Data Explorer'daki
Events listesi tek bir tür yerine bunların tamamını gösterebilsin diye.

Kabul kriteri: **hata zamanı, kaynak offseti, kategori ve severity korunur**.
Zaman: mümkün olduğunda teşhisin kendi `sequence_no`'sundan (yetkili alan,
`timing-and-naming.md` §2), yoksa `byte_offset`'ten türetilen **nominal**
kayıt ızgarası zamanıdır — gerçek `elapsed_us` değildir, çünkü kayıt
çözülemediği için bilinmez (`TruncatedTail`, `UnknownPacket`). Offset:
teşhisin kendi `byte_offset`'i (`SequenceGap` hariç — o alan taşımaz;
çağıran taraf boşluktan hemen sonraki kaydın offsetini verir).
"""

from __future__ import annotations

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.io.decoders.anomalies import DuplicateSequence, OutOfOrderSequence
from sonar_analyzer.io.decoders.crc_validation import RecordCrcMismatch
from sonar_analyzer.io.decoders.gaps import SequenceGap
from sonar_analyzer.io.decoders.naming import NameMismatch
from sonar_analyzer.io.decoders.timing import elapsed_us_for_sequence
from sonar_analyzer.io.decoders.truncation import TruncatedTail
from sonar_analyzer.io.decoders.unknown_packet import UnknownPacket
from sonar_analyzer.io.profile_a_format import FileHeaderV1

_SOURCE = "parser"
_NS_PER_US = 1_000


def _nominal_timestamp_ns_for_sequence(header: FileHeaderV1, sequence_no: int) -> int:
    """`sequence_no`'dan nominal (kayıpsız ızgara varsayımlı) zamanı hesaplar."""
    nominal_elapsed_us = elapsed_us_for_sequence(sequence_no, header.period_us)
    return header.start_time_utc_ns + nominal_elapsed_us * _NS_PER_US


def _nominal_timestamp_ns_for_offset(header: FileHeaderV1, byte_offset: int) -> int:
    """`byte_offset`'ten çözülemeyen bir kaydın nominal fiziksel index'ini,
    onu `sequence_no` gibi kullanarak zamana çevirir (en iyi çaba — gerçek
    `sequence_no` bilinmiyor, kayıt çözülemedi)."""
    nominal_index = (byte_offset - header.header_size) // header.record_size
    return _nominal_timestamp_ns_for_sequence(header, nominal_index)


def gap_to_event(gap: SequenceGap, header: FileHeaderV1, after_record_byte_offset: int) -> Event:
    """`SequenceGap`'i olaya çevirir.

    `SequenceGap` kendi `byte_offset`'ini taşımaz (kayıp kayıt hiç
    yazılmadı) — çağıran taraf boşluktan hemen sonraki kaydın fiziksel
    offsetini verir (`docs/format/fixture-corrupt.md` K-03: "offset 352
    öncesinde" ile aynı çerçeve).
    """
    return Event(
        timestamp_ns=_nominal_timestamp_ns_for_sequence(header, gap.first_missing_sequence_no),
        source=_SOURCE,
        category="sequence_gap",
        severity=Severity.WARNING,
        code="GAP",
        message=(
            f"Sira bosluğu: {gap.missing_count} kayit yok "
            f"({gap.gap_us // 1000} ms), offset {after_record_byte_offset} oncesinde"
        ),
        source_offset=after_record_byte_offset,
    )


def name_mismatch_to_event(mismatch: NameMismatch, header: FileHeaderV1) -> Event:
    """`NameMismatch`'i olaya çevirir; zaman yetkili alan `sequence_no`'dan gelir."""
    return Event(
        timestamp_ns=_nominal_timestamp_ns_for_sequence(header, mismatch.sequence_no),
        source=_SOURCE,
        category="name_mismatch",
        severity=Severity.WARNING,
        code="NAME_MISMATCH",
        message=str(mismatch),
        source_offset=mismatch.byte_offset,
    )


def duplicate_sequence_to_event(duplicate: DuplicateSequence) -> Event:
    """`DuplicateSequence`'ı olaya çevirir; `timestamp_ns` zaten dataclass'ta var."""
    return Event(
        timestamp_ns=duplicate.timestamp_ns,
        source=_SOURCE,
        category="duplicate_sequence",
        severity=Severity.WARNING,
        code="DUPLICATE_SEQUENCE",
        message=str(duplicate),
        source_offset=duplicate.byte_offset,
    )


def out_of_order_to_event(out_of_order: OutOfOrderSequence) -> Event:
    """`OutOfOrderSequence`'ı olaya çevirir — reset/bozulma sayıldığı için `ERROR`."""
    return Event(
        timestamp_ns=out_of_order.timestamp_ns,
        source=_SOURCE,
        category="out_of_order_sequence",
        severity=Severity.ERROR,
        code="OUT_OF_ORDER",
        message=str(out_of_order),
        source_offset=out_of_order.byte_offset,
    )


def truncated_tail_to_event(tail: TruncatedTail, header: FileHeaderV1) -> Event:
    """`TruncatedTail`'i olaya çevirir — K-02: uyarı, hata değil."""
    return Event(
        timestamp_ns=_nominal_timestamp_ns_for_offset(header, tail.byte_offset),
        source=_SOURCE,
        category="truncated_tail",
        severity=Severity.WARNING,
        code="TRUNCATED_TAIL",
        message=str(tail),
        source_offset=tail.byte_offset,
    )


def crc_mismatch_to_event(mismatch: RecordCrcMismatch, header: FileHeaderV1) -> Event:
    """`RecordCrcMismatch`'i olaya çevirir — K-04: veri bütünlüğü ihlali, `ERROR`."""
    return Event(
        timestamp_ns=_nominal_timestamp_ns_for_sequence(header, mismatch.sequence_no),
        source=_SOURCE,
        category="crc_error",
        severity=Severity.ERROR,
        code="CRC_ERROR",
        message=str(mismatch),
        source_offset=mismatch.byte_offset,
    )


def unknown_packet_to_event(packet: UnknownPacket, header: FileHeaderV1) -> Event:
    """`UnknownPacket`'i olaya çevirir — tümüyle tanınmayan veri, `ERROR`."""
    return Event(
        timestamp_ns=_nominal_timestamp_ns_for_offset(header, packet.byte_offset),
        source=_SOURCE,
        category="unknown_packet",
        severity=Severity.ERROR,
        code="UNKNOWN_PACKET",
        message=str(packet),
        source_offset=packet.byte_offset,
    )

"""Sürüme göre decoder seçimi — `F2-012`.

Kabul: örnek (v1) format ile sürümlü genişletilmiş (v2) format ayrı decoder
kullanır.
"""

from __future__ import annotations

import pytest
from tests.golden_bytes import (
    START_TIME_UTC_NS,
    build_valid_fixture,
    build_valid_v2_fixture,
)

from sonar_analyzer.io.decoders.errors import UnsupportedVersionError
from sonar_analyzer.io.decoders.version_dispatch import (
    peek_version,
    select_decoder,
    select_decoder_for_buffer,
)
from sonar_analyzer.io.profile_a_format import (
    DataRecordV1,
    DataRecordV2,
    FileHeaderV1,
    FileHeaderV2,
)


def test_peek_version_reads_v1_without_full_header() -> None:
    buffer = build_valid_fixture()
    assert peek_version(buffer) == 1


def test_peek_version_reads_v2_without_full_header() -> None:
    buffer = build_valid_v2_fixture()
    assert peek_version(buffer) == 2


def test_select_decoder_for_v1_uses_32_36_sizes() -> None:
    decoder = select_decoder(1)
    assert decoder.header_size == 32
    assert decoder.record_size == 64


def test_select_decoder_for_v2_uses_crc_sizes() -> None:
    decoder = select_decoder(2)
    assert decoder.header_size == 36
    assert decoder.record_size == 68


def test_v1_buffer_decodes_with_v1_decoder_end_to_end() -> None:
    buffer = build_valid_fixture()
    decoder = select_decoder_for_buffer(buffer)

    header = decoder.read_header(buffer, 0)
    assert isinstance(header, FileHeaderV1)
    assert not isinstance(header, FileHeaderV2)
    assert header.start_time_utc_ns == START_TIME_UTC_NS

    record = decoder.read_record(buffer, decoder.header_size)
    assert isinstance(record, DataRecordV1)
    assert record.sequence_no == 0


def test_v2_buffer_decodes_with_v2_decoder_end_to_end() -> None:
    buffer = build_valid_v2_fixture()
    decoder = select_decoder_for_buffer(buffer)

    header = decoder.read_header(buffer, 0)
    assert isinstance(header, FileHeaderV2)
    assert header.start_time_utc_ns == START_TIME_UTC_NS
    assert header.header_crc32 != 0

    record = decoder.read_record(buffer, decoder.header_size)
    assert isinstance(record, DataRecordV2)
    assert record.sequence_no == 0
    assert record.record_crc32 != 0


def test_v2_second_record_is_at_68_byte_stride() -> None:
    buffer = build_valid_v2_fixture()
    decoder = select_decoder_for_buffer(buffer)

    second = decoder.read_record(buffer, decoder.header_size + decoder.record_size)
    assert isinstance(second, DataRecordV2)
    assert second.sequence_no == 1
    assert second.elapsed_us == 125_000


def test_unsupported_version_raises_with_offset_8() -> None:
    with pytest.raises(UnsupportedVersionError) as excinfo:
        select_decoder(99)
    assert excinfo.value.byte_offset == 8
    assert excinfo.value.found == 99


def test_v1_and_v2_produce_different_dataclass_types() -> None:
    """Kabul kriterinin özü: iki sürüm gerçekten ayrı decoder kullanır."""
    v1_decoder = select_decoder(1)
    v2_decoder = select_decoder(2)
    assert v1_decoder.read_header is not v2_decoder.read_header
    assert v1_decoder.read_record is not v2_decoder.read_record

"""Dosya açılışında iki Profil A sürümünün ortak header doğrulaması — F2-033."""

from __future__ import annotations

from sonar_analyzer.io.decoders.crc_validation import validate_header_crc
from sonar_analyzer.io.decoders.errors import HeaderContractError, TruncatedHeaderError
from sonar_analyzer.io.decoders.limits import validate_buffer_has_header
from sonar_analyzer.io.decoders.profile_a import validate_magic
from sonar_analyzer.io.decoders.version_dispatch import select_decoder
from sonar_analyzer.io.profile_a_format import EXPECTED_CHANNEL_COUNT, FileHeaderV1
from sonar_analyzer.io.readers.binary_reader import (
    ReadableBuffer,
    read_file_header_v1,
    read_file_header_v2,
)

MAX_TIMESTAMP_NS = (1 << 63) - 1


def read_validated_header(data: ReadableBuffer) -> FileHeaderV1:
    """Ortak ilk 32 byte alanlarını verir; v2'nin CRC'sini ayrıca doğrular.

    Dönen model v1 gövdesidir; version/header_size/record_size gerçek sürümün
    değerlerini korur. V2 dosyasının CRC alanı doğrulanmadan sonuç dönmez.
    """
    validate_buffer_has_header(len(data))
    header = read_file_header_v1(data)
    validate_magic(header)
    decoder = select_decoder(header.version)
    if len(data) < decoder.header_size:
        raise TruncatedHeaderError(len(data), decoder.header_size)
    if header.version == 2:
        validate_header_crc(read_file_header_v2(data), data[:32])
    for value, expected, name, offset in (
        (header.header_size, decoder.header_size, "header_size", 10),
        (header.record_size, decoder.record_size, "record_size", 12),
        (header.channel_count, EXPECTED_CHANNEL_COUNT, "channel_count", 20),
    ):
        if value != expected:
            raise HeaderContractError(f"{name} {value} != {expected}", byte_offset=offset)
    if header.period_us <= 0:
        raise HeaderContractError("period_us pozitif olmali", byte_offset=16)
    if header.start_time_utc_ns > MAX_TIMESTAMP_NS - header.period_us * 1000:
        raise HeaderContractError("baslangic zamani int64 ns sinirini asiyor", byte_offset=24)
    return header

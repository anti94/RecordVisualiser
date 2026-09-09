"""Little-endian header okuyucusu — `F2-002`.

Yalnız **bayt → alan** dönüşümü yapar; doğrulama (`F2-003`, `F2-004`) ayrı
katmandadır. Bu ayrım bilinçli: bozuk bir header'ı okumaya çalışmak ile onu
kabul edilebilir bulmak farklı sorumluluklardır — biri her zaman denenir,
diğeri politika gerektirir.

`bytes` yerine `Buffer` (bytes/bytearray/mmap ile uyumlu) kabul edilir; ileride
`mmap` ile kopyasız okuma yapılabilmesi için (plan Bölüm 8.2 decoder tasarımı).
"""

from __future__ import annotations

from typing import Union

from sonar_analyzer.io.profile_a_format import (
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    FILE_HEADER_V1,
    FILE_HEADER_V2,
    DataRecordV1,
    DataRecordV2,
    FileHeaderV1,
    FileHeaderV2,
)

#: bytes, bytearray veya mmap.mmap kabul edilir; struct.unpack_from hepsini destekler.
ReadableBuffer = Union[bytes, bytearray, memoryview]


def read_file_header_v1(buffer: ReadableBuffer, offset: int = 0) -> FileHeaderV1:
    """32 baytlık ham veriyi `FileHeaderV1`'e çözer.

    Buffer'ın en az `offset + 32` bayt uzunluğunda olduğu **varsayılır**;
    kısa buffer'da `struct.error` yükselir (bkz. `F2-004`).
    """
    magic, version, header_size, record_size, period_us, channel_count, start_time_utc_ns = (
        FILE_HEADER_V1.unpack_from(buffer, offset)
    )
    return FileHeaderV1(
        magic=magic,
        version=version,
        header_size=header_size,
        record_size=record_size,
        period_us=period_us,
        channel_count=channel_count,
        start_time_utc_ns=start_time_utc_ns,
    )


def read_file_header_v2(buffer: ReadableBuffer, offset: int = 0) -> FileHeaderV2:
    """36 baytlık ham veriyi `FileHeaderV2`'ye çözer (CRC destekli)."""
    (
        magic,
        version,
        header_size,
        record_size,
        period_us,
        channel_count,
        start_time_utc_ns,
        header_crc32,
    ) = FILE_HEADER_V2.unpack_from(buffer, offset)
    return FileHeaderV2(
        magic=magic,
        version=version,
        header_size=header_size,
        record_size=record_size,
        period_us=period_us,
        channel_count=channel_count,
        start_time_utc_ns=start_time_utc_ns,
        header_crc32=header_crc32,
    )


def read_data_record_v1(buffer: ReadableBuffer, offset: int) -> DataRecordV1:
    """64 baytlık ham veriyi `DataRecordV1`'e çözer (8 sabit kanal)."""
    unpacked = DATA_RECORD_V1.unpack_from(buffer, offset)
    name, sequence_no, elapsed_us = unpacked[0], unpacked[1], unpacked[2]
    sensor_values = unpacked[3:11]
    bit_status, tx_status = unpacked[11], unpacked[12]
    return DataRecordV1(
        name=name,
        sequence_no=sequence_no,
        elapsed_us=elapsed_us,
        sensor_values=sensor_values,  # type: ignore[arg-type]
        bit_status=bit_status,
        tx_status=tx_status,
    )


def read_data_record_v2(buffer: ReadableBuffer, offset: int) -> DataRecordV2:
    """68 baytlık ham veriyi `DataRecordV2`'ye çözer (v1 gövdesi + `record_crc32`)."""
    unpacked = DATA_RECORD_V2.unpack_from(buffer, offset)
    name, sequence_no, elapsed_us = unpacked[0], unpacked[1], unpacked[2]
    sensor_values = unpacked[3:11]
    bit_status, tx_status, record_crc32 = unpacked[11], unpacked[12], unpacked[13]
    return DataRecordV2(
        name=name,
        sequence_no=sequence_no,
        elapsed_us=elapsed_us,
        sensor_values=sensor_values,  # type: ignore[arg-type]
        bit_status=bit_status,
        tx_status=tx_status,
        record_crc32=record_crc32,
    )

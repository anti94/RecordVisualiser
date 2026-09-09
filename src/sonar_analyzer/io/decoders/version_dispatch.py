"""Sürüme göre decoder seçimi — `F2-012`.

Profil A dosyası kendi sürümünü header'ın `version` alanında taşır (magic'ten
hemen sonra, offset 8, `"<H"`). CRC'siz sürüm 1 ve CRC destekli sürüm 2
(`docs/adr/ADR-011-crc.md` §2.3) hem header hem kayıt için **farklı**
`struct.Struct` sözleşimi kullanır — sürüm 2'nin her ikisine de ekstra bir
`uint32` CRC alanı eklenmesi yüzünden sürüm 1 decoder'ıyla çözülemez.

Bu modül `version` alanını tam header'ı çözmeden önce inceler
(`peek_version`) ve doğru header/kayıt okuyucu çiftini seçer
(`select_decoder`); böylece örnek (v1) format ile sürümlü genişletilmiş
(v2) format ayrı decoder kullanır (kabul kriteri).
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import NamedTuple, Union

from sonar_analyzer.io.decoders.errors import UnsupportedVersionError
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_HEADER_SIZE_V2,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    SUPPORTED_VERSIONS,
    DataRecordV1,
    DataRecordV2,
    FileHeaderV1,
    FileHeaderV2,
)
from sonar_analyzer.io.readers.binary_reader import (
    ReadableBuffer,
    read_data_record_v1,
    read_data_record_v2,
    read_file_header_v1,
    read_file_header_v2,
)

#: magic (8s) hemen sonrasi, "<H" — her iki surumde de ayni offsette.
_VERSION_FIELD = struct.Struct("<H")
_VERSION_FIELD_OFFSET = 8

FileHeader = Union[FileHeaderV1, FileHeaderV2]
DataRecord = Union[DataRecordV1, DataRecordV2]


def peek_version(buffer: ReadableBuffer, offset: int = 0) -> int:
    """Tam header'ı çözmeden yalnız `version` alanını okur (offset 8, `uint16`)."""
    (version,) = _VERSION_FIELD.unpack_from(buffer, offset + _VERSION_FIELD_OFFSET)
    return version


class VersionDecoder(NamedTuple):
    """Bir sürüme ait sabit boyutlar ve okuyucu fonksiyon çifti."""

    version: int
    header_size: int
    record_size: int
    read_header: Callable[[ReadableBuffer, int], FileHeader]
    read_record: Callable[[ReadableBuffer, int], DataRecord]


_DECODERS: dict[int, VersionDecoder] = {
    1: VersionDecoder(
        version=1,
        header_size=EXPECTED_HEADER_SIZE_V1,
        record_size=EXPECTED_RECORD_SIZE_V1,
        read_header=read_file_header_v1,
        read_record=read_data_record_v1,
    ),
    2: VersionDecoder(
        version=2,
        header_size=EXPECTED_HEADER_SIZE_V2,
        record_size=EXPECTED_RECORD_SIZE_V2,
        read_header=read_file_header_v2,
        read_record=read_data_record_v2,
    ),
}


def select_decoder(version: int) -> VersionDecoder:
    """`version` için doğru header/kayıt okuyucu çiftini döner.

    Desteklenmeyen sürümde `UnsupportedVersionError` yükseltir (`F2-003` ile
    aynı hata türü — sürüm doğrulaması tek bir yerde tanımlıdır).
    """
    decoder = _DECODERS.get(version)
    if decoder is None:
        raise UnsupportedVersionError(version, SUPPORTED_VERSIONS, byte_offset=8)
    return decoder


def select_decoder_for_buffer(buffer: ReadableBuffer, offset: int = 0) -> VersionDecoder:
    """Buffer'ın `version` alanını okuyup uygun decoder'ı seçer."""
    return select_decoder(peek_version(buffer, offset))

"""Profil A sürüm 1 doğrulama ve tek kayıt çözümü — `F2-003`, `F2-005`.

Sıra `docs/format/profile-a.md` §3'teki adımlarla aynıdır: magic önce, sonra
sürüm. Boyut/sınır denetimleri (`F2-004`) ayrı fonksiyondadır.
"""

from __future__ import annotations

from collections.abc import Iterator

from sonar_analyzer.io.decoders.errors import InvalidMagicError, UnsupportedVersionError
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_RECORD_SIZE_V1,
    MAGIC,
    SUPPORTED_VERSIONS,
    DataRecordV1,
    FileHeaderV1,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer, read_data_record_v1


def validate_magic(header: FileHeaderV1) -> None:
    """`magic == b"SONARBIN"` değilse `InvalidMagicError` yükseltir."""
    if header.magic != MAGIC:
        raise InvalidMagicError(header.magic, byte_offset=0)


def validate_version(header: FileHeaderV1) -> None:
    """`version` desteklenen kümede değilse `UnsupportedVersionError` yükseltir."""
    if header.version not in SUPPORTED_VERSIONS:
        raise UnsupportedVersionError(header.version, SUPPORTED_VERSIONS, byte_offset=8)


def decode_record_at_index(
    buffer: ReadableBuffer,
    index: int,
    header_size: int = EXPECTED_HEADER_SIZE_V1,
    record_size: int = EXPECTED_RECORD_SIZE_V1,
) -> DataRecordV1:
    """Sıfır tabanlı `index`'teki kaydı çözer — `F2-005`.

    Offset her zaman `header_size + index * record_size` formülüyle
    hesaplanır (kayıpsız dosyada geçerli; boşluklu dosyada `index`,
    fiziksel sırayı değil, dosyadaki n. kaydı gösterir — `sequence_no`
    ile karıştırılmamalıdır, bkz. `docs/format/timing-and-naming.md` §4).
    """
    if index < 0:
        raise ValueError(f"Kayit indeksi negatif olamaz: {index}")
    offset = header_size + index * record_size
    return read_data_record_v1(buffer, offset)


def record_count_in_buffer(
    buffer_length: int,
    header_size: int = EXPECTED_HEADER_SIZE_V1,
    record_size: int = EXPECTED_RECORD_SIZE_V1,
) -> int:
    """Buffer'a sığan **tam** kayıt sayısı; artık bayt varsa yok sayılır.

    Kesik son kayıt burada raporlanmaz (bkz. `F2-009`); yalnız kaçta tam
    kayıt olduğunu söyler.
    """
    if buffer_length < header_size:
        return 0
    return (buffer_length - header_size) // record_size


def iter_records(
    buffer: ReadableBuffer,
    header_size: int = EXPECTED_HEADER_SIZE_V1,
    record_size: int = EXPECTED_RECORD_SIZE_V1,
) -> Iterator[DataRecordV1]:
    """Buffer'daki tüm tam kayıtları sırayla çözer — `F2-006`.

    Her kaydın offseti `header_size + n * record_size` formülüyle üretilir;
    `docs/format/timing-and-naming.md` §2'deki nominal (kayıpsız) offset
    formülüyle aynıdır.
    """
    count = record_count_in_buffer(len(buffer), header_size, record_size)
    for index in range(count):
        yield decode_record_at_index(buffer, index, header_size, record_size)

"""Profil B kayıt/blok konumlarını payload okumadan indeksler — F4-091."""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.decoders.profile_b import (
    ProfileBFormatError,
    ProfileBHeader,
    decode_file_header,
)
from sonar_analyzer.io.profile_b_format import (
    BLOCK_HEADER,
    BLOCK_HEADER_SIZE,
    BLOCK_TYPE_SENSOR_RAW,
    CHANNEL_ENTRY_SIZE,
    DTYPE_SIZE,
    FILE_HEADER_SIZE,
    NUMPY_DTYPE,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_TRAILER_SIZE,
    align8,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


@dataclass(frozen=True)
class BlockIndexEntry:
    block_type: int
    channel_id: int
    dtype_code: int
    t_offset_ns: int
    byte_offset: int
    payload_offset: int
    payload_bytes: int
    sample_count: int


@dataclass(frozen=True)
class ProfileBRecordEntry:
    record_index: int
    name: str
    t_start_offset_ns: int
    byte_offset: int
    byte_size: int
    blocks: tuple[BlockIndexEntry, ...]

    def sensor_block(self, channel_id: int) -> BlockIndexEntry | None:
        return next(
            (
                b
                for b in self.blocks
                if b.channel_id == channel_id and b.block_type == BLOCK_TYPE_SENSOR_RAW
            ),
            None,
        )


@dataclass(frozen=True)
class ProfileBRecordIndex:
    header: ProfileBHeader
    source_size: int
    records: tuple[ProfileBRecordEntry, ...]
    trailing_bytes: int


def build_profile_b_index(buffer: ReadableBuffer) -> ProfileBRecordIndex:
    """Yalnız sabit boylu header dilimleri okur; örnek dizisi/view oluşturmaz.

    Son tam kayıt sonrasındaki kısa kuyruk trailing_bytes ile raporlanır.
    Header'ı mevcut fakat gövdesi kesik bir kayıt ve kendi kaydından taşan blok
    reddedilir. İndeks kaynak buffer'a referans tutmaz; mmap kapanabilir.
    """
    header = decode_file_header(buffer[:FILE_HEADER_SIZE])
    total = len(buffer)
    offset = FILE_HEADER_SIZE + header.channel_count * CHANNEL_ENTRY_SIZE
    if offset > total:
        raise ProfileBFormatError("kanal tablosu dosya sonunu asiyor", byte_offset=FILE_HEADER_SIZE)
    entries: list[ProfileBRecordEntry] = []
    while offset + RECORD_HEADER_SIZE <= total:
        name, index, size, count, _flags, time_ns, *_rest = RECORD_HEADER.unpack(
            buffer[offset : offset + RECORD_HEADER_SIZE]
        )
        if size < RECORD_HEADER_SIZE + RECORD_TRAILER_SIZE or offset + size > total:
            raise ProfileBFormatError(
                f"record_size ({size}) tampon disina cikiyor", byte_offset=offset
            )
        limit = offset + size - RECORD_TRAILER_SIZE
        cursor = offset + RECORD_HEADER_SIZE
        blocks: list[BlockIndexEntry] = []
        for _ in range(count):
            if cursor + BLOCK_HEADER_SIZE > limit:
                raise ProfileBFormatError("blok basligi kayit sonunu asiyor", byte_offset=cursor)
            kind, _flags, payload_bytes, channel_id, dtype, _reserved, time_offset = (
                BLOCK_HEADER.unpack(buffer[cursor : cursor + BLOCK_HEADER_SIZE])
            )
            payload_offset = cursor + BLOCK_HEADER_SIZE
            next_offset = align8(payload_offset + payload_bytes)
            if payload_offset + payload_bytes > limit or next_offset > limit:
                raise ProfileBFormatError(
                    "blok payload kayit sonunu asiyor", byte_offset=payload_offset
                )
            samples = 0
            if kind == BLOCK_TYPE_SENSOR_RAW:
                dtype_size = DTYPE_SIZE.get(dtype)
                if dtype_size is None or dtype not in NUMPY_DTYPE:
                    raise ProfileBFormatError(
                        "taninmayan SENSOR_RAW dtype", byte_offset=cursor + 10
                    )
                if payload_bytes % dtype_size:
                    raise ProfileBFormatError(
                        "block_size dtype boyutuna bolunmuyor", byte_offset=cursor + 4
                    )
                samples = payload_bytes // dtype_size
            blocks.append(
                BlockIndexEntry(
                    kind,
                    channel_id,
                    dtype,
                    time_offset,
                    cursor,
                    payload_offset,
                    payload_bytes,
                    samples,
                )
            )
            cursor = next_offset
        entries.append(
            ProfileBRecordEntry(
                index,
                name.split(b"\x00", 1)[0].decode("ascii", "replace"),
                time_ns,
                offset,
                size,
                tuple(blocks),
            )
        )
        offset += size
    return ProfileBRecordIndex(header, total, tuple(entries), total - offset)

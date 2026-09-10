"""Profil B akustik blok payload decoder'ı — `F4-011`.

`docs/format/profile-b.md` sözleşmesine göre bir Profil B `.bin`
tamponunu dolaşır: `FileHeader` + `ChannelTable` atlanır, kayıtlar
`record_size` üzerinden yürünür, her kayıttaki bloklar `BlockHeader`
zinciriyle çözülür. `SENSOR_RAW` bloklarının payload'ı `np.frombuffer`
ile **kopyasız view** olarak alınır.

Bu iş yalnız **çözümlemedir**; blok-içi zaman `F4-012`, zaman sorgusuna
bağlama `F4-013`, derin doğrulama sonraki işlerde. Bilinmeyen blok türü
atlanmaz — türü ve offseti ile `blocks` içinde raporlanır.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.io.decoders.errors import FormatError
from sonar_analyzer.io.profile_b_format import (
    BLOCK_HEADER,
    BLOCK_HEADER_SIZE,
    BLOCK_TYPE_SENSOR_RAW,
    CHANNEL_ENTRY_SIZE,
    DTYPE_SIZE,
    FILE_HEADER,
    FILE_HEADER_SIZE,
    MAGIC,
    NUMPY_DTYPE,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_TRAILER_SIZE,
    SUPPORTED_VERSION,
    align8,
    record_name,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


class ProfileBFormatError(FormatError):
    """Bir tamponun Profil B sözleşmesini ihlal ettiğini gösterir."""


@dataclass(frozen=True)
class ProfileBHeader:
    """`FileHeader`'ın çözümde kullanılan alanları."""

    version_major: int
    version_minor: int
    channel_count: int
    record_period_ns: int
    t0_utc_ns: int
    record_count: int


@dataclass(frozen=True)
class DecodedBlock:
    """Bir kayıttaki tek blok."""

    block_type: int
    channel_id: int
    dtype_code: int
    t_offset_ns: int
    byte_offset: int
    #: `SENSOR_RAW` ise örnek dizisi (view); değilse `None`.
    samples: NDArray[np.generic] | None

    @property
    def is_sensor_raw(self) -> bool:
        return self.block_type == BLOCK_TYPE_SENSOR_RAW


@dataclass(frozen=True)
class DecodedRecord:
    """Bir 125 ms kaydı ve blokları."""

    record_index: int
    name: str
    t_start_offset_ns: int
    byte_offset: int
    blocks: tuple[DecodedBlock, ...]

    def sensor_block(self, channel_id: int) -> DecodedBlock | None:
        for block in self.blocks:
            if block.is_sensor_raw and block.channel_id == channel_id:
                return block
        return None


def decode_file_header(buffer: ReadableBuffer) -> ProfileBHeader:
    """`FileHeader`'ı çözer; magic / sürüm uyuşmazsa `ProfileBFormatError`."""
    if len(buffer) < FILE_HEADER_SIZE:
        raise ProfileBFormatError("dosya FileHeader'dan kisa", byte_offset=0)
    fields = FILE_HEADER.unpack_from(buffer, 0)
    magic = fields[0]
    if magic != MAGIC:
        raise ProfileBFormatError(f"gecersiz magic: {magic!r}, beklenen {MAGIC!r}", byte_offset=0)
    version_major = fields[1]
    if version_major != SUPPORTED_VERSION:
        raise ProfileBFormatError(
            f"desteklenmeyen surum: {version_major}, beklenen {SUPPORTED_VERSION}",
            byte_offset=8,
        )
    return ProfileBHeader(
        version_major=version_major,
        version_minor=fields[2],
        channel_count=fields[4],
        record_period_ns=fields[6],
        t0_utc_ns=fields[8],
        record_count=fields[10],
    )


def _record_area_start(header: ProfileBHeader) -> int:
    return FILE_HEADER_SIZE + header.channel_count * CHANNEL_ENTRY_SIZE


def _decode_block(buffer: ReadableBuffer, offset: int) -> tuple[DecodedBlock, int]:
    """`offset`'teki bloğu çözer; `(blok, sonraki_offset)` döndürür."""
    block_type, _flags, block_size, ch_id, dtype_code, _rsv, t_offset_ns = BLOCK_HEADER.unpack_from(
        buffer, offset
    )
    payload_offset = offset + BLOCK_HEADER_SIZE

    samples: NDArray[np.generic] | None = None
    if block_type == BLOCK_TYPE_SENSOR_RAW:
        dtype_size = DTYPE_SIZE.get(dtype_code)
        numpy_dtype = NUMPY_DTYPE.get(dtype_code)
        if dtype_size is None or numpy_dtype is None:
            raise ProfileBFormatError(
                f"SENSOR_RAW icin taninmayan dtype kodu: {dtype_code:#x}",
                byte_offset=offset + 10,
            )
        if block_size % dtype_size != 0:
            raise ProfileBFormatError(
                f"block_size ({block_size}) dtype boyutuna ({dtype_size}) tam bolunmuyor",
                byte_offset=offset + 4,
            )
        count = block_size // dtype_size
        if payload_offset + block_size > len(buffer):
            raise ProfileBFormatError(
                "SENSOR_RAW payload dosya sonunu asiyor", byte_offset=payload_offset
            )
        samples = np.frombuffer(buffer, dtype=numpy_dtype, count=count, offset=payload_offset)

    block = DecodedBlock(
        block_type=block_type,
        channel_id=ch_id,
        dtype_code=dtype_code,
        t_offset_ns=t_offset_ns,
        byte_offset=offset,
        samples=samples,
    )
    return block, align8(payload_offset + block_size)


def iter_records(buffer: ReadableBuffer) -> Iterator[DecodedRecord]:
    """Tampondaki tüm Profil B kayıtlarını sırayla çözer."""
    header = decode_file_header(buffer)
    offset = _record_area_start(header)
    total = len(buffer)

    while offset + RECORD_HEADER_SIZE + RECORD_TRAILER_SIZE <= total:
        name_raw, record_index, record_size, block_count, _flags, t_start_offset_ns, *_rest = (
            RECORD_HEADER.unpack_from(buffer, offset)
        )
        if record_size <= 0 or offset + record_size > total:
            raise ProfileBFormatError(
                f"record_size ({record_size}) tampon disina cikiyor", byte_offset=offset
            )

        blocks: list[DecodedBlock] = []
        cur = offset + RECORD_HEADER_SIZE
        block_limit = offset + record_size - RECORD_TRAILER_SIZE
        for _ in range(block_count):
            if cur + BLOCK_HEADER_SIZE > block_limit:
                raise ProfileBFormatError("blok basligi kayit sonunu asiyor", byte_offset=cur)
            block, cur = _decode_block(buffer, cur)
            blocks.append(block)

        yield DecodedRecord(
            record_index=record_index,
            name=name_raw.split(b"\x00", 1)[0].decode("ascii", "replace"),
            t_start_offset_ns=t_start_offset_ns,
            byte_offset=offset,
            blocks=tuple(blocks),
        )
        offset += record_size


def channel_samples(buffer: ReadableBuffer, channel_id: int) -> NDArray[np.generic]:
    """Bir kanalın tüm kayıtlardaki `SENSOR_RAW` örneklerini **sırayla** birleştirir.

    Kanal ve örnek sırası kayıt sırasını korur (kabul kriteri `F4-011`).
    """
    parts: list[NDArray[np.generic]] = []
    for record in iter_records(buffer):
        block = record.sensor_block(channel_id)
        if block is not None and block.samples is not None:
            parts.append(block.samples)
    if not parts:
        return np.empty(0, dtype=np.int16)
    return np.concatenate(parts)


def acoustic_channel_ids(buffer: ReadableBuffer) -> list[int]:
    """İlk kayıtta `SENSOR_RAW` bloğu bulunan kanal kimlikleri, blok sırasıyla."""
    for record in iter_records(buffer):
        return [b.channel_id for b in record.blocks if b.is_sensor_raw]
    return []


def record_names(buffer: ReadableBuffer) -> list[str]:
    """Kayıt adları, dosyadaki sırayla."""
    return [record.name for record in iter_records(buffer)]


def expected_record_names(count: int) -> Sequence[str]:
    return [record_name(i) for i in range(count)]

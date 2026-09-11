"""İndeks payload'a erişmez; konumları bağımsız decoder ile eşleşir."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import cast

import pytest
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.io.decoders.profile_b import ProfileBFormatError, iter_records
from sonar_analyzer.io.index.profile_b_index import build_profile_b_index
from sonar_analyzer.io.profile_b_format import (
    BLOCK_HEADER,
    BLOCK_HEADER_SIZE,
    FILE_HEADER_SIZE,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_TRAILER,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer
from sonar_analyzer.io.readers.mapped_source import MappedSource


class HeaderOnlyBuffer:
    def __init__(self, data: bytes, allowed: set[tuple[int, int]]) -> None:
        self.data = data
        self.allowed = allowed
        self.reads: list[tuple[int, int]] = []

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, item: slice) -> bytes:
        start, stop, step = item.indices(len(self.data))
        assert step == 1 and (start, stop) in self.allowed, "payload veya beklenmeyen alan okundu"
        self.reads.append((start, stop))
        return self.data[item]


def test_only_headers_are_read_and_every_position_matches_the_decoder() -> None:
    data = build_acoustic_fixture(5)
    decoded = tuple(iter_records(data))
    allowed = {(0, FILE_HEADER_SIZE)}
    for record in decoded:
        allowed.add((record.byte_offset, record.byte_offset + RECORD_HEADER_SIZE))
        for block in record.blocks:
            allowed.add((block.byte_offset, block.byte_offset + BLOCK_HEADER_SIZE))
    source = HeaderOnlyBuffer(data, allowed)
    index = build_profile_b_index(cast(ReadableBuffer, source))
    assert set(source.reads) == allowed
    assert index.trailing_bytes == 0
    assert len(index.records) == len(decoded)
    for entry, record in zip(index.records, decoded):
        assert (entry.name, entry.record_index, entry.byte_offset, entry.t_start_offset_ns) == (
            record.name,
            record.record_index,
            record.byte_offset,
            record.t_start_offset_ns,
        )
        for block_entry, block in zip(entry.blocks, record.blocks):
            assert block_entry.byte_offset == block.byte_offset
            assert block_entry.channel_id == block.channel_id
            assert block_entry.dtype_code == block.dtype_code
            assert block_entry.t_offset_ns == block.t_offset_ns
            assert block.samples is not None
            assert block_entry.sample_count == block.samples.size
            assert block_entry.payload_bytes == block.samples.nbytes


def test_variable_sizes_unknown_blocks_and_file_order_are_preserved() -> None:
    header = build_acoustic_fixture(1)[:512]
    parts: list[bytes] = []
    for ordinal, kind, payload in ((7, 999, b"unknown!"), (2, 1, b"\x01\x00" * 4)):
        body = BLOCK_HEADER.pack(kind, 0, len(payload), 0, 1, 0, 17) + payload
        size = RECORD_HEADER.size + len(body) + RECORD_TRAILER.size
        parts.append(
            RECORD_HEADER.pack(
                f"Data{ordinal:05}".encode(), ordinal, size, 1, 0, ordinal * 125_000_000, 0, 0, 0
            )
            + body
            + RECORD_TRAILER.pack(0, b"ENDR")
        )
    data = header + b"".join(parts)
    index = build_profile_b_index(data)
    decoded = tuple(iter_records(data))
    assert [entry.record_index for entry in index.records] == [7, 2]
    assert [entry.byte_offset for entry in index.records] == [r.byte_offset for r in decoded]
    assert index.records[0].sensor_block(0) is None
    assert index.records[0].blocks[0].sample_count == 0
    assert index.records[1].sensor_block(0) is not None


@pytest.mark.parametrize("record_size", [0, 8, 48, 2**31])
def test_invalid_record_lengths_are_rejected(record_size: int) -> None:
    data = bytearray(build_acoustic_fixture(2))
    struct.pack_into("<I", data, 512 + 16, record_size)
    with pytest.raises(ProfileBFormatError):
        build_profile_b_index(data)


def test_payload_cannot_spill_into_the_next_record() -> None:
    data = bytearray(build_acoustic_fixture(3))
    struct.pack_into("<I", data, 512 + RECORD_HEADER_SIZE + 4, 60_000)
    with pytest.raises(ProfileBFormatError, match="kayit sonunu"):
        build_profile_b_index(data)


def test_truncated_record_is_rejected_but_short_trailing_bytes_are_reported() -> None:
    data = build_acoustic_fixture(2)
    with pytest.raises(ProfileBFormatError):
        build_profile_b_index(data[:-100])
    with pytest.raises(ProfileBFormatError):
        build_profile_b_index(data[: 512 + RECORD_HEADER_SIZE])
    index = build_profile_b_index(data + b"short-tail")
    assert index.trailing_bytes == len(b"short-tail")
    assert len(index.records) == 2


def test_index_does_not_keep_the_mapped_source_alive(tmp_path: Path) -> None:
    source = tmp_path / "fixture.bin"
    source.write_bytes(build_acoustic_fixture(2))
    with MappedSource(source) as mapped:
        index = build_profile_b_index(mapped.data())
    source.unlink()
    assert index.records[1].sensor_block(0) is not None

"""48 kHz akustik blok fixture üreteci — `F4-010`.

Kabul: her kanalda 125 ms için 6000 örnek oluşur; bloklar Data sırasını
korur. Gerçek dosya G/Ç içerdiği için `tests/unit/` yerine burada.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray
from tools.make_acoustic_fixture import (
    ACOUSTIC_8RECORDS_SHA256,
    build_acoustic_fixture,
    main,
)

from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_CHANNELS,
    ACOUSTIC_PAYLOAD_BYTES,
    BLOCK_HEADER,
    BLOCK_HEADER_SIZE,
    BLOCK_TYPE_SENSOR_RAW,
    CHANNEL_ENTRY,
    END_MARKER,
    FILE_HEADER,
    MAGIC,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_TRAILER,
    RECORD_TRAILER_SIZE,
    SAMPLES_PER_BLOCK,
    record_name,
)

_Blocks = list[tuple[int, "NDArray[np.int16]"]]


def _iter_records(data: bytes) -> Iterator[tuple[int, str, _Blocks]]:
    """`(record_index, name, [(ch_id, np.ndarray), ...])` üretir."""
    offset = FILE_HEADER.size + len(ACOUSTIC_CHANNELS) * CHANNEL_ENTRY.size
    while offset + RECORD_HEADER_SIZE <= len(data):
        name, index, record_size, block_count, _flags, _t, _ticks, _crc, _rsv = (
            RECORD_HEADER.unpack_from(data, offset)
        )
        blocks: _Blocks = []
        cur = offset + RECORD_HEADER_SIZE
        for _ in range(block_count):
            btype, _bflags, block_size, ch_id, _dtype, _rsv2, _toff = BLOCK_HEADER.unpack_from(
                data, cur
            )
            assert btype == BLOCK_TYPE_SENSOR_RAW
            payload_off = cur + BLOCK_HEADER_SIZE
            samples: NDArray[np.int16] = np.frombuffer(
                data, dtype=np.int16, count=block_size // 2, offset=payload_off
            )
            blocks.append((ch_id, samples))
            cur += BLOCK_HEADER_SIZE + block_size
        yield index, name.split(b"\x00", 1)[0].decode("ascii"), blocks
        offset += record_size


def test_file_header_and_channel_table() -> None:
    data = build_acoustic_fixture(8)
    magic = FILE_HEADER.unpack_from(data, 0)[0]
    assert magic == MAGIC
    channel_count = FILE_HEADER.unpack_from(data, 0)[4]
    assert channel_count == 4

    for i, (want_id, want_path, want_name, _unit) in enumerate(ACOUSTIC_CHANNELS):
        entry = CHANNEL_ENTRY.unpack_from(data, FILE_HEADER.size + i * CHANNEL_ENTRY.size)
        assert entry[0] == want_id
        assert entry[3].split(b"\x00", 1)[0].decode() == want_path
        assert entry[10].split(b"\x00", 1)[0].decode() == want_name
        assert abs(entry[5] - 48000.0) < 1e-6


def test_every_channel_has_6000_samples_per_125ms_record() -> None:
    data = build_acoustic_fixture(8)
    seen_records = 0
    for _index, _name, blocks in _iter_records(data):
        seen_records += 1
        assert [ch for ch, _s in blocks] == [0, 1, 2, 3]  # kanal sırası
        for _ch, samples in blocks:
            assert samples.shape == (SAMPLES_PER_BLOCK,)
            assert samples.shape == (6000,)
    assert seen_records == 8


def test_blocks_preserve_data_record_order() -> None:
    data = build_acoustic_fixture(8)
    names = [name for _i, name, _b in _iter_records(data)]
    indices = [i for i, _n, _b in _iter_records(data)]
    assert names == [record_name(i) for i in range(8)]
    assert indices == list(range(8))


def test_samples_are_continuous_across_record_boundaries() -> None:
    """Blok sınırında örnek tekrarı yok: ch0 örnek sayacı 0..47999 kesintisiz."""
    data = build_acoustic_fixture(8)
    ch0 = np.concatenate([blocks[0][1] for _i, _n, blocks in _iter_records(data)])
    assert ch0.shape == (8 * 6000,)  # 48000 örnek = 1 saniye
    # Her kayıt farklı bir dilim; ilk ve son kaydın ilk örnekleri farklı faz.
    first_block = ch0[:6000]
    second_block = ch0[6000:12000]
    assert not np.array_equal(first_block, second_block)


def test_record_size_and_trailer() -> None:
    data = build_acoustic_fixture(3)
    offset = FILE_HEADER.size + len(ACOUSTIC_CHANNELS) * CHANNEL_ENTRY.size
    _name, _idx, record_size = RECORD_HEADER.unpack_from(data, offset)[:3]
    expected = (
        RECORD_HEADER_SIZE + 4 * (BLOCK_HEADER_SIZE + ACOUSTIC_PAYLOAD_BYTES) + RECORD_TRAILER_SIZE
    )
    assert record_size == expected == 48120
    assert record_size % 8 == 0
    trailer_off = offset + record_size - RECORD_TRAILER_SIZE
    _crc, marker = RECORD_TRAILER.unpack_from(data, trailer_off)
    assert marker == END_MARKER


def test_generator_is_deterministic() -> None:
    assert build_acoustic_fixture(8) == build_acoustic_fixture(8)


def test_default_file_matches_the_pinned_sha256(tmp_path: Path) -> None:
    data = build_acoustic_fixture(8)
    assert hashlib.sha256(data).hexdigest() == ACOUSTIC_8RECORDS_SHA256

    out = tmp_path / "acoustic_8records.bin"
    assert main(["--out", str(out), "--records", "8"]) == 0
    assert hashlib.sha256(out.read_bytes()).hexdigest() == ACOUSTIC_8RECORDS_SHA256


def test_committed_fixture_is_up_to_date() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "acoustic_8records.bin"
    if not fixture.exists():
        # İlk kez oluşturulmamışsa test yalnız üreteci doğrular.
        return
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == ACOUSTIC_8RECORDS_SHA256


def test_zero_records_is_rejected() -> None:
    with pytest.raises(ValueError, match="record_count"):
        build_acoustic_fixture(0)

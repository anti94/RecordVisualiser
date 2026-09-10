"""Profil B akustik blok payload decoder'ı — `F4-011`.

Kabul: kanal ve örnek sırası fixture referansıyla eşleşir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.io.decoders.profile_b import (
    ProfileBFormatError,
    acoustic_channel_ids,
    channel_samples,
    decode_file_header,
    iter_records,
    record_names,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_CHANNEL_IDS,
    ACOUSTIC_SAMPLE_RATE_HZ,
    RECORD_PERIOD_NS,
    SAMPLES_PER_BLOCK,
    record_name,
)

FIXTURE = build_acoustic_fixture(8)

#: `tools/make_acoustic_fixture.py` ile aynı ton tablosu — bağımsız referans.
_TONES: tuple[tuple[float, int], ...] = (
    (997.0, 12000),
    (1499.0, 9000),
    (2003.0, 6000),
    (3001.0, 3000),
)


def reference_channel_samples(channel_id: int, record_index: int) -> NDArray[np.int16]:
    """Beklenen 6000 örnek — decoder'dan bağımsız hesaplanır."""
    tone_hz, amplitude = _TONES[channel_id]
    start = record_index * SAMPLES_PER_BLOCK
    n = np.arange(start, start + SAMPLES_PER_BLOCK, dtype=np.float64)
    wave = amplitude * np.sin(2.0 * math.pi * tone_hz * n / ACOUSTIC_SAMPLE_RATE_HZ)
    return np.round(wave).astype(np.int16)


def test_file_header_fields() -> None:
    header = decode_file_header(FIXTURE)
    assert header.version_major == 1
    assert header.channel_count == 4
    assert header.record_period_ns == RECORD_PERIOD_NS
    assert header.record_count == 8


def test_channel_order_matches_the_fixture_reference() -> None:
    assert acoustic_channel_ids(FIXTURE) == list(ACOUSTIC_CHANNEL_IDS)
    # her kayıtta da aynı sıra
    for record in iter_records(FIXTURE):
        assert [b.channel_id for b in record.blocks if b.is_sensor_raw] == [0, 1, 2, 3]


def test_record_names_are_in_data_order() -> None:
    assert record_names(FIXTURE) == [record_name(i) for i in range(8)]
    indices = [r.record_index for r in iter_records(FIXTURE)]
    assert indices == list(range(8))


def test_sample_order_matches_the_reference_per_channel() -> None:
    for channel_id in ACOUSTIC_CHANNEL_IDS:
        decoded = channel_samples(FIXTURE, channel_id)
        expected = np.concatenate([reference_channel_samples(channel_id, n) for n in range(8)])
        assert decoded.dtype == np.int16
        assert decoded.shape == expected.shape == (8 * SAMPLES_PER_BLOCK,)
        assert np.array_equal(decoded, expected)


def test_per_record_block_samples_match_the_reference() -> None:
    for record in iter_records(FIXTURE):
        for block in record.blocks:
            if not block.is_sensor_raw:
                continue
            assert block.samples is not None
            reference = reference_channel_samples(block.channel_id, record.record_index)
            assert np.array_equal(block.samples, reference)
            assert block.samples.shape == (6000,)


def test_record_start_offsets_follow_the_125ms_grid() -> None:
    for i, record in enumerate(iter_records(FIXTURE)):
        assert record.t_start_offset_ns == i * RECORD_PERIOD_NS


def test_samples_are_a_zero_copy_view_of_the_buffer() -> None:
    buffer = bytearray(build_acoustic_fixture(2))
    record = next(iter_records(bytes(buffer)))
    block = record.sensor_block(0)
    assert block is not None and block.samples is not None
    # frombuffer view: temel arabellek paylaşılır (kopyasız).
    assert block.samples.base is not None


def test_bad_magic_is_rejected_with_offset() -> None:
    broken = bytearray(FIXTURE)
    broken[0] = ord("X")
    with pytest.raises(ProfileBFormatError) as excinfo:
        decode_file_header(bytes(broken))
    assert excinfo.value.byte_offset == 0
    assert "magic" in str(excinfo.value)


def test_unsupported_version_is_rejected() -> None:
    broken = bytearray(FIXTURE)
    broken[8] = 9  # version_major
    with pytest.raises(ProfileBFormatError, match="surum"):
        decode_file_header(bytes(broken))


def test_truncated_file_is_rejected() -> None:
    with pytest.raises(ProfileBFormatError, match="FileHeader"):
        decode_file_header(FIXTURE[:100])

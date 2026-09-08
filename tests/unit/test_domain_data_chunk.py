"""DataChunk ve kalite alanı testleri — `F1-012`."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import DataChunk, Quality

PERIOD_NS = 125_000_000


def times(count: int, start: int = 0) -> NDArray[np.int64]:
    values: NDArray[np.int64] = start + np.arange(count, dtype=np.int64) * PERIOD_NS
    return values.astype(np.int64)


def make(count: int = 4, **overrides: object) -> DataChunk:
    defaults: dict[str, object] = {
        "channel_id": "ch0",
        "timestamps_ns": times(count),
        "values": np.arange(count, dtype=np.float32),
    }
    defaults.update(overrides)
    return DataChunk(**defaults)  # type: ignore[arg-type]


def test_length_and_bounds() -> None:
    chunk = make(8)
    assert len(chunk) == 8
    assert chunk.start_ns == 0
    assert chunk.end_ns == 7 * PERIOD_NS
    assert not chunk.is_empty


def test_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="zaman ve deger uzunluklari farkli"):
        DataChunk(
            channel_id="ch0",
            timestamps_ns=times(5),
            values=np.arange(4, dtype=np.float32),
        )


def test_quality_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="kalite uzunlugu"):
        make(4, quality=np.zeros(3, dtype=np.uint8))


def test_timestamps_must_be_int64() -> None:
    with pytest.raises(ValueError, match="int64 olmali"):
        wrong_dtype: NDArray[np.int32] = np.arange(4, dtype=np.int32)
        make(4, timestamps_ns=wrong_dtype)


def test_two_dimensional_arrays_are_rejected() -> None:
    with pytest.raises(ValueError, match="tek boyutlu"):
        two_dim: NDArray[np.int64] = times(4).reshape(2, 2)
        DataChunk(
            channel_id="ch0",
            timestamps_ns=two_dim,
            values=np.zeros(4, dtype=np.float32),
        )


def test_empty_chunk_is_valid() -> None:
    chunk = DataChunk.empty("ch0")
    assert chunk.is_empty
    assert len(chunk) == 0
    assert chunk.start_ns is None
    assert chunk.end_ns is None
    assert chunk.is_monotonic


def test_monotonic_detection() -> None:
    assert make(4).is_monotonic
    bozuk: NDArray[np.int64] = np.array([0, 2, 1, 3], dtype=np.int64) * PERIOD_NS
    assert not make(4, timestamps_ns=bozuk).is_monotonic


def test_quality_flags_are_detected() -> None:
    quality = np.zeros(4, dtype=np.uint8)
    quality[2] = int(Quality.GAP_BEFORE)
    chunk = make(4, quality=quality)

    assert chunk.has_flag(Quality.GAP_BEFORE)
    assert not chunk.has_flag(Quality.CRC_ERROR)
    assert chunk.flagged_indices(Quality.GAP_BEFORE).tolist() == [2]


def test_combined_flags() -> None:
    quality = np.zeros(3, dtype=np.uint8)
    quality[1] = int(Quality.GAP_BEFORE | Quality.JITTER)
    chunk = make(3, quality=quality)

    assert chunk.has_flag(Quality.GAP_BEFORE)
    assert chunk.has_flag(Quality.JITTER)
    assert not chunk.has_flag(Quality.CRC_ERROR)


def test_no_quality_array_means_no_flags() -> None:
    chunk = make(4)
    assert not chunk.has_flag(Quality.GAP_BEFORE)
    assert chunk.flagged_indices(Quality.GAP_BEFORE).size == 0


def test_empty_channel_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Kanal kimligi bos"):
        make(4, channel_id="  ")

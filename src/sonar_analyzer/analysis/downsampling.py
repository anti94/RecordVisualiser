"""Çizim için min/max örnek seçimi. Analiz hesaplarının girdisi değildir."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import DataChunk


def extrema_indices(values: NDArray[np.generic]) -> NDArray[np.int64]:
    """Min, max ve varsa ilk geçersiz örnek; kaynak sırası korunur."""
    if values.ndim != 1:
        raise ValueError("values tek boyutlu olmalı")
    finite = np.flatnonzero(np.isfinite(values))
    chosen: list[int] = []
    if finite.size:
        valid = values[finite]
        chosen.append(int(finite[np.argmin(valid)]))
        # Eşit maksimumda son örnek: düz blokların sağ ucu kaybolmaz.
        chosen.append(int(finite[finite.size - 1 - np.argmax(valid[::-1])]))
    missing = np.flatnonzero(~np.isfinite(values))
    if missing.size:
        chosen.append(int(missing[0]))
    return np.array(sorted(set(chosen)), dtype=np.int64)


def envelope_indices(values: NDArray[np.generic], max_points: object) -> NDArray[np.int64]:
    """Bitişik kovalardan orijinal örnekler seçer; sonuç bütçeyi aşmaz."""
    if isinstance(max_points, bool) or not isinstance(max_points, int) or max_points < 1:
        raise ValueError("max_points pozitif tam sayı olmalı")
    if values.ndim != 1:
        raise ValueError("values tek boyutlu olmalı")
    count = int(values.size)
    if count <= max_points:
        return np.arange(count, dtype=np.int64)
    missing = np.flatnonzero(~np.isfinite(values))
    if max_points < 3 and missing.size:
        chosen = [int(missing[0])]
        finite = np.flatnonzero(np.isfinite(values))
        if max_points == 2 and finite.size:
            chosen.append(int(finite[np.argmax(np.abs(values[finite]))]))
        return np.array(sorted(chosen), dtype=np.int64)
    if max_points == 1:
        return np.array([int(np.argmax(np.abs(values)))], dtype=np.int64)
    bucket_count = max_points // (3 if missing.size else 2)
    selected: list[NDArray[np.int64]] = []
    for bucket in range(bucket_count):
        start = bucket * count // bucket_count
        stop = (bucket + 1) * count // bucket_count
        selected.append(extrema_indices(values[start:stop]) + start)
    return np.concatenate(selected)


def downsample_chunk(chunk: DataChunk, max_points: int | None) -> DataChunk:
    """Seçilen zaman, değer ve kaliteyi birlikte taşır; kaynağı değiştirmez."""
    if max_points is None:
        return chunk
    keep = envelope_indices(chunk.values, max_points)
    return DataChunk(
        channel_id=chunk.channel_id,
        timestamps_ns=chunk.timestamps_ns[keep],
        values=chunk.values[keep],
        quality=None if chunk.quality is None else chunk.quality[keep],
    )

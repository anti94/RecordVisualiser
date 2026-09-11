"""Zaman kovalarının uç değerlerini sınırlı bellekle biriktirir — F4-095."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from sonar_analyzer.analysis.downsampling import downsample_chunk, extrema_indices
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange


def _extrema(chunk: DataChunk) -> DataChunk:
    keep = extrema_indices(chunk.values)
    return DataChunk(
        chunk.channel_id,
        chunk.timestamps_ns[keep],
        chunk.values[keep],
        None if chunk.quality is None else chunk.quality[keep],
    )


def _join(chunks: list[DataChunk], channel_id: str) -> DataChunk:
    if not chunks:
        return DataChunk.empty(channel_id)
    times = np.concatenate([chunk.timestamps_ns for chunk in chunks])
    values = np.concatenate([chunk.values for chunk in chunks])
    flags = (
        np.concatenate(
            [
                np.zeros(len(chunk), dtype=np.uint8) if chunk.quality is None else chunk.quality
                for chunk in chunks
            ]
        )
        if any(chunk.quality is not None for chunk in chunks)
        else None
    )
    order = np.argsort(times, kind="stable")
    return DataChunk(
        channel_id, times[order], values[order], None if flags is None else flags[order]
    )


def streaming_envelope(
    chunks: Iterable[DataChunk], channel_id: str, span: TimeRange, max_points: int
) -> DataChunk:
    """Her eşit zaman kovasında ilk min, son max ve ilk geçersiz örnek kalır.

    Girdi parçalarının kendi zamanları sıralı olmalıdır; parçalar örtüşebilir.
    Saklanan ara sonuç en çok üç örnek/kova ve tek girdi parçasıdır.
    Zamanlar ve kalite bayrakları seçilen kaynak örneğinden birlikte taşınır.
    """
    downsample_chunk(DataChunk.empty(channel_id), max_points)
    if span.start_ns == span.end_ns:
        return DataChunk.empty(channel_id)
    bucket_count = min(max(1, max_points // 3), span.end_ns - span.start_ns)
    edges = np.array(
        [
            span.start_ns + (span.end_ns - span.start_ns) * i // bucket_count
            for i in range(bucket_count + 1)
        ],
        dtype=np.int64,
    )
    buckets: list[DataChunk | None] = [None] * bucket_count
    for chunk in chunks:
        if not len(chunk):
            continue
        first = max(0, int(np.searchsorted(edges, int(chunk.timestamps_ns[0]), side="right")) - 1)
        last = min(
            bucket_count, int(np.searchsorted(edges, int(chunk.timestamps_ns[-1]), side="right"))
        )
        boundaries = np.searchsorted(chunk.timestamps_ns, edges[first : last + 1])
        for bucket in range(first, last):
            lo, hi = int(boundaries[bucket - first]), int(boundaries[bucket - first + 1])
            if hi <= lo:
                continue
            current = _extrema(
                DataChunk(
                    channel_id,
                    chunk.timestamps_ns[lo:hi],
                    chunk.values[lo:hi],
                    None if chunk.quality is None else chunk.quality[lo:hi],
                )
            )
            previous = buckets[bucket]
            buckets[bucket] = (
                current if previous is None else _extrema(_join([previous, current], channel_id))
            )
    return downsample_chunk(_join([b for b in buckets if b is not None], channel_id), max_points)

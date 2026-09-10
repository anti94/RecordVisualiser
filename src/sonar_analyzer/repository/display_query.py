"""Viewport için özet seviyesi seçimi; tam analiz sorguları özet kullanmaz."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from sonar_analyzer.analysis.downsampling import downsample_chunk, extrema_indices
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.index.summary_pyramid import SummaryLevel, build_summary_pyramid


class ViewportSummary:
    """Bir zaman penceresinin değişmez verisi ve min/max seviyeleri."""

    def __init__(self, chunk: DataChunk) -> None:
        self.chunk = DataChunk(
            chunk.channel_id,
            chunk.timestamps_ns.copy(),
            chunk.values.copy(),
            None if chunk.quality is None else chunk.quality.copy(),
        )
        self.chunk.timestamps_ns.setflags(write=False)
        self.chunk.values.setflags(write=False)
        if self.chunk.quality is not None:
            self.chunk.quality.setflags(write=False)
        if not self.chunk.is_monotonic:
            raise ValueError("Özet kaynağının zamanları sıralı olmalı")
        self.pyramid = build_summary_pyramid(self.chunk.values)

    @property
    def nbytes(self) -> int:
        flags = 0 if self.chunk.quality is None else self.chunk.quality.nbytes
        return (
            int(self.chunk.timestamps_ns.nbytes + self.chunk.values.nbytes + flags)
            + self.pyramid.nbytes
        )

    def choose_level(self, start: int, stop: int, max_points: int) -> SummaryLevel | None:
        if stop - start <= max_points:
            return None
        for level in self.pyramid.levels:
            blocks = (stop - 1) // level.block_size - start // level.block_size + 1
            if blocks * 3 <= max_points:
                return level
        return self.pyramid.levels[-1] if self.pyramid.levels else None

    def query(self, span: TimeRange, max_points: int) -> DataChunk:
        chunk = self.chunk
        start = int(np.searchsorted(chunk.timestamps_ns, span.start_ns, side="left"))
        stop = int(np.searchsorted(chunk.timestamps_ns, span.end_ns, side="left"))
        level = self.choose_level(start, stop, max_points)
        if level is None:
            keep = np.arange(start, stop, dtype=np.int64)
        else:
            selected: list[int] = []
            for block in range(start // level.block_size, (stop - 1) // level.block_size + 1):
                lo = max(start, block * level.block_size)
                hi = min(stop, (block + 1) * level.block_size)
                if lo == block * level.block_size and hi == min(
                    len(chunk), (block + 1) * level.block_size
                ):
                    selected.extend(level.block_indices(block).tolist())
                else:
                    # Kısmi blok: viewport dışındaki bir tepe seçimi etkileyemez.
                    selected.extend((extrema_indices(chunk.values[lo:hi]) + lo).tolist())
            keep = np.array(selected, dtype=np.int64)
        result = DataChunk(
            chunk.channel_id,
            chunk.timestamps_ns[keep],
            chunk.values[keep],
            None if chunk.quality is None else chunk.quality[keep],
        )
        return downsample_chunk(result, max_points)


class DisplayQuery:
    """Son çizim penceresini tutar; içindeki pan/zoom sorguları tekrar decode edilmez."""

    def __init__(self, read: Callable[[str, TimeRange], DataChunk]) -> None:
        self._read = read
        self._cached: tuple[str, TimeRange, ViewportSummary] | None = None

    def clear(self) -> None:
        self._cached = None

    def query(self, channel_id: str, span: TimeRange, max_points: int | None) -> DataChunk:
        if max_points is None:
            return self._read(channel_id, span)
        # Boş/saklanmış sorgularda da aynı bütçe doğrulaması uygulanır.
        downsample_chunk(DataChunk.empty(channel_id), max_points)
        cached = self._cached
        if (
            cached is None
            or cached[0] != channel_id
            or cached[1].start_ns > span.start_ns
            or cached[1].end_ns < span.end_ns
        ):
            summary = ViewportSummary(self._read(channel_id, span))
            self._cached = (channel_id, span, summary)
        else:
            summary = cached[2]
        return summary.query(span, max_points)

"""Viewport için özet seviyesi seçimi; tam analiz sorguları özet kullanmaz.

`F4-059`: üretilen pencere özetleri **bellek sınırlı bir LRU önbellekte**
tutulur. Kullanıcı ileri geri gezindikçe daha önce çözülmüş pencereler
yeniden decode edilmez; bütçe aşılınca en az kullanılan pencere çıkar ve
ölçülen kullanım `cache_stats()` ile raporlanır.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from sonar_analyzer.analysis.downsampling import downsample_chunk, extrema_indices
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.index.summary_pyramid import SummaryLevel, build_summary_pyramid
from sonar_analyzer.repository.memory_cache import (
    DEFAULT_MAX_BYTES,
    CacheStats,
    MemoryBoundedCache,
)


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
    """Çizilen pencereleri tutar; içlerindeki pan/zoom sorguları tekrar decode edilmez.

    Pencereler `F4-059` bellek sınırlı LRU önbelleğinde saklanır: bütçe
    aşılınca en az kullanılan pencere çıkar, ölçülen kullanım
    `cache_stats()` ile raporlanır.
    """

    def __init__(
        self,
        read: Callable[[str, TimeRange], DataChunk],
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self._read = read
        self._cache: MemoryBoundedCache[tuple[str, int, int], ViewportSummary] = MemoryBoundedCache(
            max_bytes
        )

    def clear(self) -> None:
        self._cache.clear()

    def cache_stats(self) -> CacheStats:
        """Önbelleğin ölçülen kullanımı ve sayaçları — `F4-059`."""
        return self._cache.stats()

    def _covering(self, channel_id: str, span: TimeRange) -> ViewportSummary | None:
        """`span`'i **kapsayan** saklı bir pencere varsa onu döndürür."""
        for key in reversed(self._cache.keys()):  # en yeniden en eskiye
            cached_channel, start_ns, end_ns = key
            if cached_channel == channel_id and start_ns <= span.start_ns and end_ns >= span.end_ns:
                return self._cache.get(key)
        self._cache.get((channel_id, span.start_ns, span.end_ns))  # ıska sayılsın
        return None

    def query(self, channel_id: str, span: TimeRange, max_points: int | None) -> DataChunk:
        if max_points is None:
            return self._read(channel_id, span)
        # Boş/saklanmış sorgularda da aynı bütçe doğrulaması uygulanır.
        downsample_chunk(DataChunk.empty(channel_id), max_points)
        summary = self._covering(channel_id, span)
        if summary is None:
            summary = ViewportSummary(self._read(channel_id, span))
            self._cache.put((channel_id, span.start_ns, span.end_ns), summary)
        return summary.query(span, max_points)

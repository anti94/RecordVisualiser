"""Kaynak indekslerini taşıyan çok seviyeli min/max blokları — F4-057."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.downsampling import extrema_indices

BASE_BLOCK_SIZE = 32
LEVEL_FACTOR = 4


@dataclass(frozen=True)
class SummaryLevel:
    """Her blok için min/max/geçersiz örneklerin orijinal konumları."""

    block_size: int
    indices: NDArray[np.int64]
    offsets: NDArray[np.int64]

    @property
    def block_count(self) -> int:
        return int(self.offsets.size) - 1

    def block_indices(self, block: int) -> NDArray[np.int64]:
        if not 0 <= block < self.block_count:
            raise IndexError("Özet blok indeksi sınır dışında")
        return self.indices[int(self.offsets[block]) : int(self.offsets[block + 1])]

    @property
    def nbytes(self) -> int:
        return int(self.indices.nbytes + self.offsets.nbytes)


@dataclass(frozen=True)
class SummaryPyramid:
    sample_count: int
    levels: tuple[SummaryLevel, ...]

    @property
    def nbytes(self) -> int:
        """Özet dizilerinin bayt sayısı; kaynak verinin kendisi tutulmaz."""
        return sum(level.nbytes for level in self.levels)


def _level(block_size: int, blocks: list[NDArray[np.int64]]) -> SummaryLevel:
    indices = np.concatenate(blocks)
    offsets = np.concatenate(
        (np.zeros(1, dtype=np.int64), np.cumsum([len(block) for block in blocks], dtype=np.int64))
    )
    indices.setflags(write=False)
    offsets.setflags(write=False)
    return SummaryLevel(block_size, indices, offsets)


def build_summary_pyramid(
    values: NDArray[np.generic], *, base_block_size: int = BASE_BLOCK_SIZE
) -> SummaryPyramid:
    """İlk seviyeyi kaynaktan, üst seviyeleri alt blokların özetlerinden üretir.

    Son kısmi blok dahil edilir. Kaynak değiştirilirse özet yeniden kurulmalıdır.
    F4-060 kaynak kimliği bunu cache sınırında zorlar.
    """
    if base_block_size < 2:
        raise ValueError("base_block_size en az 2 olmalı")
    if values.ndim != 1:
        raise ValueError("values tek boyutlu olmalı")
    count = int(values.size)
    if count == 0:
        return SummaryPyramid(0, ())
    blocks = [
        extrema_indices(values[start : start + base_block_size]) + start
        for start in range(0, count, base_block_size)
    ]
    current = _level(base_block_size, blocks)
    levels = [current]
    while current.block_count > 1:
        merged: list[NDArray[np.int64]] = []
        for start in range(0, current.block_count, LEVEL_FACTOR):
            stop = min(start + LEVEL_FACTOR, current.block_count)
            candidates = current.indices[int(current.offsets[start]) : int(current.offsets[stop])]
            merged.append(candidates[extrema_indices(values[candidates])])
        current = _level(current.block_size * LEVEL_FACTOR, merged)
        levels.append(current)
    return SummaryPyramid(count, tuple(levels))

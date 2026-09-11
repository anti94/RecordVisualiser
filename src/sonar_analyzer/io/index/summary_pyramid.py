"""Kaynak indekslerini taşıyan çok seviyeli min/max blokları — F4-057."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BASE_BLOCK_SIZE = 32
LEVEL_FACTOR = 4
_TILE_SAMPLES = 131_072
_NO_INDEX = np.iinfo(np.int64).max


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


def _extrema_rows(values: NDArray[np.generic], positions: NDArray[np.int64]) -> NDArray[np.int64]:
    """Her satırdan ilk min, son max ve ilk geçersiz kaynak konumunu seçer."""
    present = positions < values.size
    samples = values[np.where(present, positions, 0)]
    finite = present & np.isfinite(samples)
    rows = np.arange(positions.shape[0])
    chosen = np.full((positions.shape[0], 3), _NO_INDEX, dtype=np.int64)
    if np.all(finite):
        first_min = np.argmin(samples, axis=1)
        last_max = samples.shape[1] - 1 - np.argmax(samples[:, ::-1], axis=1)
        chosen[:, 0] = positions[rows, first_min]
        chosen[:, 1] = positions[rows, last_max]
    else:
        # Geçersiz hücreleri aynı satırın bir sonlu değeriyle doldurmak,
        # int64 değerleri float'a dönüştürmeden min/max hesaplamayı sağlar.
        representative = samples[rows, np.argmax(finite, axis=1)]
        clean = np.where(finite, samples, representative[:, None])
        minima = (clean == np.min(clean, axis=1)[:, None]) & finite
        maxima = (clean == np.max(clean, axis=1)[:, None]) & finite
        has_finite = np.any(finite, axis=1)
        chosen[:, 0] = np.where(has_finite, positions[rows, np.argmax(minima, axis=1)], _NO_INDEX)
        chosen[:, 1] = np.where(
            has_finite,
            positions[rows, samples.shape[1] - 1 - np.argmax(maxima[:, ::-1], axis=1)],
            _NO_INDEX,
        )
        missing = present & ~finite
        chosen[:, 2] = np.where(
            np.any(missing, axis=1), positions[rows, np.argmax(missing, axis=1)], _NO_INDEX
        )
    chosen.sort(axis=1)
    chosen[:, 1:][chosen[:, 1:] == chosen[:, :-1]] = _NO_INDEX
    chosen.sort(axis=1)
    return chosen


def _level(block_size: int, grid: NDArray[np.int64]) -> SummaryLevel:
    present = grid != _NO_INDEX
    indices = grid[present]
    offsets = np.empty(grid.shape[0] + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(np.sum(present, axis=1), dtype=np.int64, out=offsets[1:])
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
    block_count = (count + base_block_size - 1) // base_block_size
    grid = np.empty((block_count, 3), dtype=np.int64)
    tile_rows = max(1, _TILE_SAMPLES // base_block_size)
    columns = np.arange(min(base_block_size, count), dtype=np.int64)
    for start in range(0, block_count, tile_rows):
        stop = min(start + tile_rows, block_count)
        positions = np.arange(start, stop, dtype=np.int64)[:, None] * base_block_size + columns
        positions[positions >= count] = _NO_INDEX
        grid[start:stop] = _extrema_rows(values, positions)
    current = _level(base_block_size, grid)
    levels = [current]
    while current.block_count > 1:
        parent_count = (current.block_count + LEVEL_FACTOR - 1) // LEVEL_FACTOR
        merged = np.empty((parent_count, 3), dtype=np.int64)
        tile_rows = _TILE_SAMPLES // (LEVEL_FACTOR * 3)
        for start in range(0, parent_count, tile_rows):
            stop = min(start + tile_rows, parent_count)
            candidates = grid[start * LEVEL_FACTOR : stop * LEVEL_FACTOR]
            padding = (stop - start) * LEVEL_FACTOR - len(candidates)
            if padding:
                candidates = np.pad(candidates, ((0, padding), (0, 0)), constant_values=_NO_INDEX)
            merged[start:stop] = _extrema_rows(values, candidates.reshape(stop - start, -1))
        grid = merged
        current = _level(current.block_size * LEVEL_FACTOR, grid)
        levels.append(current)
    return SummaryPyramid(count, tuple(levels))

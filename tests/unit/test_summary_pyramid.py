"""Her özet seviyesinin doğrudan ham blok min/max referansıyla karşılaştırılması."""

import numpy as np
import pytest

from sonar_analyzer.analysis.downsampling import extrema_indices
from sonar_analyzer.io.index.summary_pyramid import build_summary_pyramid


@pytest.mark.parametrize("count", [1, 31, 32, 33, 1003, 4097])
def test_all_levels_match_raw_block_extrema(count: int) -> None:
    values = np.random.default_rng(55).integers(-20, 20, size=count).astype(np.float64)
    values[::51] = np.nan
    pyramid = build_summary_pyramid(values)
    for level in pyramid.levels:
        assert level.block_count == (count + level.block_size - 1) // level.block_size
        for block in range(level.block_count):
            start = block * level.block_size
            stop = min(start + level.block_size, count)
            finite = [i for i in range(start, stop) if np.isfinite(values[i])]
            missing = [i for i in range(start, stop) if not np.isfinite(values[i])]
            expected: set[int] = set()
            if finite:
                expected.add(min(finite, key=lambda i: (values[i], i)))
                expected.add(max(finite, key=lambda i: (values[i], i)))
            if missing:
                expected.add(missing[0])
            assert list(level.block_indices(block)) == sorted(expected)
        assert not level.indices.flags.writeable
        assert not level.offsets.flags.writeable
    assert pyramid.levels[-1].block_count == 1


def test_summary_storage_is_bounded_and_does_not_retain_source() -> None:
    values = np.ones(100_000)
    pyramid = build_summary_pyramid(values)
    assert pyramid.nbytes < values.nbytes // 4
    assert all(not np.shares_memory(level.indices, values) for level in pyramid.levels)
    assert np.all(values == 1)


def test_empty_input_has_no_levels() -> None:
    pyramid = build_summary_pyramid(np.array([]))
    assert pyramid.sample_count == 0 and pyramid.levels == () and pyramid.nbytes == 0


@pytest.mark.parametrize("block_size", [2, 32, 127, 1024])
@pytest.mark.parametrize("case", ["int64", "uint64", "ties", "invalid", "mixed"])
def test_vectorized_selection_preserves_dtype_ties_and_partial_blocks(
    block_size: int, case: str
) -> None:
    if case == "int64":
        values = np.array([2**63 - 3, 2**63 - 2, -(2**63), 2**63 - 1] * 101, dtype=np.int64)
    elif case == "uint64":
        values = np.array([2**64 - 3, 2**64 - 2, 0, 2**64 - 1] * 101, dtype=np.uint64)
    elif case == "ties":
        values = np.array([0.0, -0.0, 1.0, 1.0] * 101)
    elif case == "invalid":
        values = np.array([np.nan, np.inf, -np.inf, np.nan] * 101)
    else:
        values = np.array([np.nan, 7.0, np.inf, -3.0, -3.0, 7.0, -np.inf] * 57)
    original = values.copy()
    pyramid = build_summary_pyramid(values, base_block_size=block_size)
    for level in pyramid.levels:
        for block in range(level.block_count):
            start = block * level.block_size
            expected = extrema_indices(values[start : start + level.block_size]) + start
            np.testing.assert_array_equal(level.block_indices(block), expected)
    np.testing.assert_array_equal(values, original)


def test_vectorized_tiles_preserve_extrema_at_tile_edges() -> None:
    values = np.random.default_rng(81).normal(size=131_137)
    values[131_071:131_074] = [1e9, np.nan, -1e9]
    pyramid = build_summary_pyramid(values)
    for level in pyramid.levels:
        for block in range(level.block_count):
            start = block * level.block_size
            expected = extrema_indices(values[start : start + level.block_size]) + start
            np.testing.assert_array_equal(level.block_indices(block), expected)


def test_invalid_block_size_and_block_access_fail() -> None:
    with pytest.raises(ValueError):
        build_summary_pyramid(np.ones(4), base_block_size=1)
    level = build_summary_pyramid(np.ones(4)).levels[0]
    with pytest.raises(IndexError):
        level.block_indices(-1)
    with pytest.raises(IndexError):
        level.block_indices(1)

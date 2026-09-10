"""Waterfall zaman dilimi modeli — `F4-050`.

Kabul: yeni dilim eklenir; geçmiş için belirlenen sınır korunur.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.stft import stft
from sonar_analyzer.analysis.waterfall import (
    DEFAULT_MAX_SLICES,
    WaterfallError,
    WaterfallModel,
)

Vec = NDArray[np.float64]

BINS = 5


def _slice(value: float, bins: int = BINS) -> Vec:
    """Her bini `value` olan bir dilim (kimliği kolay doğrulanır)."""
    return np.full(bins, value, dtype=np.float64)


def _filled(count: int, capacity: int = 4) -> WaterfallModel:
    model = WaterfallModel(BINS, max_slices=capacity)
    for index in range(count):
        model.append(float(index), _slice(float(index)))
    return model


# --------------------------------------------------------------------------- #
# kurulum
# --------------------------------------------------------------------------- #


def test_a_new_model_is_empty() -> None:
    model = WaterfallModel(BINS, max_slices=8)
    assert len(model) == 0
    assert not model.is_full
    assert model.capacity == 8
    assert model.bin_count == BINS
    assert model.matrix().shape == (0, BINS)
    assert model.times_s().shape == (0,)


def test_the_default_history_limit_is_documented() -> None:
    assert DEFAULT_MAX_SLICES == 256
    assert WaterfallModel(BINS).capacity == DEFAULT_MAX_SLICES


@pytest.mark.parametrize("bad", [0, -1])
def test_a_nonpositive_bin_count_is_rejected(bad: int) -> None:
    with pytest.raises(WaterfallError, match="bin sayısı"):
        WaterfallModel(bad)


@pytest.mark.parametrize("bad", [0, -5])
def test_a_nonpositive_history_limit_is_rejected(bad: int) -> None:
    with pytest.raises(WaterfallError, match="geçmiş sınırı"):
        WaterfallModel(BINS, max_slices=bad)


# --------------------------------------------------------------------------- #
# yeni dilim eklenir
# --------------------------------------------------------------------------- #


def test_appending_grows_the_model() -> None:
    model = WaterfallModel(BINS, max_slices=4)
    for index in range(3):
        model.append(float(index), _slice(float(index)))
        assert len(model) == index + 1
    assert not model.is_full


def test_slices_are_stored_oldest_first() -> None:
    model = _filled(3)
    assert np.allclose(model.times_s(), [0.0, 1.0, 2.0])
    matrix = model.matrix()
    assert matrix.shape == (3, BINS)
    assert np.allclose(matrix[0], _slice(0.0))
    assert np.allclose(matrix[-1], _slice(2.0))


def test_newest_and_oldest_report_the_ends() -> None:
    model = _filled(3)
    assert model.newest().time_s == 2.0
    assert np.allclose(model.newest().magnitudes, _slice(2.0))
    assert model.oldest().time_s == 0.0
    assert np.allclose(model.oldest().magnitudes, _slice(0.0))
    assert model.time_span_s() == 2.0


def test_a_single_slice_has_zero_span() -> None:
    model = _filled(1)
    assert model.time_span_s() == 0.0
    assert model.newest().time_s == model.oldest().time_s


def test_slice_at_indexes_from_the_oldest() -> None:
    model = _filled(3)
    assert model.slice_at(0).time_s == 0.0
    assert model.slice_at(2).time_s == 2.0
    with pytest.raises(WaterfallError, match="indeksi aralık dışı"):
        model.slice_at(3)


def test_a_returned_slice_is_a_copy() -> None:
    model = _filled(2)
    taken = model.newest()
    taken.magnitudes[0] = 999.0
    assert model.newest().magnitudes[0] == 1.0


# --------------------------------------------------------------------------- #
# geçmiş sınırı korunur
# --------------------------------------------------------------------------- #


def test_the_length_never_exceeds_the_limit() -> None:
    model = WaterfallModel(BINS, max_slices=4)
    for index in range(50):
        model.append(float(index), _slice(float(index)))
        assert len(model) <= 4
    assert len(model) == 4
    assert model.is_full


def test_the_capacity_never_changes() -> None:
    model = WaterfallModel(BINS, max_slices=3)
    for index in range(20):
        model.append(float(index), _slice(float(index)))
        assert model.capacity == 3


def test_the_oldest_slice_is_dropped_first() -> None:
    model = _filled(4, capacity=4)
    assert model.oldest().time_s == 0.0

    model.append(4.0, _slice(4.0))

    assert len(model) == 4
    assert model.oldest().time_s == 1.0  # 0 düştü
    assert model.newest().time_s == 4.0
    assert np.allclose(model.times_s(), [1.0, 2.0, 3.0, 4.0])


def test_the_newest_slice_is_always_kept_even_when_full() -> None:
    model = WaterfallModel(BINS, max_slices=2)
    for index in range(10):
        model.append(float(index), _slice(float(index)))
        assert model.newest().time_s == float(index)
        assert np.allclose(model.newest().magnitudes, _slice(float(index)))


def test_the_matrix_stays_ordered_after_wrapping() -> None:
    model = WaterfallModel(BINS, max_slices=3)
    for index in range(7):
        model.append(float(index), _slice(float(index)))

    assert np.allclose(model.times_s(), [4.0, 5.0, 6.0])
    matrix = model.matrix()
    assert np.allclose(matrix[0], _slice(4.0))
    assert np.allclose(matrix[1], _slice(5.0))
    assert np.allclose(matrix[2], _slice(6.0))


def test_a_limit_of_one_keeps_only_the_newest() -> None:
    model = WaterfallModel(BINS, max_slices=1)
    for index in range(5):
        model.append(float(index), _slice(float(index)))
        assert len(model) == 1
        assert model.newest().time_s == float(index)
        assert model.oldest().time_s == float(index)


def test_the_span_tracks_the_retained_history() -> None:
    model = WaterfallModel(BINS, max_slices=3)
    for index in range(10):
        model.append(float(index), _slice(float(index)))
    # Yalnız son üç dilim tutuluyor: 7, 8, 9.
    assert model.time_span_s() == 2.0


def test_clear_drops_the_history_but_keeps_the_capacity() -> None:
    model = _filled(4, capacity=4)
    model.clear()
    assert len(model) == 0
    assert not model.is_full
    assert model.capacity == 4
    assert model.matrix().shape == (0, BINS)

    # Temizlikten sonra zaman yeniden başlayabilir.
    model.append(0.0, _slice(7.0))
    assert model.newest().time_s == 0.0


# --------------------------------------------------------------------------- #
# geçerlilik
# --------------------------------------------------------------------------- #


def test_a_slice_with_the_wrong_bin_count_is_rejected() -> None:
    model = WaterfallModel(BINS, max_slices=4)
    with pytest.raises(WaterfallError, match="bin taşımalı"):
        model.append(0.0, _slice(1.0, bins=BINS + 1))


def test_a_two_dimensional_slice_is_rejected() -> None:
    model = WaterfallModel(BINS, max_slices=4)
    with pytest.raises(WaterfallError, match="tek boyutlu"):
        model.append(0.0, np.zeros((2, BINS)))


def test_time_must_move_forward() -> None:
    model = _filled(2)
    with pytest.raises(WaterfallError, match="ileri gelmeli"):
        model.append(1.0, _slice(9.0))  # son damga 1.0
    with pytest.raises(WaterfallError, match="ileri gelmeli"):
        model.append(0.5, _slice(9.0))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_a_nonfinite_timestamp_is_rejected(bad: float) -> None:
    model = WaterfallModel(BINS, max_slices=4)
    with pytest.raises(WaterfallError, match="sonlu olmalı"):
        model.append(bad, _slice(1.0))


def test_reading_an_empty_model_is_rejected_not_faked() -> None:
    model = WaterfallModel(BINS, max_slices=4)
    for call in (model.newest, model.oldest, model.newest_time_s, model.oldest_time_s):
        with pytest.raises(WaterfallError, match="boş"):
            call()
    with pytest.raises(WaterfallError, match="boş"):
        model.time_span_s()


# --------------------------------------------------------------------------- #
# STFT'den besleme
# --------------------------------------------------------------------------- #


def _chirp(count: int = 4_000, rate: float = 1_000.0) -> Vec:
    t = np.arange(count, dtype=np.float64) / rate
    duration = count / rate
    return np.sin(2.0 * math.pi * (50.0 * t + 0.5 * 350.0 / duration * t * t))


def test_extend_from_stft_appends_every_column() -> None:
    result = stft(_chirp(), 1_000.0, segment_length=256, overlap=0.5)
    model = WaterfallModel(result.bin_count, max_slices=1_000)

    added = model.extend_from_stft(result)

    assert added == result.frame_count
    assert len(model) == result.frame_count
    assert np.allclose(model.times_s(), result.times_s)
    assert np.allclose(model.matrix(), result.magnitudes.T)


def test_extend_from_stft_respects_the_history_limit() -> None:
    result = stft(_chirp(), 1_000.0, segment_length=256, overlap=0.5)
    limit = 5
    model = WaterfallModel(result.bin_count, max_slices=limit)

    model.extend_from_stft(result)

    assert len(model) == limit
    assert np.allclose(model.times_s(), result.times_s[-limit:])
    assert np.allclose(model.newest().magnitudes, result.magnitudes[:, -1])


def test_extend_from_stft_rejects_a_bin_count_mismatch() -> None:
    result = stft(_chirp(), 1_000.0, segment_length=256)
    model = WaterfallModel(result.bin_count + 1, max_slices=10)
    with pytest.raises(WaterfallError, match="bin taşıyor"):
        model.extend_from_stft(result)

"""Kayan pencere ortalaması — pencere ve kenar davranışı — `F4-017`.

Kabul: bilinen kısa dizide pencere ve kenar davranışı **tanımlı**
sonucu verir. Beklenen değerler elle hesaplandı ve ``numpy.convolve``
merkezlemesiyle çapraz doğrulandı.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.processing.windowing import (
    EDGE_NAN,
    EDGE_SHRINK,
    MAX_WINDOW,
    MIN_WINDOW,
    WindowingError,
    moving_average,
    validate_window,
)

Vec = NDArray[np.float64]

X = np.array([1.0, 2.0, 3.0, 4.0, 5.0])


def _f(*values: float) -> Vec:
    return np.array(values, dtype=np.float64)


# --------------------------------------------------------------------------- #
# shrink (öntanımlı) — kısmi pencere uçlarda
# --------------------------------------------------------------------------- #


def test_window_1_is_identity() -> None:
    out = moving_average(X, 1)
    assert np.array_equal(out, X)
    assert out is not X  # yeni dizi


def test_odd_window_3_shrink() -> None:
    # i0:[1,2] i1:[1,2,3] i2:[2,3,4] i3:[3,4,5] i4:[4,5]
    assert np.allclose(moving_average(X, 3), _f(1.5, 2.0, 3.0, 4.0, 4.5))


def test_odd_window_5_shrink() -> None:
    # i0:[1,2,3] i1:[1..4] i2:[1..5] i3:[2..5] i4:[3,4,5]
    assert np.allclose(moving_average(X, 5), _f(2.0, 2.5, 3.0, 3.5, 4.0))


def test_even_window_2_leans_left() -> None:
    # çift pencere: [i-1, i]  -> i0:[1] i1:[1,2] i2:[2,3] i3:[3,4] i4:[4,5]
    assert np.allclose(moving_average(X, 2), _f(1.0, 1.5, 2.5, 3.5, 4.5))


def test_even_window_4_leans_left() -> None:
    # [i-2, i+1] -> i0:[1,2] i1:[1,2,3] i2:[1..4] i3:[2..5] i4:[3,4,5]
    assert np.allclose(moving_average(X, 4), _f(1.5, 2.0, 2.5, 3.5, 4.0))


def test_window_larger_than_signal_is_the_running_partial_mean() -> None:
    # window 10 > 3: her konumun penceresi tüm diziyi kapsar -> genel ortalama
    assert np.allclose(moving_average(_f(1.0, 2.0, 3.0), 10), _f(2.0, 2.0, 2.0))


def test_matches_convolve_reference_for_random_data() -> None:
    rng = np.random.default_rng(17)
    data = rng.normal(size=64)
    for window in (2, 3, 4, 7, 16):
        kernel = np.ones(window)
        totals = np.convolve(data, kernel, mode="same")
        counts = np.convolve(np.ones(data.size), kernel, mode="same")
        assert np.allclose(moving_average(data, window), totals / counts)


# --------------------------------------------------------------------------- #
# nan kenar modu — tam pencere sığmayan konumlar NaN
# --------------------------------------------------------------------------- #


def test_edge_nan_marks_incomplete_windows() -> None:
    out = moving_average(X, 3, edges=EDGE_NAN)
    assert np.isnan(out[0]) and np.isnan(out[4])
    assert np.allclose(out[1:4], _f(2.0, 3.0, 4.0))


def test_edge_nan_window_5_leaves_only_the_center() -> None:
    out = moving_average(X, 5, edges=EDGE_NAN)
    assert np.isnan(out[[0, 1, 3, 4]]).all()
    assert out[2] == 3.0


def test_edge_modes_are_named_constants() -> None:
    assert EDGE_SHRINK == "shrink"
    assert EDGE_NAN == "nan"


# --------------------------------------------------------------------------- #
# NaN yayılımı yereldir
# --------------------------------------------------------------------------- #


def test_nan_spreads_only_across_its_window() -> None:
    out = moving_average(_f(2.0, 2.0, np.nan, 2.0, 2.0), 3)
    assert np.isnan(out[1]) and np.isnan(out[2]) and np.isnan(out[3])
    assert out[0] == 2.0 and out[4] == 2.0


def test_nan_does_not_contaminate_downstream_positions() -> None:
    # Kümülatif toplam kullanılsaydı 3. konumdan sonrası da NaN olurdu.
    out = moving_average(_f(10.0, np.nan, 10.0, 10.0, 10.0, 10.0), 3)
    assert np.isnan(out[[0, 1, 2]]).all()
    assert np.allclose(out[3:], 10.0)


# --------------------------------------------------------------------------- #
# genel davranış
# --------------------------------------------------------------------------- #


def test_length_is_always_preserved() -> None:
    for window in (1, 2, 3, 8, 50):
        assert moving_average(np.arange(20, dtype=np.float64), window).shape == (20,)


def test_input_is_not_mutated() -> None:
    data = _f(5.0, 1.0, 4.0, 2.0, 3.0)
    snapshot = data.copy()
    moving_average(data, 3)
    moving_average(data, 4, edges=EDGE_NAN)
    assert np.array_equal(data, snapshot)


def test_empty_array_returns_empty() -> None:
    assert moving_average(np.empty(0, dtype=np.float64), 5).shape == (0,)


def test_repeated_calls_are_identical() -> None:
    data = np.linspace(-3.0, 7.0, 33)
    assert np.array_equal(moving_average(data, 6), moving_average(data, 6))


# --------------------------------------------------------------------------- #
# pencere doğrulama — "sıfır veya aşırı pencere reddedilir" (F4-018 zemini)
# --------------------------------------------------------------------------- #


def test_validate_window_accepts_the_boundaries() -> None:
    assert validate_window(MIN_WINDOW) == 1
    assert validate_window(MAX_WINDOW) == MAX_WINDOW


def test_validate_window_rejects_zero_and_negative() -> None:
    for bad in (0, -1, -1000):
        with pytest.raises(WindowingError, match=">="):
            validate_window(bad)


def test_validate_window_rejects_excessive_window() -> None:
    with pytest.raises(WindowingError, match="aşırı"):
        validate_window(MAX_WINDOW + 1)


def test_validate_window_rejects_bool() -> None:
    with pytest.raises(WindowingError, match="tam sayı"):
        validate_window(True)


def test_moving_average_rejects_bad_window() -> None:
    with pytest.raises(WindowingError):
        moving_average(X, 0)


def test_moving_average_rejects_unknown_edge_mode() -> None:
    with pytest.raises(WindowingError, match="kenar modu"):
        moving_average(X, 3, edges="reflect")


def test_moving_average_rejects_2d_input() -> None:
    with pytest.raises(WindowingError, match="tek boyutlu"):
        moving_average(np.ones((3, 3)), 2)


# --------------------------------------------------------------------------- #
# apply_step / zincir entegrasyonu
# --------------------------------------------------------------------------- #


def test_apply_step_uses_the_same_golden_result() -> None:
    step = ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 3})
    assert np.allclose(apply_step(X, step), _f(1.5, 2.0, 3.0, 4.0, 4.5))


def test_chain_moving_average_matches_direct_call() -> None:
    step = ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 4})
    result = ProcessingChain([step]).run(X)
    assert np.allclose(result.values, moving_average(X, 4))
    assert result.invalid_count == 0

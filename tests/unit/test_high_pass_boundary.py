"""High-pass sınır ve transient davranışı — `F4-031`.

Kabul: kısa dizi ve sınır parametreleri kontrollü sonuç verir.

Değişmez: yüksek geçiren çıktısı **her girdi için** tam sayısal
hassasiyette sıfır toplamlıdır (DC kazancı sıfır). FFT dairesel evrişim
varsaydığından periyodik olmayan sinyallerde geçici (transient) **uçlara
yerleşir**; iç bölge beklenen filtrelenmiş değere oturur.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.filters import (
    FILTER_MAX_ORDER,
    butterworth_highpass_response,
    high_pass,
)

Vec = NDArray[np.float64]


def _sum_abs(x: Vec) -> float:
    return float(np.abs(x).sum())


# --------------------------------------------------------------------------- #
# kısa diziler
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 8, 16])
def test_short_arrays_run_and_sum_to_zero(n: int) -> None:
    rng = np.random.default_rng(n)
    x = rng.normal(size=n)
    y = high_pass(x, 100.0, 20.0, 4)
    assert y.shape == (n,)
    assert abs(float(y.sum())) < 1e-9 * max(1.0, _sum_abs(x))


def test_single_sample_is_zeroed() -> None:
    # n=1: yalnız DC bini var, H(0)=0.
    assert np.array_equal(high_pass(np.array([4.2]), 100.0, 20.0, 4), np.array([0.0]))


def test_two_sample_signal_is_antisymmetric_and_zero_sum() -> None:
    y = high_pass(np.array([3.0, -1.0]), 100.0, 20.0, 4)
    assert abs(float(y.sum())) < 1e-12
    assert abs(y[0] + y[1]) < 1e-12


# --------------------------------------------------------------------------- #
# sıfır toplam değişmezi
# --------------------------------------------------------------------------- #


def test_constant_signal_is_exactly_zero() -> None:
    y = high_pass(np.full(64, 3.7), 200.0, 20.0, 4)
    assert np.allclose(y, 0.0, atol=1e-12)


@pytest.mark.parametrize(
    "make",
    [
        lambda: np.random.default_rng(0).normal(size=200),
        lambda: np.linspace(0.0, 10.0, 200),
        lambda: np.concatenate([np.zeros(100), np.ones(100)]),  # basamak
        lambda: np.arange(128, dtype=np.float64) ** 2,
    ],
)
def test_output_always_sums_to_zero(make: object) -> None:
    x = np.asarray(make(), dtype=np.float64)  # type: ignore[operator]
    y = high_pass(x, 256.0, 8.0, 4)
    assert abs(float(y.sum())) < 1e-7 * max(1.0, _sum_abs(x))


# --------------------------------------------------------------------------- #
# sınır cutoff'ları
# --------------------------------------------------------------------------- #


def test_cutoff_just_above_zero_only_removes_the_mean() -> None:
    rng = np.random.default_rng(3)
    x = rng.normal(size=256) + 12.0
    y = high_pass(x, 200.0, 1e-6, 4)  # H(f>0) ~= 1, H(0) = 0
    assert np.allclose(y, x - x.mean(), atol=1e-9)


def test_cutoff_just_below_nyquist_suppresses_mid_band() -> None:
    sr, n = 200.0, 400
    k = np.arange(n, dtype=np.float64)
    x = np.sin(2.0 * np.pi * 30.0 * k / sr)  # 30 Hz
    y = high_pass(x, sr, 99.9, 4)  # Nyquist 100
    assert np.max(np.abs(y)) < 0.01 * np.max(np.abs(x))


def test_order_1_and_max_order_both_run_and_max_rolls_off_steeper() -> None:
    fc, f_low = 100.0, 25.0
    g1 = butterworth_highpass_response(np.array([f_low]), fc, 1)[0]
    gmax = butterworth_highpass_response(np.array([f_low]), fc, FILTER_MAX_ORDER)[0]
    assert gmax < g1  # yüksek order alt bandı daha çok bastırır

    x = np.random.default_rng(7).normal(size=128)
    for order in (1, FILTER_MAX_ORDER):
        y = high_pass(x, 400.0, fc, order)
        assert abs(float(y.sum())) < 1e-8 * _sum_abs(x)


# --------------------------------------------------------------------------- #
# transient uçlara yerleşir
# --------------------------------------------------------------------------- #


def test_ramp_transient_lives_at_the_edges() -> None:
    x = np.linspace(0.0, 10.0, 256)
    y = high_pass(x, 256.0, 8.0, 4)
    # En büyük sapma ilk/son 16 örnekte (sarım süreksizliği).
    peak = int(np.argmax(np.abs(y)))
    assert peak < 16 or peak >= 256 - 16
    # İç bölge oturmuş: rampa trendi kalktı, ortalama ~0.
    assert abs(float(np.mean(y[64:192]))) < 0.5


def test_impulse_response_is_zero_mean_and_centered() -> None:
    imp = np.zeros(128, dtype=np.float64)
    imp[64] = 1.0
    h = high_pass(imp, 200.0, 20.0, 4)
    assert abs(float(h.sum())) < 1e-9
    assert int(np.argmax(np.abs(h))) == 64  # tepe darbede


def test_input_is_not_mutated_on_short_arrays() -> None:
    x = np.array([1.0, 2.0, 3.0])
    snap = x.copy()
    high_pass(x, 100.0, 20.0, 4)
    assert np.array_equal(x, snap)

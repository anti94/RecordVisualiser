"""Detrend / DC kaldırma hesabı — `F4-015`.

Kabul: sabit ofset ve doğrusal trend **referans sonucu** üretir.

Referanslar bağımsızdır:

* ``constant`` — elle hesaplanmış vektör ve ``x - x.mean()``.
* ``linear`` — ``numpy.linalg.lstsq`` ile ``[i, 1]`` tasarım matrisi
  üzerinden en küçük kareler (modülün normal-denklem uygulamasından
  ayrı bir yol).
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.steps import (
    DETREND_MODES,
    ProcessingStep,
    StepKind,
    StepValidationError,
)

Vec = NDArray[np.float64]


def _f(*values: float) -> Vec:
    return np.array(values, dtype=np.float64)


def _reference_linear_detrend(x: Vec) -> Vec:
    n = x.size
    index = np.arange(n, dtype=np.float64)
    design = np.vstack([index, np.ones(n)]).T
    coeffs, *_rest = np.linalg.lstsq(design, x, rcond=None)
    return x - design @ coeffs


def _detrend_step(mode: str) -> ProcessingStep:
    return ProcessingStep(StepKind.DETREND, "ch0", {"mode": mode})


# --------------------------------------------------------------------------- #
# constant (DC kaldırma)
# --------------------------------------------------------------------------- #


def test_constant_detrend_on_a_hand_computed_vector() -> None:
    x = _f(1.0, 2.0, 3.0, 4.0, 5.0)  # ortalama = 3
    out = apply_step(x, _detrend_step("constant"))
    assert np.array_equal(out, _f(-2.0, -1.0, 0.0, 1.0, 2.0))


def test_constant_detrend_removes_only_the_mean() -> None:
    rng = np.random.default_rng(20240609)
    signal = rng.normal(size=256)
    x = signal + 42.0  # sabit ofset eklendi
    out = apply_step(x, _detrend_step("constant"))
    assert abs(float(out.mean())) < 1e-12
    assert np.allclose(out, x - x.mean())
    # Şekil korunur: fark yalnız sabit.
    assert np.allclose(x - out, x.mean())


def test_constant_detrend_ignores_nan_in_the_baseline() -> None:
    x = _f(10.0, 20.0, np.nan, 40.0, 30.0)
    finite_mean = np.array([10.0, 20.0, 40.0, 30.0]).mean()  # 25
    out = apply_step(x, _detrend_step("constant"))
    assert np.isnan(out[2])
    assert np.allclose(out[[0, 1, 3, 4]], x[[0, 1, 3, 4]] - finite_mean)


# --------------------------------------------------------------------------- #
# linear (doğrusal trend çıkarma)
# --------------------------------------------------------------------------- #


def test_linear_detrend_flattens_a_pure_ramp() -> None:
    index = np.arange(100, dtype=np.float64)
    x = 3.0 * index + 7.0  # tam doğrusal
    out = apply_step(x, _detrend_step("linear"))
    assert np.allclose(out, 0.0, atol=1e-9)


def test_linear_detrend_matches_lstsq_reference() -> None:
    rng = np.random.default_rng(7)
    index = np.arange(500, dtype=np.float64)
    x = 0.4 * index - 12.0 + 5.0 * np.sin(index / 11.0) + rng.normal(scale=0.3, size=index.size)
    out = apply_step(x, _detrend_step("linear"))
    assert np.allclose(out, _reference_linear_detrend(x), atol=1e-9)


def test_linear_detrend_leaves_no_residual_slope_or_mean() -> None:
    rng = np.random.default_rng(101)
    index = np.arange(400, dtype=np.float64)
    x = -2.5 * index + 33.0 + rng.normal(scale=1.0, size=index.size)
    out = apply_step(x, _detrend_step("linear"))
    residual_slope = np.polyfit(index, out, 1)[0]
    assert abs(float(out.mean())) < 1e-9
    assert abs(float(residual_slope)) < 1e-9


def test_linear_detrend_ignores_nan_in_the_fit() -> None:
    index = np.arange(50, dtype=np.float64)
    x = 2.0 * index + 1.0
    x[10] = np.nan
    x[25] = np.nan
    out = apply_step(x, _detrend_step("linear"))
    finite = np.isfinite(out)
    assert np.isnan(out[10]) and np.isnan(out[25])
    # NaN'lar uydurmadan dışlandığı için kalan ideal doğru üzerinde: ~0.
    assert np.allclose(out[finite], 0.0, atol=1e-9)


def test_linear_detrend_falls_back_to_constant_with_one_finite_sample() -> None:
    x = _f(np.nan, np.nan, 5.0, np.nan)
    out = apply_step(x, _detrend_step("linear"))
    assert out[2] == 0.0  # tek sonlu örnek: kendi ortalamasını çıkarır
    assert np.isnan(out[[0, 1, 3]]).all()


# --------------------------------------------------------------------------- #
# genel davranış
# --------------------------------------------------------------------------- #


def test_detrend_does_not_mutate_input() -> None:
    x = _f(1.0, 5.0, 2.0, 9.0, 4.0)
    snapshot = x.copy()
    apply_step(x, _detrend_step("linear"))
    apply_step(x, _detrend_step("constant"))
    assert np.array_equal(x, snapshot)


def test_detrend_empty_array_returns_empty() -> None:
    out = apply_step(np.empty(0, dtype=np.float64), _detrend_step("linear"))
    assert out.shape == (0,)


def test_detrend_all_nan_passes_through() -> None:
    x = _f(np.nan, np.nan, np.nan)
    out = apply_step(x, _detrend_step("constant"))
    assert np.isnan(out).all()


# --------------------------------------------------------------------------- #
# zincir + kalite politikası
# --------------------------------------------------------------------------- #


def test_detrend_runs_inside_a_chain() -> None:
    index = np.arange(64, dtype=np.float64)
    x = 1.5 * index + 20.0 + np.cos(index)
    chain = ProcessingChain([_detrend_step("linear")])
    result = chain.run(x)
    assert np.allclose(result.values, _reference_linear_detrend(x), atol=1e-9)
    assert result.step_count == 1
    assert result.invalid_count == 0


def test_chain_quality_flags_are_excluded_from_the_trend_fit() -> None:
    index = np.arange(80, dtype=np.float64)
    x = 4.0 * index - 5.0  # tam doğrusal
    quality = np.zeros(index.size, dtype=np.uint32)
    quality[[3, 40, 77]] = int(Quality.CRC_ERROR)  # bu örnekler NaN'a çevrilecek
    result = ProcessingChain([_detrend_step("linear")]).run(x, quality)
    finite = np.isfinite(result.values)
    # Bozuk örnekler uydurmayı kaydırmadı: kalan örnekler ideal doğruda.
    assert np.allclose(result.values[finite], 0.0, atol=1e-9)
    assert result.invalid_mask[[3, 40, 77]].all()


# --------------------------------------------------------------------------- #
# adım modeli (parametre sözleşmesi)
# --------------------------------------------------------------------------- #


def test_detrend_step_defaults_to_constant() -> None:
    step = ProcessingStep.default(StepKind.DETREND, "ch0")
    assert step.parameters == {"mode": "constant"}


def test_detrend_step_accepts_both_modes() -> None:
    for mode in DETREND_MODES:
        assert ProcessingStep(StepKind.DETREND, "ch0", {"mode": mode}).parameters["mode"] == mode


def test_detrend_step_rejects_unknown_mode() -> None:
    with pytest.raises(StepValidationError, match="mode"):
        ProcessingStep(StepKind.DETREND, "ch0", {"mode": "quadratic"})


def test_detrend_step_rejects_wrong_type() -> None:
    with pytest.raises(StepValidationError):
        ProcessingStep(StepKind.DETREND, "ch0", {"mode": 3})


def test_detrend_step_signature_distinguishes_mode() -> None:
    a = ProcessingStep(StepKind.DETREND, "ch0", {"mode": "constant"})
    b = ProcessingStep(StepKind.DETREND, "ch0", {"mode": "linear"})
    again = ProcessingStep(StepKind.DETREND, "ch0", {"mode": "constant"})
    assert a.signature() != b.signature()
    assert a.signature() == again.signature()

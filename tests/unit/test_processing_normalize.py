"""Normalize hesabı — `F4-019`.

Kabul: referans genlik doğru ölçeklenir; sıfır sinyal bölme hatası
üretmez.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.steps import (
    NORMALIZE_MODES,
    ProcessingStep,
    StepKind,
    StepValidationError,
)

Vec = NDArray[np.float64]


def _f(*values: float) -> Vec:
    return np.array(values, dtype=np.float64)


def _step(mode: str = "peak", reference: float = 1.0) -> ProcessingStep:
    return ProcessingStep(StepKind.NORMALIZE, "ch0", {"mode": mode, "reference": reference})


def _peak(values: Vec) -> float:
    finite = values[np.isfinite(values)]
    return float(np.abs(finite).max())


def _rms(values: Vec) -> float:
    finite = values[np.isfinite(values)]
    return float(np.sqrt(np.mean(np.square(finite))))


# --------------------------------------------------------------------------- #
# peak
# --------------------------------------------------------------------------- #


def test_peak_normalize_hand_computed() -> None:
    out = apply_step(_f(1.0, -4.0, 2.0, 3.0), _step("peak", 1.0))
    assert np.allclose(out, _f(0.25, -1.0, 0.5, 0.75))


def test_peak_normalize_scales_to_the_reference_amplitude() -> None:
    x = _f(0.2, -1.5, 0.9, 1.1, -0.4)
    for reference in (0.5, 1.0, 3.0, 12.5):
        out = apply_step(x, _step("peak", reference))
        assert abs(_peak(out) - reference) < 1e-12
        # Şekil korunur: sabit çarpan.
        ratio = out / x
        assert np.allclose(ratio, ratio[0])


def test_peak_normalize_preserves_sign() -> None:
    x = _f(-2.0, 1.0, -0.5)
    out = apply_step(x, _step("peak", 1.0))
    assert np.array_equal(np.sign(out), np.sign(x))


# --------------------------------------------------------------------------- #
# rms
# --------------------------------------------------------------------------- #


def test_rms_normalize_hand_computed() -> None:
    # rms([3,-3,3,-3]) = 3 -> reference 1 => [1,-1,1,-1]
    out = apply_step(_f(3.0, -3.0, 3.0, -3.0), _step("rms", 1.0))
    assert np.allclose(out, _f(1.0, -1.0, 1.0, -1.0))


def test_rms_normalize_scales_to_the_reference_rms() -> None:
    x = _f(0.0, 4.0, 0.0, -4.0, 0.0, 4.0, 0.0, -4.0)  # rms = sqrt(8)
    for reference in (1.0, 2.0, 7.5):
        out = apply_step(x, _step("rms", reference))
        assert abs(_rms(out) - reference) < 1e-12


# --------------------------------------------------------------------------- #
# sıfır sinyal — bölme hatası yok
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", list(NORMALIZE_MODES))
def test_zero_signal_is_returned_unchanged_without_warning(mode: str) -> None:
    zeros = np.zeros(6, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # herhangi bir RuntimeWarning testi düşürür
        out = apply_step(zeros, _step(mode, 2.0))
    assert np.array_equal(out, zeros)
    assert np.isfinite(out).all()  # inf / nan yok


def test_all_nan_signal_passes_through() -> None:
    x = _f(np.nan, np.nan, np.nan)
    out = apply_step(x, _step("peak", 1.0))
    assert np.isnan(out).all()


def test_empty_signal_returns_empty() -> None:
    assert apply_step(np.empty(0, dtype=np.float64), _step()).shape == (0,)


# --------------------------------------------------------------------------- #
# NaN'a dayanıklılık
# --------------------------------------------------------------------------- #


def test_peak_normalize_ignores_nan_in_the_norm() -> None:
    x = _f(np.nan, 2.0, -4.0, 1.0)  # sonlu tepe = 4
    out = apply_step(x, _step("peak", 1.0))
    assert np.isnan(out[0])
    assert np.allclose(out[1:], _f(0.5, -1.0, 0.25))


def test_rms_normalize_ignores_nan_in_the_norm() -> None:
    x = _f(3.0, np.nan, -3.0, 3.0, -3.0)  # sonlu rms = 3
    out = apply_step(x, _step("rms", 1.0))
    assert np.isnan(out[1])
    assert np.allclose(out[[0, 2, 3, 4]], _f(1.0, -1.0, 1.0, -1.0))


# --------------------------------------------------------------------------- #
# genel
# --------------------------------------------------------------------------- #


def test_input_is_not_mutated() -> None:
    x = _f(1.0, -4.0, 2.0, 3.0)
    snapshot = x.copy()
    apply_step(x, _step("peak", 5.0))
    apply_step(x, _step("rms", 2.0))
    assert np.array_equal(x, snapshot)


def test_normalize_runs_inside_a_chain() -> None:
    x = _f(0.1, -0.8, 0.4, 0.8, -0.2)
    result = ProcessingChain([_step("peak", 1.0)]).run(x)
    assert abs(_peak(result.values) - 1.0) < 1e-12
    assert result.invalid_count == 0


def test_chain_zero_signal_normalize_is_clean() -> None:
    result = ProcessingChain([_step("rms", 3.0)]).run(np.zeros(4, dtype=np.float64))
    assert np.array_equal(result.values, np.zeros(4))
    assert not result.invalid_mask.any()


def test_chain_quality_flags_are_excluded_from_the_norm() -> None:
    x = _f(2.0, 2.0, 100.0, 2.0, -2.0)  # 100.0 CRC hatalı -> norm'a girmemeli
    quality = np.zeros(x.size, dtype=np.uint32)
    quality[2] = int(Quality.CRC_ERROR)
    result = ProcessingChain([_step("peak", 1.0)]).run(x, quality)
    finite = np.isfinite(result.values)
    # Sonlu tepe 2.0 üzerinden ölçeklendi; 100.0 dikkate alınmadı.
    assert abs(_peak(result.values) - 1.0) < 1e-12
    assert np.isnan(result.values[2])
    assert np.allclose(result.values[finite], _f(1.0, 1.0, 1.0, -1.0))


# --------------------------------------------------------------------------- #
# adım modeli
# --------------------------------------------------------------------------- #


def test_normalize_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.NORMALIZE, "ch0")
    assert step.parameters == {"mode": "peak", "reference": 1.0}


def test_normalize_step_rejects_nonpositive_reference() -> None:
    for bad in (0.0, -1.0, -3.5):
        with pytest.raises(StepValidationError, match="reference"):
            ProcessingStep(StepKind.NORMALIZE, "ch0", {"mode": "peak", "reference": bad})


def test_normalize_step_rejects_unknown_mode() -> None:
    with pytest.raises(StepValidationError, match="mode"):
        ProcessingStep(StepKind.NORMALIZE, "ch0", {"mode": "loudness", "reference": 1.0})


def test_normalize_step_coerces_int_reference_to_float() -> None:
    step = ProcessingStep(StepKind.NORMALIZE, "ch0", {"mode": "rms", "reference": 4})
    assert step.parameters["reference"] == 4.0
    assert isinstance(step.parameters["reference"], float)


def test_normalize_step_signature_distinguishes_parameters() -> None:
    a = _step("peak", 1.0)
    assert a.signature() != _step("rms", 1.0).signature()
    assert a.signature() != _step("peak", 2.0).signature()
    assert a.signature() == _step("peak", 1.0).signature()

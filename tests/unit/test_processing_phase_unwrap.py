"""Faz unwrap hesabı — `F4-023`.

Kabul: bilinen faz sıçramaları sürekliliğe dönüşür.

Referans `numpy.unwrap`; ayrıca sarılmış bir rampanın geri kazanımı ve
komşu farkların tam periyodun altında kalması bağımsız olarak denetlenir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.steps import (
    PHASE_UNWRAP_PERIOD,
    PHASE_UNWRAP_UNITS,
    ProcessingStep,
    StepKind,
    StepValidationError,
)

Vec = NDArray[np.float64]
TWO_PI = 2.0 * math.pi


def _f(*values: float) -> Vec:
    return np.array(values, dtype=np.float64)


def _step(unit: str = "radians", discontinuity: float = math.pi) -> ProcessingStep:
    return ProcessingStep(
        StepKind.PHASE_UNWRAP, "ch0", {"unit": unit, "discontinuity": discontinuity}
    )


# --------------------------------------------------------------------------- #
# radyan
# --------------------------------------------------------------------------- #


def test_known_jump_becomes_continuous() -> None:
    wrapped = _f(0.0, 1.0, 2.0, 3.0, -3.0, -2.0, -1.0)
    out = apply_step(wrapped, _step())
    assert np.allclose(out, np.unwrap(wrapped))
    # Sıçrama noktasında tam bir periyot eklendi.
    assert abs(out[4] - (-3.0 + TWO_PI)) < 1e-12
    # Artık hiçbir komşu farkı yarım periyodu aşmıyor.
    assert np.all(np.abs(np.diff(out)) < math.pi)


def test_wrapped_ramp_is_recovered() -> None:
    true_phase = np.linspace(0.0, 10.0 * math.pi, 200)
    wrapped = np.mod(true_phase + math.pi, TWO_PI) - math.pi
    out = apply_step(wrapped, _step())
    assert np.allclose(out, true_phase, atol=1e-9)


def test_already_continuous_signal_is_unchanged() -> None:
    smooth = np.linspace(0.0, 2.0, 50)
    assert np.allclose(apply_step(smooth, _step()), smooth)


def test_discontinuity_threshold_controls_whether_a_jump_is_unwrapped() -> None:
    jump = _f(0.0, 0.0, 4.0, 4.0)  # +4 rad sıçrama
    # Eşik pi (~3.14): |4| >= eşik -> düzeltilir (bir periyot çıkar).
    fixed = apply_step(jump, _step(discontinuity=math.pi))
    assert np.allclose(fixed, _f(0.0, 0.0, 4.0 - TWO_PI, 4.0 - TWO_PI))
    # Eşik 5.0: |4| < eşik -> dokunulmaz.
    left = apply_step(jump, _step(discontinuity=5.0))
    assert np.allclose(left, jump)


# --------------------------------------------------------------------------- #
# derece
# --------------------------------------------------------------------------- #


def test_degrees_unit_uses_a_360_period() -> None:
    true_deg = np.linspace(0.0, 1800.0, 200)
    wrapped = np.mod(true_deg + 180.0, 360.0) - 180.0
    out = apply_step(wrapped, _step("degrees", 180.0))
    assert np.allclose(out, true_deg, atol=1e-7)
    assert np.all(np.abs(np.diff(out)) < 180.0)


def test_degrees_known_jump() -> None:
    wrapped = _f(170.0, 175.0, -179.0, -170.0)  # 175 -> -179 : -354 sıçrama
    out = apply_step(wrapped, _step("degrees", 180.0))
    assert np.allclose(out, np.unwrap(wrapped, period=360.0))
    assert abs(out[2] - (-179.0 + 360.0)) < 1e-9


# --------------------------------------------------------------------------- #
# NaN / kenar durumlar
# --------------------------------------------------------------------------- #


def test_nan_makes_everything_after_it_undefined() -> None:
    out = apply_step(_f(0.0, 1.0, np.nan, 2.0, 3.0), _step())
    assert out[0] == 0.0 and out[1] == 1.0
    assert np.isnan(out[2:]).all()


def test_single_sample_and_empty() -> None:
    assert np.array_equal(apply_step(_f(5.0), _step()), _f(5.0))
    assert apply_step(np.empty(0, dtype=np.float64), _step()).shape == (0,)


def test_input_is_not_mutated() -> None:
    wrapped = _f(0.0, 3.0, -3.0, 2.0, -2.0)
    snapshot = wrapped.copy()
    apply_step(wrapped, _step())
    apply_step(wrapped, _step("degrees", 90.0))
    assert np.array_equal(wrapped, snapshot)


def test_length_is_preserved() -> None:
    rng = np.random.default_rng(5)
    wrapped = np.mod(rng.normal(scale=20.0, size=137) + math.pi, TWO_PI) - math.pi
    assert apply_step(wrapped, _step()).shape == (137,)


# --------------------------------------------------------------------------- #
# zincir
# --------------------------------------------------------------------------- #


def test_runs_inside_a_chain() -> None:
    true_phase = np.linspace(0.0, 6.0 * math.pi, 120)
    wrapped = np.mod(true_phase + math.pi, TWO_PI) - math.pi
    result = ProcessingChain([_step()]).run(wrapped)
    assert np.allclose(result.values, true_phase, atol=1e-9)
    assert result.invalid_count == 0


# --------------------------------------------------------------------------- #
# adım modeli
# --------------------------------------------------------------------------- #


def test_period_table() -> None:
    assert abs(PHASE_UNWRAP_PERIOD["radians"] - TWO_PI) < 1e-12
    assert PHASE_UNWRAP_PERIOD["degrees"] == 360.0
    assert set(PHASE_UNWRAP_PERIOD) == set(PHASE_UNWRAP_UNITS)


def test_step_defaults_to_radians_and_pi() -> None:
    step = ProcessingStep.default(StepKind.PHASE_UNWRAP, "ch0")
    assert step.parameters["unit"] == "radians"
    assert abs(float(step.parameters["discontinuity"]) - math.pi) < 1e-12  # type: ignore[arg-type]


def test_step_rejects_nonpositive_discontinuity() -> None:
    for bad in (0.0, -1.0):
        with pytest.raises(StepValidationError, match="discontinuity"):
            _step(discontinuity=bad)


def test_step_rejects_discontinuity_at_or_above_a_full_period() -> None:
    with pytest.raises(StepValidationError, match="periyot"):
        _step("radians", 7.0)  # > 2*pi
    with pytest.raises(StepValidationError, match="periyot"):
        _step("degrees", 360.0)


def test_step_rejects_unknown_unit() -> None:
    with pytest.raises(StepValidationError, match="unit"):
        ProcessingStep(StepKind.PHASE_UNWRAP, "ch0", {"unit": "turns", "discontinuity": 0.5})


def test_step_coerces_int_discontinuity_to_float() -> None:
    step = ProcessingStep(StepKind.PHASE_UNWRAP, "ch0", {"unit": "degrees", "discontinuity": 90})
    assert step.parameters["discontinuity"] == 90.0
    assert isinstance(step.parameters["discontinuity"], float)


def test_step_signature_distinguishes_unit_and_threshold() -> None:
    base = _step("radians", math.pi)
    assert base.signature() != _step("degrees", math.pi).signature()
    assert base.signature() != _step("radians", 2.0).signature()
    assert base.signature() == _step("radians", math.pi).signature()

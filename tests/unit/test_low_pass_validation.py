"""Low-pass cutoff ve order sınır doğrulaması — `F4-028`.

Kabul: Nyquist dışındaki cutoff ve geçersiz order reddedilir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sonar_analyzer.processing.filters import (
    FILTER_MAX_ORDER,
    FILTER_MIN_ORDER,
    FilterError,
    low_pass,
    nyquist_hz,
    validate_cutoff,
    validate_order,
    validate_sample_rate,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

# --------------------------------------------------------------------------- #
# nyquist_hz / validate_sample_rate
# --------------------------------------------------------------------------- #


def test_nyquist_is_half_the_sample_rate() -> None:
    assert nyquist_hz(48_000.0) == 24_000.0
    assert nyquist_hz(1_000.0) == 500.0


@pytest.mark.parametrize("bad", [0.0, -1.0, -48_000.0, math.nan, math.inf])
def test_validate_sample_rate_rejects_nonpositive_or_nonfinite(bad: float) -> None:
    with pytest.raises(FilterError, match="sample rate"):
        validate_sample_rate(bad)


def test_validate_sample_rate_accepts_positive() -> None:
    validate_sample_rate(1.0)
    validate_sample_rate(48_000.0)


# --------------------------------------------------------------------------- #
# validate_cutoff
# --------------------------------------------------------------------------- #


def test_cutoff_at_exactly_nyquist_is_rejected() -> None:
    with pytest.raises(FilterError, match="Nyquist"):
        validate_cutoff(500.0, 1_000.0)


def test_cutoff_above_nyquist_is_rejected() -> None:
    with pytest.raises(FilterError, match="Nyquist"):
        validate_cutoff(600.0, 1_000.0)


@pytest.mark.parametrize("bad", [0.0, -10.0, math.nan, math.inf])
def test_cutoff_nonpositive_or_nonfinite_is_rejected(bad: float) -> None:
    with pytest.raises(FilterError):
        validate_cutoff(bad, 1_000.0)


def test_cutoff_just_below_nyquist_is_accepted() -> None:
    validate_cutoff(499.999, 1_000.0)
    validate_cutoff(1.0, 1_000.0)


def test_validate_cutoff_also_checks_the_sample_rate() -> None:
    with pytest.raises(FilterError, match="sample rate"):
        validate_cutoff(100.0, 0.0)


# --------------------------------------------------------------------------- #
# validate_order
# --------------------------------------------------------------------------- #


def test_order_boundaries_are_accepted() -> None:
    validate_order(FILTER_MIN_ORDER)
    validate_order(FILTER_MAX_ORDER)


@pytest.mark.parametrize("bad", [0, -1, FILTER_MAX_ORDER + 1, 100])
def test_order_out_of_range_is_rejected(bad: int) -> None:
    with pytest.raises(FilterError, match="order"):
        validate_order(bad)


def test_order_must_be_an_integer() -> None:
    with pytest.raises(FilterError, match="tam sayı"):
        validate_order(4.0)
    with pytest.raises(FilterError, match="tam sayı"):
        validate_order(True)
    with pytest.raises(FilterError, match="tam sayı"):
        validate_order("4")


# --------------------------------------------------------------------------- #
# low_pass() ham girdi doğrulaması
# --------------------------------------------------------------------------- #


def test_low_pass_raises_filter_error_not_something_else() -> None:
    x = np.zeros(64, dtype=np.float64)
    with pytest.raises(FilterError, match="Nyquist"):
        low_pass(x, 200.0, 100.0, 4)
    with pytest.raises(FilterError, match="order"):
        low_pass(x, 200.0, 40.0, FILTER_MAX_ORDER + 1)
    with pytest.raises(FilterError, match="tek boyutlu"):
        low_pass(np.zeros((4, 4)), 200.0, 40.0, 4)


# --------------------------------------------------------------------------- #
# ProcessingStep(LOW_PASS) — işlem başlamadan reddedilir
# --------------------------------------------------------------------------- #


def _low_pass(sample_rate_hz: float, cutoff_hz: float, order: int) -> ProcessingStep:
    return ProcessingStep(
        StepKind.LOW_PASS,
        "ch0",
        {"sample_rate_hz": sample_rate_hz, "cutoff_hz": cutoff_hz, "order": order},
    )


def test_step_rejects_cutoff_outside_the_open_band() -> None:
    with pytest.raises(StepValidationError, match="Nyquist"):
        _low_pass(1_000.0, 500.0, 4)  # == Nyquist
    with pytest.raises(StepValidationError, match="Nyquist"):
        _low_pass(1_000.0, 900.0, 4)  # > Nyquist
    with pytest.raises(StepValidationError):
        _low_pass(1_000.0, 0.0, 4)


def test_step_rejects_invalid_order() -> None:
    with pytest.raises(StepValidationError, match="order"):
        _low_pass(1_000.0, 100.0, 0)
    with pytest.raises(StepValidationError, match="order"):
        _low_pass(1_000.0, 100.0, FILTER_MAX_ORDER + 5)


def test_step_rejects_nonpositive_sample_rate() -> None:
    with pytest.raises(StepValidationError, match="sample rate"):
        _low_pass(0.0, 100.0, 4)


def test_step_accepts_valid_parameters_at_the_boundary() -> None:
    step = _low_pass(1_000.0, 499.9, FILTER_MAX_ORDER)
    assert step.parameters["cutoff_hz"] == 499.9
    assert step.parameters["order"] == FILTER_MAX_ORDER


def test_step_bool_order_is_rejected_by_the_type_check() -> None:
    with pytest.raises(StepValidationError):
        ProcessingStep(
            StepKind.LOW_PASS,
            "ch0",
            {"sample_rate_hz": 1_000.0, "cutoff_hz": 100.0, "order": True},
        )

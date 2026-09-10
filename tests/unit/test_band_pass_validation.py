"""Band-pass alt/üst sınır doğrulaması — `F4-034`.

Kabul: ters veya Nyquist dışı bant **işlem başlamadan** reddedilir.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sonar_analyzer.processing.filters import (
    FILTER_MAX_ORDER,
    FilterError,
    band_pass,
    validate_band,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

SR = 1_000.0  # Nyquist = 500


# --------------------------------------------------------------------------- #
# validate_band — ters bant
# --------------------------------------------------------------------------- #


def test_reversed_band_is_rejected() -> None:
    with pytest.raises(FilterError, match="ters bant"):
        validate_band(300.0, 100.0, SR)


def test_equal_bounds_are_rejected() -> None:
    with pytest.raises(FilterError, match="ters bant"):
        validate_band(200.0, 200.0, SR)


def test_the_message_names_both_bounds() -> None:
    with pytest.raises(FilterError) as excinfo:
        validate_band(300.0, 100.0, SR)
    message = str(excinfo.value)
    assert "300" in message
    assert "100" in message


# --------------------------------------------------------------------------- #
# validate_band — Nyquist dışı
# --------------------------------------------------------------------------- #


def test_upper_bound_at_or_above_nyquist_is_rejected() -> None:
    with pytest.raises(FilterError, match="Nyquist"):
        validate_band(100.0, 500.0, SR)  # == Nyquist
    with pytest.raises(FilterError, match="Nyquist"):
        validate_band(100.0, 900.0, SR)  # > Nyquist


def test_lower_bound_at_or_above_nyquist_is_rejected() -> None:
    with pytest.raises(FilterError, match="Nyquist"):
        validate_band(500.0, 600.0, SR)


@pytest.mark.parametrize("bad", [0.0, -10.0, math.nan, math.inf])
def test_nonpositive_or_nonfinite_lower_bound_is_rejected(bad: float) -> None:
    with pytest.raises(FilterError):
        validate_band(bad, 300.0, SR)


@pytest.mark.parametrize("bad", [0.0, -10.0, math.nan, math.inf])
def test_nonpositive_or_nonfinite_upper_bound_is_rejected(bad: float) -> None:
    with pytest.raises(FilterError):
        validate_band(100.0, bad, SR)


def test_nonpositive_sample_rate_is_rejected() -> None:
    with pytest.raises(FilterError, match="sample rate"):
        validate_band(100.0, 300.0, 0.0)


# --------------------------------------------------------------------------- #
# geçerli bantlar
# --------------------------------------------------------------------------- #


def test_a_normal_band_is_accepted() -> None:
    validate_band(100.0, 300.0, SR)


def test_bounds_hugging_the_open_interval_are_accepted() -> None:
    validate_band(0.001, 499.999, SR)


# --------------------------------------------------------------------------- #
# band_pass() ham girdi doğrulaması
# --------------------------------------------------------------------------- #


def test_band_pass_rejects_reversed_and_out_of_range_bands() -> None:
    x = np.zeros(128, dtype=np.float64)
    with pytest.raises(FilterError, match="ters bant"):
        band_pass(x, SR, 300.0, 100.0, 4)
    with pytest.raises(FilterError, match="Nyquist"):
        band_pass(x, SR, 100.0, 500.0, 4)
    with pytest.raises(FilterError, match="order"):
        band_pass(x, SR, 100.0, 300.0, FILTER_MAX_ORDER + 1)
    with pytest.raises(FilterError, match="tek boyutlu"):
        band_pass(np.zeros((4, 4)), SR, 100.0, 300.0, 4)


# --------------------------------------------------------------------------- #
# ProcessingStep(BAND_PASS) — işlem başlamadan reddedilir
# --------------------------------------------------------------------------- #


def _band_step(low: float, high: float, order: int = 4, sample_rate_hz: float = SR):
    return ProcessingStep(
        StepKind.BAND_PASS,
        "ch0",
        {
            "sample_rate_hz": sample_rate_hz,
            "low_cutoff_hz": low,
            "high_cutoff_hz": high,
            "order": order,
        },
    )


def test_step_rejects_a_reversed_band() -> None:
    with pytest.raises(StepValidationError, match="ters bant"):
        _band_step(300.0, 100.0)


def test_step_rejects_a_band_outside_nyquist() -> None:
    with pytest.raises(StepValidationError, match="Nyquist"):
        _band_step(100.0, 500.0)
    with pytest.raises(StepValidationError, match="Nyquist"):
        _band_step(600.0, 800.0)


def test_step_rejects_a_nonpositive_lower_bound() -> None:
    with pytest.raises(StepValidationError):
        _band_step(0.0, 300.0)


def test_step_rejects_an_invalid_order() -> None:
    with pytest.raises(StepValidationError, match="order"):
        _band_step(100.0, 300.0, order=0)
    with pytest.raises(StepValidationError, match="order"):
        _band_step(100.0, 300.0, order=FILTER_MAX_ORDER + 3)


def test_step_rejects_a_nonpositive_sample_rate() -> None:
    with pytest.raises(StepValidationError, match="sample rate"):
        _band_step(100.0, 300.0, sample_rate_hz=0.0)


def test_step_accepts_a_valid_band_at_the_boundary() -> None:
    step = _band_step(0.5, 499.5, order=FILTER_MAX_ORDER)
    assert step.parameters["low_cutoff_hz"] == 0.5
    assert step.parameters["high_cutoff_hz"] == 499.5
    assert step.parameters["order"] == FILTER_MAX_ORDER


def test_step_error_names_the_step_kind() -> None:
    with pytest.raises(StepValidationError, match="band_pass"):
        _band_step(300.0, 100.0)

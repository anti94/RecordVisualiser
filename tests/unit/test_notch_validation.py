"""Notch merkez frekansı ve Q sınır doğrulaması — `F4-037`.

Kabul: geçersiz frekans ve Q **açıklamalı** hata üretir — mesaj hem
kısıtı hem verilen değeri adlar.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sonar_analyzer.processing.filters import (
    FILTER_MAX_ORDER,
    FilterError,
    notch,
    validate_notch,
    validate_quality_factor,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

SR = 1_000.0  # Nyquist = 500


# --------------------------------------------------------------------------- #
# validate_quality_factor
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", [0.0, -1.0, -30.0, math.nan, math.inf])
def test_nonpositive_or_nonfinite_q_is_rejected(bad: float) -> None:
    with pytest.raises(FilterError, match="Q pozitif ve sonlu"):
        validate_quality_factor(bad)


def test_q_error_names_the_offending_value() -> None:
    with pytest.raises(FilterError) as excinfo:
        validate_quality_factor(-7.5)
    assert "-7.5" in str(excinfo.value)


@pytest.mark.parametrize("good", [0.001, 0.5, 1.0, 30.0, 1_000.0])
def test_positive_finite_q_is_accepted(good: float) -> None:
    validate_quality_factor(good)


# --------------------------------------------------------------------------- #
# validate_notch — merkez frekansı
# --------------------------------------------------------------------------- #


def test_center_at_or_above_nyquist_is_rejected() -> None:
    with pytest.raises(FilterError, match="Nyquist"):
        validate_notch(500.0, 30.0, SR)  # == Nyquist
    with pytest.raises(FilterError, match="Nyquist"):
        validate_notch(750.0, 30.0, SR)  # > Nyquist


@pytest.mark.parametrize("bad", [0.0, -50.0, math.nan, math.inf])
def test_nonpositive_or_nonfinite_center_is_rejected(bad: float) -> None:
    with pytest.raises(FilterError):
        validate_notch(bad, 30.0, SR)


def test_center_error_names_the_nyquist_limit_and_the_value() -> None:
    with pytest.raises(FilterError) as excinfo:
        validate_notch(750.0, 30.0, SR)
    message = str(excinfo.value)
    assert "500" in message  # Nyquist
    assert "750" in message  # verilen


def test_a_valid_centre_and_q_are_accepted() -> None:
    validate_notch(50.0, 30.0, SR)
    validate_notch(499.9, 0.01, SR)


def test_nonpositive_sample_rate_is_rejected() -> None:
    with pytest.raises(FilterError, match="sample rate"):
        validate_notch(50.0, 30.0, 0.0)


def test_bad_q_is_reported_even_with_a_valid_centre() -> None:
    with pytest.raises(FilterError, match="Q"):
        validate_notch(50.0, 0.0, SR)


# --------------------------------------------------------------------------- #
# notch() ham girdi doğrulaması
# --------------------------------------------------------------------------- #


def test_notch_rejects_every_invalid_argument() -> None:
    x = np.zeros(128, dtype=np.float64)
    with pytest.raises(FilterError, match="Nyquist"):
        notch(x, SR, 500.0, 30.0, 4)
    with pytest.raises(FilterError, match="Q"):
        notch(x, SR, 50.0, -2.0, 4)
    with pytest.raises(FilterError, match="order"):
        notch(x, SR, 50.0, 30.0, FILTER_MAX_ORDER + 1)
    with pytest.raises(FilterError, match="tek boyutlu"):
        notch(np.zeros((4, 4)), SR, 50.0, 30.0, 4)


# --------------------------------------------------------------------------- #
# ProcessingStep(NOTCH) — işlem başlamadan reddedilir
# --------------------------------------------------------------------------- #


def _notch_step(
    center: float,
    q: float,
    order: int = 4,
    sample_rate_hz: float = SR,
):
    return ProcessingStep(
        StepKind.NOTCH,
        "ch0",
        {"sample_rate_hz": sample_rate_hz, "center_hz": center, "q": q, "order": order},
    )


def test_step_rejects_a_centre_outside_nyquist() -> None:
    with pytest.raises(StepValidationError, match="Nyquist"):
        _notch_step(500.0, 30.0)
    with pytest.raises(StepValidationError, match="Nyquist"):
        _notch_step(900.0, 30.0)


def test_step_rejects_a_nonpositive_centre() -> None:
    with pytest.raises(StepValidationError):
        _notch_step(0.0, 30.0)


@pytest.mark.parametrize("bad_q", [0.0, -1.0])
def test_step_rejects_a_nonpositive_q(bad_q: float) -> None:
    with pytest.raises(StepValidationError, match="Q"):
        _notch_step(50.0, bad_q)


def test_step_rejects_an_invalid_order() -> None:
    with pytest.raises(StepValidationError, match="order"):
        _notch_step(50.0, 30.0, order=0)
    with pytest.raises(StepValidationError, match="order"):
        _notch_step(50.0, 30.0, order=FILTER_MAX_ORDER + 2)


def test_step_rejects_a_nonpositive_sample_rate() -> None:
    with pytest.raises(StepValidationError, match="sample rate"):
        _notch_step(50.0, 30.0, sample_rate_hz=0.0)


def test_step_error_names_the_step_kind() -> None:
    with pytest.raises(StepValidationError, match="notch"):
        _notch_step(50.0, -1.0)


def test_step_accepts_boundary_values() -> None:
    step = _notch_step(499.5, 0.01, order=FILTER_MAX_ORDER)
    assert step.parameters["center_hz"] == 499.5
    assert step.parameters["q"] == 0.01
    assert step.parameters["order"] == FILTER_MAX_ORDER

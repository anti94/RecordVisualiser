"""İşlem adımı ve parametre modeli — `F4-001`.

Kabul: her adım girdi kanalı ve tekrar üretilebilir parametre taşır.
"""

from __future__ import annotations

import json

import pytest

from sonar_analyzer.processing.steps import (
    MAX_MOVING_AVERAGE_WINDOW,
    PARAMETER_SPECS,
    ProcessingStep,
    StepKind,
    StepValidationError,
)


def test_default_fills_every_parameter_for_the_kind() -> None:
    step = ProcessingStep.default(StepKind.CLIP, "ch0")
    assert step.input_channel_id == "ch0"
    assert set(step.parameters) == {spec.name for spec in PARAMETER_SPECS[StepKind.CLIP]}
    assert step.enabled is True


def test_step_requires_a_non_empty_input_channel() -> None:
    with pytest.raises(StepValidationError, match="girdi kanalı"):
        ProcessingStep(kind=StepKind.ABS, input_channel_id="  ", parameters={})


def test_missing_parameter_is_rejected() -> None:
    with pytest.raises(StepValidationError, match="eksik"):
        ProcessingStep(kind=StepKind.SCALE, input_channel_id="ch0", parameters={})


def test_unknown_parameter_is_rejected() -> None:
    with pytest.raises(StepValidationError, match="tanımsız parametre"):
        ProcessingStep(
            kind=StepKind.SCALE,
            input_channel_id="ch0",
            parameters={"factor": 2.0, "bogus": 1},
        )


def test_wrong_parameter_type_is_rejected() -> None:
    with pytest.raises(StepValidationError, match="olmalı"):
        ProcessingStep(
            kind=StepKind.MOVING_AVERAGE,
            input_channel_id="ch0",
            parameters={"window": "three"},
        )


def test_bool_is_not_accepted_where_int_is_expected() -> None:
    with pytest.raises(StepValidationError):
        ProcessingStep(
            kind=StepKind.MOVING_AVERAGE,
            input_channel_id="ch0",
            parameters={"window": True},
        )


def test_int_is_coerced_to_float_for_float_parameters() -> None:
    step = ProcessingStep(kind=StepKind.SCALE, input_channel_id="ch0", parameters={"factor": 3})
    assert step.parameters["factor"] == 3.0
    assert isinstance(step.parameters["factor"], float)


def test_clip_rejects_lo_above_hi() -> None:
    with pytest.raises(StepValidationError, match="lo, hi"):
        ProcessingStep(
            kind=StepKind.CLIP,
            input_channel_id="ch0",
            parameters={"lo": 5.0, "hi": 1.0},
        )


def test_moving_average_window_must_be_positive() -> None:
    with pytest.raises(StepValidationError, match="window"):
        ProcessingStep(
            kind=StepKind.MOVING_AVERAGE,
            input_channel_id="ch0",
            parameters={"window": 0},
        )


def test_moving_average_window_boundary_is_accepted() -> None:
    step = ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": MAX_MOVING_AVERAGE_WINDOW})
    assert step.parameters["window"] == MAX_MOVING_AVERAGE_WINDOW


def test_moving_average_rejects_excessive_window() -> None:
    with pytest.raises(StepValidationError, match="aşırı"):
        ProcessingStep(
            kind=StepKind.MOVING_AVERAGE,
            input_channel_id="ch0",
            parameters={"window": MAX_MOVING_AVERAGE_WINDOW + 1},
        )


# -- tekrar üretilebilirlik ---------------------------------


def test_signature_is_stable_for_equal_inputs() -> None:
    a = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    b = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2})  # int -> float
    assert a.signature() == b.signature()
    # JSON çözümlenebilir ve ilkellerden oluşur
    assert isinstance(json.loads(a.signature()), list)


def test_signature_changes_with_parameter_channel_or_kind() -> None:
    base = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    assert base.signature() != base.with_parameters(factor=3.0).signature()
    assert base.signature() != base.with_input("ch1").signature()
    assert base.signature() != ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 2.0}).signature()


def test_signature_ignores_parameter_insertion_order() -> None:
    a = ProcessingStep(StepKind.CLIP, "ch0", {"lo": 0.0, "hi": 1.0})
    b = ProcessingStep(StepKind.CLIP, "ch0", {"hi": 1.0, "lo": 0.0})
    assert a.signature() == b.signature()


# -- serileştirme ------------------------------------------


def test_dict_round_trip() -> None:
    step = ProcessingStep(StepKind.MOVING_AVERAGE, "ch2", {"window": 5}, enabled=False)
    assert ProcessingStep.from_dict(step.to_dict()) == step


def test_from_dict_rejects_unknown_kind() -> None:
    with pytest.raises(StepValidationError, match="Tanınmayan"):
        ProcessingStep.from_dict({"kind": "wavelet", "input_channel_id": "ch0"})


def test_from_dict_rejects_non_object() -> None:
    with pytest.raises(StepValidationError, match="nesne"):
        ProcessingStep.from_dict([1, 2, 3])


def test_with_parameters_and_with_input_are_pure() -> None:
    original = ProcessingStep.default(StepKind.SCALE, "ch0")
    changed = original.with_parameters(factor=9.0).with_input("ch9")
    assert original.parameters["factor"] == 1.0  # değişmedi
    assert original.input_channel_id == "ch0"
    assert changed.parameters["factor"] == 9.0
    assert changed.input_channel_id == "ch9"

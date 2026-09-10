"""Sıralı işlem zinciri yürütücüsü — `F4-002`.

Kabul: iki adım tanımlı sırayla uygulanır; ham dizi değişmez.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import (
    ChainExecutionError,
    ProcessingChain,
    apply_step,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind


def _arr(*xs: float) -> NDArray[np.float64]:
    return np.array(xs, dtype=np.float64)


# -- iki adım, tanımlı sıra ----------------------------------


def test_two_steps_apply_in_the_declared_order() -> None:
    # scale(2) sonra offset(10):  x -> 2x -> 2x + 10
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0}),
            ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 10.0}),
        ]
    )
    out = chain.run(_arr(1.0, 2.0, 3.0)).values
    assert np.array_equal(out, _arr(12.0, 14.0, 16.0))


def test_order_matters() -> None:
    scale = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    offset = ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 10.0})
    x = _arr(1.0, 2.0)
    first = ProcessingChain([scale, offset]).run(x).values  # 2x + 10
    second = ProcessingChain([offset, scale]).run(x).values  # 2(x + 10)
    assert np.array_equal(first, _arr(12.0, 14.0))
    assert np.array_equal(second, _arr(22.0, 24.0))
    assert not np.array_equal(first, second)


# -- ham dizi değişmez -------------------------------------


def test_input_array_is_never_mutated() -> None:
    raw = _arr(1.0, -2.0, 3.0)
    snapshot = raw.copy()
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.ABS, "ch0", {}),
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": 100.0}),
            ProcessingStep(StepKind.CLIP, "ch0", {"lo": 0.0, "hi": 250.0}),
        ]
    )
    result = chain.run(raw)
    assert np.array_equal(raw, snapshot)  # girdi dokunulmadı
    assert result.values is not raw
    assert np.array_equal(result.values, _arr(100.0, 200.0, 250.0))


def test_apply_step_returns_a_fresh_array() -> None:
    raw = _arr(1.0, 2.0)
    out = apply_step(raw, ProcessingStep(StepKind.SCALE, "ch0", {"factor": 1.0}))
    assert out is not raw
    out[0] = 999.0
    assert raw[0] == 1.0


# -- devre dışı adımlar / boş zincir -----------------------


def test_disabled_steps_are_skipped() -> None:
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": 3.0}, enabled=False),
            ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 1.0}),
        ]
    )
    result = chain.run(_arr(0.0, 1.0))
    assert np.array_equal(result.values, _arr(1.0, 2.0))
    assert result.step_count == 1  # yalnız etkin adım sayılır


def test_empty_chain_returns_a_copy_of_the_input() -> None:
    raw = _arr(5.0, 6.0)
    result = ProcessingChain().run(raw)
    assert np.array_equal(result.values, raw)
    assert result.values is not raw
    assert result.step_count == 0


# -- moving average -------------------------------------


def test_moving_average_keeps_length_and_shrinks_at_edges() -> None:
    step = ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 3})
    out = ProcessingChain([step]).run(_arr(0.0, 3.0, 6.0, 9.0)).values
    assert out.shape == (4,)
    # uçlar kısmi pencere: (0+3)/2, (0+3+6)/3, (3+6+9)/3, (6+9)/2
    assert np.allclose(out, [1.5, 3.0, 6.0, 7.5])


# -- tekrar üretilebilirlik ----------------------------


def test_chain_signature_is_stable_and_order_sensitive() -> None:
    a = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    b = ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 1.0})
    assert ProcessingChain([a, b]).signature() == ProcessingChain([a, b]).signature()
    assert ProcessingChain([a, b]).signature() != ProcessingChain([b, a]).signature()


def test_disabled_step_does_not_change_the_signature() -> None:
    a = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    b_on = ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 1.0})
    b_off = ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 1.0}, enabled=False)
    assert ProcessingChain([a]).signature() == ProcessingChain([a, b_off]).signature()
    assert ProcessingChain([a]).signature() != ProcessingChain([a, b_on]).signature()


def test_applied_signatures_match_the_enabled_steps() -> None:
    a = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    b = ProcessingStep(StepKind.ABS, "ch0", {})
    result = ProcessingChain([a, b]).run(_arr(-1.0))
    assert list(result.applied) == [a.signature(), b.signature()]


# -- kurma yardımcıları -------------------------------


def test_chain_edit_helpers_are_pure() -> None:
    a = ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})
    b = ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 1.0})
    c = ProcessingStep(StepKind.ABS, "ch0", {})
    base = ProcessingChain([a, b])

    assert base.with_step(c).steps == [a, b, c]
    assert base.without_index(0).steps == [b]
    assert ProcessingChain([a, b, c]).moved(2, 0).steps == [c, a, b]
    assert base.steps == [a, b]  # taban değişmedi


def test_two_dimensional_input_is_rejected() -> None:
    with pytest.raises(ChainExecutionError, match="tek boyutlu"):
        ProcessingChain([ProcessingStep(StepKind.ABS, "ch0", {})]).run(
            np.zeros((2, 2), dtype=np.float64)
        )


def test_list_round_trip() -> None:
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0}),
            ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 4}, enabled=False),
        ]
    )
    assert ProcessingChain.from_list(chain.to_list()).steps == chain.steps

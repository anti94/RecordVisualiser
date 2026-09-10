"""NaN ve kalite bayrağı politikası — `F4-005`.

Kabul: geçersiz örnekler sessizce geçerli değere dönüşmez.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.processing.chain import (
    ChainExecutionError,
    ProcessingChain,
    invalid_input_mask,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind


def _f(*xs: float) -> NDArray[np.float64]:
    return np.array(xs, dtype=np.float64)


def _q(*xs: int) -> NDArray[np.uint8]:
    return np.array(xs, dtype=np.uint8)


# -- invalid_input_mask -----------------------------------


def test_nan_and_inf_are_invalid() -> None:
    mask = invalid_input_mask(_f(1.0, np.nan, np.inf, -np.inf, 2.0))
    assert list(mask) == [False, True, True, True, False]


def test_value_quality_flags_are_invalid_but_timing_flags_are_not() -> None:
    values = _f(1.0, 2.0, 3.0, 4.0)
    quality = _q(
        int(Quality.OK),
        int(Quality.CRC_ERROR),
        int(Quality.GAP_BEFORE),  # zaman bayrağı — değeri geçersiz kılmaz
        int(Quality.SUSPECT),
    )
    assert list(invalid_input_mask(values, quality)) == [False, True, False, True]


def test_quality_length_mismatch_is_rejected() -> None:
    with pytest.raises(ChainExecutionError, match="aynı uzunlukta"):
        invalid_input_mask(_f(1.0, 2.0), _q(0))


# -- politika: sessiz iyileşme yok ------------------------


def test_clip_does_not_heal_infinity_into_a_bound() -> None:
    # np.clip(inf, 0, 1) tek başına 1.0 döndürür — politika bunu engeller.
    chain = ProcessingChain([ProcessingStep(StepKind.CLIP, "ch0", {"lo": 0.0, "hi": 1.0})])
    result = chain.run(_f(0.5, np.inf, -np.inf, 0.9))
    assert np.isnan(result.values[1]) and np.isnan(result.values[2])
    assert result.values[0] == 0.5 and result.values[3] == 0.9
    assert list(result.invalid_mask) == [False, True, True, False]


def test_nan_propagates_through_every_step_and_stays_invalid() -> None:
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.ABS, "ch0", {}),
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": 10.0}),
            ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 5.0}),
            ProcessingStep(StepKind.CLIP, "ch0", {"lo": -1e9, "hi": 1e9}),
        ]
    )
    result = chain.run(_f(-1.0, np.nan, 3.0))
    assert np.isnan(result.values[1])
    assert result.values[0] == 15.0 and result.values[2] == 35.0
    assert result.invalid_count == 1


def test_quality_flagged_sample_never_becomes_a_number() -> None:
    chain = ProcessingChain([ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0})])
    values = _f(10.0, 20.0, 30.0)
    quality = _q(int(Quality.OK), int(Quality.CRC_ERROR), int(Quality.OK))
    result = chain.run(values, quality)
    assert result.values[0] == 20.0 and result.values[2] == 60.0
    assert np.isnan(result.values[1])  # CRC hatalı örnek geçerli değere dönmedi
    assert list(result.invalid_mask) == [False, True, False]
    # Ham girdi değişmedi.
    assert np.array_equal(values, _f(10.0, 20.0, 30.0))


def test_moving_average_spreads_nan_rather_than_averaging_around_it() -> None:
    chain = ProcessingChain([ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 3})])
    result = chain.run(_f(2.0, 2.0, np.nan, 2.0, 2.0))
    # nan komşularına yayılır; hiçbir konum "2.0" gibi makul bir değere iyileşmez.
    assert np.isnan(result.values[1]) and np.isnan(result.values[2]) and np.isnan(result.values[3])
    assert result.values[0] == 2.0 and result.values[4] == 2.0


def test_clean_input_has_an_all_false_invalid_mask() -> None:
    result = ProcessingChain([ProcessingStep(StepKind.ABS, "ch0", {})]).run(_f(-1.0, 2.0, -3.0))
    assert not result.invalid_mask.any()
    assert result.invalid_count == 0

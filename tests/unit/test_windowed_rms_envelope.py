"""Pencereli RMS ve tepe-tutma zarfı — `F4-021`.

Kabul: sabit genlikli sinyalde beklenen RMS/zarf oluşur.

Golden değerler elle hesaplandı; merkezleme ve kenar davranışı
`moving_average` (`F4-017`) ile aynıdır.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError
from sonar_analyzer.processing.windowing import (
    EDGE_NAN,
    MAX_WINDOW,
    WindowingError,
    windowed_envelope,
    windowed_rms,
)

Vec = NDArray[np.float64]


def _f(*values: float) -> Vec:
    return np.array(values, dtype=np.float64)


# --------------------------------------------------------------------------- #
# windowed_rms — sabit genlik
# --------------------------------------------------------------------------- #


def test_rms_of_a_dc_signal_is_the_level() -> None:
    assert np.allclose(windowed_rms(_f(5.0, 5.0, 5.0, 5.0, 5.0, 5.0), 3), 5.0)


def test_rms_of_a_square_wave_is_the_amplitude() -> None:
    square = _f(3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0)
    assert np.allclose(windowed_rms(square, 4), 3.0)
    assert np.allclose(windowed_rms(square, 2), 3.0)


def test_rms_hand_computed_short_array() -> None:
    # x = [0,1,2,3,4] -> x^2 = [0,1,4,9,16]; window 3 shrink karesel ortalama:
    # [0.5, 5/3, 14/3, 29/3, 12.5] -> sqrt
    out = windowed_rms(_f(0.0, 1.0, 2.0, 3.0, 4.0), 3)
    expected = np.sqrt(_f(0.5, 5.0 / 3.0, 14.0 / 3.0, 29.0 / 3.0, 12.5))
    assert np.allclose(out, expected)


def test_rms_window_1_is_absolute_value() -> None:
    assert np.allclose(windowed_rms(_f(-3.0, 4.0, -5.0), 1), _f(3.0, 4.0, 5.0))


def test_rms_of_a_full_period_sine_is_amplitude_over_sqrt2() -> None:
    n = np.arange(64, dtype=np.float64)
    amp = 7.0
    sine = amp * np.sin(2.0 * np.pi * 4.0 * n / 64.0)  # 4 tam periyot
    out = windowed_rms(sine, 64)  # merkez konum tüm diziyi kapsar
    assert abs(out[32] - amp / np.sqrt(2.0)) < 1e-9


def test_rms_result_is_never_negative() -> None:
    rng = np.random.default_rng(3)
    out = windowed_rms(rng.normal(size=200), 9)
    assert np.all(out >= 0.0)


def test_rms_nan_spreads_locally() -> None:
    out = windowed_rms(_f(2.0, 2.0, np.nan, 2.0, 2.0), 3)
    assert np.isnan(out[[1, 2, 3]]).all()
    assert out[0] == 2.0 and out[4] == 2.0


def test_rms_edge_nan_marks_partial_windows() -> None:
    out = windowed_rms(_f(5.0, 5.0, 5.0, 5.0, 5.0), 3, edges=EDGE_NAN)
    assert np.isnan(out[[0, 4]]).all()
    assert np.allclose(out[1:4], 5.0)


# --------------------------------------------------------------------------- #
# windowed_envelope — tepe tutma
# --------------------------------------------------------------------------- #


def test_envelope_of_a_dc_signal_is_the_level() -> None:
    assert np.allclose(windowed_envelope(_f(5.0, 5.0, 5.0), 3), 5.0)


def test_envelope_of_a_square_wave_is_the_amplitude() -> None:
    square = _f(3.0, -3.0, 3.0, -3.0, 3.0, -3.0)
    assert np.allclose(windowed_envelope(square, 2), 3.0)
    assert np.allclose(windowed_envelope(square, 4), 3.0)


def test_envelope_hand_computed_short_array() -> None:
    # |x| = [1,2,3,4,5]; window 3 shrink kayan tepe:
    # i0 max(1,2)=2  i1 max(1,2,3)=3  i2 max(2,3,4)=4  i3 max(3,4,5)=5  i4 max(4,5)=5
    out = windowed_envelope(_f(1.0, -2.0, 3.0, -4.0, 5.0), 3)
    assert np.array_equal(out, _f(2.0, 3.0, 4.0, 5.0, 5.0))


def test_envelope_window_1_is_absolute_value() -> None:
    assert np.array_equal(windowed_envelope(_f(1.0, -2.0, 3.0), 1), _f(1.0, 2.0, 3.0))


def test_envelope_of_a_sine_recovers_the_amplitude() -> None:
    n = np.arange(32, dtype=np.float64)
    amp = 4.0
    sine = amp * np.sin(2.0 * np.pi * n / 8.0)  # örnekler tam ±amp'a değiyor
    out = windowed_envelope(sine, 8)  # bir tam periyot
    assert np.allclose(out[4:28], amp, atol=1e-9)


def test_envelope_nan_spreads_locally() -> None:
    out = windowed_envelope(_f(1.0, 1.0, np.nan, 1.0, 1.0), 3)
    assert np.isnan(out[[1, 2, 3]]).all()
    assert out[0] == 1.0 and out[4] == 1.0


def test_envelope_edge_nan_marks_partial_windows() -> None:
    out = windowed_envelope(_f(1.0, 2.0, 3.0, 4.0, 5.0), 3, edges=EDGE_NAN)
    assert np.isnan(out[[0, 4]]).all()
    assert np.array_equal(out[1:4], _f(3.0, 4.0, 5.0))


# --------------------------------------------------------------------------- #
# ortak: uzunluk / değişmezlik / boş / doğrulama
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("func", [windowed_rms, windowed_envelope])
def test_length_is_preserved(func: object) -> None:
    fn = func  # tip daraltma için
    assert fn(np.arange(20, dtype=np.float64), 7).shape == (20,)  # type: ignore[operator]


@pytest.mark.parametrize("func", [windowed_rms, windowed_envelope])
def test_input_is_not_mutated(func: object) -> None:
    data = _f(5.0, -1.0, 4.0, -2.0, 3.0)
    snapshot = data.copy()
    func(data, 3)  # type: ignore[operator]
    assert np.array_equal(data, snapshot)


@pytest.mark.parametrize("func", [windowed_rms, windowed_envelope])
def test_empty_array_returns_empty(func: object) -> None:
    assert func(np.empty(0, dtype=np.float64), 4).shape == (0,)  # type: ignore[operator]


@pytest.mark.parametrize("func", [windowed_rms, windowed_envelope])
def test_rejects_bad_window(func: object) -> None:
    with pytest.raises(WindowingError):
        func(_f(1.0, 2.0, 3.0), 0)  # type: ignore[operator]
    with pytest.raises(WindowingError):
        func(_f(1.0, 2.0, 3.0), MAX_WINDOW + 1)  # type: ignore[operator]


def test_envelope_rejects_2d_and_bad_edges() -> None:
    with pytest.raises(WindowingError, match="tek boyutlu"):
        windowed_envelope(np.ones((2, 2)), 2)
    with pytest.raises(WindowingError, match="kenar modu"):
        windowed_envelope(_f(1.0, 2.0), 2, edges="reflect")


# --------------------------------------------------------------------------- #
# apply_step / zincir entegrasyonu
# --------------------------------------------------------------------------- #


def test_apply_step_windowed_rms_matches_direct_call() -> None:
    x = _f(1.0, -2.0, 3.0, -4.0, 5.0, -6.0)
    step = ProcessingStep(StepKind.WINDOWED_RMS, "ch0", {"window": 3})
    assert np.allclose(apply_step(x, step), windowed_rms(x, 3))


def test_apply_step_envelope_matches_direct_call() -> None:
    x = _f(1.0, -2.0, 3.0, -4.0, 5.0, -6.0)
    step = ProcessingStep(StepKind.ENVELOPE, "ch0", {"window": 3})
    assert np.allclose(apply_step(x, step), windowed_envelope(x, 3))


def test_chain_constant_amplitude_gives_expected_rms_and_envelope() -> None:
    square = _f(*([2.0, -2.0] * 16))  # sabit genlik 2.0
    rms = ProcessingChain([ProcessingStep(StepKind.WINDOWED_RMS, "ch0", {"window": 4})]).run(square)
    env = ProcessingChain([ProcessingStep(StepKind.ENVELOPE, "ch0", {"window": 4})]).run(square)
    assert np.allclose(rms.values, 2.0)
    assert np.allclose(env.values, 2.0)
    assert rms.invalid_count == 0 and env.invalid_count == 0


# --------------------------------------------------------------------------- #
# adım modeli
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", [StepKind.WINDOWED_RMS, StepKind.ENVELOPE])
def test_step_defaults_to_window_5(kind: StepKind) -> None:
    assert ProcessingStep.default(kind, "ch0").parameters == {"window": 5}


@pytest.mark.parametrize("kind", [StepKind.WINDOWED_RMS, StepKind.ENVELOPE])
def test_step_rejects_zero_window(kind: StepKind) -> None:
    with pytest.raises(StepValidationError, match="window"):
        ProcessingStep(kind, "ch0", {"window": 0})


@pytest.mark.parametrize("kind", [StepKind.WINDOWED_RMS, StepKind.ENVELOPE])
def test_step_rejects_excessive_window(kind: StepKind) -> None:
    with pytest.raises(StepValidationError, match="aşırı"):
        ProcessingStep(kind, "ch0", {"window": MAX_WINDOW + 1})


def test_step_signature_distinguishes_kind_and_window() -> None:
    a = ProcessingStep(StepKind.WINDOWED_RMS, "ch0", {"window": 5})
    assert a.signature() != ProcessingStep(StepKind.ENVELOPE, "ch0", {"window": 5}).signature()
    assert a.signature() != ProcessingStep(StepKind.WINDOWED_RMS, "ch0", {"window": 6}).signature()

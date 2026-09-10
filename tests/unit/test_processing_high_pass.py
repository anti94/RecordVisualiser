"""Sıfır-fazlı Butterworth yüksek geçiren filtre — `F4-030`.

Kabul: DC ve düşük frekans referansa (Butterworth genlik yanıtı) uygun
bastırılır. Sınır/transient davranışı `F4-031`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.filters import (
    FilterError,
    butterworth_highpass_response,
    butterworth_lowpass_response,
    high_pass,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

Vec = NDArray[np.float64]


def _tone(amp: float, freq_hz: float, rate_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


def _hp(f: float, fc: float, n: int) -> float:
    if f == 0.0:
        return 0.0
    return 1.0 / math.sqrt(1.0 + (fc / f) ** (2 * n))


# --------------------------------------------------------------------------- #
# genlik yanıtı
# --------------------------------------------------------------------------- #


def test_dc_gain_is_exactly_zero() -> None:
    resp = butterworth_highpass_response(np.array([0.0]), 100.0, 4)
    assert resp[0] == 0.0


def test_gain_is_minus_3db_at_the_cutoff_for_every_order() -> None:
    for order in (1, 2, 4, 8):
        resp = butterworth_highpass_response(np.array([250.0]), 250.0, order)
        assert abs(resp[0] - 1.0 / math.sqrt(2.0)) < 1e-12


def test_gain_approaches_unity_far_above_the_cutoff() -> None:
    resp = butterworth_highpass_response(np.array([100.0 * 50.0]), 50.0, 4)
    assert abs(resp[0] - 1.0) < 1e-12


def test_response_matches_the_closed_form() -> None:
    freqs = np.array([0.0, 10.0, 50.0, 200.0, 1000.0])
    fc, n = 100.0, 3
    resp = butterworth_highpass_response(freqs, fc, n)
    expected = np.array([_hp(float(f), fc, n) for f in freqs])
    assert np.allclose(resp, expected, atol=1e-12)


def test_low_and_high_pass_are_power_complementary() -> None:
    freqs = np.linspace(1.0, 500.0, 97)
    for order in (1, 2, 4, 6):
        lp = butterworth_lowpass_response(freqs, 100.0, order)
        hp = butterworth_highpass_response(freqs, 100.0, order)
        assert np.allclose(lp**2 + hp**2, 1.0, atol=1e-12)


# --------------------------------------------------------------------------- #
# zaman alanı
# --------------------------------------------------------------------------- #


def test_dc_offset_is_removed() -> None:
    sr, n = 200.0, 200
    x = 5.0 + _tone(1.0, 20.0, sr, n)  # 5.0 DC + 20 Hz
    y = high_pass(x, sr, 5.0, 4)
    assert abs(float(np.mean(y))) < 1e-9  # DC gitti
    assert np.allclose(y, _tone(1.0, 20.0, sr, n), atol=1e-6)


def test_low_frequency_tone_is_suppressed_per_the_reference() -> None:
    sr, n = 200.0, 200
    x = _tone(3.0, 2.0, sr, n)  # 2 Hz, cutoff 40, order 4
    y = high_pass(x, sr, 40.0, 4)
    gain = _hp(2.0, 40.0, 4)  # ~6e-6
    assert np.allclose(y, x * gain, atol=1e-9)
    assert np.max(np.abs(y)) < 1e-4


def test_high_frequency_tone_passes_through() -> None:
    sr, n = 200.0, 200
    x = _tone(2.0, 80.0, sr, n)
    y = high_pass(x, sr, 20.0, 4)
    assert np.allclose(y, x, atol=1e-6)


def test_zero_phase_no_group_delay() -> None:
    sr, n = 256.0, 256
    x = _tone(1.0, 60.0, sr, n)
    y = high_pass(x, sr, 20.0, 4)
    assert int(np.argmax(y[:32])) == int(np.argmax(x[:32]))


# --------------------------------------------------------------------------- #
# kenar durumlar
# --------------------------------------------------------------------------- #


def test_nan_makes_the_whole_output_nan() -> None:
    x = _tone(1.0, 50.0, 200.0, 50)
    x[10] = np.nan
    assert np.isnan(high_pass(x, 200.0, 20.0, 4)).all()


def test_empty_and_length_preserved() -> None:
    assert high_pass(np.empty(0, dtype=np.float64), 200.0, 20.0, 4).shape == (0,)
    assert high_pass(np.zeros(77, dtype=np.float64), 200.0, 20.0, 4).shape == (77,)


def test_input_is_not_mutated() -> None:
    x = _tone(1.0, 40.0, 200.0, 128)
    snapshot = x.copy()
    high_pass(x, 200.0, 20.0, 4)
    assert np.array_equal(x, snapshot)


def test_high_pass_rejects_bad_parameters() -> None:
    x = np.zeros(64, dtype=np.float64)
    with pytest.raises(FilterError):
        high_pass(x, 200.0, 100.0, 4)  # cutoff == Nyquist
    with pytest.raises(FilterError):
        high_pass(x, 200.0, 40.0, 0)


# --------------------------------------------------------------------------- #
# adım modeli / zincir
# --------------------------------------------------------------------------- #


def test_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.HIGH_PASS, "ch0")
    assert step.parameters == {"sample_rate_hz": 48_000.0, "cutoff_hz": 200.0, "order": 4}


def test_step_rejects_cutoff_beyond_nyquist() -> None:
    with pytest.raises(StepValidationError, match="Nyquist"):
        ProcessingStep(
            StepKind.HIGH_PASS,
            "ch0",
            {"sample_rate_hz": 1_000.0, "cutoff_hz": 700.0, "order": 4},
        )


def test_apply_step_matches_high_pass() -> None:
    x = _tone(1.0, 55.0, 200.0, 200) + 3.0
    step = ProcessingStep(
        StepKind.HIGH_PASS, "ch0", {"sample_rate_hz": 200.0, "cutoff_hz": 20.0, "order": 4}
    )
    assert np.allclose(apply_step(x, step), high_pass(x, 200.0, 20.0, 4))


def test_chain_high_pass_removes_a_drift_offset() -> None:
    sr, n = 200.0, 200
    x = 7.5 + _tone(1.0, 45.0, sr, n)
    step = ProcessingStep(
        StepKind.HIGH_PASS, "ch0", {"sample_rate_hz": sr, "cutoff_hz": 10.0, "order": 5}
    )
    result = ProcessingChain([step]).run(x)
    assert result.invalid_count == 0
    assert abs(float(np.mean(result.values))) < 1e-9
    assert np.allclose(result.values, _tone(1.0, 45.0, sr, n), atol=1e-5)


def test_step_signature_distinguishes_low_and_high_pass() -> None:
    params = {"sample_rate_hz": 1_000.0, "cutoff_hz": 100.0, "order": 4}
    lo = ProcessingStep(StepKind.LOW_PASS, "ch0", dict(params))
    hi = ProcessingStep(StepKind.HIGH_PASS, "ch0", dict(params))
    assert lo.signature() != hi.signature()

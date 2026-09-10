"""Sıfır-fazlı Butterworth alçak geçiren filtre — `F4-027`.

Kabul: düşük frekans korunur; yüksek frekans referansa (Butterworth
genlik yanıtı) uygun bastırılır.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.filters import (
    FilterError,
    butterworth_lowpass_response,
    low_pass,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

Vec = NDArray[np.float64]


def _tone(amp: float, freq_hz: float, rate_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


def _butter(f: float, fc: float, n: int) -> float:
    return 1.0 / math.sqrt(1.0 + (f / fc) ** (2 * n))


# --------------------------------------------------------------------------- #
# genlik yanıtı — analitik referans
# --------------------------------------------------------------------------- #


def test_gain_is_unity_at_dc() -> None:
    resp = butterworth_lowpass_response(np.array([0.0]), 100.0, 4)
    assert resp[0] == 1.0


def test_gain_is_minus_3db_at_the_cutoff_for_every_order() -> None:
    for order in (1, 2, 4, 8):
        resp = butterworth_lowpass_response(np.array([250.0]), 250.0, order)
        assert abs(resp[0] - 1.0 / math.sqrt(2.0)) < 1e-12


def test_response_matches_the_closed_form() -> None:
    freqs = np.array([10.0, 50.0, 200.0, 500.0, 1000.0])
    fc, n = 100.0, 3
    resp = butterworth_lowpass_response(freqs, fc, n)
    expected = np.array([_butter(float(f), fc, n) for f in freqs])
    assert np.allclose(resp, expected, atol=1e-12)


def test_rolloff_is_20n_db_per_decade() -> None:
    fc, n = 100.0, 2
    high = butterworth_lowpass_response(np.array([10.0 * fc]), fc, n)[0]
    at_fc = butterworth_lowpass_response(np.array([fc]), fc, n)[0]
    # H(10 fc) / H(fc) ~= sqrt(2) * 10**-n
    assert abs(high / at_fc - math.sqrt(2.0) * 10.0**-n) < 1e-6


# --------------------------------------------------------------------------- #
# zaman alanı — ton geçişi
# --------------------------------------------------------------------------- #


def test_low_frequency_tone_passes_through_unchanged() -> None:
    sr, n = 200.0, 200
    x = _tone(2.0, 5.0, sr, n)  # 5 Hz, cutoff 50
    y = low_pass(x, sr, 50.0, 4)
    gain = _butter(5.0, 50.0, 4)  # ~1 - 5e-9
    assert np.allclose(y, x * gain, atol=1e-9)
    assert np.allclose(y, x, atol=1e-6)


def test_high_frequency_tone_is_suppressed_per_the_reference() -> None:
    sr, n = 200.0, 200
    x = _tone(3.0, 80.0, sr, n)  # 80 Hz, cutoff 20, order 4
    y = low_pass(x, sr, 20.0, 4)
    gain = _butter(80.0, 20.0, 4)  # 1/sqrt(1 + 4**8) ~= 1/256
    assert np.allclose(y, x * gain, atol=1e-9)
    assert np.max(np.abs(y)) < 0.02  # 3 * (1/256) ~= 0.0117


def test_two_tone_signal_keeps_the_low_and_drops_the_high() -> None:
    sr, n = 400.0, 400
    low = _tone(1.0, 6.0, sr, n)
    high = _tone(1.0, 150.0, sr, n)
    y = low_pass(low + high, sr, 30.0, 6)
    # H(150, 30, 6) ~= 6e-5 -> yüksek ton pratikte yok.
    assert np.allclose(y, low, atol=1e-3)


def test_zero_phase_no_group_delay() -> None:
    sr, n = 256.0, 256
    x = _tone(1.0, 4.0, sr, n)
    y = low_pass(x, sr, 40.0, 4)
    # Faz kaymamış: tepe indeksleri aynı.
    assert int(np.argmax(y[:64])) == int(np.argmax(x[:64]))


# --------------------------------------------------------------------------- #
# kenar durumlar
# --------------------------------------------------------------------------- #


def test_nan_makes_the_whole_output_nan() -> None:
    x = _tone(1.0, 5.0, 100.0, 50)
    x[10] = np.nan
    assert np.isnan(low_pass(x, 100.0, 20.0, 4)).all()


def test_empty_and_length_preserved() -> None:
    assert low_pass(np.empty(0, dtype=np.float64), 100.0, 20.0, 4).shape == (0,)
    assert low_pass(np.zeros(123, dtype=np.float64), 100.0, 20.0, 4).shape == (123,)


def test_input_is_not_mutated() -> None:
    x = _tone(1.0, 7.0, 200.0, 128)
    snapshot = x.copy()
    low_pass(x, 200.0, 40.0, 4)
    assert np.array_equal(x, snapshot)


def test_low_pass_rejects_bad_parameters() -> None:
    x = np.zeros(64, dtype=np.float64)
    with pytest.raises(FilterError):
        low_pass(x, 200.0, 100.0, 4)  # cutoff == Nyquist
    with pytest.raises(FilterError):
        low_pass(x, 200.0, 0.0, 4)
    with pytest.raises(FilterError):
        low_pass(x, 200.0, 40.0, 0)
    with pytest.raises(FilterError):
        low_pass(x, 200.0, 40.0, 9)


# --------------------------------------------------------------------------- #
# adım modeli / zincir
# --------------------------------------------------------------------------- #


def test_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.LOW_PASS, "ch0")
    assert step.parameters == {"sample_rate_hz": 48_000.0, "cutoff_hz": 8_000.0, "order": 4}


def test_step_rejects_cutoff_at_or_above_nyquist() -> None:
    with pytest.raises(StepValidationError, match="Nyquist"):
        ProcessingStep(
            StepKind.LOW_PASS,
            "ch0",
            {"sample_rate_hz": 1_000.0, "cutoff_hz": 500.0, "order": 4},
        )


def test_step_rejects_bad_order() -> None:
    with pytest.raises(StepValidationError, match="order"):
        ProcessingStep(
            StepKind.LOW_PASS,
            "ch0",
            {"sample_rate_hz": 1_000.0, "cutoff_hz": 100.0, "order": 20},
        )


def test_apply_step_matches_low_pass() -> None:
    x = _tone(1.0, 9.0, 200.0, 200)
    step = ProcessingStep(
        StepKind.LOW_PASS, "ch0", {"sample_rate_hz": 200.0, "cutoff_hz": 40.0, "order": 4}
    )
    assert np.allclose(apply_step(x, step), low_pass(x, 200.0, 40.0, 4))


def test_chain_low_pass_runs_clean() -> None:
    sr, n = 200.0, 200
    x = _tone(1.0, 4.0, sr, n) + _tone(1.0, 90.0, sr, n)
    step = ProcessingStep(
        StepKind.LOW_PASS, "ch0", {"sample_rate_hz": sr, "cutoff_hz": 25.0, "order": 5}
    )
    result = ProcessingChain([step]).run(x)
    assert result.invalid_count == 0
    assert np.allclose(result.values, _tone(1.0, 4.0, sr, n), atol=5e-3)

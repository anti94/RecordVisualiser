"""Sıfır-fazlı Butterworth notch (bant söndüren) filtre — `F4-036`.

Kabul: hedef ton bastırılır; komşu ton referans toleransta kalır.
Sınır doğrulaması `F4-037`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.filters import (
    FilterError,
    butterworth_bandpass_response,
    butterworth_notch_response,
    notch,
    notch_bandwidth_hz,
    notch_edges_hz,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

Vec = NDArray[np.float64]

F0 = 50.0
Q = 30.0
ORDER = 4
SR = 400.0
N = 400  # bin aralığı 1 Hz -> 50 ve 60 Hz tam bine oturur


def _tone(amp: float, freq_hz: float, rate_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


def _notch_gain(f: float, center: float = F0, q: float = Q, order: int = ORDER) -> float:
    denominator = f * f - center * center
    if denominator == 0.0:
        return 0.0
    ratio = abs((f * (center / q)) / denominator)
    return 1.0 / math.sqrt(1.0 + ratio ** (2 * order))


def _resp(f: float, order: int = ORDER) -> float:
    return float(butterworth_notch_response(np.array([f]), F0, Q, order)[0])


# --------------------------------------------------------------------------- #
# genlik yanıtı — analitik değişmezler
# --------------------------------------------------------------------------- #


def test_gain_at_the_center_is_exactly_zero() -> None:
    for order in (1, 2, 4, 8):
        assert _resp(F0, order) == 0.0


def test_dc_passes_unchanged() -> None:
    assert abs(_resp(0.0) - 1.0) < 1e-12


def test_bandwidth_is_center_over_q() -> None:
    assert abs(notch_bandwidth_hz(F0, Q) - F0 / Q) < 1e-12
    assert abs(notch_bandwidth_hz(100.0, 4.0) - 25.0) < 1e-12


def test_edges_are_a_geometric_pair_separated_by_the_bandwidth() -> None:
    low, high = notch_edges_hz(F0, Q)
    assert abs((high - low) - notch_bandwidth_hz(F0, Q)) < 1e-12
    assert abs(low * high - F0 * F0) < 1e-9
    assert low < F0 < high


def test_gain_is_minus_3db_at_both_edges_for_every_order() -> None:
    low, high = notch_edges_hz(F0, Q)
    for order in (1, 2, 4, 8):
        assert abs(_resp(low, order) - 1.0 / math.sqrt(2.0)) < 1e-9
        assert abs(_resp(high, order) - 1.0 / math.sqrt(2.0)) < 1e-9


def test_response_matches_the_closed_form() -> None:
    freqs = np.array([0.0, 10.0, 49.0, 51.0, 60.0, 190.0])
    resp = butterworth_notch_response(freqs, F0, Q, 3)
    expected = np.array([_notch_gain(float(f), order=3) for f in freqs])
    assert np.allclose(resp, expected, atol=1e-12)


def test_notch_and_band_pass_are_power_complementary() -> None:
    low, high = notch_edges_hz(F0, Q)
    freqs = np.linspace(1.0, 199.0, 101)
    for order in (1, 2, 4):
        bp = butterworth_bandpass_response(freqs, low, high, order)
        nt = butterworth_notch_response(freqs, F0, Q, order)
        assert np.allclose(bp**2 + nt**2, 1.0, atol=1e-9)


def test_far_frequencies_approach_unity() -> None:
    assert abs(_resp(5.0) - 1.0) < 1e-6
    assert abs(_resp(190.0) - 1.0) < 1e-6


# --------------------------------------------------------------------------- #
# zaman alanı — hedef ton / komşu ton
# --------------------------------------------------------------------------- #


def test_target_tone_is_removed() -> None:
    x = _tone(3.0, F0, SR, N)
    y = notch(x, SR, F0, Q, ORDER)
    assert np.max(np.abs(y)) < 1e-9


def test_neighbouring_tone_stays_within_the_reference_tolerance() -> None:
    x = _tone(1.0, 60.0, SR, N)
    y = notch(x, SR, F0, Q, ORDER)
    gain = _notch_gain(60.0)
    assert np.allclose(y, x * gain, atol=1e-9)
    assert abs(gain - 1.0) < 1e-6  # komşu ton pratikte dokunulmamış


def test_two_tone_signal_keeps_only_the_neighbour() -> None:
    target = _tone(2.0, F0, SR, N)
    neighbour = _tone(1.0, 60.0, SR, N)
    y = notch(target + neighbour, SR, F0, Q, ORDER)
    assert np.allclose(y, neighbour, atol=1e-6)
    # Hedef bin tümüyle boşaldı.
    assert abs(complex(np.fft.rfft(y)[int(F0)])) < 1e-6


def test_dc_offset_survives_the_notch() -> None:
    x = 4.0 + _tone(1.0, 60.0, SR, N)
    y = notch(x, SR, F0, Q, ORDER)
    assert abs(float(np.mean(y)) - 4.0) < 1e-9


def test_zero_phase_no_group_delay() -> None:
    x = _tone(1.0, 60.0, SR, N)
    y = notch(x, SR, F0, Q, ORDER)
    gain = _notch_gain(60.0)
    assert gain > 0.0
    assert np.allclose(y, x * gain, atol=1e-9)


def test_a_narrower_notch_touches_the_neighbour_less() -> None:
    neighbour = 55.0
    wide = _notch_gain(neighbour, q=2.0)
    narrow = _notch_gain(neighbour, q=50.0)
    assert narrow > wide


# --------------------------------------------------------------------------- #
# kenar durumlar
# --------------------------------------------------------------------------- #


def test_nan_makes_the_whole_output_nan() -> None:
    x = _tone(1.0, 60.0, SR, 64)
    x[5] = np.nan
    assert np.isnan(notch(x, SR, F0, Q, ORDER)).all()


def test_empty_and_length_preserved() -> None:
    assert notch(np.empty(0, dtype=np.float64), SR, F0, Q, ORDER).shape == (0,)
    assert notch(np.zeros(111, dtype=np.float64), SR, F0, Q, ORDER).shape == (111,)


def test_input_is_not_mutated() -> None:
    x = _tone(1.0, F0, SR, 128)
    snapshot = x.copy()
    notch(x, SR, F0, Q, ORDER)
    assert np.array_equal(x, snapshot)


def test_notch_rejects_bad_parameters() -> None:
    x = np.zeros(64, dtype=np.float64)
    with pytest.raises(FilterError, match="Nyquist"):
        notch(x, SR, 200.0, Q, ORDER)  # merkez == Nyquist
    with pytest.raises(FilterError, match="Q"):
        notch(x, SR, F0, 0.0, ORDER)
    with pytest.raises(FilterError, match="order"):
        notch(x, SR, F0, Q, 0)


# --------------------------------------------------------------------------- #
# adım modeli / zincir
# --------------------------------------------------------------------------- #


def test_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.NOTCH, "ch0")
    assert step.parameters == {
        "sample_rate_hz": 48_000.0,
        "center_hz": 50.0,
        "q": 30.0,
        "order": 4,
    }


def test_step_rejects_a_nonpositive_q() -> None:
    with pytest.raises(StepValidationError, match="Q"):
        ProcessingStep(
            StepKind.NOTCH,
            "ch0",
            {"sample_rate_hz": SR, "center_hz": F0, "q": -1.0, "order": 4},
        )


def test_apply_step_matches_notch() -> None:
    x = _tone(1.0, F0, SR, N) + _tone(1.0, 60.0, SR, N)
    step = ProcessingStep(
        StepKind.NOTCH,
        "ch0",
        {"sample_rate_hz": SR, "center_hz": F0, "q": Q, "order": ORDER},
    )
    assert np.allclose(apply_step(x, step), notch(x, SR, F0, Q, ORDER))


def test_chain_notch_removes_mains_hum() -> None:
    signal = _tone(1.0, 60.0, SR, N)
    hum = _tone(0.8, F0, SR, N)
    step = ProcessingStep(
        StepKind.NOTCH,
        "ch0",
        {"sample_rate_hz": SR, "center_hz": F0, "q": Q, "order": ORDER},
    )
    result = ProcessingChain([step]).run(signal + hum)
    assert result.invalid_count == 0
    assert np.allclose(result.values, signal, atol=1e-6)

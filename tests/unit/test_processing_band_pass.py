"""Sıfır-fazlı Butterworth bant geçiren filtre — `F4-033`.

Kabul: bant içi ve dışı tonlar referans davranışı gösterir. Sınır
doğrulaması `F4-034`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.filters import (
    FilterError,
    band_center_hz,
    band_pass,
    butterworth_bandpass_response,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

Vec = NDArray[np.float64]

LO, HI = 20.0, 80.0
F0 = math.sqrt(LO * HI)  # 40.0


def _tone(amp: float, freq_hz: float, rate_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


def _bp(f: float, lo: float, hi: float, n: int) -> float:
    if f == 0.0:
        return 0.0
    ratio = abs((f * f - lo * hi) / (f * (hi - lo)))
    return 1.0 / math.sqrt(1.0 + ratio ** (2 * n))


def _resp(f: float, order: int = 4) -> float:
    return float(butterworth_bandpass_response(np.array([f]), LO, HI, order)[0])


# --------------------------------------------------------------------------- #
# genlik yanıtı — analitik değişmezler
# --------------------------------------------------------------------------- #


def test_band_center_is_the_geometric_mean() -> None:
    assert abs(band_center_hz(LO, HI) - 40.0) < 1e-12
    assert abs(band_center_hz(100.0, 400.0) - 200.0) < 1e-12


def test_gain_is_unity_at_the_geometric_center() -> None:
    for order in (1, 2, 4, 8):
        assert abs(_resp(F0, order) - 1.0) < 1e-12


def test_both_band_edges_are_minus_3db_for_every_order() -> None:
    for order in (1, 2, 4, 8):
        assert abs(_resp(LO, order) - 1.0 / math.sqrt(2.0)) < 1e-12
        assert abs(_resp(HI, order) - 1.0 / math.sqrt(2.0)) < 1e-12


def test_dc_gain_is_exactly_zero() -> None:
    assert _resp(0.0) == 0.0


def test_response_matches_the_closed_form() -> None:
    freqs = np.array([0.0, 5.0, 20.0, 40.0, 80.0, 300.0])
    resp = butterworth_bandpass_response(freqs, LO, HI, 3)
    expected = np.array([_bp(float(f), LO, HI, 3) for f in freqs])
    assert np.allclose(resp, expected, atol=1e-12)


def test_response_is_symmetric_in_log_frequency_about_the_center() -> None:
    for factor in (1.5, 2.0, 4.0, 10.0):
        assert abs(_resp(F0 * factor) - _resp(F0 / factor)) < 1e-12


def test_response_falls_off_on_both_sides() -> None:
    assert _resp(F0) > _resp(HI) > _resp(4.0 * HI)
    assert _resp(F0) > _resp(LO) > _resp(LO / 4.0)


# --------------------------------------------------------------------------- #
# zaman alanı — bant içi / dışı tonlar
# --------------------------------------------------------------------------- #


def test_in_band_tone_passes_through() -> None:
    sr, n = 400.0, 400
    x = _tone(2.0, F0, sr, n)  # tam merkez
    y = band_pass(x, sr, LO, HI, 4)
    assert np.allclose(y, x, atol=1e-9)


def test_below_band_tone_is_suppressed_per_the_reference() -> None:
    sr, n = 400.0, 400
    x = _tone(3.0, 4.0, sr, n)  # 4 Hz, bandın çok altında
    y = band_pass(x, sr, LO, HI, 4)
    gain = _bp(4.0, LO, HI, 4)
    assert np.allclose(y, x * gain, atol=1e-9)
    assert np.max(np.abs(y)) < 0.01 * 3.0


def test_above_band_tone_is_suppressed_per_the_reference() -> None:
    sr, n = 1000.0, 1000
    x = _tone(3.0, 400.0, sr, n)  # 400 Hz, bandın çok üstünde
    y = band_pass(x, sr, LO, HI, 4)
    gain = _bp(400.0, LO, HI, 4)
    assert np.allclose(y, x * gain, atol=1e-9)
    assert np.max(np.abs(y)) < 0.01 * 3.0


def test_three_tone_signal_keeps_only_the_in_band_component() -> None:
    sr, n = 1000.0, 1000
    inside = _tone(1.0, F0, sr, n)
    below = _tone(1.0, 2.0, sr, n)
    above = _tone(1.0, 400.0, sr, n)
    y = band_pass(inside + below + above, sr, LO, HI, 5)
    assert np.allclose(y, inside, atol=5e-3)


def test_zero_phase_no_group_delay() -> None:
    # Bant içinde ama merkez dışı bir ton: çıktı girdinin POZİTİF skaler
    # katı olmalı (kayma yok, işaret dönmüyor) ve kat tam referans kazanç.
    sr, n = 400.0, 400
    x = _tone(1.0, 30.0, sr, n)  # 30 tam periyot
    y = band_pass(x, sr, LO, HI, 4)
    gain = _bp(30.0, LO, HI, 4)
    assert gain > 0.0
    assert np.allclose(y, x * gain, atol=1e-9)


# --------------------------------------------------------------------------- #
# kenar durumlar
# --------------------------------------------------------------------------- #


def test_dc_offset_is_removed() -> None:
    sr, n = 400.0, 400
    x = 9.0 + _tone(1.0, F0, sr, n)
    y = band_pass(x, sr, LO, HI, 4)
    assert abs(float(y.sum())) < 1e-9


def test_nan_makes_the_whole_output_nan() -> None:
    x = _tone(1.0, F0, 400.0, 64)
    x[7] = np.nan
    assert np.isnan(band_pass(x, 400.0, LO, HI, 4)).all()


def test_empty_and_length_preserved() -> None:
    assert band_pass(np.empty(0, dtype=np.float64), 400.0, LO, HI, 4).shape == (0,)
    assert band_pass(np.zeros(99, dtype=np.float64), 400.0, LO, HI, 4).shape == (99,)


def test_input_is_not_mutated() -> None:
    x = _tone(1.0, F0, 400.0, 128)
    snapshot = x.copy()
    band_pass(x, 400.0, LO, HI, 4)
    assert np.array_equal(x, snapshot)


def test_band_pass_rejects_a_reversed_band() -> None:
    with pytest.raises(FilterError, match="ters bant"):
        band_pass(np.zeros(64), 400.0, HI, LO, 4)


# --------------------------------------------------------------------------- #
# adım modeli / zincir
# --------------------------------------------------------------------------- #


def test_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.BAND_PASS, "ch0")
    assert step.parameters == {
        "sample_rate_hz": 48_000.0,
        "low_cutoff_hz": 500.0,
        "high_cutoff_hz": 5_000.0,
        "order": 4,
    }


def test_step_rejects_a_reversed_band() -> None:
    with pytest.raises(StepValidationError, match="ters bant"):
        ProcessingStep(
            StepKind.BAND_PASS,
            "ch0",
            {
                "sample_rate_hz": 1_000.0,
                "low_cutoff_hz": 300.0,
                "high_cutoff_hz": 100.0,
                "order": 4,
            },
        )


def test_apply_step_matches_band_pass() -> None:
    sr, n = 400.0, 400
    x = _tone(1.0, F0, sr, n) + _tone(1.0, 3.0, sr, n)
    step = ProcessingStep(
        StepKind.BAND_PASS,
        "ch0",
        {"sample_rate_hz": sr, "low_cutoff_hz": LO, "high_cutoff_hz": HI, "order": 4},
    )
    assert np.allclose(apply_step(x, step), band_pass(x, sr, LO, HI, 4))


def test_chain_band_pass_isolates_the_band() -> None:
    sr, n = 1000.0, 1000
    inside = _tone(1.0, F0, sr, n)
    x = inside + _tone(1.0, 2.0, sr, n) + _tone(1.0, 450.0, sr, n)
    step = ProcessingStep(
        StepKind.BAND_PASS,
        "ch0",
        {"sample_rate_hz": sr, "low_cutoff_hz": LO, "high_cutoff_hz": HI, "order": 5},
    )
    result = ProcessingChain([step]).run(x)
    assert result.invalid_count == 0
    assert np.allclose(result.values, inside, atol=5e-3)

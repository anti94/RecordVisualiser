"""Fourier tabanlı yeniden örnekleme / desimasyon — `F4-025`.

Kabul: hedef sample rate, örnek sayısı ve alias denetimi referansla
eşleşir.

Referanslar bağımsızdır: tam periyot içeren bir sinüs, yeni örnek
noktalarında analitik olarak hesaplanır; hedef Nyquist üstündeki bir ton
tümüyle bastırılmalı (naif desimasyon ise onu düşük frekansa katlar).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.chain import ProcessingChain, apply_step
from sonar_analyzer.processing.resampling import (
    ResampleError,
    fourier_resample,
    resample_to_rate,
    resampled_length,
)
from sonar_analyzer.processing.steps import ProcessingStep, StepKind, StepValidationError

Vec = NDArray[np.float64]
TWO_PI = 2.0 * math.pi


def _tone(amp: float, freq_hz: float, rate_hz: float, count: int) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(TWO_PI * freq_hz * k / rate_hz)


def _resample_step(source_hz: float, target_hz: float) -> ProcessingStep:
    return ProcessingStep(
        StepKind.RESAMPLE, "ch0", {"source_rate_hz": source_hz, "target_rate_hz": target_hz}
    )


# --------------------------------------------------------------------------- #
# örnek sayısı
# --------------------------------------------------------------------------- #


def test_resampled_length_matches_the_rate_ratio() -> None:
    assert resampled_length(1_000, 100.0, 60.0) == 600
    assert resampled_length(1_000, 100.0, 250.0) == 2_500
    assert resampled_length(3, 100.0, 100.0) == 3
    assert resampled_length(0, 100.0, 60.0) == 0


def test_resampled_length_rejects_nonpositive_rates() -> None:
    with pytest.raises(ResampleError, match="kaynak"):
        resampled_length(100, 0.0, 60.0)
    with pytest.raises(ResampleError, match="hedef"):
        resampled_length(100, 100.0, -1.0)


def test_output_length_tracks_the_target_rate() -> None:
    x = _tone(1.0, 5.0, 100.0, 200)
    out = resample_to_rate(x, 100.0, 37.0)
    assert out.size == resampled_length(200, 100.0, 37.0)
    assert abs(out.size / x.size - 37.0 / 100.0) < 1.0 / x.size


# --------------------------------------------------------------------------- #
# değer doğruluğu — tam periyot içeren sinüs
# --------------------------------------------------------------------------- #


def test_upsampling_a_pure_tone_reproduces_the_continuous_sine() -> None:
    x = _tone(3.0, 10.0, 100.0, 100)  # 10 tam periyot
    out = resample_to_rate(x, 100.0, 200.0)
    expected = _tone(3.0, 10.0, 200.0, 200)
    assert out.shape == (200,)
    assert np.allclose(out, expected, atol=1e-9)


def test_downsampling_a_pure_tone_reproduces_the_continuous_sine() -> None:
    x = _tone(2.0, 10.0, 100.0, 100)
    out = resample_to_rate(x, 100.0, 50.0)  # yeni Nyquist 25 > 10
    expected = _tone(2.0, 10.0, 50.0, 50)
    assert out.shape == (50,)
    assert np.allclose(out, expected, atol=1e-9)


def test_band_limited_signal_survives_a_down_up_round_trip() -> None:
    x = _tone(1.0, 3.0, 100.0, 100) + _tone(0.7, 7.0, 100.0, 100) + _tone(0.4, 11.0, 100.0, 100)
    down = resample_to_rate(x, 100.0, 50.0)  # Nyquist 25 > 11
    up = resample_to_rate(down, 50.0, 100.0)
    assert np.allclose(up, x, atol=1e-9)


# --------------------------------------------------------------------------- #
# alias denetimi
# --------------------------------------------------------------------------- #


def test_component_above_the_new_nyquist_is_removed_not_aliased() -> None:
    amp = 5.0
    x = _tone(amp, 40.0, 200.0, 200)  # 40 Hz, kaynak Nyquist 100
    out = resample_to_rate(x, 200.0, 60.0)  # yeni Nyquist 30 < 40
    # Fourier yöntemi 40 Hz bileşenini tümüyle atar.
    assert np.max(np.abs(out)) < 1e-9


def test_naive_decimation_would_alias_the_same_component() -> None:
    amp = 5.0
    x = _tone(amp, 40.0, 200.0, 200)
    naive = x[::3]  # ~66.7 Hz'e naif desimasyon
    # Enerji korunur çünkü 40 Hz düşük frekansa katlanır (alias).
    assert np.max(np.abs(naive)) > 0.5 * amp


# --------------------------------------------------------------------------- #
# kenar durumlar
# --------------------------------------------------------------------------- #


def test_equal_rates_return_a_copy() -> None:
    x = _tone(1.0, 4.0, 100.0, 64)
    out = resample_to_rate(x, 100.0, 100.0)
    assert out is not x
    assert np.array_equal(out, x)


def test_empty_input_returns_empty() -> None:
    assert resample_to_rate(np.empty(0, dtype=np.float64), 100.0, 50.0).shape == (0,)


def test_nan_makes_the_whole_output_nan() -> None:
    out = resample_to_rate(np.array([1.0, 2.0, np.nan, 4.0]), 100.0, 50.0)
    assert np.isnan(out).all()


def test_input_is_not_mutated() -> None:
    x = _tone(1.0, 6.0, 100.0, 80)
    snapshot = x.copy()
    resample_to_rate(x, 100.0, 60.0)
    resample_to_rate(x, 100.0, 160.0)
    assert np.array_equal(x, snapshot)


def test_fourier_resample_rejects_bad_arguments() -> None:
    with pytest.raises(ResampleError, match="pozitif"):
        fourier_resample(np.ones(10), 0)
    with pytest.raises(ResampleError, match="tek boyutlu"):
        fourier_resample(np.ones((3, 3)), 4)


def test_resample_to_rate_rejects_nonpositive_rates() -> None:
    with pytest.raises(ResampleError):
        resample_to_rate(np.ones(10), 0.0, 50.0)
    with pytest.raises(ResampleError):
        resample_to_rate(np.ones(10), 100.0, 0.0)


# --------------------------------------------------------------------------- #
# adım modeli / zincir
# --------------------------------------------------------------------------- #


def test_step_defaults() -> None:
    step = ProcessingStep.default(StepKind.RESAMPLE, "ch0")
    assert step.parameters == {"source_rate_hz": 48_000.0, "target_rate_hz": 24_000.0}


def test_step_rejects_nonpositive_rates() -> None:
    with pytest.raises(StepValidationError, match="pozitif"):
        ProcessingStep(StepKind.RESAMPLE, "ch0", {"source_rate_hz": 0.0, "target_rate_hz": 1.0})
    with pytest.raises(StepValidationError, match="pozitif"):
        ProcessingStep(StepKind.RESAMPLE, "ch0", {"source_rate_hz": 100.0, "target_rate_hz": -5.0})


def test_step_coerces_int_rates_to_float() -> None:
    step = ProcessingStep(
        StepKind.RESAMPLE, "ch0", {"source_rate_hz": 48000, "target_rate_hz": 16000}
    )
    assert step.parameters["source_rate_hz"] == 48_000.0
    assert isinstance(step.parameters["target_rate_hz"], float)


def test_step_signature_distinguishes_rates() -> None:
    a = ProcessingStep(StepKind.RESAMPLE, "ch0", {"source_rate_hz": 100.0, "target_rate_hz": 50.0})
    b = ProcessingStep(StepKind.RESAMPLE, "ch0", {"source_rate_hz": 100.0, "target_rate_hz": 25.0})
    assert a.signature() != b.signature()


def test_apply_step_matches_resample_to_rate() -> None:
    x = _tone(1.0, 8.0, 100.0, 100)
    assert np.allclose(apply_step(x, _resample_step(100.0, 40.0)), resample_to_rate(x, 100.0, 40.0))


def test_chain_resample_changes_the_length() -> None:
    x = _tone(1.0, 5.0, 100.0, 100)
    result = ProcessingChain([_resample_step(100.0, 30.0)]).run(x)
    assert result.values.size == resampled_length(100, 100.0, 30.0) == 30
    assert result.invalid_count == 0

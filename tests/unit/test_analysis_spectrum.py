"""Tek taraflı FFT genlik spektrumu — `F4-040`.

Kabul: bilinen sinüsün tepe frekansı ve genliği doğru çıkar.
dB / Nyquist / kısa pencere sınır denetimleri `F4-041`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.spectrum import (
    SpectrumError,
    amplitude_to_db,
    one_sided_fft,
)
from sonar_analyzer.analysis.windows import WindowKind

Vec = NDArray[np.float64]

FS = 1_000.0
N = 1_000  # bin genişliği 1 Hz -> tam sayı frekanslar tam bine oturur
ALL_WINDOWS = list(WindowKind)


def _tone(amp: float, freq_hz: float, rate_hz: float = FS, count: int = N) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


# --------------------------------------------------------------------------- #
# eksen
# --------------------------------------------------------------------------- #


def test_axis_is_the_rfft_grid() -> None:
    result = one_sided_fft(_tone(1.0, 10.0), FS)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(N, d=1.0 / FS))
    assert len(result) == N // 2 + 1
    assert result.frequencies_hz[0] == 0.0
    assert result.frequencies_hz[-1] == FS / 2.0


def test_resolution_and_nyquist_are_reported() -> None:
    result = one_sided_fft(_tone(1.0, 10.0), FS)
    assert abs(result.resolution_hz - 1.0) < 1e-12
    assert result.nyquist_hz == 500.0
    assert result.sample_count == N
    assert result.sample_rate_hz == FS


def test_resolution_follows_the_sample_count() -> None:
    result = one_sided_fft(_tone(1.0, 10.0, 800.0, 400), 800.0)
    assert abs(result.resolution_hz - 2.0) < 1e-12


# --------------------------------------------------------------------------- #
# bilinen sinüs: tepe frekansı ve genliği
# --------------------------------------------------------------------------- #


def test_known_sine_peaks_at_its_frequency_with_its_amplitude() -> None:
    result = one_sided_fft(_tone(3.0, 10.0), FS)
    assert abs(result.peak_frequency_hz - 10.0) < 1e-12
    assert abs(result.peak_amplitude - 3.0) < 1e-9
    assert result.peak_index == 10


@pytest.mark.parametrize("window", ALL_WINDOWS)
def test_amplitude_is_recovered_for_every_window(window: WindowKind) -> None:
    # Coherent gain düzeltmesi sayesinde pencere ne olursa olsun genlik aynı.
    result = one_sided_fft(_tone(2.5, 40.0), FS, window=window)
    assert abs(result.peak_frequency_hz - 40.0) < 1e-12
    assert abs(result.peak_amplitude - 2.5) < 1e-9
    assert result.window_kind == window.value


@pytest.mark.parametrize("freq", [1.0, 7.0, 123.0, 499.0])
def test_the_peak_lands_on_the_right_bin(freq: float) -> None:
    result = one_sided_fft(_tone(1.0, freq), FS)
    assert abs(result.peak_frequency_hz - freq) < 1e-12


@pytest.mark.parametrize("amp", [0.001, 0.5, 1.0, 42.0, 1_000.0])
def test_the_amplitude_scales_linearly(amp: float) -> None:
    result = one_sided_fft(_tone(amp, 25.0), FS)
    assert abs(result.peak_amplitude - amp) < 1e-9 * max(1.0, amp)


def test_two_tones_are_both_recovered() -> None:
    signal = _tone(2.0, 10.0) + _tone(0.5, 50.0)
    result = one_sided_fft(signal, FS)
    assert abs(result.amplitudes[10] - 2.0) < 1e-9
    assert abs(result.amplitudes[50] - 0.5) < 1e-9
    # Diğer binler pratikte boş.
    others = np.delete(result.amplitudes, [10, 50])
    assert np.max(others) < 1e-9


def test_a_cosine_is_recovered_too() -> None:
    k = np.arange(N, dtype=np.float64)
    signal = 1.5 * np.cos(2.0 * math.pi * 30.0 * k / FS)
    result = one_sided_fft(signal, FS)
    assert abs(result.peak_frequency_hz - 30.0) < 1e-12
    assert abs(result.peak_amplitude - 1.5) < 1e-9


def test_phase_does_not_change_the_amplitude() -> None:
    k = np.arange(N, dtype=np.float64)
    for phase in (0.0, 0.4, math.pi / 2, 2.0):
        signal = 2.0 * np.sin(2.0 * math.pi * 20.0 * k / FS + phase)
        result = one_sided_fft(signal, FS)
        assert abs(result.amplitudes[20] - 2.0) < 1e-9


# --------------------------------------------------------------------------- #
# DC ve Nyquist iki katı alınmaz
# --------------------------------------------------------------------------- #


def test_dc_amplitude_is_the_mean_level() -> None:
    result = one_sided_fft(np.full(N, 5.0), FS)
    assert abs(result.amplitudes[0] - 5.0) < 1e-9
    assert np.max(result.amplitudes[1:]) < 1e-9


def test_nyquist_amplitude_is_not_doubled() -> None:
    # (-1)^n tam Nyquist'te genliği 2.0 olan bir tondur.
    alternating = 2.0 * np.power(-1.0, np.arange(N, dtype=np.float64))
    result = one_sided_fft(alternating, FS)
    assert abs(result.frequencies_hz[-1] - 500.0) < 1e-12
    assert abs(result.amplitudes[-1] - 2.0) < 1e-9


def test_a_dc_offset_does_not_disturb_a_tone() -> None:
    result = one_sided_fft(4.0 + _tone(1.0, 60.0), FS)
    assert abs(result.amplitudes[0] - 4.0) < 1e-9
    assert abs(result.amplitudes[60] - 1.0) < 1e-9


# --------------------------------------------------------------------------- #
# dB dönüşümü (sınırları F4-041)
# --------------------------------------------------------------------------- #


def test_amplitude_to_db_uses_20log10() -> None:
    db = amplitude_to_db(np.array([1.0, 0.1, 0.01, 2.0]))
    assert abs(db[0] - 0.0) < 1e-12
    assert abs(db[1] + 20.0) < 1e-12
    assert abs(db[2] + 40.0) < 1e-12
    assert abs(db[3] - 20.0 * math.log10(2.0)) < 1e-12


def test_zero_amplitude_stops_at_the_floor() -> None:
    db = amplitude_to_db(np.array([0.0]), floor_db=-120.0)
    assert db[0] == -120.0
    assert np.isfinite(db).all()


def test_a_reference_shifts_the_scale() -> None:
    db = amplitude_to_db(np.array([2.0]), reference=2.0)
    assert abs(db[0]) < 1e-12


# --------------------------------------------------------------------------- #
# hata yolları
# --------------------------------------------------------------------------- #


def test_empty_signal_is_rejected() -> None:
    with pytest.raises(SpectrumError, match="boş sinyal"):
        one_sided_fft(np.empty(0, dtype=np.float64), FS)


def test_nonpositive_sample_rate_is_rejected() -> None:
    with pytest.raises(SpectrumError, match="sample rate"):
        one_sided_fft(_tone(1.0, 10.0), 0.0)


def test_two_dimensional_input_is_rejected() -> None:
    with pytest.raises(SpectrumError, match="tek boyutlu"):
        one_sided_fft(np.zeros((4, 4)), FS)


def test_nonpositive_db_reference_is_rejected() -> None:
    with pytest.raises(SpectrumError, match="referansı"):
        amplitude_to_db(np.array([1.0]), reference=0.0)


def test_input_is_not_mutated() -> None:
    signal = _tone(1.0, 10.0)
    snapshot = signal.copy()
    one_sided_fft(signal, FS, window=WindowKind.HANN)
    assert np.array_equal(signal, snapshot)

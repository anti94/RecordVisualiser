"""FFT, dB ve Nyquist sınır doğrulamaları — `F4-041`.

Kabul: DC, Nyquist, sıfır sinyal ve kısa pencere **kontrollü** sonuç
verir — her durumda tanımlı, sonlu ve elle doğrulanabilir bir çıktı.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.spectrum import (
    DEFAULT_DB_FLOOR,
    amplitude_to_db,
    one_sided_fft,
)
from sonar_analyzer.analysis.windows import WindowKind

Vec = NDArray[np.float64]

FS = 1_000.0
N = 1_000


def _tone(amp: float, freq_hz: float, rate_hz: float = FS, count: int = N) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / rate_hz)


def _alternating(amp: float, count: int = N) -> Vec:
    """Tam Nyquist'te genliği `amp` olan ton."""
    return amp * np.power(-1.0, np.arange(count, dtype=np.float64))


# --------------------------------------------------------------------------- #
# DC
# --------------------------------------------------------------------------- #


def test_dc_only_signal_puts_everything_in_bin_zero() -> None:
    result = one_sided_fft(np.full(N, 7.25), FS)
    assert abs(result.amplitudes[0] - 7.25) < 1e-9
    assert np.max(result.amplitudes[1:]) < 1e-9
    assert result.peak_index == 0


def test_negative_dc_reports_its_magnitude() -> None:
    result = one_sided_fft(np.full(N, -3.5), FS)
    assert abs(result.amplitudes[0] - 3.5) < 1e-9


def test_dc_is_exact_even_with_a_tapering_window() -> None:
    # Hann pencerede DC bin 1'e sızar (ana lob) ama bin 0 yine tam çıkar.
    result = one_sided_fft(np.full(N, 2.0), FS, window=WindowKind.HANN)
    assert abs(result.amplitudes[0] - 2.0) < 1e-9
    assert result.amplitudes[1] > 0.0  # sızıntı gerçek, gizlenmiyor
    assert np.max(result.amplitudes[2:]) < 1e-9


def test_a_zero_mean_signal_has_no_dc() -> None:
    result = one_sided_fft(_tone(1.0, 25.0), FS)
    assert result.amplitudes[0] < 1e-12


# --------------------------------------------------------------------------- #
# Nyquist
# --------------------------------------------------------------------------- #


def test_even_length_has_an_exact_nyquist_bin_that_is_not_doubled() -> None:
    result = one_sided_fft(_alternating(2.0), FS)
    assert result.frequencies_hz[-1] == FS / 2.0
    assert abs(result.amplitudes[-1] - 2.0) < 1e-9
    assert np.max(result.amplitudes[:-1]) < 1e-9


def test_odd_length_has_no_nyquist_bin_and_doubles_the_last_one() -> None:
    count = 999
    result = one_sided_fft(_tone(1.5, 499.0, 999.0, count), 999.0)
    assert len(result) == (count + 1) // 2
    assert result.frequencies_hz[-1] < 999.0 / 2.0  # tam Nyquist bin yok
    assert abs(result.frequencies_hz[-1] - 499.0) < 1e-9
    assert abs(result.amplitudes[-1] - 1.5) < 1e-9  # normal bin: iki katı alınır


def test_dc_tone_and_nyquist_together_satisfy_parseval() -> None:
    signal = 3.0 + _tone(2.0, 10.0) + _alternating(1.0)
    result = one_sided_fft(signal, FS)

    assert abs(result.amplitudes[0] - 3.0) < 1e-9
    assert abs(result.amplitudes[10] - 2.0) < 1e-9
    assert abs(result.amplitudes[-1] - 1.0) < 1e-9

    # mean(x^2) = amp_dc^2 + amp_nyq^2 + sum(diger amp^2)/2
    middle = result.amplitudes[1:-1]
    reconstructed = (
        result.amplitudes[0] ** 2
        + result.amplitudes[-1] ** 2
        + float(np.sum(np.square(middle))) / 2.0
    )
    assert abs(reconstructed - float(np.mean(np.square(signal)))) < 1e-9


def test_no_bin_exceeds_the_nyquist_frequency() -> None:
    result = one_sided_fft(_tone(1.0, 10.0), FS)
    assert float(np.max(result.frequencies_hz)) <= result.nyquist_hz


# --------------------------------------------------------------------------- #
# sıfır sinyal
# --------------------------------------------------------------------------- #


def test_zero_signal_gives_an_all_zero_spectrum() -> None:
    result = one_sided_fft(np.zeros(N), FS)
    assert np.array_equal(result.amplitudes, np.zeros(N // 2 + 1))
    assert result.peak_amplitude == 0.0
    assert np.isfinite(result.amplitudes).all()


def test_zero_signal_in_db_stops_at_the_floor_without_infinities() -> None:
    result = one_sided_fft(np.zeros(N), FS)
    db = amplitude_to_db(result.amplitudes)
    assert np.all(db == DEFAULT_DB_FLOOR)
    assert np.isfinite(db).all()


@pytest.mark.parametrize("window", list(WindowKind))
def test_zero_signal_is_zero_for_every_window(window: WindowKind) -> None:
    result = one_sided_fft(np.zeros(256), FS, window=window)
    assert np.max(result.amplitudes) == 0.0


# --------------------------------------------------------------------------- #
# kısa pencereler
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 8])
def test_short_windows_produce_a_well_formed_spectrum(count: int) -> None:
    rng = np.random.default_rng(count)
    result = one_sided_fft(rng.normal(size=count), FS)
    assert len(result) == count // 2 + 1
    assert result.frequencies_hz.shape == result.amplitudes.shape
    assert np.isfinite(result.amplitudes).all()
    assert np.all(result.amplitudes >= 0.0)


def test_single_sample_spectrum_is_its_magnitude() -> None:
    result = one_sided_fft(np.array([-4.0]), FS)
    assert len(result) == 1
    assert result.frequencies_hz[0] == 0.0
    assert abs(result.amplitudes[0] - 4.0) < 1e-12
    assert abs(result.resolution_hz - FS) < 1e-12


def test_two_sample_spectrum_is_mean_and_half_difference() -> None:
    a, b = 3.0, -1.0
    result = one_sided_fft(np.array([a, b]), FS)
    assert len(result) == 2
    assert abs(result.amplitudes[0] - abs(a + b) / 2.0) < 1e-12  # DC
    assert abs(result.amplitudes[1] - abs(a - b) / 2.0) < 1e-12  # Nyquist


def test_three_sample_spectrum_doubles_the_non_dc_bin() -> None:
    values = np.array([1.0, -1.0, 0.0])
    result = one_sided_fft(values, FS)
    spectrum = np.fft.rfft(values)
    assert len(result) == 2
    assert abs(result.amplitudes[0] - abs(spectrum[0]) / 3.0) < 1e-12
    assert abs(result.amplitudes[1] - 2.0 * abs(spectrum[1]) / 3.0) < 1e-12


def test_a_short_window_still_finds_a_tone_on_a_bin() -> None:
    # 8 örnek, fs=8 -> bin genişliği 1 Hz; 2 Hz tam bine oturur.
    result = one_sided_fft(_tone(1.0, 2.0, 8.0, 8), 8.0)
    assert abs(result.peak_frequency_hz - 2.0) < 1e-12
    assert abs(result.peak_amplitude - 1.0) < 1e-9


# --------------------------------------------------------------------------- #
# dB dönüşümü
# --------------------------------------------------------------------------- #


def test_db_is_monotonic_in_amplitude() -> None:
    amplitudes = np.array([0.0, 1e-6, 1e-3, 0.1, 1.0, 10.0])
    db = amplitude_to_db(amplitudes)
    assert np.all(np.diff(db) > 0.0)


def test_the_default_floor_is_minus_200_db() -> None:
    assert DEFAULT_DB_FLOOR == -200.0
    assert amplitude_to_db(np.array([0.0]))[0] == -200.0


def test_anything_below_the_floor_is_clamped_to_it() -> None:
    db = amplitude_to_db(np.array([1e-30, 0.0]), floor_db=-100.0)
    assert np.all(db == -100.0)


def test_a_reference_shifts_the_scale_by_its_own_db() -> None:
    amplitudes = np.array([0.5, 1.0, 4.0])
    plain = amplitude_to_db(amplitudes)
    shifted = amplitude_to_db(amplitudes, reference=2.0)
    assert np.allclose(shifted, plain - 20.0 * math.log10(2.0))


def test_negative_amplitudes_use_their_magnitude() -> None:
    assert np.allclose(amplitude_to_db(np.array([-1.0])), amplitude_to_db(np.array([1.0])))


def test_nan_amplitude_stays_nan() -> None:
    db = amplitude_to_db(np.array([np.nan, 1.0]))
    assert np.isnan(db[0])
    assert abs(db[1]) < 1e-12


def test_db_preserves_shape_and_handles_an_empty_array() -> None:
    assert amplitude_to_db(np.zeros(7)).shape == (7,)
    assert amplitude_to_db(np.empty(0, dtype=np.float64)).shape == (0,)


def test_db_of_a_known_tone_spectrum_peaks_at_its_level() -> None:
    result = one_sided_fft(_tone(0.1, 40.0), FS)
    db = amplitude_to_db(result.amplitudes)
    assert abs(db[40] + 20.0) < 1e-6  # 0.1 -> -20 dB
    assert int(np.argmax(db)) == 40

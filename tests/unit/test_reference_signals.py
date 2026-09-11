"""Referans sinyallerle FFT / PSD / STFT / filtre doğrulaması — `F4-087`.

Kabul: FFT, PSD, STFT ve filtre sonuçları NumPy/SciPy referanslarıyla
eşleşir.

**SciPy bu ortamda kurulu değildir** (isteğe bağlı `dsp` ekstrası) ve
analiz katmanı bilinçli olarak saf NumPy'dir. Bu yüzden referanslar iki
yerden gelir ve ikisi de bağımsızdır:

* **NumPy referansı** — `np.fft` ile doğrudan, uygulamanın kod yolundan
  geçmeden hesaplanan aynı büyüklük.
* **Analitik referans** — sinyalin kapalı formundan türeyen beklenen
  değer (tepe genliği, Parseval gücü, düz gürültü tabanı, Butterworth'un
  −3 dB noktası, chirp'in anlık frekansı).

Dört kanonik sinyal kullanılır: **sinüs** (tek frekans), **chirp**
(kayan frekans), **beyaz gürültü** (düz spektrum) ve **impulse** (düz
spektrum + filtrenin dürtü yanıtı).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import welch_psd
from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.stft import stft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.processing.filters import (
    band_pass,
    butterworth_bandpass_response,
    butterworth_highpass_response,
    butterworth_lowpass_response,
    high_pass,
    low_pass,
)

FS = 1000.0
N = 4000
#: Bin genişliği fs/N = 0.25 Hz — 100 Hz tam bine oturur, sızıntı yok.
TONE_HZ = 100.0
TONE_AMPLITUDE = 2.0

FloatArray = NDArray[np.float64]


def _times(count: int = N, sample_rate_hz: float = FS) -> FloatArray:
    return np.arange(count, dtype=np.float64) / sample_rate_hz


def sine(amplitude: float = TONE_AMPLITUDE, frequency_hz: float = TONE_HZ) -> FloatArray:
    return amplitude * np.sin(2.0 * math.pi * frequency_hz * _times())


def chirp(f0_hz: float = 50.0, f1_hz: float = 400.0) -> FloatArray:
    """Doğrusal kayan frekans: anlık frekans `f0 + (f1-f0)*t/T`."""
    t = _times()
    duration = N / FS
    phase = f0_hz * t + (f1_hz - f0_hz) / (2.0 * duration) * t**2
    return np.sin(2.0 * math.pi * phase)


def white_noise(count: int = 20_000, seed: int = 7) -> FloatArray:
    """Birim varyanslı beyaz gürültü — sabit seed, tekrar üretilebilir."""
    return np.random.default_rng(seed).standard_normal(count)


def impulse(count: int = 512) -> FloatArray:
    data = np.zeros(count, dtype=np.float64)
    data[0] = 1.0
    return data


def numpy_amplitude_reference(values: FloatArray, sample_rate_hz: float = FS) -> FloatArray:
    """Tek taraflı genlik spektrumunun **bağımsız** NumPy karşılığı.

    Uygulamanın kodundan geçmez: `np.fft.rfft` + tek taraflı ölçekleme
    (uçlar iki kez sayılmaz).
    """
    del sample_rate_hz
    spectrum = np.fft.rfft(values)
    amplitudes = 2.0 * np.abs(spectrum) / values.size
    amplitudes[0] /= 2.0
    if values.size % 2 == 0:
        amplitudes[-1] /= 2.0
    return amplitudes


# --------------------------------------------------------------------------- #
# SINUS — FFT
# --------------------------------------------------------------------------- #


def test_the_sine_spectrum_matches_the_numpy_reference() -> None:
    values = sine()
    result = one_sided_fft(values, FS, window=WindowKind.RECTANGULAR)
    assert np.allclose(result.amplitudes, numpy_amplitude_reference(values))


def test_the_sine_peak_is_at_its_analytic_frequency_and_amplitude() -> None:
    """Tam bine oturan bir tonun tepe genliği kendi genliğidir."""
    result = one_sided_fft(sine(), FS, window=WindowKind.RECTANGULAR)
    assert result.peak_frequency_hz == TONE_HZ
    assert abs(result.peak_amplitude - TONE_AMPLITUDE) < 1e-9


def test_the_frequency_axis_matches_the_numpy_reference() -> None:
    result = one_sided_fft(sine(), FS, window=WindowKind.RECTANGULAR)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(N, 1.0 / FS))


def test_parseval_holds_for_the_sine() -> None:
    """Zaman alanı gücü = frekans alanı gücü (analitik: A²/2)."""
    values = sine()
    spectrum = np.fft.rfft(values)
    time_power = float(np.sum(values**2)) / N
    freq_power = float(
        2.0 * np.sum(np.abs(spectrum) ** 2) / N**2
        - np.abs(spectrum[0]) ** 2 / N**2
        - np.abs(spectrum[-1]) ** 2 / N**2
    )
    assert abs(time_power - freq_power) < 1e-9
    assert abs(time_power - TONE_AMPLITUDE**2 / 2.0) < 1e-9


@pytest.mark.parametrize("frequency_hz", [10.0, 100.0, 250.0, 400.0])
def test_every_bin_centred_tone_is_found_exactly(frequency_hz: float) -> None:
    result = one_sided_fft(sine(frequency_hz=frequency_hz), FS, window=WindowKind.RECTANGULAR)
    assert result.peak_frequency_hz == frequency_hz


# --------------------------------------------------------------------------- #
# SINUS — PSD
# --------------------------------------------------------------------------- #


def test_the_sine_psd_peaks_at_the_tone() -> None:
    result = welch_psd(sine(), FS, window=WindowKind.HANN)
    assert abs(result.peak_frequency_hz - TONE_HZ) < result.resolution_hz


def test_the_integrated_psd_power_matches_the_analytic_power() -> None:
    """Bir sinüsün ortalama gücü A²/2; PSD integrali onu vermeli."""
    result = welch_psd(sine(), FS, window=WindowKind.HANN)
    assert abs(result.integrated_power - TONE_AMPLITUDE**2 / 2.0) < 0.02


def test_the_psd_axis_matches_the_numpy_reference() -> None:
    result = welch_psd(sine(), FS, window=WindowKind.HANN, segment_length=256)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(256, 1.0 / FS))


# --------------------------------------------------------------------------- #
# BEYAZ GURULTU — duz spektrum
# --------------------------------------------------------------------------- #


def test_white_noise_has_a_flat_psd_at_the_analytic_level() -> None:
    """Birim varyanslı gürültünün tek taraflı PSD tabanı `1 / (fs/2)`."""
    result = welch_psd(white_noise(), FS, window=WindowKind.HANN, segment_length=1024)
    expected = 1.0 / (FS / 2.0)
    assert abs(float(np.mean(result.density)) - expected) < 0.1 * expected


def test_the_noise_floor_does_not_drift_across_the_band() -> None:
    """Düzlük: bandın alt ve üst yarısı aynı seviyede."""
    result = welch_psd(white_noise(), FS, window=WindowKind.HANN, segment_length=1024)
    half = result.density.size // 2
    lower = float(np.mean(result.density[1:half]))
    upper = float(np.mean(result.density[half:-1]))
    assert abs(lower - upper) < 0.25 * lower


def test_the_integrated_noise_power_matches_its_variance() -> None:
    values = white_noise()
    result = welch_psd(values, FS, window=WindowKind.HANN, segment_length=1024)
    assert abs(result.integrated_power - float(np.var(values))) < 0.1


def test_noise_is_reproducible_from_its_seed() -> None:
    assert np.array_equal(white_noise(), white_noise())
    assert not np.array_equal(white_noise(seed=1), white_noise(seed=2))


# --------------------------------------------------------------------------- #
# IMPULSE — duz spektrum
# --------------------------------------------------------------------------- #


def test_the_impulse_spectrum_matches_the_numpy_reference() -> None:
    values = impulse()
    result = one_sided_fft(values, FS, window=WindowKind.RECTANGULAR)
    assert np.allclose(result.amplitudes, numpy_amplitude_reference(values))


def test_the_impulse_spectrum_is_flat_across_the_interior_bins() -> None:
    """Birim dürtünün spektrumu düzdür; uçlar tek taraflı ölçekten yarıdır."""
    values = impulse()
    result = one_sided_fft(values, FS, window=WindowKind.RECTANGULAR)
    interior = result.amplitudes[1:-1]
    expected = 2.0 / values.size
    assert np.allclose(interior, expected)
    assert abs(result.amplitudes[0] - expected / 2.0) < 1e-15
    assert abs(result.amplitudes[-1] - expected / 2.0) < 1e-15


def test_a_shifted_impulse_keeps_the_flat_magnitude() -> None:
    """Kaydırma yalnız fazı değiştirir; genlik düz kalır."""
    values = impulse()
    shifted = np.roll(values, 37)
    first = one_sided_fft(values, FS, window=WindowKind.RECTANGULAR)
    second = one_sided_fft(shifted, FS, window=WindowKind.RECTANGULAR)
    assert np.allclose(first.amplitudes, second.amplitudes)


# --------------------------------------------------------------------------- #
# CHIRP — STFT anlik frekansi izler
# --------------------------------------------------------------------------- #


def test_the_stft_tracks_the_chirp_instantaneous_frequency() -> None:
    """Her sütunun tepe satırı, analitik anlık frekansa yarım bin içinde."""
    result = stft(chirp(), FS, segment_length=256, overlap=0.5, window=WindowKind.HANN)
    peaks = result.peak_frequencies_hz()
    duration = N / FS
    expected = 50.0 + (400.0 - 50.0) * result.times_s / duration
    assert np.max(np.abs(peaks - expected)) < result.resolution_hz


def test_the_chirp_trace_rises_monotonically() -> None:
    result = stft(chirp(), FS, segment_length=256, overlap=0.5, window=WindowKind.HANN)
    peaks = result.peak_frequencies_hz()
    # Bin cozunurlugu nedeniyle esitlik olabilir, ama geri gitmemeli.
    assert bool(np.all(np.diff(peaks) >= 0.0))


def test_the_chirp_starts_and_ends_near_its_endpoints() -> None:
    result = stft(chirp(), FS, segment_length=256, overlap=0.5, window=WindowKind.HANN)
    peaks = result.peak_frequencies_hz()
    assert abs(float(peaks[0]) - 50.0) < 4 * result.resolution_hz
    assert abs(float(peaks[-1]) - 400.0) < 4 * result.resolution_hz


def test_a_steady_tone_gives_a_flat_stft_trace() -> None:
    """Karşılaştırma: sabit tonda iz kaymaz."""
    result = stft(sine(), FS, segment_length=256, overlap=0.5, window=WindowKind.HANN)
    peaks = result.peak_frequencies_hz()
    assert np.max(np.abs(peaks - TONE_HZ)) < result.resolution_hz


def test_the_stft_axes_match_the_numpy_reference() -> None:
    result = stft(chirp(), FS, segment_length=256, overlap=0.5, window=WindowKind.HANN)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(256, 1.0 / FS))
    assert result.bin_count == 256 // 2 + 1


# --------------------------------------------------------------------------- #
# FILTRELER — impulse yaniti = genlik yaniti
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("order", [1, 2, 4, 8])
def test_the_low_pass_impulse_response_equals_its_magnitude_response(order: int) -> None:
    """Sıfır-fazlı FFT filtresinin dürtü yanıtının spektrumu = tasarım eğrisi."""
    values = impulse()
    filtered = low_pass(values, cutoff_hz=100.0, sample_rate_hz=FS, order=order)
    spectrum = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(values.size, 1.0 / FS)
    assert np.allclose(spectrum, butterworth_lowpass_response(freqs, 100.0, order), atol=1e-12)


@pytest.mark.parametrize("order", [1, 2, 4])
def test_the_high_pass_impulse_response_equals_its_magnitude_response(order: int) -> None:
    values = impulse()
    filtered = high_pass(values, cutoff_hz=100.0, sample_rate_hz=FS, order=order)
    spectrum = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(values.size, 1.0 / FS)
    assert np.allclose(spectrum, butterworth_highpass_response(freqs, 100.0, order), atol=1e-12)


@pytest.mark.parametrize("order", [1, 2, 4])
def test_the_band_pass_impulse_response_equals_its_magnitude_response(order: int) -> None:
    values = impulse()
    filtered = band_pass(
        values, low_cutoff_hz=80.0, high_cutoff_hz=200.0, sample_rate_hz=FS, order=order
    )
    spectrum = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(values.size, 1.0 / FS)
    assert np.allclose(
        spectrum, butterworth_bandpass_response(freqs, 80.0, 200.0, order), atol=1e-12
    )


@pytest.mark.parametrize("order", [1, 2, 4, 8])
def test_the_cutoff_is_the_analytic_minus_three_decibel_point(order: int) -> None:
    """Butterworth tanımı: kesimde kazanç tam `1/sqrt(2)`."""
    cutoff = np.array([100.0])
    gain = float(butterworth_lowpass_response(cutoff, 100.0, order)[0])
    assert abs(gain - 1.0 / math.sqrt(2.0)) < 1e-12


def test_low_and_high_pass_are_power_complementary() -> None:
    """Aynı kesimde `|H_lp|² + |H_hp|² = 1` — Butterworth kimliği."""
    freqs = np.linspace(0.0, FS / 2.0, 601)
    for order in (1, 2, 4):
        low = butterworth_lowpass_response(freqs, 120.0, order)
        high = butterworth_highpass_response(freqs, 120.0, order)
        assert np.allclose(low**2 + high**2, 1.0, atol=1e-12)


def test_a_tone_inside_the_pass_band_survives_the_filter() -> None:
    """50 Hz tonu 100 Hz alçak geçirenden neredeyse bozulmadan çıkar."""
    values = sine(frequency_hz=50.0)
    filtered = low_pass(values, cutoff_hz=100.0, sample_rate_hz=FS, order=4)
    result = one_sided_fft(filtered, FS, window=WindowKind.RECTANGULAR)
    expected_gain = float(butterworth_lowpass_response(np.array([50.0]), 100.0, 4)[0])
    assert result.peak_frequency_hz == 50.0
    assert abs(result.peak_amplitude - TONE_AMPLITUDE * expected_gain) < 1e-9


def test_a_tone_in_the_stop_band_is_attenuated_by_the_designed_amount() -> None:
    """400 Hz tonu 100 Hz alçak geçirende tasarım kazancı kadar kalır."""
    values = sine(frequency_hz=400.0)
    filtered = low_pass(values, cutoff_hz=100.0, sample_rate_hz=FS, order=4)
    result = one_sided_fft(filtered, FS, window=WindowKind.RECTANGULAR)
    expected_gain = float(butterworth_lowpass_response(np.array([400.0]), 100.0, 4)[0])
    assert abs(result.peak_amplitude - TONE_AMPLITUDE * expected_gain) < 1e-9
    assert expected_gain < 0.005  # gercekten bastirilmis


def test_the_filter_is_zero_phase_on_a_symmetric_impulse() -> None:
    """Sıfır-fazlı filtre simetrik girdiyi simetrik bırakır (grup gecikmesi yok)."""
    values = np.zeros(512, dtype=np.float64)
    values[256] = 1.0
    filtered = low_pass(values, cutoff_hz=100.0, sample_rate_hz=FS, order=4)
    assert abs(float(np.argmax(filtered)) - 256.0) < 1e-9
    left = filtered[256 - 50 : 256]
    right = filtered[257 : 257 + 50]
    assert np.allclose(left, right[::-1], atol=1e-12)

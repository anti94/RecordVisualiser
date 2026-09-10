"""Welch güç spektral yoğunluğu — `F4-043`.

Kabul: referans sinyalin yoğunluğu ve entegre gücü toleransta eşleşir.
Sınır doğrulamaları `F4-044`.

Referanslar analitik: tam bine oturan ``A*sin`` için entegre güç
``A^2/2``, sabit ``c`` için ``c^2``, beyaz gürültü için varyansı.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import (
    PsdError,
    power_to_db,
    segment_starts,
    segment_step,
    welch_psd,
)
from sonar_analyzer.analysis.windows import (
    REFERENCE_ENBW,
    WindowKind,
    equivalent_noise_bandwidth,
    window_values,
)

Vec = NDArray[np.float64]

FS = 1_000.0
N = 4_096
ALL_WINDOWS = list(WindowKind)


def _tone(amp: float, freq_hz: float, count: int = N) -> Vec:
    k = np.arange(count, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


# --------------------------------------------------------------------------- #
# parçalama
# --------------------------------------------------------------------------- #


def test_segment_step_follows_the_overlap() -> None:
    assert segment_step(256, 0.0) == 256
    assert segment_step(256, 0.5) == 128
    assert segment_step(256, 0.75) == 64
    assert segment_step(10, 0.99) == 1  # en az bir örnek ilerlenir


def test_segment_starts_cover_whole_segments_only() -> None:
    # 1000 örnek, 256'lık parça, örtüşmesiz: son tam parça 512'de başlar.
    assert segment_starts(1_000, 256, 0.0) == [0, 256, 512]
    starts = segment_starts(1_024, 256, 0.5)
    assert starts == list(range(0, 769, 128))
    assert starts[-1] + 256 <= 1_024


def test_a_signal_shorter_than_the_segment_has_no_starts() -> None:
    assert segment_starts(100, 256, 0.5) == []


# --------------------------------------------------------------------------- #
# eksen ve biçim
# --------------------------------------------------------------------------- #


def test_axis_is_the_segment_rfft_grid() -> None:
    result = welch_psd(_tone(1.0, 50.0), FS, segment_length=512)
    assert np.allclose(result.frequencies_hz, np.fft.rfftfreq(512, d=1.0 / FS))
    assert len(result) == 512 // 2 + 1
    assert abs(result.resolution_hz - FS / 512.0) < 1e-12
    assert result.nyquist_hz == 500.0


def test_metadata_is_reported() -> None:
    result = welch_psd(_tone(1.0, 50.0), FS, segment_length=512, overlap=0.5, window="hamming")
    assert result.segment_length == 512
    assert result.overlap == 0.5
    assert result.window_kind == "hamming"
    assert result.segment_count == len(segment_starts(N, 512, 0.5))


def test_density_is_never_negative() -> None:
    rng = np.random.default_rng(11)
    result = welch_psd(rng.normal(size=N), FS)
    assert np.all(result.density >= 0.0)


# --------------------------------------------------------------------------- #
# entegre güç referansla eşleşir
# --------------------------------------------------------------------------- #


def test_integrated_power_of_a_tone_is_half_the_squared_amplitude() -> None:
    amp = 3.0
    # Tek parça, tam periyot: değer tam olarak A^2/2.
    result = welch_psd(_tone(amp, 50.0, 1_000), FS, segment_length=1_000, overlap=0.0)
    assert abs(result.integrated_power - amp**2 / 2.0) < 1e-9


@pytest.mark.parametrize("window", ALL_WINDOWS)
def test_integrated_power_is_window_independent(window: WindowKind) -> None:
    amp = 2.0
    result = welch_psd(
        _tone(amp, 50.0, 1_000), FS, segment_length=1_000, overlap=0.0, window=window
    )
    assert abs(result.integrated_power - amp**2 / 2.0) < 1e-9


def test_integrated_power_of_a_constant_is_its_square() -> None:
    result = welch_psd(np.full(1_000, 2.5), FS, segment_length=1_000, overlap=0.0)
    assert abs(result.integrated_power - 6.25) < 1e-9


def test_integrated_power_of_two_tones_adds_up() -> None:
    signal = _tone(1.0, 50.0, 1_000) + _tone(2.0, 150.0, 1_000)
    result = welch_psd(signal, FS, segment_length=1_000, overlap=0.0)
    expected = 1.0**2 / 2.0 + 2.0**2 / 2.0
    assert abs(result.integrated_power - expected) < 1e-9


def test_integrated_power_of_white_noise_matches_its_variance() -> None:
    rng = np.random.default_rng(4)
    sigma = 1.5
    noise = rng.normal(scale=sigma, size=200_000)
    result = welch_psd(noise, FS, segment_length=1_024, overlap=0.5)
    assert abs(result.integrated_power - sigma**2) < 0.05 * sigma**2


def test_averaging_over_segments_keeps_the_power() -> None:
    single = welch_psd(_tone(2.0, 60.0, 1_000), FS, segment_length=1_000, overlap=0.0)
    averaged = welch_psd(_tone(2.0, 60.0), FS, segment_length=500, overlap=0.5)
    assert abs(averaged.integrated_power - single.integrated_power) < 1e-6
    assert averaged.segment_count > single.segment_count


# --------------------------------------------------------------------------- #
# yoğunluk referansla eşleşir
# --------------------------------------------------------------------------- #


def test_a_tone_peaks_at_its_frequency() -> None:
    result = welch_psd(_tone(1.0, 120.0), FS, segment_length=1_000, overlap=0.0)
    assert abs(result.peak_frequency_hz - 120.0) < 1e-9


@pytest.mark.parametrize("window", ALL_WINDOWS)
def test_peak_density_follows_the_window_enbw(window: WindowKind) -> None:
    # Tek bir ton için: P_peak * ENBW * df == A^2 / 2.
    amp = 1.0
    length = 1_000
    result = welch_psd(
        _tone(amp, 100.0, length), FS, segment_length=length, overlap=0.0, window=window
    )
    enbw = equivalent_noise_bandwidth(window_values(window, length))
    assert abs(enbw - REFERENCE_ENBW[window]) < 1e-12
    recovered = result.peak_density * enbw * result.resolution_hz
    assert abs(recovered - amp**2 / 2.0) < 1e-6


def test_white_noise_density_is_flat_at_twice_the_variance_over_fs() -> None:
    rng = np.random.default_rng(9)
    sigma = 1.0
    noise = rng.normal(scale=sigma, size=400_000)
    result = welch_psd(noise, FS, segment_length=1_024, overlap=0.5)
    expected = 2.0 * sigma**2 / FS  # tek taraflı: varyans / (fs/2)
    interior = result.density[10:-10]
    assert abs(float(np.mean(interior)) - expected) < 0.05 * expected


def test_detrend_removes_the_dc_bin_without_touching_a_tone() -> None:
    signal = 5.0 + _tone(1.0, 80.0, 1_000)
    plain = welch_psd(signal, FS, segment_length=1_000, overlap=0.0)
    detrended = welch_psd(signal, FS, segment_length=1_000, overlap=0.0, detrend=True)

    assert plain.density[0] > 0.0
    assert detrended.density[0] < 1e-9
    assert abs(detrended.integrated_power - 0.5) < 1e-6  # yalnız ton kaldı


# --------------------------------------------------------------------------- #
# dB dönüşümü (10 log10)
# --------------------------------------------------------------------------- #


def test_power_to_db_uses_10log10() -> None:
    db = power_to_db(np.array([1.0, 0.1, 0.01, 100.0]))
    assert abs(db[0]) < 1e-12
    assert abs(db[1] + 10.0) < 1e-12
    assert abs(db[2] + 20.0) < 1e-12
    assert abs(db[3] - 20.0) < 1e-12


def test_zero_power_stops_at_the_floor() -> None:
    db = power_to_db(np.array([0.0]), floor_db=-150.0)
    assert db[0] == -150.0
    assert np.isfinite(db).all()


def test_nan_power_stays_nan() -> None:
    db = power_to_db(np.array([np.nan, 1.0]))
    assert np.isnan(db[0])
    assert abs(db[1]) < 1e-12


def test_negative_power_is_rejected() -> None:
    with pytest.raises(PsdError, match="negatif"):
        power_to_db(np.array([-1.0]))


def test_nonpositive_db_reference_is_rejected() -> None:
    with pytest.raises(PsdError, match="referansı"):
        power_to_db(np.array([1.0]), reference=0.0)


# --------------------------------------------------------------------------- #
# hata yolları (kapsamlısı F4-044)
# --------------------------------------------------------------------------- #


def test_empty_signal_is_rejected() -> None:
    with pytest.raises(PsdError, match="boş sinyal"):
        welch_psd(np.empty(0, dtype=np.float64), FS)


def test_a_segment_longer_than_the_signal_is_rejected() -> None:
    with pytest.raises(PsdError, match="uzun olamaz"):
        welch_psd(np.zeros(100), FS, segment_length=256)


def test_input_is_not_mutated() -> None:
    signal = _tone(1.0, 50.0)
    snapshot = signal.copy()
    welch_psd(signal, FS, detrend=True)
    assert np.array_equal(signal, snapshot)

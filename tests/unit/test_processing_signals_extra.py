"""Noise, chirp ve impulse üreteçleri — `F1-019`."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.processing.signals import chirp, impulse, noise


def test_noise_same_seed_is_identical() -> None:
    first = noise("ch0", 1000.0, 0.5, seed=42)
    second = noise("ch0", 1000.0, 0.5, seed=42)
    assert np.array_equal(first.values, second.values)
    assert first.values.tobytes() == second.values.tobytes()


def test_noise_different_seed_differs() -> None:
    first = noise("ch0", 1000.0, 0.5, seed=1)
    second = noise("ch0", 1000.0, 0.5, seed=2)
    assert not np.array_equal(first.values, second.values)


def test_noise_sample_count_and_duration() -> None:
    chunk = noise("ch0", 8000.0, 0.25, seed=0)
    assert len(chunk) == 2000
    assert chunk.timestamps_ns[0] == 0
    assert chunk.end_ns == (1999 * 1_000_000_000) // 8000


def test_noise_amplitude_scales_spread() -> None:
    small = noise("ch0", 4000.0, 1.0, amplitude=1.0, seed=7)
    large = noise("ch0", 4000.0, 1.0, amplitude=10.0, seed=7)
    assert float(large.values.std()) > float(small.values.std()) * 5


def test_noise_rejects_negative_amplitude() -> None:
    with pytest.raises(ValueError, match="Genlik negatif"):
        noise("ch0", 1000.0, 0.1, amplitude=-1.0)


def test_chirp_sample_count_and_duration() -> None:
    chunk = chirp("ch0", 8000.0, 0.5, start_hz=100.0, end_hz=1000.0)
    assert len(chunk) == 4000
    assert chunk.values.dtype == np.float32


def test_chirp_is_deterministic() -> None:
    first = chirp("ch0", 8000.0, 0.5, start_hz=100.0, end_hz=1000.0)
    second = chirp("ch0", 8000.0, 0.5, start_hz=100.0, end_hz=1000.0)
    assert first.values.tobytes() == second.values.tobytes()


def test_chirp_frequency_sweeps_upward() -> None:
    """İlk yarının baskın frekansı ikinci yarınınkinden düşük olmalı."""
    rate = 8000.0
    chunk = chirp("ch0", rate, 1.0, start_hz=200.0, end_hz=2000.0)
    values = chunk.values.astype(np.float64)
    half = values.size // 2

    def peak_hz(segment: NDArray[np.float64]) -> float:
        spectrum = np.abs(np.fft.rfft(segment))
        return float(np.argmax(spectrum)) * rate / segment.size

    first_half = peak_hz(values[:half])
    second_half = peak_hz(values[half:])
    assert first_half < second_half
    assert 200.0 <= first_half <= 1100.0
    assert 1100.0 <= second_half <= 2000.0


def test_chirp_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="Frekanslar pozitif"):
        chirp("ch0", 8000.0, 1.0, start_hz=0.0, end_hz=100.0)
    with pytest.raises(ValueError, match="Nyquist"):
        chirp("ch0", 1000.0, 1.0, start_hz=100.0, end_hz=900.0)
    with pytest.raises(ValueError, match="suresi pozitif"):
        chirp("ch0", 1000.0, 0.0, start_hz=10.0, end_hz=100.0)


def test_impulse_positions_and_zeros() -> None:
    chunk = impulse("ch0", 1000.0, 1.0, positions_s=[0.1, 0.5], amplitude=3.0)
    assert len(chunk) == 1000
    assert float(chunk.values[100]) == 3.0
    assert float(chunk.values[500]) == 3.0
    assert float(np.count_nonzero(chunk.values)) == 2


def test_impulse_is_narrow() -> None:
    """Darbe tek örneklik olmalı; komşuları sıfır kalmalı."""
    chunk = impulse("ch0", 1000.0, 0.5, positions_s=[0.25])
    assert float(chunk.values[249]) == 0.0
    assert float(chunk.values[250]) == 1.0
    assert float(chunk.values[251]) == 0.0


def test_impulse_empty_positions_gives_silence() -> None:
    chunk = impulse("ch0", 1000.0, 0.1, positions_s=[])
    assert len(chunk) == 100
    assert not np.any(chunk.values)


def test_impulse_rejects_out_of_range_position() -> None:
    with pytest.raises(ValueError, match="sinyal disinda"):
        impulse("ch0", 1000.0, 0.1, positions_s=[0.5])
    with pytest.raises(ValueError, match="negatif olamaz"):
        impulse("ch0", 1000.0, 0.1, positions_s=[-0.01])


def test_all_generators_share_time_axis() -> None:
    """Aynı hız ve süre için üç üretecin zaman ekseni birebir aynı olmalı."""
    rate, duration = 2000.0, 0.5
    axes = [
        noise("ch0", rate, duration, seed=0).timestamps_ns,
        chirp("ch0", rate, duration, start_hz=50.0, end_hz=500.0).timestamps_ns,
        impulse("ch0", rate, duration, positions_s=[0.1]).timestamps_ns,
    ]
    assert np.array_equal(axes[0], axes[1])
    assert np.array_equal(axes[1], axes[2])
    assert axes[0].size == 1000

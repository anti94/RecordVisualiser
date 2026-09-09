"""Deterministik sinüs üreteci testleri — `F1-018`."""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.processing.signals import (
    NS_PER_SECOND,
    sample_count,
    sine,
    time_axis,
)


def test_sample_count() -> None:
    assert sample_count(96000.0, 1.0) == 96000
    assert sample_count(8.0, 1.0) == 8
    assert sample_count(8.0, 0.125) == 1
    assert sample_count(1000.0, 0.0) == 0


@pytest.mark.parametrize(
    ("rate", "duration", "expected"),
    [(0.0, 1.0, "pozitif olmali"), (-1.0, 1.0, "pozitif olmali"), (10.0, -1.0, "negatif olamaz")],
)
def test_sample_count_rejects_invalid(rate: float, duration: float, expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        sample_count(rate, duration)


def test_time_axis_is_integer_and_evenly_spaced() -> None:
    stamps = time_axis(8.0, 1.0)
    assert stamps.dtype == np.int64
    assert stamps.size == 8
    assert stamps[0] == 0
    assert stamps[1] == 125_000_000
    assert stamps[-1] == 875_000_000
    assert np.all(np.diff(stamps) == 125_000_000)


def test_time_axis_respects_start() -> None:
    stamps = time_axis(8.0, 0.5, start_ns=1_000_000_000)
    assert stamps[0] == 1_000_000_000
    assert stamps.size == 4


def test_time_axis_does_not_accumulate_error() -> None:
    """Uzun dizide son örneğin konumu tam olmalı."""
    rate = 96000.0
    stamps = time_axis(rate, 10.0)
    assert stamps.size == 960_000
    expected_last = ((stamps.size - 1) * NS_PER_SECOND) // int(rate)
    assert stamps[-1] == expected_last


def test_sine_is_deterministic() -> None:
    """Aynı parametreler bit düzeyinde aynı diziyi üretmeli."""
    first = sine("ch0", 8000.0, 0.5, frequency_hz=100.0)
    second = sine("ch0", 8000.0, 0.5, frequency_hz=100.0)

    assert np.array_equal(first.timestamps_ns, second.timestamps_ns)
    assert np.array_equal(first.values, second.values)
    assert first.values.tobytes() == second.values.tobytes()


def test_sine_sample_count_and_dtype() -> None:
    chunk = sine("ch0", 96000.0, 0.25, frequency_hz=5000.0)
    assert len(chunk) == 24000
    assert chunk.values.dtype == np.float32
    assert chunk.timestamps_ns.dtype == np.int64


def test_sine_amplitude_and_offset() -> None:
    chunk = sine("ch0", 1000.0, 1.0, frequency_hz=1.0, amplitude=3.0, offset=10.0)
    assert float(chunk.values.max()) <= 13.0 + 1e-5
    assert float(chunk.values.min()) >= 7.0 - 1e-5
    assert 9.9 < float(chunk.values.mean()) < 10.1


def test_sine_phase_shift() -> None:
    """90 derece faz kaymış sinüs kosinüs olur: ilk örnek tepe değeridir."""
    chunk = sine("ch0", 1000.0, 0.01, frequency_hz=10.0, phase_rad=float(np.pi / 2))
    assert abs(float(chunk.values[0]) - 1.0) < 1e-6


def test_sine_frequency_is_correct() -> None:
    """FFT tepesi istenen frekansta olmalı."""
    rate, freq = 8000.0, 250.0
    chunk = sine("ch0", rate, 1.0, frequency_hz=freq)
    spectrum = np.abs(np.fft.rfft(chunk.values.astype(np.float64)))
    peak_bin = int(np.argmax(spectrum))
    peak_hz = peak_bin * rate / chunk.values.size
    assert abs(peak_hz - freq) <= 1.0


def test_sine_rejects_frequency_above_nyquist() -> None:
    with pytest.raises(ValueError, match="Nyquist"):
        sine("ch0", 1000.0, 1.0, frequency_hz=600.0)


def test_sine_rejects_non_positive_frequency() -> None:
    with pytest.raises(ValueError, match="Frekans pozitif"):
        sine("ch0", 1000.0, 1.0, frequency_hz=0.0)


def test_sine_produces_valid_chunk() -> None:
    chunk = sine("ch0", 8.0, 1.0, frequency_hz=1.0, start_ns=500)
    assert chunk.channel_id == "ch0"
    assert chunk.is_monotonic
    assert chunk.start_ns == 500

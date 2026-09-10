"""Profil B blok içi örnek zamanları — `F4-012`.

Kabul: 6000 örnek 125 ms aralığı kapsar; blok sınırında örnek tekrarı
olmaz.
"""

from __future__ import annotations

import numpy as np
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.io.decoders.profile_b_timing import (
    NS_PER_SECOND,
    block_sample_times_ns,
    block_span_ns,
    channel_sample_times_ns,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_CHANNEL_IDS,
    RECORD_PERIOD_NS,
    SAMPLES_PER_BLOCK,
)


def test_a_6000_sample_block_covers_exactly_125ms() -> None:
    times = block_sample_times_ns(0, SAMPLES_PER_BLOCK)
    assert times.shape == (6000,)
    assert times.dtype == np.int64
    assert times[0] == 0
    # Yarı-açık: son örnek 125 ms'nin ALTINDA.
    assert times[-1] < RECORD_PERIOD_NS
    # Bir örnek daha eklense tam 125 ms olurdu.
    assert block_span_ns(SAMPLES_PER_BLOCK) == RECORD_PERIOD_NS == 125_000_000


def test_sample_times_are_strictly_increasing_within_a_block() -> None:
    times = block_sample_times_ns(1_000, SAMPLES_PER_BLOCK)
    assert np.all(np.diff(times) > 0)
    # Adım ~1/48000 s ≈ 20833 ns (tam sayı bölme nedeniyle 20833 veya 20834).
    steps = np.unique(np.diff(times))
    assert set(steps.tolist()) <= {20833, 20834}


def test_no_repeat_at_the_block_boundary() -> None:
    first = block_sample_times_ns(0, SAMPLES_PER_BLOCK)
    second = block_sample_times_ns(RECORD_PERIOD_NS, SAMPLES_PER_BLOCK)
    # İkinci bloğun ilk örneği, birinci bloğun son örneğinden KESİNLİKLE büyük.
    assert second[0] > first[-1]
    # Aradaki boşluk yaklaşık bir örnek periyodu (tekrar değil).
    gap = int(second[0] - first[-1])
    assert 20000 < gap < 21000


def test_offset_shifts_the_whole_block() -> None:
    base = block_sample_times_ns(0, 10)
    shifted = block_sample_times_ns(7_777, 10)
    assert np.array_equal(shifted - 7_777, base)


def test_empty_block_yields_empty_times() -> None:
    assert block_sample_times_ns(123, 0).shape == (0,)


def test_channel_times_over_the_fixture_span_one_second_without_repeats() -> None:
    data = build_acoustic_fixture(8)
    for channel_id in ACOUSTIC_CHANNEL_IDS:
        times = channel_sample_times_ns(data, channel_id)
        assert times.shape == (8 * SAMPLES_PER_BLOCK,)  # 48000 örnek
        # Kesinlikle monoton artan: hiçbir blok sınırında tekrar yok.
        assert np.all(np.diff(times) > 0)
        # Toplam süre ~1 saniye (8 × 125 ms), son örnek 1 s'nin altında.
        t0 = int(times[0])
        assert times[-1] - t0 < NS_PER_SECOND
        assert 8 * RECORD_PERIOD_NS == NS_PER_SECOND


def test_record_boundaries_land_on_the_125ms_grid() -> None:
    data = build_acoustic_fixture(4)
    times = channel_sample_times_ns(data, 0)
    t0 = int(times[0])
    # Her 6000. örnek yeni kaydın başlangıcı = tam k*125 ms.
    for k in range(4):
        assert int(times[k * SAMPLES_PER_BLOCK]) - t0 == k * RECORD_PERIOD_NS

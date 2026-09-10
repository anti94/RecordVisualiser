"""Profil B akustik blokları zaman sorgusuna bağlama — `F4-013`.

Kabul: bloklar arası seçim doğru örnek aralığını döndürür.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b import channel_samples
from sonar_analyzer.io.decoders.profile_b_query import (
    acoustic_recording_span,
    query_acoustic_channel,
)
from sonar_analyzer.io.decoders.profile_b_timing import channel_sample_times_ns
from sonar_analyzer.io.profile_b_format import RECORD_PERIOD_NS, SAMPLES_PER_BLOCK

FIXTURE = build_acoustic_fixture(8)
CH = 0

#: `channel_sample_times_ns` ile aynı ankor + zamanlar (referans dilimleme için).
_TIMES = channel_sample_times_ns(FIXTURE, CH)
_SAMPLES = channel_samples(FIXTURE, CH)


def _reference_slice(start_ns: int, end_ns: int) -> tuple[NDArray[np.int64], NDArray[np.generic]]:
    mask = (start_ns <= _TIMES) & (end_ns > _TIMES)
    return _TIMES[mask], _SAMPLES[mask]


def test_full_span_returns_every_sample() -> None:
    span = acoustic_recording_span(FIXTURE, CH)
    assert span is not None
    chunk = query_acoustic_channel(FIXTURE, CH, span)
    assert len(chunk) == 8 * SAMPLES_PER_BLOCK == 48_000
    assert np.array_equal(chunk.timestamps_ns, _TIMES)
    assert np.array_equal(chunk.values, _SAMPLES.astype(np.float64))
    assert chunk.timestamps_ns.dtype == np.int64
    assert chunk.channel_id == "0"


def test_selection_crossing_a_record_boundary_returns_the_exact_slice() -> None:
    t0 = int(_TIMES[0])
    # Kayıt 2'nin ortasından kayıt 3'ün ortasına: iki bloğu birden keser.
    start = t0 + 2 * RECORD_PERIOD_NS + 40_000_000  # +40 ms into record 2
    end = t0 + 3 * RECORD_PERIOD_NS + 40_000_000  # +40 ms into record 3
    chunk = query_acoustic_channel(FIXTURE, CH, TimeRange(start, end))

    ref_times, ref_values = _reference_slice(start, end)
    assert np.array_equal(chunk.timestamps_ns, ref_times)
    assert np.array_equal(chunk.values, ref_values.astype(np.float64))
    # Pencere yaklaşık 125 ms; ~6000 örnek beklenir.
    assert abs(len(chunk) - SAMPLES_PER_BLOCK) <= 1
    # Yarı-açık: tüm zamanlar [start, end) içinde.
    assert chunk.timestamps_ns[0] >= start
    assert chunk.timestamps_ns[-1] < end


def test_boundary_selection_has_no_gap_or_overlap() -> None:
    """Bir kaydın sonu + sonraki kaydın başı: ardışık örnekler, atlama/tekrar yok."""
    t0 = int(_TIMES[0])
    boundary = t0 + 4 * RECORD_PERIOD_NS  # kayıt 3 -> 4 sınırı
    chunk = query_acoustic_channel(FIXTURE, CH, TimeRange(boundary - 30_000, boundary + 30_000))
    diffs = np.diff(chunk.timestamps_ns)
    assert np.all(diffs > 0)  # kesin artan
    assert np.all(diffs < 21_000)  # her adım ~bir örnek periyodu — sınırda boşluk yok
    # Sınırın hemen solundaki ve sağındaki örnek ardışık.
    left = chunk.timestamps_ns[chunk.timestamps_ns < boundary]
    right = chunk.timestamps_ns[chunk.timestamps_ns >= boundary]
    assert left.size and right.size
    assert 0 < int(right[0] - left[-1]) < 21_000


def test_window_outside_the_recording_is_empty_but_valid() -> None:
    span = acoustic_recording_span(FIXTURE, CH)
    assert span is not None
    after = TimeRange(span.end_ns + 1_000, span.end_ns + 2_000)
    chunk = query_acoustic_channel(FIXTURE, CH, after)
    assert len(chunk) == 0
    assert chunk.timestamps_ns.shape == (0,)
    assert chunk.values.shape == (0,)


def test_zero_width_window_is_empty() -> None:
    t0 = int(_TIMES[0])
    chunk = query_acoustic_channel(FIXTURE, CH, TimeRange(t0 + 1_000_000, t0 + 1_000_000))
    assert len(chunk) == 0


def test_each_channel_can_be_queried_independently() -> None:
    span = acoustic_recording_span(FIXTURE, 2)
    assert span is not None
    narrow = TimeRange(span.start_ns, span.start_ns + 10_000_000)  # ilk 10 ms
    chunk = query_acoustic_channel(FIXTURE, 2, narrow)
    ref_times = channel_sample_times_ns(FIXTURE, 2)
    ref_vals = channel_samples(FIXTURE, 2)
    mask = (ref_times >= narrow.start_ns) & (ref_times < narrow.end_ns)
    assert np.array_equal(chunk.timestamps_ns, ref_times[mask])
    assert np.array_equal(chunk.values, ref_vals[mask].astype(np.float64))

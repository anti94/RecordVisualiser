"""Çizim penceresi önbelleği bellek sınırlı — `F4-059`.

Kabul: bütçe aşılınca eski girdiler çıkar; ölçülen kullanım raporlanır.

Burada `DisplayQuery`'nin gerçek kullanımı denetlenir: aynı pencereye
dönmek yeniden decode ettirmez, bütçe küçükse eski pencereler çıkar ve
`cache_stats()` ölçülen kullanımı raporlar.
"""

from __future__ import annotations

import numpy as np

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.display_query import DisplayQuery, ViewportSummary

PERIOD_NS = 1_000_000
POINTS = 4_000
BUDGET = 256


class _CountingReader:
    """`DisplayQuery`'nin decode çağrılarını sayan sahte okuyucu."""

    def __init__(self) -> None:
        self.calls: list[TimeRange] = []

    def __call__(self, channel_id: str, span: TimeRange) -> DataChunk:
        self.calls.append(span)
        times = np.arange(0, POINTS, dtype=np.int64) * PERIOD_NS
        mask = (times >= span.start_ns) & (times < span.end_ns)
        return DataChunk(
            channel_id,
            times[mask],
            np.sin(times[mask] / 1e8).astype(np.float64),
        )


def _span(start_index: int, stop_index: int) -> TimeRange:
    return TimeRange(start_index * PERIOD_NS, stop_index * PERIOD_NS)


# --------------------------------------------------------------------------- #
# aynı pencere yeniden decode edilmez
# --------------------------------------------------------------------------- #


def test_a_repeated_window_is_served_from_the_cache() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, POINTS), BUDGET)
    query.query("ch0", _span(0, POINTS), BUDGET)

    assert len(reader.calls) == 1
    assert query.cache_stats().hits >= 1


def test_a_zoom_inside_a_cached_window_is_not_decoded_again() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, POINTS), BUDGET)
    inner = query.query("ch0", _span(100, 200), BUDGET)

    assert len(reader.calls) == 1
    assert len(inner) > 0


def test_a_window_outside_the_cached_one_is_decoded() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, 100), BUDGET)
    query.query("ch0", _span(200, 300), BUDGET)

    assert len(reader.calls) == 2


def test_another_channel_is_decoded_separately() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, POINTS), BUDGET)
    query.query("ch1", _span(0, POINTS), BUDGET)

    assert len(reader.calls) == 2


def test_returning_to_an_earlier_window_still_hits() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, 500), BUDGET)
    query.query("ch0", _span(1_000, 1_500), BUDGET)
    query.query("ch0", _span(0, 500), BUDGET)  # geri dönüş

    assert len(reader.calls) == 2  # üçüncüsü önbellekten geldi


def test_clear_forces_a_fresh_decode() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, POINTS), BUDGET)
    query.clear()
    query.query("ch0", _span(0, POINTS), BUDGET)

    assert len(reader.calls) == 2
    assert query.cache_stats().entries == 1


# --------------------------------------------------------------------------- #
# bütçe aşılınca eski girdiler çıkar
# --------------------------------------------------------------------------- #


def _summary_bytes() -> int:
    reader = _CountingReader()
    return ViewportSummary(reader("ch0", _span(0, 500))).nbytes


def test_a_tight_budget_evicts_older_windows() -> None:
    single = _summary_bytes()
    reader = _CountingReader()
    # İki pencere sığmayacak kadar dar bir bütçe.
    query = DisplayQuery(reader, max_bytes=int(single * 1.5))

    query.query("ch0", _span(0, 500), BUDGET)
    query.query("ch0", _span(1_000, 1_500), BUDGET)

    stats = query.cache_stats()
    assert stats.entries == 1
    assert stats.evictions >= 1
    assert stats.used_bytes <= stats.max_bytes


def test_the_budget_is_never_exceeded_while_browsing() -> None:
    single = _summary_bytes()
    reader = _CountingReader()
    query = DisplayQuery(reader, max_bytes=int(single * 2.5))

    for index in range(20):
        query.query("ch0", _span(index * 100, index * 100 + 500), BUDGET)
        stats = query.cache_stats()
        assert stats.used_bytes <= stats.max_bytes

    assert query.cache_stats().evictions > 0


def test_an_evicted_window_is_decoded_again() -> None:
    single = _summary_bytes()
    reader = _CountingReader()
    query = DisplayQuery(reader, max_bytes=int(single * 1.5))

    query.query("ch0", _span(0, 500), BUDGET)
    query.query("ch0", _span(1_000, 1_500), BUDGET)  # ilkini çıkarır
    query.query("ch0", _span(0, 500), BUDGET)  # yeniden decode

    assert len(reader.calls) == 3


# --------------------------------------------------------------------------- #
# ölçülen kullanım raporlanır
# --------------------------------------------------------------------------- #


def test_the_stats_report_real_measured_bytes() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    query.query("ch0", _span(0, 500), BUDGET)

    stats = query.cache_stats()
    assert stats.entries == 1
    assert stats.used_bytes == _summary_bytes()
    assert stats.used_bytes > 0
    assert 0.0 < stats.usage_ratio <= 1.0


def test_the_stats_describe_themselves() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)
    query.query("ch0", _span(0, 500), BUDGET)
    query.query("ch0", _span(0, 500), BUDGET)

    text = query.cache_stats().describe()
    assert "girdi" in text
    assert "isabet" in text


def test_a_full_resolution_query_bypasses_the_cache() -> None:
    reader = _CountingReader()
    query = DisplayQuery(reader)

    # max_points None: tam analiz sorgusu — özet de önbellek de kullanılmaz.
    query.query("ch0", _span(0, POINTS), None)
    query.query("ch0", _span(0, POINTS), None)

    assert len(reader.calls) == 2
    assert query.cache_stats().entries == 0

"""Yakın tekrar olaylarını gruplama — `F3-049`.

Kabul: grup sayısı ve açılan ayrıntılar özgün olayları korur.
"""

from __future__ import annotations

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import group_near_events

MS = 1_000_000


def _ev(t_ms: int, code: str = "THERMAL", source: str = "BIT", message: str = "repeat") -> Event:
    return Event(
        timestamp_ns=t_ms * MS,
        source=source,
        category="BIT",
        severity=Severity.WARNING,
        code=code,
        message=message,
    )


def test_a_burst_of_repeats_collapses_to_one_group() -> None:
    burst = [_ev(1000), _ev(1050), _ev(1100)]

    groups = group_near_events(burst, window_ns=200 * MS)

    assert len(groups) == 1
    assert groups[0].count == 3
    assert groups[0].is_group
    assert groups[0].representative is burst[0]
    # ozgun olaylar hic degistirilmeden, sirayla korunur
    assert list(groups[0].events) == burst


def test_events_further_apart_than_the_window_stay_separate() -> None:
    groups = group_near_events([_ev(1000), _ev(1300)], window_ns=200 * MS)

    assert [g.count for g in groups] == [1, 1]
    assert all(not g.is_group for g in groups)


def test_different_kinds_within_the_window_are_not_grouped() -> None:
    groups = group_near_events(
        [_ev(1000, code="THERMAL"), _ev(1050, code="VOLTAGE")], window_ns=200 * MS
    )

    assert [g.count for g in groups] == [1, 1]


def test_same_kind_false_groups_purely_by_time() -> None:
    groups = group_near_events(
        [_ev(1000, code="A"), _ev(1050, code="B")], window_ns=200 * MS, same_kind=False
    )

    assert len(groups) == 1
    assert groups[0].count == 2


def test_unsorted_input_is_ordered_within_the_group() -> None:
    groups = group_near_events([_ev(1100), _ev(1000), _ev(1050)], window_ns=200 * MS)

    assert len(groups) == 1
    assert [e.timestamp_ns for e in groups[0].events] == [1000 * MS, 1050 * MS, 1100 * MS]


def test_no_event_is_lost_across_all_groups() -> None:
    events = [_ev(0), _ev(30), _ev(60), _ev(1000), _ev(1030), _ev(5000)]

    groups = group_near_events(events, window_ns=100 * MS)

    assert sum(g.count for g in groups) == len(events)
    flat = [e for g in groups for e in g.events]
    assert sorted(flat, key=lambda e: e.timestamp_ns) == sorted(
        events, key=lambda e: e.timestamp_ns
    )


def test_empty_input_yields_no_groups() -> None:
    assert group_near_events([]) == []


def test_single_event_is_a_one_member_group() -> None:
    groups = group_near_events([_ev(1000)])

    assert len(groups) == 1
    assert groups[0].count == 1
    assert not groups[0].is_group
    assert groups[0].span_ns == 0

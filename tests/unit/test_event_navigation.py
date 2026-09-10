"""Zamana ve komşu olaya gitme — `F3-059`.

Kabul: sınır dışı zaman güvenli sınırlanır; olay sırası korunur.
"""

from __future__ import annotations

from sonar_analyzer.application.event_navigation import (
    clamp_time_ns,
    next_event,
    previous_event,
)
from sonar_analyzer.domain.event import Event, Severity

SECOND = 1_000_000_000


def _ev(t_s: float) -> Event:
    return Event(
        timestamp_ns=int(t_s * SECOND),
        source="BIT",
        category="BIT",
        severity=Severity.INFO,
        code="X",
        message=f"olay @ {t_s}",
    )


# -- clamp_time_ns --------------------------------------------------


def test_clamp_keeps_an_in_range_time_unchanged() -> None:
    assert clamp_time_ns(5 * SECOND, 0, 10 * SECOND) == 5 * SECOND


def test_clamp_pulls_a_time_before_the_start_up_to_the_start() -> None:
    assert clamp_time_ns(-3 * SECOND, 2 * SECOND, 10 * SECOND) == 2 * SECOND


def test_clamp_pulls_a_time_after_the_end_down_to_the_end() -> None:
    assert clamp_time_ns(99 * SECOND, 0, 10 * SECOND) == 10 * SECOND


def test_clamp_tolerates_a_reversed_range() -> None:
    assert clamp_time_ns(5 * SECOND, 10 * SECOND, 0) == 5 * SECOND
    assert clamp_time_ns(-1, 10 * SECOND, 0) == 0
    assert clamp_time_ns(99 * SECOND, 10 * SECOND, 0) == 10 * SECOND


def test_clamp_on_boundaries_is_inclusive() -> None:
    assert clamp_time_ns(0, 0, 10 * SECOND) == 0
    assert clamp_time_ns(10 * SECOND, 0, 10 * SECOND) == 10 * SECOND


# -- previous_event / next_event ----------------------------------

EVENTS = [_ev(1.0), _ev(2.5), _ev(2.5), _ev(4.0)]


def test_next_event_is_strictly_after_the_reference() -> None:
    result = next_event(EVENTS, int(2.5 * SECOND))
    assert result is not None
    assert result.timestamp_ns == int(4.0 * SECOND)


def test_previous_event_is_strictly_before_the_reference() -> None:
    result = previous_event(EVENTS, int(2.5 * SECOND))
    assert result is not None
    assert result.timestamp_ns == int(1.0 * SECOND)


def test_next_event_returns_none_past_the_last_event() -> None:
    assert next_event(EVENTS, int(4.0 * SECOND)) is None
    assert next_event(EVENTS, int(9.0 * SECOND)) is None


def test_previous_event_returns_none_before_the_first_event() -> None:
    assert previous_event(EVENTS, int(1.0 * SECOND)) is None
    assert previous_event(EVENTS, 0) is None


def test_navigation_orders_unsorted_input_chronologically() -> None:
    shuffled = [_ev(4.0), _ev(1.0), _ev(2.5), _ev(0.5)]
    # 1.5 s'ten ileri yürüyünce olaylar zaman sırasında gelir.
    seen: list[float] = []
    cursor = int(1.5 * SECOND)
    while True:
        nxt = next_event(shuffled, cursor)
        if nxt is None:
            break
        seen.append(nxt.timestamp_ns / SECOND)
        cursor = nxt.timestamp_ns
    assert seen == [2.5, 4.0]


def test_walking_back_and_forth_is_consistent() -> None:
    forward = next_event(EVENTS, int(1.0 * SECOND))
    assert forward is not None and forward.timestamp_ns == int(2.5 * SECOND)
    back = previous_event(EVENTS, forward.timestamp_ns)
    assert back is not None and back.timestamp_ns == int(1.0 * SECOND)


def test_empty_event_list_yields_none() -> None:
    assert next_event([], 0) is None
    assert previous_event([], 0) is None

"""Birleşik olay filtreleme — `F3-043`.

Kabul: zaman + severity + kaynak + metin ölçütlerinin birlikte (AND)
sonucu beklenen olay kümesidir.
"""

from __future__ import annotations

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import distinct_sources, filter_events

SECOND = 1_000_000_000


def _ev(t_s: float, source: str, severity: Severity, message: str) -> Event:
    return Event(
        timestamp_ns=int(t_s * SECOND),
        source=source,
        category="BIT",
        severity=severity,
        code="X",
        message=message,
    )


EVENTS = [
    _ev(0, "BIT", Severity.INFO, "power ok"),
    _ev(1, "BIT", Severity.ERROR, "thermal fail"),
    _ev(2, "Comms", Severity.WARNING, "link degraded"),
    _ev(3, "Comms", Severity.CRITICAL, "link fail"),
    _ev(4, "BIT", Severity.ERROR, "voltage fail"),
]


def _messages(events: list[Event]) -> list[str]:
    return [e.message for e in events]


def test_no_criteria_returns_everything() -> None:
    assert filter_events(EVENTS) == EVENTS


def test_source_filter_alone() -> None:
    assert _messages(filter_events(EVENTS, source="BIT")) == [
        "power ok",
        "thermal fail",
        "voltage fail",
    ]


def test_min_severity_filter_alone() -> None:
    assert _messages(filter_events(EVENTS, min_severity=Severity.ERROR)) == [
        "thermal fail",
        "link fail",
        "voltage fail",
    ]


def test_text_filter_is_case_insensitive_substring() -> None:
    assert _messages(filter_events(EVENTS, text="FAIL")) == [
        "thermal fail",
        "link fail",
        "voltage fail",
    ]


def test_time_window_is_inclusive_on_both_ends() -> None:
    windowed = filter_events(EVENTS, start_ns=1 * SECOND, end_ns=3 * SECOND)
    assert _messages(windowed) == ["thermal fail", "link degraded", "link fail"]


def test_all_four_criteria_combine_with_and() -> None:
    result = filter_events(
        EVENTS,
        start_ns=0,
        end_ns=3 * SECOND,
        min_severity=Severity.ERROR,
        source="BIT",
        text="fail",
    )
    assert _messages(result) == ["thermal fail"]


def test_combination_with_no_match_is_empty() -> None:
    assert filter_events(EVENTS, source="Comms", min_severity=Severity.ERROR, text="thermal") == []


def test_distinct_sources_preserves_first_seen_order() -> None:
    assert distinct_sources(EVENTS) == ["BIT", "Comms"]

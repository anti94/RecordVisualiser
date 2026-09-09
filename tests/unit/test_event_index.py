"""Olay indeksini oluşturma — `F2-029`.

Kabul: severity özeti referans sayıları verir.
"""

from __future__ import annotations

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.io.index.event_index import EventIndex, build_event_index


def _event(severity: Severity, code: str) -> Event:
    return Event(
        timestamp_ns=0,
        source="parser",
        category="test",
        severity=severity,
        code=code,
        message=f"test olay {code}",
    )


def test_severity_summary_gives_reference_counts() -> None:
    """Kabul kriteri: severity özeti referans sayıları verir."""
    events = [
        _event(Severity.WARNING, "1"),
        _event(Severity.WARNING, "2"),
        _event(Severity.WARNING, "3"),
        _event(Severity.ERROR, "4"),
        _event(Severity.ERROR, "5"),
        _event(Severity.INFO, "6"),
    ]

    index = build_event_index(events)

    assert index.total_count == 6
    assert index.count_for(Severity.WARNING) == 3
    assert index.count_for(Severity.ERROR) == 2
    assert index.count_for(Severity.INFO) == 1
    assert index.count_for(Severity.CRITICAL) == 0


def test_empty_event_list_gives_zero_counts() -> None:
    index = build_event_index([])
    assert index.total_count == 0
    assert index.count_for(Severity.ERROR) == 0


def test_single_severity_events_all_counted_together() -> None:
    events = [_event(Severity.ERROR, str(i)) for i in range(5)]
    index = build_event_index(events)
    assert index.count_for(Severity.ERROR) == 5
    assert index.total_count == 5


def test_event_index_is_immutable() -> None:
    import dataclasses

    import pytest

    index = EventIndex(total_count=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        index.total_count = 1  # type: ignore[misc]

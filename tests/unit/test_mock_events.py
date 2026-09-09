"""Sahte BIT, TX ve sistem olayları — `F1-021`.

Kabul: **bilinen zamanlarda** PASS/FAIL ve TX geçişleri oluşur. Bu yüzden her
test somut bir saniye değeri kontrol eder; "en az bir olay var" gibi belirsiz
bir iddia yeterli değildir.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.event import BitState, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TxState
from sonar_analyzer.repository.mock_repository import (
    BIT_COMPONENTS,
    MockEventSchedule,
    MockRecordingRepository,
)
from sonar_analyzer.repository.protocol import EventFilter

SECOND = 1_000_000_000
SPAN = TimeRange(0, 10 * SECOND)


@pytest.fixture()
def repo() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=10.0)


# -- BIT ------------------------------------------------------------------


def test_bit_runs_once_per_second_for_every_component(repo: MockRecordingRepository) -> None:
    results = repo.bit_results(SPAN)
    assert len(results) == 10 * len(BIT_COMPONENTS)
    assert len(BIT_COMPONENTS) == 8, "mockup sekiz alt sistem gosteriyor"


def test_bit_timestamps_are_on_known_seconds(repo: MockRecordingRepository) -> None:
    seconds = sorted({r.timestamp_ns // SECOND for r in repo.bit_results(SPAN)})
    assert seconds == list(range(10))


def test_known_failure_at_four_seconds(repo: MockRecordingRepository) -> None:
    """Zamanlama tablosu 4.0 s'de Thermal Management FAIL diyor."""
    failures = [r for r in repo.bit_results(SPAN) if r.state is BitState.FAIL]

    assert len(failures) == 1
    failure = failures[0]
    assert failure.timestamp_ns == 4 * SECOND
    assert failure.component == "Thermal Management"
    assert failure.severity is Severity.ERROR
    assert failure.code == 0x0412


def test_all_other_results_pass(repo: MockRecordingRepository) -> None:
    results = repo.bit_results(SPAN)
    passing = [r for r in results if r.state is BitState.PASS]
    assert len(passing) == len(results) - 1
    assert all(r.severity is Severity.INFO for r in passing)


def test_bit_results_are_filtered_by_time(repo: MockRecordingRepository) -> None:
    early = repo.bit_results(TimeRange(0, 2 * SECOND))
    assert {r.timestamp_ns // SECOND for r in early} == {0, 1}
    assert all(r.state is BitState.PASS for r in early)

    around_failure = repo.bit_results(TimeRange(4 * SECOND, 5 * SECOND))
    assert any(r.state is BitState.FAIL for r in around_failure)


# -- TX -------------------------------------------------------------------


def test_transmission_intervals_are_at_known_times(repo: MockRecordingRepository) -> None:
    intervals = repo.transmissions(SPAN)
    bounds = [(i.start_ns, i.end_ns) for i in intervals]
    assert bounds == [
        (2 * SECOND, 3_500_000_000),
        (6 * SECOND, 7 * SECOND),
    ]
    assert all(i.state is TxState.ACTIVE for i in intervals)


def test_transmission_carries_parameters(repo: MockRecordingRepository) -> None:
    interval = repo.transmissions(SPAN)[0]
    assert interval.frequency_hz == 12_000.0
    assert interval.power_w == 250.0
    assert interval.mode == "LFM"
    assert interval.duration_seconds == 1.5


def test_tx_state_transitions(repo: MockRecordingRepository) -> None:
    """IDLE -> ACTIVE -> IDLE geçişleri bilinen anlarda olmalı."""
    assert repo.tx_state_at(1 * SECOND) is TxState.IDLE
    assert repo.tx_state_at(2 * SECOND) is TxState.ACTIVE
    assert repo.tx_state_at(3 * SECOND) is TxState.ACTIVE
    assert repo.tx_state_at(3_500_000_000) is TxState.IDLE, "bitis siniri disaridadir"
    assert repo.tx_state_at(5 * SECOND) is TxState.IDLE
    assert repo.tx_state_at(6 * SECOND) is TxState.ACTIVE
    assert repo.tx_state_at(7 * SECOND) is TxState.IDLE


def test_transmissions_are_filtered_by_overlap(repo: MockRecordingRepository) -> None:
    assert len(repo.transmissions(TimeRange(0, 4 * SECOND))) == 1
    assert len(repo.transmissions(TimeRange(4 * SECOND, 5 * SECOND))) == 0
    assert len(repo.transmissions(TimeRange(0, 10 * SECOND))) == 2


# -- Sistem olaylari ------------------------------------------------------


def test_system_events_at_known_times(repo: MockRecordingRepository) -> None:
    events = [e for e in repo.events(SPAN) if e.source == "System"]
    assert [e.timestamp_ns for e in events] == [0, 500_000_000]
    assert "Simulasyon" in events[0].message


def test_events_include_bit_results(repo: MockRecordingRepository) -> None:
    events = repo.events(SPAN)
    bit_events = [e for e in events if e.source == "BIT"]
    assert len(bit_events) == 10 * len(BIT_COMPONENTS)

    failure = [e for e in bit_events if e.state == "fail"]
    assert len(failure) == 1
    assert failure[0].timestamp_ns == 4 * SECOND


def test_events_are_sorted_by_time(repo: MockRecordingRepository) -> None:
    stamps = [e.timestamp_ns for e in repo.events(SPAN)]
    assert stamps == sorted(stamps)


def test_events_can_be_filtered(repo: MockRecordingRepository) -> None:
    only_errors = repo.events(SPAN, EventFilter(min_severity=Severity.ERROR))
    assert len(only_errors) == 1
    assert only_errors[0].timestamp_ns == 4 * SECOND

    only_system = repo.events(SPAN, EventFilter(sources=["System"]))
    assert len(only_system) == 2


# -- Zamanlamanin degistirilebilirligi ------------------------------------


def test_schedule_can_be_customized() -> None:
    schedule = MockEventSchedule(
        bit_period_s=2.0,
        bit_failures=((6.0, "Power Supply"),),
        tx_intervals_s=((1.0, 2.0),),
        system_events=(),
    )
    repo = MockRecordingRepository(duration_s=8.0, schedule=schedule)

    seconds = sorted({r.timestamp_ns // SECOND for r in repo.bit_results(TimeRange(0, 8 * SECOND))})
    assert seconds == [0, 2, 4, 6]

    failures = [r for r in repo.bit_results(TimeRange(0, 8 * SECOND)) if r.state is BitState.FAIL]
    assert len(failures) == 1
    assert failures[0].component == "Power Supply"
    assert failures[0].timestamp_ns == 6 * SECOND

    assert len(repo.transmissions(TimeRange(0, 8 * SECOND))) == 1
    assert [e for e in repo.events(TimeRange(0, 8 * SECOND)) if e.source == "System"] == []


def test_invalid_tx_interval_is_rejected() -> None:
    repo = MockRecordingRepository(
        duration_s=5.0,
        schedule=MockEventSchedule(tx_intervals_s=((3.0, 1.0),)),
    )
    with pytest.raises(ValueError, match="Gecersiz TX araligi"):
        repo.transmissions(TimeRange(0, 5 * SECOND))


def test_start_offset_shifts_events() -> None:
    repo = MockRecordingRepository(duration_s=10.0, start_ns=100 * SECOND)
    failures = [
        r
        for r in repo.bit_results(TimeRange(100 * SECOND, 110 * SECOND))
        if r.state is BitState.FAIL
    ]
    assert failures[0].timestamp_ns == 104 * SECOND

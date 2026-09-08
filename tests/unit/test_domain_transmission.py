"""TransmissionInterval testleri — `F1-015`."""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState

P = RECORD_PERIOD_NS


def test_state_codes() -> None:
    assert TxState.from_code(0) is TxState.IDLE
    assert TxState.from_code(1) is TxState.ACTIVE
    assert TxState.from_code(2) is TxState.FAULT
    assert TxState.from_code(3) is TxState.ARMED


def test_unknown_state_code_is_not_idle() -> None:
    """Tanınmayan kod IDLE varsayılmaz; transmisyon var mı yok mu belirsizdir."""
    assert TxState.from_code(42) is TxState.UNKNOWN
    assert TxState.from_code(42) is not TxState.IDLE


def make(**overrides: object) -> TransmissionInterval:
    defaults: dict[str, object] = {
        "time_range": TimeRange(2 * P, 6 * P),
        "state": TxState.ACTIVE,
        "frequency_hz": 12_000.0,
        "power_w": 250.0,
        "mode": "LFM",
    }
    defaults.update(overrides)
    return TransmissionInterval(**defaults)  # type: ignore[arg-type]


def test_start_end_and_duration() -> None:
    interval = make()
    assert interval.start_ns == 2 * P
    assert interval.end_ns == 6 * P
    assert interval.duration_ns == 4 * P
    assert interval.duration_seconds == 0.5


def test_reversed_range_is_rejected_by_time_range() -> None:
    with pytest.raises(ValueError, match="Ters zaman araligi"):
        make(time_range=TimeRange(6 * P, 2 * P))


def test_idle_cannot_be_an_interval() -> None:
    with pytest.raises(ValueError, match="IDLE bir transmisyon araligi olusturmaz"):
        make(state=TxState.IDLE)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"frequency_hz": 0.0}, "Frekans pozitif"),
        ({"frequency_hz": -1.0}, "Frekans pozitif"),
        ({"bandwidth_hz": -1.0}, "Bant genisligi negatif"),
        ({"power_w": -0.5}, "Guc negatif"),
        ({"boundary_uncertainty_ns": -1}, "belirsizligi negatif"),
    ],
)
def test_invalid_values_are_rejected(overrides: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        make(**overrides)


def test_default_uncertainty_is_one_record_period() -> None:
    assert make().boundary_uncertainty_ns == P


def test_fault_interval() -> None:
    assert make(state=TxState.FAULT).is_fault
    assert not make().is_fault


def _samples(states: list[TxState]) -> list[tuple[int, TxState]]:
    return [(index * P, state) for index, state in enumerate(states)]


def test_derives_single_interval_from_samples() -> None:
    # fixture-valid-8records.md: n=2..5 ACTIVE, digerleri IDLE
    states = [TxState.IDLE, TxState.IDLE] + [TxState.ACTIVE] * 4 + [TxState.IDLE, TxState.IDLE]
    intervals = TransmissionInterval.from_state_samples(_samples(states))

    assert len(intervals) == 1
    interval = intervals[0]
    assert interval.start_ns == 2 * P  # 250 ms
    assert interval.end_ns == 6 * P  # 750 ms
    assert interval.duration_ns == 4 * P  # 500 ms
    assert interval.closed


def test_derives_multiple_intervals() -> None:
    states = [
        TxState.ACTIVE,
        TxState.IDLE,
        TxState.ACTIVE,
        TxState.ACTIVE,
        TxState.IDLE,
    ]
    intervals = TransmissionInterval.from_state_samples(_samples(states))
    assert [(i.start_ns, i.end_ns) for i in intervals] == [(0, P), (2 * P, 4 * P)]


def test_open_interval_at_end_of_recording_is_marked() -> None:
    """Kayıt ACTIVE iken biterse aralık kapanmış gibi gösterilmez."""
    states = [TxState.IDLE, TxState.ACTIVE, TxState.ACTIVE]
    intervals = TransmissionInterval.from_state_samples(_samples(states))

    assert len(intervals) == 1
    assert not intervals[0].closed
    assert intervals[0].end_ns == 3 * P, "son ornegin penceresi kadar uzatilir"


def test_no_active_sample_yields_no_interval() -> None:
    states = [TxState.IDLE, TxState.ARMED, TxState.FAULT]
    assert TransmissionInterval.from_state_samples(_samples(states)) == []


def test_samples_are_sorted_before_deriving() -> None:
    unordered = [(4 * P, TxState.IDLE), (0, TxState.ACTIVE), (2 * P, TxState.ACTIVE)]
    intervals = TransmissionInterval.from_state_samples(unordered)
    assert len(intervals) == 1
    assert (intervals[0].start_ns, intervals[0].end_ns) == (0, 4 * P)


def test_empty_sample_list() -> None:
    assert TransmissionInterval.from_state_samples([]) == []


def test_str_shows_uncertainty() -> None:
    text = str(make())
    assert "0.500 s" in text
    assert "+/-125 ms" in text

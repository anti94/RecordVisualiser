"""Event ve BitResult testleri — `F1-014`."""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.event import BitResult, BitState, Event, Severity


def test_severity_codes_round_trip() -> None:
    for code, expected in [
        (0, Severity.INFO),
        (1, Severity.WARNING),
        (2, Severity.ERROR),
        (3, Severity.CRITICAL),
    ]:
        assert Severity.from_code(code) is expected


def test_unknown_severity_code_is_not_silently_info() -> None:
    """Tanınmayan şiddet kodu en azından uyarı sayılır, INFO'ya düşürülmez."""
    assert Severity.from_code(99) is Severity.WARNING


def test_severity_ranking() -> None:
    assert Severity.INFO.rank < Severity.WARNING.rank
    assert Severity.WARNING.rank < Severity.ERROR.rank
    assert Severity.ERROR.rank < Severity.CRITICAL.rank


def test_bit_state_codes_round_trip() -> None:
    assert BitState.from_code(0) is BitState.PASS
    assert BitState.from_code(1) is BitState.WARN
    assert BitState.from_code(2) is BitState.FAIL
    assert BitState.from_code(3) is BitState.NOT_RUN


def test_unknown_bit_code_becomes_unknown_not_pass() -> None:
    """Tanınmayan kod PASS varsayılmaz; bu, arızayı gizlerdi."""
    assert BitState.from_code(7) is BitState.UNKNOWN
    assert BitState.from_code(255) is BitState.UNKNOWN
    assert BitState.from_code(7) is not BitState.PASS


def test_failure_states() -> None:
    assert BitState.FAIL.is_failure
    assert BitState.WARN.is_failure
    assert not BitState.PASS.is_failure
    assert not BitState.NOT_RUN.is_failure
    assert not BitState.UNKNOWN.is_failure


def make_event(**overrides: object) -> Event:
    defaults: dict[str, object] = {
        "timestamp_ns": 500_000_000,
        "source": "BIT",
        "category": "Thermal",
        "severity": Severity.ERROR,
        "code": "0x0412",
        "message": "Amplifikator sicakligi yuksek",
    }
    defaults.update(overrides)
    return Event(**defaults)  # type: ignore[arg-type]


def test_event_carries_category_and_severity() -> None:
    event = make_event()
    assert event.category == "Thermal"
    assert event.severity is Severity.ERROR
    assert event.is_alarm


def test_info_event_is_not_alarm() -> None:
    assert not make_event(severity=Severity.INFO).is_alarm
    assert not make_event(severity=Severity.WARNING).is_alarm
    assert make_event(severity=Severity.CRITICAL).is_alarm


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"source": " "}, "kaynagi bos"),
        ({"category": ""}, "kategorisi bos"),
        ({"message": "   "}, "mesaji bos"),
    ],
)
def test_event_rejects_empty_fields(overrides: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        make_event(**overrides)


def make_bit(**overrides: object) -> BitResult:
    defaults: dict[str, object] = {
        "timestamp_ns": 500_000_000,
        "test_id": 8,
        "component": "Thermal Management",
        "state": BitState.FAIL,
        "severity": Severity.ERROR,
        "code": 0x0412,
        "measured": 87.5,
        "unit": "C",
    }
    defaults.update(overrides)
    return BitResult(**defaults)  # type: ignore[arg-type]


def test_bit_result_fields_and_failure() -> None:
    result = make_bit()
    assert result.state is BitState.FAIL
    assert result.is_failure
    assert result.measured == 87.5
    assert result.display_name == "Thermal Management (test 8)"


def test_bit_result_converts_to_event_without_loss() -> None:
    result = make_bit(detail="Sicaklik esigi asildi")
    event = result.to_event()

    assert event.timestamp_ns == result.timestamp_ns
    assert event.source == "BIT"
    assert event.category == "Thermal Management"
    assert event.severity is Severity.ERROR
    assert event.state == "fail"
    assert event.value == 87.5
    assert event.unit == "C"
    assert event.message == "Sicaklik esigi asildi"


def test_bit_event_falls_back_to_display_name() -> None:
    event = make_bit(detail="").to_event()
    assert event.message == "Thermal Management (test 8)"


def test_unknown_state_survives_conversion() -> None:
    """UNKNOWN durum olaya çevrilirken PASS'a dönüşmemeli."""
    event = make_bit(state=BitState.from_code(9)).to_event()
    assert event.state == "unknown"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"test_id": -1}, "negatif olamaz"),
        ({"component": " "}, "bilesen adi bos"),
    ],
)
def test_bit_rejects_invalid_values(overrides: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        make_bit(**overrides)

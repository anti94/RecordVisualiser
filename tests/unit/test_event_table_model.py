"""Ortak olay tablosu modeli — `F3-042` (plan Bölüm 5.5).

Kabul: sütunlar doğru domain alanlarını gösterir.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import (
    EMPTY_CELL,
    EVENT_COLUMNS,
    event_cell_text,
    event_row,
    format_event_time,
)

START_NS = 0


def _event(**overrides: object) -> Event:
    base: dict[str, object] = {
        "timestamp_ns": START_NS + 4_000_000_000,
        "source": "Thermal Subsystem",
        "category": "BIT",
        "severity": Severity.ERROR,
        "code": "BIT_THERMAL_FAIL",
        "message": "Sicaklik esigi asildi",
        "state": "PASS -> FAIL",
        "value": 87.5,
        "unit": "C",
    }
    base.update(overrides)
    return Event(**base)  # type: ignore[arg-type]


def test_columns_are_the_section_5_5_set_in_order() -> None:
    assert EVENT_COLUMNS == (
        "Time",
        "Severity",
        "Category",
        "Source",
        "Code",
        "State",
        "Message",
        "Value",
    )


def test_each_column_maps_to_the_expected_domain_field() -> None:
    event = _event()

    assert event_cell_text(event, "Time", start_ns=START_NS) == "+4.000 s (00:00:04.000)"
    assert event_cell_text(event, "Severity", start_ns=START_NS) == "Error"
    assert event_cell_text(event, "Category", start_ns=START_NS) == "BIT"
    assert event_cell_text(event, "Source", start_ns=START_NS) == "Thermal Subsystem"
    assert event_cell_text(event, "Code", start_ns=START_NS) == "BIT_THERMAL_FAIL"
    assert event_cell_text(event, "State", start_ns=START_NS) == "PASS -> FAIL"
    assert event_cell_text(event, "Message", start_ns=START_NS) == "Sicaklik esigi asildi"
    assert event_cell_text(event, "Value", start_ns=START_NS) == "87.5 C"


def test_time_is_relative_and_absolute_together() -> None:
    assert format_event_time(START_NS, START_NS) == "+0.000 s (00:00:00.000)"
    assert format_event_time(START_NS + 2_500_000_000, START_NS) == "+2.500 s (00:00:02.500)"
    # olay kayıt başlangıcından önceyse göreli değer negatif
    assert format_event_time(START_NS - 1_000_000_000, START_NS).startswith("-1.000 s")


def test_optional_fields_fall_back_to_a_dash() -> None:
    bare = _event(state=None, value=None, unit=None)

    assert event_cell_text(bare, "State", start_ns=START_NS) == EMPTY_CELL
    assert event_cell_text(bare, "Value", start_ns=START_NS) == EMPTY_CELL


def test_value_without_unit_shows_only_the_number() -> None:
    assert event_cell_text(_event(value=3, unit=None), "Value", start_ns=START_NS) == "3"


def test_string_value_is_shown_verbatim() -> None:
    assert event_cell_text(_event(value="OPEN", unit=None), "Value", start_ns=START_NS) == "OPEN"


def test_severity_label_is_capitalised_for_every_level() -> None:
    labels = {
        event_cell_text(_event(severity=level), "Severity", start_ns=START_NS) for level in Severity
    }
    assert labels == {"Info", "Warning", "Error", "Critical"}


def test_event_row_returns_all_columns_in_order() -> None:
    row = event_row(_event(), start_ns=START_NS)

    assert len(row) == len(EVENT_COLUMNS)
    assert row[0].startswith("+4.000 s")
    assert row[-1] == "87.5 C"


def test_unknown_column_raises() -> None:
    with pytest.raises(KeyError):
        event_cell_text(_event(), "Nonsense", start_ns=START_NS)

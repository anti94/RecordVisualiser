"""Olay seçimini Inspector detayına bağlama — `F3-044`.

Kabul: kaynak, kod ve ilgili kanallar doğru gösterilir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.inspector import EMPTY_VALUE, InspectorPanel
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _event() -> Event:
    return Event(
        timestamp_ns=4_000_000_000,
        source="Thermal Subsystem",
        category="sensors",
        severity=Severity.ERROR,
        code="BIT_THERMAL_FAIL",
        message="Temperature threshold exceeded",
        state="PASS -> FAIL",
    )


def _channel(channel_id: str, name: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="C",
        sample_rate_hz=1.0,
    )


# -- InspectorPanel.show_event ------------------------------


def test_show_event_fills_source_code_and_related_channels(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    related = [_channel("ch1", "Temperature")]

    panel.show_event(_event(), related)

    assert panel.event_field_value("Source") == "Thermal Subsystem"
    assert panel.event_field_value("Code") == "BIT_THERMAL_FAIL"
    assert panel.event_field_value("Severity") == "Error"
    assert panel.event_field_value("State") == "PASS -> FAIL"
    assert panel.event_field_value("Related channels") == "Temperature"
    assert panel.event_detail.isVisibleTo(panel)


def test_no_related_channels_shows_a_dash(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)

    panel.show_event(_event(), [])

    assert panel.event_field_value("Related channels") == EMPTY_VALUE


def test_showing_a_channel_hides_the_event_detail(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_event(_event(), [])
    assert panel.event_detail.isVisibleTo(panel)

    panel.show_channel(_channel("ch0", "Pressure"))

    assert not panel.event_detail.isVisibleTo(panel)
    assert panel.detail.isVisibleTo(panel)


def test_clear_blanks_the_event_fields(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_event(_event(), [_channel("ch1", "Temperature")])

    panel.clear()

    assert not panel.event_detail.isVisibleTo(panel)
    assert panel.event_field_value("Source") == EMPTY_VALUE


# -- uctan uca: Events tablosunda satir secince Inspector dolar --


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


def test_selecting_an_event_row_binds_it_to_the_inspector(window: MainWindow) -> None:
    assert window.bottom_dock.event_row_count() > 0
    expected_source = window.bottom_dock.event_cell(0, "Source")
    expected_code = window.bottom_dock.event_cell(0, "Code")

    window.bottom_dock.events.selectRow(0)

    inspector = window.right_dock.inspector
    assert window.right_dock.inspector_is_open
    assert inspector.event_field_value("Source") == expected_source
    assert inspector.event_field_value("Code") == expected_code

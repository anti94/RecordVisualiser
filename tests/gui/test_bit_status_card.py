"""BIT / System Status kartı — `F1-035`.

Kabul: genel durum, son güncelleme ve alt sistem tablosu için alan vardır.
"""

from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import BitResult, BitState, Severity
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.bit_status import (
    FAILURE_TEXT,
    NO_DATA_TEXT,
    NOMINAL_TEXT,
    UNKNOWN_TEXT,
    WARNING_TEXT,
    BitStatusCard,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def card(qtbot: QtBot) -> BitStatusCard:
    widget = BitStatusCard()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def result(component: str, state: BitState, test_id: int = 0) -> BitResult:
    return BitResult(
        timestamp_ns=0,
        test_id=test_id,
        component=component,
        state=state,
        severity=Severity.ERROR if state is BitState.FAIL else Severity.INFO,
    )


# -- alanlar ---------------------------------------------------------------


def test_card_has_badge_button_and_table(card: BitStatusCard) -> None:
    assert card.badge_text() == NO_DATA_TEXT
    assert card.run_button.text() == "Run BIT Analysis"
    assert card.table.columnCount() == 2
    assert card.last_update.text().startswith("Last Update:")


def test_card_is_used_in_the_right_column(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    assert isinstance(win.right_dock.bit_status, BitStatusCard)
    assert win.right_dock.cards["card_bit_status"] is win.right_dock.bit_status


# -- rozet / tablo tutarliligi ---------------------------------------------


def test_badge_says_nominal_when_all_pass(card: BitStatusCard) -> None:
    card.set_results([result("Power Supply", BitState.PASS), result("Storage", BitState.PASS)])
    assert card.badge_text() == NOMINAL_TEXT
    assert card.row_count() == 2


def test_badge_cannot_claim_nominal_with_a_failure(card: BitStatusCard) -> None:
    """Kabul kuralı: rozet ile tablo çelişemez."""
    card.set_results(
        [result("Power Supply", BitState.PASS), result("Thermal Management", BitState.FAIL)]
    )
    assert card.badge_text() == FAILURE_TEXT
    assert card.badge_text() != NOMINAL_TEXT


def test_warning_is_reflected_in_the_badge(card: BitStatusCard) -> None:
    card.set_results([result("Power Supply", BitState.PASS), result("Storage", BitState.WARN)])
    assert card.badge_text() == WARNING_TEXT


def test_failure_outranks_warning(card: BitStatusCard) -> None:
    card.set_results([result("A", BitState.WARN), result("B", BitState.FAIL)])
    assert card.badge_text() == FAILURE_TEXT


def test_unknown_state_is_not_reported_as_nominal(card: BitStatusCard) -> None:
    card.set_results([result("A", BitState.PASS), result("B", BitState.UNKNOWN)])
    assert card.badge_text() == UNKNOWN_TEXT


# -- tablo -----------------------------------------------------------------


def test_worst_result_per_subsystem_is_shown(card: BitStatusCard) -> None:
    """Bir testin geçmesi, aynı bileşendeki arızayı gizlememeli."""
    card.set_results(
        [
            result("Thermal Management", BitState.PASS, test_id=1),
            result("Thermal Management", BitState.FAIL, test_id=2),
        ]
    )
    assert card.row_count() == 1
    assert card.status_text("Thermal Management") == "Fail"


def test_subsystems_are_sorted(card: BitStatusCard) -> None:
    card.set_results([result("Storage", BitState.PASS), result("Communication", BitState.PASS)])
    assert card.subsystem_names() == ["Communication", "Storage"]


def test_status_cell_has_icon(card: BitStatusCard) -> None:
    card.set_results([result("Storage", BitState.PASS)])
    item = card.table.item(0, 1)
    assert item is not None
    assert not item.icon().isNull()
    assert item.text() == "OK"


def test_unknown_subsystem_lookup_raises(card: BitStatusCard) -> None:
    card.set_results([result("Storage", BitState.PASS)])
    with pytest.raises(KeyError, match="Tabloda yok"):
        card.status_text("Yok")


def test_last_update_is_shown(card: BitStatusCard) -> None:
    card.set_results(
        [result("Storage", BitState.PASS)], updated_at=datetime(2026, 9, 9, 15, 32, 10)
    )
    assert card.last_update.text() == "Last Update: 15:32:10"


def test_clear_resets_the_card(card: BitStatusCard) -> None:
    card.set_results([result("Storage", BitState.FAIL)])
    card.clear()
    assert card.row_count() == 0
    assert card.badge_text() == NO_DATA_TEXT


# -- pencereye baglanma ----------------------------------------------------


def test_recording_fills_the_card(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=10.0))

    card = win.right_dock.bit_status
    assert card.row_count() == 8, "mockup sekiz alt sistem gosteriyor"
    assert card.badge_text() == FAILURE_TEXT, "4.0 s'de Thermal FAIL var"
    assert card.status_text("Thermal Management") == "Fail"
    assert card.status_text("Power Supply") == "OK"


def test_run_button_refreshes_without_touching_hardware(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=10.0))

    win.right_dock.bit_status.run_button.click()

    text = "\n".join(win.bottom_dock.log_lines())
    assert "BIT ozeti yenilendi" in text
    assert "komut gondermez" in win.right_dock.bit_status.run_button.toolTip()

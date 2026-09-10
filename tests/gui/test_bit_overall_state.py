"""Sağ BIT kartı — genel özet en yüksek severity'yi yansıtır — `F3-051`.

Kabul: genel özet en yüksek severity'yi yansıtır; Warning varken tümü
normal yazmaz.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import BitResult, BitState, Severity
from sonar_analyzer.ui.cards.bit_status import (
    FAILURE_TEXT,
    NOMINAL_TEXT,
    WARNING_TEXT,
    BitStatusCard,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _result(component: str, state: BitState, test_id: int = 0) -> BitResult:
    return BitResult(
        timestamp_ns=0,
        test_id=test_id,
        component=component,
        state=state,
        severity=Severity.ERROR if state is BitState.FAIL else Severity.INFO,
    )


@pytest.fixture()
def card(qtbot: QtBot) -> BitStatusCard:
    widget = BitStatusCard()
    qtbot.addWidget(widget)
    return widget


def test_no_data_has_no_overall_state(card: BitStatusCard) -> None:
    assert card.overall_state() is None


def test_all_pass_overall_state_is_pass(card: BitStatusCard) -> None:
    card.set_results([_result("Power", BitState.PASS), _result("Comms", BitState.PASS)])

    assert card.overall_state() is BitState.PASS
    assert card.badge_text() == NOMINAL_TEXT


def test_one_warning_makes_the_overall_state_warn(card: BitStatusCard) -> None:
    card.set_results(
        [
            _result("Power", BitState.PASS),
            _result("Thermal", BitState.WARN),
            _result("Comms", BitState.PASS),
        ]
    )

    assert card.overall_state() is BitState.WARN
    assert card.badge_text() == WARNING_TEXT
    assert card.badge_text() != NOMINAL_TEXT, "Warning varken tümü normal yazmaz"


def test_failure_outranks_warning_in_the_overall_state(card: BitStatusCard) -> None:
    card.set_results(
        [
            _result("Thermal", BitState.WARN),
            _result("Storage", BitState.FAIL),
            _result("Power", BitState.PASS),
        ]
    )

    assert card.overall_state() is BitState.FAIL
    assert card.badge_text() == FAILURE_TEXT


def test_overall_state_is_the_worst_across_subsystems_not_within_one(card: BitStatusCard) -> None:
    # aynı alt sistemde hem PASS hem WARN; başka alt sistem tümü PASS
    card.set_results(
        [
            _result("Thermal", BitState.PASS),
            _result("Thermal", BitState.WARN),
            _result("Power", BitState.PASS),
        ]
    )

    assert card.overall_state() is BitState.WARN
    assert card.status_text("Thermal") != card.status_text("Power")


# -- uctan uca: kayit karti doldurur -----------------------


def test_recording_summary_reflects_the_worst_subsystem(qtbot: QtBot, tmp_path: Path) -> None:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()

    card = win.right_dock.bit_status
    # golden fixture 4.0 s'de Thermal FAIL taşır
    assert card.overall_state() is BitState.FAIL
    assert card.badge_text() == FAILURE_TEXT

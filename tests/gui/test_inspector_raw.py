"""Geliştirici ham kayıt görünümü (Inspector Raw) — `F3-040`.

Kabul: seçim kaynak offsetini ve ham/ölçeklenmiş değeri gösterir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot
from tests.golden_bytes import START_TIME_UTC_NS

from sonar_analyzer.domain.raw_record import SampleInspection
from sonar_analyzer.ui.docks.inspector import EMPTY_VALUE, RAW_FIELDS, InspectorPanel
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
PERIOD_NS = 125_000_000
HEADER_SIZE = 32
RECORD_SIZE = 64


# -- InspectorPanel Raw grubu -------------------------------


def test_raw_group_shows_offset_raw_and_scaled_distinctly(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)

    panel.show_raw_sample(
        SampleInspection(
            channel_id="ch0",
            timestamp_ns=1_000,
            byte_offset=224,
            raw_value=200.0,
            scaled_value=100.0,
        ),
        unit="bar",
    )

    assert panel.raw_field_value("Source offset") == "224 (0xE0)"
    assert panel.raw_field_value("Raw value") == "200"
    assert panel.raw_field_value("Scaled value") == "100 bar"
    assert panel.raw_field_value("Sample time") == "1000 ns"


def test_clear_blanks_the_raw_fields(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_raw_sample(
        SampleInspection("ch0", 1, 64, 1.0, 1.0),
    )

    panel.clear()

    for field in RAW_FIELDS:
        assert panel.raw_field_value(field) == EMPTY_VALUE


def test_unknown_raw_field_raises(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    with pytest.raises(KeyError):
        panel.raw_field_value("nope")


# -- uctan uca: crosshair bir ornege kenetlenince Raw dolar ---


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


def test_moving_the_cursor_fills_the_raw_view_for_the_selected_channel(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    inspector = window.right_dock.inspector

    # n = 3 örneği: x = 3 * 0.125 = 0.375 s
    window.plot_panel.set_cursor(0.375)

    assert inspector.raw_field_value("Source offset") == f"{HEADER_SIZE + 3 * RECORD_SIZE} (0xE0)"
    assert inspector.raw_field_value("Raw value") == "101.5"
    assert inspector.raw_field_value("Scaled value") == "101.5 bar"
    assert inspector.raw_field_value("Sample time") == f"{START_TIME_UTC_NS + 3 * PERIOD_NS} ns"

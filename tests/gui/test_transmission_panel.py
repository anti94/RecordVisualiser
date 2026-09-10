"""Transmission sekmesi TX aralıklarına bağlı — `F3-048`.

Kabul: seçili kaydın TX durumu ve zaman aralıkları sekmede görünür.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.transmission_panel import TransmissionPanel, transmission_row

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
SECOND = 1_000_000_000


def _interval(
    start_s: float,
    end_s: float,
    *,
    state: TxState = TxState.ACTIVE,
    closed: bool = True,
) -> TransmissionInterval:
    return TransmissionInterval(
        time_range=TimeRange(int(start_s * SECOND), int(end_s * SECOND)),
        state=state,
        closed=closed,
    )


# -- TransmissionPanel dogrudan ----------------------------


def test_panel_lists_state_and_time_bounds(qtbot: QtBot) -> None:
    panel = TransmissionPanel()
    qtbot.addWidget(panel)

    panel.set_intervals(
        [_interval(0.25, 0.75), _interval(1.5, 2.0, state=TxState.FAULT)], start_ns=0
    )

    assert panel.interval_count() == 2
    assert panel.interval_cell(0, "State") == "Active"
    assert panel.interval_cell(0, "Start").startswith("+0.250 s (")
    assert panel.interval_cell(0, "End").startswith("+0.750 s (")
    assert "±" in panel.interval_cell(0, "Duration")
    assert panel.interval_cell(1, "State") == "Fault"


def test_open_at_end_interval_is_noted(qtbot: QtBot) -> None:
    panel = TransmissionPanel()
    qtbot.addWidget(panel)

    panel.set_intervals([_interval(0.0, 1.0, closed=False)], start_ns=0)

    assert "açık kaldı" in panel.interval_cell(0, "Note")


def test_transmission_row_helper_matches_the_columns() -> None:
    row = transmission_row(_interval(1.0, 3.0), start_ns=0)

    assert row[0] == "Active"
    assert row[1].startswith("+1.000 s")
    assert row[2].startswith("+3.000 s")
    assert row[3].startswith("2.000 s ±")


def test_clear_empties_the_table_and_shows_the_hint(qtbot: QtBot) -> None:
    panel = TransmissionPanel()
    qtbot.addWidget(panel)
    panel.set_intervals([_interval(0.0, 1.0)], start_ns=0)

    panel.clear()

    assert panel.interval_count() == 0


def test_unknown_column_raises(qtbot: QtBot) -> None:
    panel = TransmissionPanel()
    qtbot.addWidget(panel)
    with pytest.raises(KeyError):
        panel.interval_cell(0, "Nope")


# -- uctan uca: Transmission sekmesi -----------------------


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


def test_transmission_tab_is_enabled_and_shows_intervals(window: MainWindow) -> None:
    assert "Transmission" in window.view_tabs.enabled_tabs()
    assert window.transmission_panel.interval_count() > 0

    tx_index = window.view_tabs.tab_titles().index("Transmission")
    window.view_tabs.setCurrentIndex(tx_index)

    assert window.center_stack.currentWidget() is window.transmission_panel
    assert window.transmission_panel.interval_cell(0, "State") in {"Active", "Fault", "Armed"}


def test_switching_back_to_time_series_restores_the_plot_view(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    tx_index = window.view_tabs.tab_titles().index("Transmission")
    ts_index = window.view_tabs.tab_titles().index("Time Series")

    window.view_tabs.setCurrentIndex(tx_index)
    assert not window.center_shows_plot

    window.view_tabs.setCurrentIndex(ts_index)
    assert window.center_shows_plot


def test_closing_the_recording_clears_the_transmission_table(window: MainWindow) -> None:
    assert window.transmission_panel.interval_count() > 0

    window.close_active_recording()

    assert window.transmission_panel.interval_count() == 0

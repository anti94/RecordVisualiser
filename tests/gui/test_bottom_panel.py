"""Alt Log/Messages alanı ve Events sekmesi — `F1-026`.

Kabul: Log merkezin altında; olay tablosu aynı alanda ayrı sekmededir.
"""

from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.bottom_panel import (
    EVENT_COLUMNS,
    EVENTS_TAB_TITLE,
    LOG_TAB_TITLE,
    MAX_LOG_LINES,
    BottomPanelDock,
    format_timestamp,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


@pytest.fixture()
def panel(qtbot: QtBot) -> BottomPanelDock:
    dock = BottomPanelDock()
    qtbot.addWidget(dock)
    dock.show()
    qtbot.waitExposed(dock)
    return dock


# -- yerlesim --------------------------------------------------------------


def test_panel_is_below_the_center(window: MainWindow) -> None:
    assert isinstance(window.bottom_dock, BottomPanelDock)
    assert window.dockWidgetArea(window.bottom_dock) == Qt.DockWidgetArea.BottomDockWidgetArea


def test_panel_is_visually_below_center(window: MainWindow, qtbot: QtBot) -> None:
    """Alt panelin üst kenarı, merkez alanın alt kenarından aşağıda olmalı."""
    qtbot.waitUntil(lambda: window.bottom_dock.height() > 0, timeout=2000)
    center_bottom = window.center.mapTo(window, window.center.rect().bottomLeft()).y()
    panel_top = window.bottom_dock.mapTo(window, window.bottom_dock.rect().topLeft()).y()
    assert panel_top >= center_bottom


def test_log_and_events_are_tabs_of_the_same_area(panel: BottomPanelDock) -> None:
    assert panel.tab_titles() == [LOG_TAB_TITLE, EVENTS_TAB_TITLE]
    assert panel.tabs.count() == 2


def test_dock_has_stable_object_name(window: MainWindow) -> None:
    assert window.bottom_dock.objectName() == "dock_bottom_panel"


# -- log -------------------------------------------------------------------


def test_log_starts_empty(panel: BottomPanelDock) -> None:
    assert panel.log_lines() == []
    assert panel.log.isReadOnly()


def test_append_log_writes_timestamped_line(panel: BottomPanelDock) -> None:
    panel.append_log("Kayit acildi", timestamp=datetime(2026, 9, 9, 15, 30, 12))
    lines = panel.log_lines()
    assert lines == ["[15:30:12] Kayit acildi"]


def test_log_keeps_order(panel: BottomPanelDock) -> None:
    panel.append_log("birinci")
    panel.append_log("ikinci")
    lines = panel.log_lines()
    assert "birinci" in lines[0]
    assert "ikinci" in lines[1]


def test_log_is_bounded(panel: BottomPanelDock) -> None:
    """Uzun oturumda log sınırsız büyümemeli."""
    for index in range(MAX_LOG_LINES + 50):
        panel.append_log(f"satir {index}")
    assert len(panel.log_lines()) <= MAX_LOG_LINES


def test_clear_log(panel: BottomPanelDock) -> None:
    panel.append_log("bir sey")
    panel.clear_log()
    assert panel.log_lines() == []


def test_opening_a_recording_writes_to_log(window: MainWindow) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    window.set_recording(repo.metadata(), repo.channels())

    text = "\n".join(window.bottom_dock.log_lines())
    assert "Kayit acildi" in text
    assert "8 kanal bulundu" in text


# -- olaylar ---------------------------------------------------------------


def test_events_table_starts_empty(panel: BottomPanelDock) -> None:
    assert panel.event_row_count() == 0
    # F3-042: plan Bölüm 5.5'in sekiz sütunu
    assert panel.events.columnCount() == 8
    assert list(EVENT_COLUMNS) == [
        "Time",
        "Severity",
        "Category",
        "Source",
        "Code",
        "State",
        "Message",
        "Value",
    ]


def test_events_are_listed_with_columns(panel: BottomPanelDock) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    events = repo.events(TimeRange(0, 10 * SECOND))
    panel.set_events(events)

    assert panel.event_row_count() == len(events)
    assert panel.event_cell(0, "Source") in {"BIT", "System"}
    # F3-042: göreli + mutlak zaman birlikte
    assert panel.event_cell(0, "Time").startswith("+0.000 s (00:00:00")


def test_known_failure_appears_in_events(panel: BottomPanelDock) -> None:
    """4.0 s'deki Thermal Management FAIL tabloda görünmeli."""
    repo = MockRecordingRepository(duration_s=10.0)
    panel.set_events(repo.events(TimeRange(0, 10 * SECOND)))

    rows = [
        row
        for row in range(panel.event_row_count())
        if panel.event_cell(row, "Severity") == "Error"
    ]
    assert len(rows) == 1
    row = rows[0]
    assert panel.event_cell(row, "Category") == "Thermal Management"
    assert panel.event_cell(row, "Time") == "+4.000 s (00:00:04.000)"
    assert "basarisiz" in panel.event_cell(row, "Message")


def test_severity_cell_has_icon_and_text(panel: BottomPanelDock) -> None:
    """Durum yalnız renkle anlatılmıyor: ikon ve metin birlikte."""
    repo = MockRecordingRepository(duration_s=10.0)
    panel.set_events(repo.events(TimeRange(0, 10 * SECOND)))

    column = EVENT_COLUMNS.index("Severity")
    item = panel.events.item(0, column)
    assert item is not None
    assert item.text() != "", "metin bos olmamali"
    assert not item.icon().isNull(), "ikon bulunmali"
    assert item.text() in item.toolTip()


def test_events_are_separate_from_log(panel: BottomPanelDock) -> None:
    """Olay tablosu Log ile karıştırılmamalı (plan Bölüm 5.5)."""
    repo = MockRecordingRepository(duration_s=5.0)
    panel.set_events(repo.events(TimeRange(0, 5 * SECOND)))

    assert panel.event_row_count() > 0
    assert panel.log_lines() == [], "olaylar log'a yazilmamali"


def test_set_events_replaces_previous_rows(panel: BottomPanelDock) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    panel.set_events(repo.events(TimeRange(0, 10 * SECOND)))
    first_count = panel.event_row_count()

    panel.set_events(repo.events(TimeRange(0, 2 * SECOND)))
    assert panel.event_row_count() < first_count


def test_clear_events(panel: BottomPanelDock) -> None:
    repo = MockRecordingRepository(duration_s=5.0)
    panel.set_events(repo.events(TimeRange(0, 5 * SECOND)))
    panel.clear_events()
    assert panel.event_row_count() == 0


def test_unknown_column_raises(panel: BottomPanelDock) -> None:
    with pytest.raises(KeyError, match="Tanimsiz olay sutunu"):
        panel.event_cell(0, "Yok")


def test_timestamp_format() -> None:
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(4 * SECOND) == "00:00:04.000"
    assert format_timestamp(4_500_000_000) == "00:00:04.500"

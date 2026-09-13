"""Open .bin File düğmesi ve dosya özet kartı — `F1-034`.

Kabul: File, Size, Start, Duration ve Platform alanları sol üsttedir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QGroupBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.data_explorer import (
    EMPTY_VALUE,
    MOCKUP_SUMMARY_FIELDS,
    SUMMARY_FIELDS,
    DataExplorerDock,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000
#: 2026-09-08T21:00:00Z
ANCHOR_NS = 1_788_901_200 * SECOND


@pytest.fixture()
def dock(qtbot: QtBot) -> DataExplorerDock:
    widget = DataExplorerDock()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


# -- yerlesim --------------------------------------------------------------


def test_summary_fields_are_in_mockup_order(dock: DataExplorerDock) -> None:
    """Mockup'taki beş alan, aynı sırada ve **başta** olmalı.

    Kart sonradan büyüyebilir (`F7-052` "Format" ekledi) ama mockup'ın
    alanları kaydırılamaz: sıra ve konum `F6-031` kabulünün parçası.
    Yeni bilgi sona eklenir.
    """
    assert list(MOCKUP_SUMMARY_FIELDS) == ["File", "Size", "Start", "Duration", "Platform"]
    assert list(SUMMARY_FIELDS[: len(MOCKUP_SUMMARY_FIELDS)]) == list(MOCKUP_SUMMARY_FIELDS)


def test_extra_fields_come_after_the_mockup_ones(dock: DataExplorerDock) -> None:
    """Eklenen alanlar mockup alanlarını bölmemeli."""
    extra = SUMMARY_FIELDS[len(MOCKUP_SUMMARY_FIELDS) :]

    assert "Format" in extra
    assert not set(extra) & set(MOCKUP_SUMMARY_FIELDS)


def test_summary_is_a_card(dock: DataExplorerDock) -> None:
    card = dock.findChild(QGroupBox, "card_file_summary")
    assert card is not None
    assert card.title() == "Recording"


def test_open_button_is_above_the_summary(dock: DataExplorerDock) -> None:
    """Düğme sol sütunun en üstünde olmalı."""
    card = dock.findChild(QGroupBox, "card_file_summary")
    assert card is not None
    button_top = dock.open_button.mapTo(dock, dock.open_button.rect().topLeft()).y()
    card_top = card.mapTo(dock, card.rect().topLeft()).y()
    assert button_top < card_top


def test_summary_is_above_the_channel_tabs(dock: DataExplorerDock) -> None:
    card = dock.findChild(QGroupBox, "card_file_summary")
    assert card is not None
    card_top = card.mapTo(dock, card.rect().topLeft()).y()
    tabs_top = dock.tabs.mapTo(dock, dock.tabs.rect().topLeft()).y()
    assert card_top < tabs_top


# -- degerler --------------------------------------------------------------


def test_all_fields_empty_before_a_recording(dock: DataExplorerDock) -> None:
    for field in SUMMARY_FIELDS:
        assert dock.summary_value(field) == EMPTY_VALUE


def test_start_is_shown_as_readable_utc(dock: DataExplorerDock) -> None:
    """Ham nanosaniye kullanıcıya bir şey anlatmıyor."""
    metadata = RecordingMetadata(
        recording_id="rec-1",
        source_path="D:/kayitlar/ornek.bin",
        time_range=TimeRange(ANCHOR_NS, ANCHOR_NS + 3661 * SECOND),
        channel_count=8,
        record_count=29288,
        device_id="SONAR-X1",
        file_size_bytes=2_576_980_378,
    )
    dock.set_recording(metadata, [])

    assert dock.summary_value("Start") == "2026-09-08 21:00:00 UTC"
    assert dock.summary_value("Duration") == "01:01:01"
    assert dock.summary_value("File") == "D:/kayitlar/ornek.bin"
    assert dock.summary_value("Platform") == "SONAR-X1"
    assert dock.summary_value("Size") == "2.4 GB"


def test_zero_start_shows_placeholder(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    dock.set_recording(repo.metadata(), repo.channels())
    assert dock.summary_value("Start") == EMPTY_VALUE, "simulasyon ankoru 0"


def test_size_placeholder_when_unknown(dock: DataExplorerDock) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    dock.set_recording(repo.metadata(), repo.channels())
    assert dock.summary_value("Size") == EMPTY_VALUE


def test_window_fills_the_summary(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=120.0))
    assert window.left_dock.summary_value("Duration") == "00:02:00"
    assert window.left_dock.summary_value("File") == "Simülasyon"


def test_open_button_text_matches_mockup(dock: DataExplorerDock) -> None:
    assert dock.open_button.text() == "Open .bin File"
    assert dock.open_button.objectName() == "button_open_bin"

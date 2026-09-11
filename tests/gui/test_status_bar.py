"""Durum çubuğu alanları — `F1-028`.

Kabul: dosya, işlem, bağlantı, cursor ve bellek alanları mockup alt şeridinde
görünür.
"""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.status_bar import (
    EMPTY_VALUE,
    READY_TEXT,
    AppStatusBar,
    MemoryUsage,
    read_memory_usage,
)

pytestmark = pytest.mark.gui

EXPECTED_FIELDS = ["status", "file", "connection", "recording", "cursor", "memory"]


@pytest.fixture()
def bar(qtbot: QtBot) -> AppStatusBar:
    widget = AppStatusBar()
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


# -- alanlar ---------------------------------------------------------------


def test_all_five_fields_exist(bar: AppStatusBar) -> None:
    assert bar.field_names() == EXPECTED_FIELDS


def test_window_uses_the_status_bar(window: MainWindow) -> None:
    assert isinstance(window.status, AppStatusBar)
    assert window.statusBar() is window.status
    assert window.status.objectName() == "status_bar"


def test_empty_fields_show_a_placeholder_not_nothing(bar: AppStatusBar) -> None:
    """Değeri olmayan alan gizlenmiyor; boş mu yok mu ayırt edilebiliyor."""
    assert bar.field_value("status") == READY_TEXT
    for name in ("file", "connection", "cursor", "memory"):
        assert bar.field_value(name) == EMPTY_VALUE


def test_set_field_and_status(bar: AppStatusBar) -> None:
    bar.set_field("file", "D:/kayitlar/ornek.bin")
    assert bar.field_value("file") == "D:/kayitlar/ornek.bin"

    bar.set_status("Parsing...")
    assert bar.field_value("status") == "Parsing..."

    bar.set_status("")
    assert bar.field_value("status") == READY_TEXT, "bos durum Ready'e doner"


def test_empty_value_falls_back_to_placeholder(bar: AppStatusBar) -> None:
    bar.set_field("connection", "")
    assert bar.field_value("connection") == EMPTY_VALUE


def test_unknown_field_raises(bar: AppStatusBar) -> None:
    with pytest.raises(KeyError, match="Tanimsiz durum alani"):
        bar.field_value("yok")
    with pytest.raises(KeyError, match="Tanimsiz durum alani"):
        bar.set_field("yok", "x")


# -- cursor ----------------------------------------------------------------


def test_cursor_time_is_formatted(bar: AppStatusBar) -> None:
    bar.set_cursor_time(12.3456)
    assert bar.field_value("cursor") == "t = 12.346 s"


def test_cursor_time_can_be_cleared(bar: AppStatusBar) -> None:
    bar.set_cursor_time(1.0)
    bar.set_cursor_time(None)
    assert bar.field_value("cursor") == EMPTY_VALUE


def test_playback_updates_cursor_field(window: MainWindow) -> None:
    repo = MockRecordingRepository(duration_s=60.0)
    window.set_recording(repo.metadata(), repo.channels())

    window.playback_dock.set_position(30.0)
    assert window.status.field_value("cursor") == "t = 30.000 s"


# -- bellek ----------------------------------------------------------------


def test_memory_text_and_bar(bar: AppStatusBar) -> None:
    usage = MemoryUsage(used_bytes=int(1.2 * 1024**3), total_bytes=8 * 1024**3)
    bar.update_memory(usage)

    assert bar.field_value("memory") == "Memory: 1.2 / 8.0 GB"
    assert bar.memory_bar.value() == 15


def test_memory_falls_back_when_unavailable(bar: AppStatusBar) -> None:
    """Ölçüm alınamazsa gösterge boşalır, uygulama etkilenmez."""
    bar.update_memory(MemoryUsage(1, 2))
    bar.memory_label.setText("bir sey")

    bar.update_memory(None)
    measured = read_memory_usage()
    if measured is None:
        assert bar.field_value("memory") == EMPTY_VALUE
    else:
        assert bar.field_value("memory").startswith("Memory:")


def test_memory_ratio_handles_zero_total() -> None:
    assert MemoryUsage(used_bytes=5, total_bytes=0).ratio == 0.0


def test_real_measurement_is_plausible() -> None:
    """Windows'ta gerçek ölçüm alınabilmeli ve makul değerler vermeli.

    Hedef platform Windows olduğu için burada `skip` kullanılmıyor: ölçümün
    çalışmaması gerçek bir hatadır ve testin bunu göstermesi gerekir.
    """
    usage = read_memory_usage()
    if sys.platform != "win32":
        pytest.skip("bellek olcumu yalnizca Windows'ta uygulandi")
    assert usage is not None, "Windows'ta bellek olcumu alinamadi"
    assert usage.used_bytes > 0
    assert usage.total_bytes > usage.used_bytes
    assert 0.0 < usage.ratio < 1.0


def test_recording_fills_file_field(window: MainWindow) -> None:
    repo = MockRecordingRepository(duration_s=10.0)
    window.set_recording(repo.metadata(), repo.channels())
    assert window.status.field_value("file") == "Simülasyon"

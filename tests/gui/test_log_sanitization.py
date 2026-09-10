"""Yükleme/analiz mesajları alt loga bağlı — `F3-053`.

Kabul: zaman damgalı durum mesajları görünür; ham payload loga düşmez.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.docks.bottom_panel import (
    MAX_LOG_MESSAGE_LEN,
    BottomPanelDock,
    sanitize_log_message,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
_TIMESTAMPED = re.compile(r"^\[\d\d:\d\d:\d\d\] ")


# -- sanitize_log_message ---------------------------------


def test_short_status_message_is_unchanged() -> None:
    assert sanitize_log_message("Yuklendi: kayit.bin") == "Yuklendi: kayit.bin"


def test_newlines_and_tabs_collapse_to_single_spaces() -> None:
    assert sanitize_log_message("line1\nline2\tline3\r\nline4") == "line1 line2 line3 line4"


def test_control_and_binary_bytes_are_stripped() -> None:
    dirty = "payload\x00\x01\x02\x1f end"
    assert sanitize_log_message(dirty) == "payload end"


def test_a_long_dump_is_truncated_with_a_marker() -> None:
    result = sanitize_log_message("x" * 5000)

    assert len(result) == MAX_LOG_MESSAGE_LEN
    assert result.endswith("(kesildi)")


def test_whitespace_runs_are_collapsed() -> None:
    assert sanitize_log_message("a     b\t\t  c") == "a b c"


# -- BottomPanelDock.append_log --------------------------


@pytest.fixture()
def dock(qtbot: QtBot) -> BottomPanelDock:
    widget = BottomPanelDock()
    qtbot.addWidget(widget)
    return widget


def test_append_log_prefixes_a_timestamp(dock: BottomPanelDock) -> None:
    dock.append_log("Kayit acildi: kayit.bin")

    line = dock.log_lines()[-1]
    assert _TIMESTAMPED.match(line)
    assert line.endswith("Kayit acildi: kayit.bin")


def test_append_log_never_writes_a_raw_payload(dock: BottomPanelDock) -> None:
    dock.append_log("HEADER" + "\x00\xff" * 4000 + "TAIL")

    lines = dock.log_lines()
    assert len(lines) == 1  # tek satir, ham dokuntu satirlara bolunmedi
    assert "\x00" not in lines[0]
    assert len(lines[0]) <= MAX_LOG_MESSAGE_LEN + len("[00:00:00] ")
    assert "(kesildi)" in lines[0]


# -- uctan uca: yukleme lifecycle mesajlari -------------


def test_load_lifecycle_produces_only_clean_timestamped_lines(qtbot: QtBot, tmp_path: Path) -> None:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()

    lines = win.bottom_dock.log_lines()
    assert lines, "yükleme durum mesajları görünmeli"
    for line in lines:
        assert _TIMESTAMPED.match(line), line
        assert "\x00" not in line
        assert len(line) <= MAX_LOG_MESSAGE_LEN + len("[00:00:00] ")
    joined = "\n".join(lines)
    assert "Yuklendi:" in joined
    assert "kanal bulundu" in joined

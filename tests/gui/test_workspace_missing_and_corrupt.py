"""Eksik kaynak ve bozuk workspace davranışı — `F3-070`.

Kabul: eksik dosya bildirilir; açık oturum kontrolsüz silinmez.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.model import WorkspaceError, WorkspaceModel

pytestmark = pytest.mark.gui

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"


def _open_recording_window(qtbot: QtBot, tmp_path: Path) -> tuple[MainWindow, Path]:
    target = tmp_path / "kayit.bin"
    shutil.copyfile(FIXTURE, target)
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win, target


def test_missing_source_is_reported_not_swallowed(qtbot: QtBot, tmp_path: Path) -> None:
    author, target = _open_recording_window(qtbot, tmp_path)
    author.open_channel("ch0")
    saved = author.save_workspace(tmp_path / "s.json")

    # Kaynağı sil: geri yükleyen pencere onu bulamamalı ama bildirmeli.
    # `F4-054`: kaynak bellek esleniyor; silmeden once birakilmali.
    author.close_recordings()
    target.unlink()

    reader = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(reader)
    reported: list[list[str]] = []
    reader.restore_workspace(saved, on_missing_sources=reported.append)

    assert len(reader.last_missing_sources) == 1
    assert Path(reader.last_missing_sources[0]).name == "kayit.bin"
    assert reported == [reader.last_missing_sources]
    log = "\n".join(reader.bottom_dock.log_lines())
    assert "bulunamadi" in log and "kayit.bin" in log


def test_all_present_leaves_missing_list_empty(qtbot: QtBot, tmp_path: Path) -> None:
    author, _target = _open_recording_window(qtbot, tmp_path)
    author.open_channel("ch0")
    saved = author.save_workspace(tmp_path / "s.json")

    # Aynı pencere (dosya hâlâ yerinde) geri yükler.
    author.restore_workspace(saved)
    assert author.last_missing_sources == []


def test_corrupt_workspace_does_not_disturb_the_open_session(qtbot: QtBot, tmp_path: Path) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=5.0))
    win.open_channel("ch0")
    win.plot_panel.set_x_range(1.0, 3.0)

    before_channels = win.plot_panel.plotted_channel_ids()
    before_range = win.plot_panel.visible_x_range()

    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(WorkspaceError):
        win.restore_workspace(bad)

    # Açık oturum hiç değişmedi.
    assert win.plot_panel.plotted_channel_ids() == before_channels
    assert win.plot_panel.visible_x_range() == before_range
    assert any("korundu" in line for line in win.bottom_dock.log_lines())


def test_semantically_invalid_workspace_is_also_rejected_safely(
    qtbot: QtBot, tmp_path: Path
) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=5.0))
    win.open_channel("ch1")
    before = win.plot_panel.plotted_channel_ids()

    doc = WorkspaceModel().to_dict()
    doc["layout_mode"] = "cascade"  # geçersiz
    bad = tmp_path / "invalid.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(WorkspaceError):
        win.restore_workspace(bad)

    assert win.plot_panel.plotted_channel_ids() == before

"""Run BIT Analysis eylemi kayıt analizine bağlı — `F3-052`.

Kabul: seçili kaydın BIT özeti yenilenir; cihaz komutu gönderilmez.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


class _CountingLoader:
    """Gerçek `.bin` okuyucuyu sarar, çağrı sayar."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, path: Path) -> FileRecordingRepository:
        self.calls += 1
        repo = FileRecordingRepository()
        repo.open(path)
        return repo


@pytest.fixture()
def window_and_loader(qtbot: QtBot, tmp_path: Path) -> tuple[MainWindow, _CountingLoader]:
    loader = _CountingLoader()
    win = MainWindow(error_notifier=lambda _p, _m: None, loader=loader)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win, loader


def test_run_button_refreshes_the_bit_summary(
    window_and_loader: tuple[MainWindow, _CountingLoader],
) -> None:
    win, _loader = window_and_loader
    card = win.right_dock.bit_status
    assert card.row_count() > 0
    badge_before = card.badge_text()

    card.run_button.click()

    assert card.row_count() > 0
    assert card.badge_text() == badge_before
    assert any("BIT ozeti yenilendi" in line for line in win.bottom_dock.log_lines())


def test_refresh_does_not_reopen_the_file_or_hit_a_device(
    window_and_loader: tuple[MainWindow, _CountingLoader],
) -> None:
    win, loader = window_and_loader
    assert loader.calls == 1  # yalnız açılışta

    win.refresh_bit_analysis()
    win.refresh_bit_analysis()

    assert loader.calls == 1, "yenileme dosyayı yeniden açmaz / cihaza gitmez"


def test_refresh_without_an_open_recording_is_reported(qtbot: QtBot) -> None:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)

    win.refresh_bit_analysis()

    assert any("acik kayit yok" in line for line in win.bottom_dock.log_lines())


def test_run_button_updates_the_last_update_label(
    window_and_loader: tuple[MainWindow, _CountingLoader],
) -> None:
    win, _loader = window_and_loader
    card = win.right_dock.bit_status

    card.run_button.click()

    assert card.last_update.text().startswith("Last Update: ")
    assert "—" not in card.last_update.text()

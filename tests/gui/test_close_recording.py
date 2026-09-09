"""Dosya kapatma ve bağlı panel temizliği — `F3-007`.

Kabul: kapatılan dosyanın sorguları iptal olur; diğer kayıtlar çalışır.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.file_loader import default_loader
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    return win


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(VALID_FIXTURE, target)
    return target


def _open(qtbot: QtBot, window: MainWindow, paths: list[Path]) -> None:
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()


# -- kapatilan dosyanin sorgulari iptal olur -------------------------------


def test_closing_releases_the_snapshot_so_no_query_can_run(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kabul kriteri (ilk yarı): kapatılan dosyanın sorguları iptal olur."""
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])
    repository = window.loaded_results[0].repository
    assert repository is not None

    window.action("action_close").trigger()

    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        repository.metadata()
    window.close()


def test_opening_a_channel_after_close_is_a_no_op(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kapatılmış snapshot'a sorgu gönderilmez; çağrı sessizce döner."""
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])
    window.action("action_close").trigger()

    window.open_channel("ch0")  # istisna firlatmamali

    assert not window.center_shows_plot
    window.close()


def test_close_cancels_an_in_flight_load(qtbot: QtBot, tmp_path: Path) -> None:
    """Süren yükleme iptal edilir: kapatılan görünüm geri gelmez."""

    def slow_loader(path: Path) -> FileRecordingRepository:
        time.sleep(0.3)
        return default_loader(path)

    window = MainWindow(loader=slow_loader, error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)

    first = _copy(tmp_path, "ilk.bin")
    _open(qtbot, window, [first])

    later = [_copy(tmp_path, f"sonra{i}.bin") for i in range(3)]
    window.file_open._dialog = lambda _p, _s: [str(path) for path in later]  # type: ignore[assignment]
    window.action("action_open").trigger()
    request_id = window.active_load_request_id

    window.action("action_close").trigger()
    assert window.file_loader.is_cancelled(request_id)

    deadline = time.monotonic() + 10
    while window.active_load_request_id and time.monotonic() < deadline:
        qtbot.wait(50)
    qtbot.wait(200)

    assert window.loaded_results == ()
    window.close()


# -- bagli panel temizligi -------------------------------------------------


def test_closing_clears_the_bound_panels(qtbot: QtBot, window: MainWindow, tmp_path: Path) -> None:
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])
    window.open_channel("ch0")
    assert window.left_dock.visible_channel_ids()

    window.action("action_close").trigger()

    assert window.left_dock.visible_channel_ids() == []
    assert window.left_dock.summary_value("File") == "—"
    assert window.bottom_dock.event_row_count() == 0
    assert not window.center_shows_plot
    window.close()


def test_close_action_is_disabled_when_nothing_is_open(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    assert not window.action("action_close").isEnabled()

    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])
    assert window.action("action_close").isEnabled()

    window.action("action_close").trigger()
    assert not window.action("action_close").isEnabled()
    assert not window.action("action_export").isEnabled()
    window.close()


def test_closing_with_nothing_open_is_harmless(qtbot: QtBot, window: MainWindow) -> None:
    window.close_active_recording()  # istisna firlatmamali
    assert window.left_dock.visible_channel_ids() == []
    window.close()


# -- diger kayitlar CALISIR ------------------------------------------------


def test_closing_one_recording_promotes_the_next_one(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kabul kriteri (ikinci yarı): diğer kayıtlar çalışır."""
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")
    _open(qtbot, window, [first, second])
    assert "birinci.bin" in window.left_dock.summary_value("File")

    window.action("action_close").trigger()

    # Ikinci kayit etkin gorunum oldu ve sorgulanabiliyor.
    assert "ikinci.bin" in window.left_dock.summary_value("File")
    assert window.left_dock.visible_channel_ids() == [f"ch{i}" for i in range(8)]
    window.open_channel("ch0")
    assert window.center_shows_plot
    assert window.action("action_close").isEnabled()
    window.close()


def test_second_recording_survives_the_first_being_closed(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kapatma yalnız hedef kaydın snapshot'ını bırakır."""
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")
    _open(qtbot, window, [first, second])
    first_repository = window.loaded_results[0].repository
    second_repository = window.loaded_results[1].repository
    assert first_repository is not None
    assert second_repository is not None

    window.action("action_close").trigger()

    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        first_repository.metadata()
    # Digeri hala calisiyor.
    assert second_repository.metadata().record_count == 8
    window.close()


def test_closing_both_recordings_empties_the_workspace(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")
    _open(qtbot, window, [first, second])

    window.action("action_close").trigger()
    window.action("action_close").trigger()

    assert window.left_dock.visible_channel_ids() == []
    assert not window.action("action_close").isEnabled()
    window.close()


def test_externally_provided_repository_is_not_closed_by_the_window(
    qtbot: QtBot, window: MainWindow
) -> None:
    """Pencerenin sahibi olmadığı kaynak (simülasyon) kapatılmaz, yalnız bırakılır."""
    repository = MockRecordingRepository()
    window.set_repository(repository)

    window.action("action_close").trigger()

    assert window.left_dock.visible_channel_ids() == []
    # Disaridan verilen kaynak hala kullanilabilir; kapatma sorumlulugu
    # cagirana ait.
    assert repository.channels()
    window.close()

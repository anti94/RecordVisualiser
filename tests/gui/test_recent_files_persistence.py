"""Son dosyalar ve varsayılan klasörü kaydetme — `F3-008`.

Kabul: yeniden açılışta liste korunur; eksik dosya anlaşılır hata verir.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.load_errors import LoadErrorMessage
from sonar_analyzer.settings.store import AppSettings
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(VALID_FIXTURE, target)
    return target


def _open(qtbot: QtBot, window: MainWindow, paths: list[Path]) -> None:
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()


class _FakeStore:
    """Gerçek ayar dosyasına dokunmayan sahte kalıcı depo."""

    def __init__(self) -> None:
        self.saved: list[AppSettings] = []

    def write(self, settings: AppSettings) -> Path:
        self.saved.append(settings)
        return Path("bellek-ici")


# -- listeye ekleme ve kalicilik ---------------------------------------------


def test_opening_a_file_persists_it_to_recent_files(qtbot: QtBot, tmp_path: Path) -> None:
    store = _FakeStore()
    window = MainWindow(settings_writer=store.write, error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = _copy(tmp_path, "kayit.bin")

    _open(qtbot, window, [target])

    assert window.recent_files == (str(target),)
    assert store.saved
    assert store.saved[-1].recent_files == [str(target)]
    window.close()


def test_recent_list_survives_a_simulated_restart(qtbot: QtBot, tmp_path: Path) -> None:
    """Kabul kriteri (ilk yarı): yeniden açılışta liste korunur."""
    store = _FakeStore()
    first_window = MainWindow(settings_writer=store.write, error_notifier=lambda _p, _m: None)
    qtbot.addWidget(first_window)
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, first_window, [target])
    persisted = store.saved[-1]
    first_window.close()

    # "Yeniden acilis": ayni ayarlarla yeni bir pencere kuruluyor -- app.py
    # bunu load_settings() sonucuyla yapiyor.
    second_window = MainWindow(settings=persisted, error_notifier=lambda _p, _m: None)
    qtbot.addWidget(second_window)

    assert second_window.recent_files == (str(target),)
    second_window.close()


def test_multi_selection_preserves_order_in_recent_files(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    first = _copy(tmp_path, "a.bin")
    second = _copy(tmp_path, "b.bin")

    _open(qtbot, window, [first, second])

    assert window.recent_files == (str(first), str(second))
    window.close()


def test_reopening_a_file_moves_it_to_the_front(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    first = _copy(tmp_path, "a.bin")
    second = _copy(tmp_path, "b.bin")

    _open(qtbot, window, [first])
    _open(qtbot, window, [second])
    _open(qtbot, window, [first])

    assert window.recent_files == (str(first), str(second))
    window.close()


# -- varsayilan klasor --------------------------------------------------


def test_opening_a_file_updates_the_default_directory(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = _copy(tmp_path, "kayit.bin")

    _open(qtbot, window, [target])

    assert window.file_open.last_directory == str(target.parent)


def test_startup_seeds_the_picker_from_saved_settings(tmp_path: Path) -> None:
    settings = AppSettings(last_directory=str(tmp_path))
    window = MainWindow(settings=settings, error_notifier=lambda _p, _m: None)

    assert window.file_open.last_directory == str(tmp_path)
    window.close()


def test_startup_falls_back_to_most_recent_files_directory(tmp_path: Path) -> None:
    recent_path = str(tmp_path / "eski.bin")
    settings = AppSettings(recent_files=[recent_path])
    window = MainWindow(settings=settings, error_notifier=lambda _p, _m: None)

    assert window.file_open.last_directory == str(tmp_path)
    window.close()


# -- eksik dosya: anlasilir hata + listeden cikarma --------------------------


def test_missing_file_gives_an_understandable_error(qtbot: QtBot, tmp_path: Path) -> None:
    """Kabul kriteri (ikinci yarı): eksik dosya anlaşılır hata verir."""
    shown: list[LoadErrorMessage] = []
    window = MainWindow(error_notifier=lambda _p, m: shown.append(m))
    qtbot.addWidget(window)

    window.open_recent(tmp_path / "silinmis.bin")
    while window.active_load_request_id:
        qtbot.wait(20)

    assert len(shown) == 1
    assert "bulunamadi" in shown[0].user_text.lower()
    window.close()


def test_missing_recent_file_is_dropped_from_the_list(qtbot: QtBot, tmp_path: Path) -> None:
    """Kalıcı olarak yok olan dosya son dosyalar listesinden çıkarılır."""
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = _copy(tmp_path, "kayit.bin")
    _open(qtbot, window, [target])
    assert window.recent_files == (str(target),)

    target.unlink()
    window.open_recent(target)
    while window.active_load_request_id:
        qtbot.wait(20)

    assert window.recent_files == ()
    window.close()


def test_settings_write_failure_does_not_crash_the_window(qtbot: QtBot, tmp_path: Path) -> None:
    """Ayar dosyasına yazılamazsa uygulama durmaz, yalnız log'a düşer."""

    def failing_writer(_settings: AppSettings) -> Path:
        raise OSError("disk dolu")

    window = MainWindow(settings_writer=failing_writer, error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = _copy(tmp_path, "kayit.bin")

    _open(qtbot, window, [target])  # istisna firlatmamali

    assert window.left_dock.visible_channel_ids()
    assert "Ayarlar kaydedilemedi" in "\n".join(window.bottom_dock.log_lines())
    window.close()


def test_settings_are_immutable_between_windows(tmp_path: Path) -> None:
    """Bir pencereye verilen `AppSettings` başka bir pencereyi etkilemez."""
    shared = AppSettings(recent_files=["C:\\ortak.bin"])
    first = MainWindow(settings=shared, error_notifier=lambda _p, _m: None)
    second = MainWindow(settings=replace(shared), error_notifier=lambda _p, _m: None)

    assert first.recent_files == second.recent_files == ("C:\\ortak.bin",)
    first.close()
    second.close()

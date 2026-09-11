"""Pencere konumunun kaydedilmesi ve geri yüklenmesi — `F4-083`.

Kabul: monitör çıkartılınca pencere görünür alana geri gelir.

Saf geometri `tests/unit/test_window_placement.py`'de denetlenir; burada
pencerenin o geometriyi gerçekten **kaydedip uyguladığı** sınanır. Ekran
listesi enjekte edilir, böylece "ikinci monitör söküldü" durumu test
makinesinin donanımından bağımsız kurulabilir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pathlib import Path

from pytestqt.qtbot import QtBot

from sonar_analyzer.settings.store import AppSettings
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.window_placement import Rect, encode_geometry, visible_area

pytestmark = pytest.mark.gui

PRIMARY = Rect(0, 0, 1920, 1080)
SECONDARY = Rect(1920, 0, 1920, 1080)
#: İkinci monitörde kaydedilmiş bir pencere.
ON_SECONDARY = Rect(2200, 200, 800, 600)


class _Recorder:
    """Ayar yazıcısı yerine geçer; yazılan her sürümü saklar."""

    def __init__(self) -> None:
        self.written: list[AppSettings] = []

    def __call__(self, settings: AppSettings) -> Path:
        self.written.append(settings)
        return Path("settings.json")


def _window(qtbot: QtBot, settings: AppSettings) -> tuple[MainWindow, _Recorder]:
    recorder = _Recorder()
    window = MainWindow(settings=settings, settings_writer=recorder)
    qtbot.addWidget(window)
    return window, recorder


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    return _window(qtbot, AppSettings())[0]


# --------------------------------------------------------------------------- #
# kaydetme
# --------------------------------------------------------------------------- #


def test_a_fresh_install_has_no_saved_placement(win: MainWindow) -> None:
    assert win.restore_window_placement([PRIMARY]) is False


def test_the_current_placement_is_readable(win: MainWindow) -> None:
    win.setGeometry(120, 80, 900, 700)
    assert win.current_placement() == Rect(120, 80, 900, 700)


def test_remembering_writes_the_placement_to_settings(qtbot: QtBot) -> None:
    window, recorder = _window(qtbot, AppSettings())
    window.setGeometry(120, 80, 900, 700)
    window.remember_window_placement()
    assert recorder.written
    assert recorder.written[-1].window_geometry == "120,80,900,700"


def test_remembering_an_unchanged_placement_writes_nothing(qtbot: QtBot) -> None:
    window, recorder = _window(qtbot, AppSettings())
    window.setGeometry(120, 80, 900, 700)
    window.remember_window_placement()
    before = len(recorder.written)
    window.remember_window_placement()
    assert len(recorder.written) == before


# --------------------------------------------------------------------------- #
# geri yukleme ve SINIRLAMA
# --------------------------------------------------------------------------- #


def test_a_placement_on_an_existing_monitor_is_applied_as_is(qtbot: QtBot) -> None:
    win, _recorder = _window(qtbot, AppSettings(window_geometry=encode_geometry(ON_SECONDARY)))

    assert win.restore_window_placement([PRIMARY, SECONDARY]) is True

    assert win.current_placement() == ON_SECONDARY


def test_a_placement_on_a_removed_monitor_comes_back(qtbot: QtBot) -> None:
    """Kabul kriterinin kendisi: ikinci monitör söküldü."""
    win, _recorder = _window(qtbot, AppSettings(window_geometry=encode_geometry(ON_SECONDARY)))

    assert win.restore_window_placement([PRIMARY]) is True

    placed = win.current_placement()
    assert placed != ON_SECONDARY
    assert visible_area(placed, [PRIMARY]) == placed.area
    assert (placed.width, placed.height) == (800, 600)


def test_the_recovery_is_explained_in_the_log(qtbot: QtBot) -> None:
    win, _recorder = _window(qtbot, AppSettings(window_geometry=encode_geometry(ON_SECONDARY)))
    win.restore_window_placement([PRIMARY])
    assert any("görünür alanda değildi" in line for line in win.bottom_dock.log_lines())


def test_no_message_when_nothing_had_to_move(qtbot: QtBot) -> None:
    win, _recorder = _window(qtbot, AppSettings(window_geometry=encode_geometry(ON_SECONDARY)))
    win.restore_window_placement([PRIMARY, SECONDARY])
    assert not any("görünür alanda değildi" in line for line in win.bottom_dock.log_lines())


def test_a_broken_record_is_ignored(qtbot: QtBot) -> None:
    win, _recorder = _window(qtbot, AppSettings(window_geometry="bozuk"))
    assert win.restore_window_placement([PRIMARY]) is False


def test_without_any_screen_nothing_is_applied(qtbot: QtBot) -> None:
    win, _recorder = _window(qtbot, AppSettings(window_geometry=encode_geometry(ON_SECONDARY)))
    assert win.restore_window_placement([]) is False


def test_a_full_round_trip_survives_the_monitor_being_removed(qtbot: QtBot) -> None:
    """Kaydet -> monitör sökül -> aç: pencere görünür yerde."""
    first, recorder = _window(qtbot, AppSettings())
    first.setGeometry(ON_SECONDARY.x, ON_SECONDARY.y, ON_SECONDARY.width, ON_SECONDARY.height)
    first.remember_window_placement()

    second, _ = _window(qtbot, recorder.written[-1])
    assert second.restore_window_placement([PRIMARY]) is True

    placed = second.current_placement()
    assert visible_area(placed, [PRIMARY]) == placed.area


def test_the_real_screen_list_is_readable(win: MainWindow) -> None:
    """Gerçek ekranlar okunabiliyor; testler bunu enjekte edebiliyor."""
    screens = win.available_screens()
    assert all(screen.width > 0 and screen.height > 0 for screen in screens)

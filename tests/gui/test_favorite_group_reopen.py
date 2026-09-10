"""Favori grubu grafiğe yeniden açma — `F3-017`.

Kabul: grup tekrar açılır; bu kayıtta bulunamayan kanal ayrı raporlanır.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.settings.store import AppSettings, FavoriteGroup
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


class _RecordingWriter:
    """`settings_writer` yerine geçer; yazılan son ayarı tutar."""

    def __init__(self) -> None:
        self.last: AppSettings | None = None
        self.calls = 0

    def __call__(self, settings: AppSettings) -> Path:
        self.last = settings
        self.calls += 1
        return Path("bellekte.json")


def _open_window(
    qtbot: QtBot, tmp_path: Path, settings: AppSettings | None = None
) -> tuple[MainWindow, _RecordingWriter]:
    writer = _RecordingWriter()
    win = MainWindow(
        error_notifier=lambda _p, _m: None,
        settings=settings,
        settings_writer=writer,
    )
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win, writer


# -- kaydetme: secim kalici hale gelir -----------------------------------


def test_save_favorite_group_from_tree_selection_persists(qtbot: QtBot, tmp_path: Path) -> None:
    win, writer = _open_window(qtbot, tmp_path)
    for channel_id in ("ch0", "ch6"):
        item = win.left_dock.item_for_channel(channel_id)
        assert item is not None
        item.setSelected(True)

    win.save_favorite_group("Seyir")

    assert "Seyir" in win.favorite_group_names
    assert writer.last is not None
    assert writer.last.favorite_groups == [
        FavoriteGroup(name="Seyir", channel_ids=["ch0", "ch6"]),
    ]


def test_save_favorite_group_with_explicit_ids(qtbot: QtBot, tmp_path: Path) -> None:
    win, writer = _open_window(qtbot, tmp_path)

    win.save_favorite_group("Akustik", ["ch5"])

    assert writer.last is not None
    assert writer.last.favorite_groups == [FavoriteGroup(name="Akustik", channel_ids=["ch5"])]


def test_save_with_no_selection_and_empty_plot_does_nothing(qtbot: QtBot, tmp_path: Path) -> None:
    win, writer = _open_window(qtbot, tmp_path)

    calls_before = writer.calls
    win.save_favorite_group("Bos")

    assert win.favorite_group_names == ()
    assert writer.calls == calls_before, "kanal yoksa ayar yeniden yazilmamali"
    assert any("kanal secili degil" in line for line in win.bottom_dock.log_lines())


# -- yeniden acma: grup cizilir, eksik kanal ayri raporlanir ------------


def test_open_favorite_group_plots_found_channels(qtbot: QtBot, tmp_path: Path) -> None:
    settings = AppSettings(
        favorite_groups=[FavoriteGroup(name="Seyir", channel_ids=["ch0", "ch6"])]
    )
    win, _writer = _open_window(qtbot, tmp_path, settings)

    win.open_favorite_group("Seyir")

    assert win.plot_panel.plotted_channel_ids() == ["ch0", "ch6"]
    assert win.center_shows_plot


def test_open_favorite_group_reports_missing_channels_separately(
    qtbot: QtBot, tmp_path: Path
) -> None:
    settings = AppSettings(
        favorite_groups=[FavoriteGroup(name="Karma", channel_ids=["ch0", "yok-1", "ch6", "yok-2"])]
    )
    win, _writer = _open_window(qtbot, tmp_path, settings)

    win.open_favorite_group("Karma")

    assert win.plot_panel.plotted_channel_ids() == ["ch0", "ch6"]
    log = "\n".join(win.bottom_dock.log_lines())
    assert "2 kanal grafige eklendi" in log
    assert "2 kanal bu kayitta yok" in log
    assert "yok-1" in log and "yok-2" in log


def test_open_unknown_favorite_group_is_reported(qtbot: QtBot, tmp_path: Path) -> None:
    win, _writer = _open_window(qtbot, tmp_path)

    win.open_favorite_group("HicYok")

    assert win.plot_panel.plotted_channel_ids() == []
    assert any("bulunamadi: HicYok" in line for line in win.bottom_dock.log_lines())


def test_saved_group_survives_a_reload_and_reopens(qtbot: QtBot, tmp_path: Path) -> None:
    win, writer = _open_window(qtbot, tmp_path)
    win.save_favorite_group("Seyir", ["ch0", "ch6"])
    assert writer.last is not None

    # `F4-054`: kaynak bellek esleniyor; ikinci pencere ayni dosyayi yeniden
    # kopyalamadan once ilk pencere kilidi birakmali.
    win.close_recordings()

    # Kaydedilen ayarla yeni bir pencere: grup hâlâ açılabilir olmalı.
    win2, _writer2 = _open_window(qtbot, tmp_path, writer.last)
    win2.open_favorite_group("Seyir")

    assert win2.plot_panel.plotted_channel_ids() == ["ch0", "ch6"]

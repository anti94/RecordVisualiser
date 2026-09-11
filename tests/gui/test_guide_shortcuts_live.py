"""Kılavuz kısayolları çalışan pencereyle eşleşiyor mu — `F6-028`.

Kabul: **Bölüm 16 kısayolları paketli uygulamadaki davranışla eşleşir.**

`tests/unit/test_guide_shortcuts.py` kılavuzu *kaynaktaki tablolara*
(`MENU_SPECS`, `SHORTCUTS`) karşı denetler. Bu yeterli değildir: bir
tablo tanımlanıp pencereye hiç kurulmamış olabilir, ya da pencere
tabloda olmayan bir tuşu doğrudan bağlayabilir.

Bu test döngüyü kapatır: **gerçekten kurulmuş** `QAction` ve `QShortcut`
nesnelerinin tuş dizilerini çalışan pencereden toplar ve kılavuzun
tablosuyla birebir karşılaştırır. Paketli uygulama da aynı `MainWindow`
kurulumunu kullandığı için, burada eşleşen davranış pakette de eşleşir.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtGui import QAction, QShortcut
from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide" / "klavye-ve-mouse.md"


def _documented_shortcuts() -> set[str]:
    """Kılavuz tablolarının ilk sütunundaki tuş dizileri."""
    found: set[str] = set()
    for line in GUIDE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            found.add(match.group(1))
    return found


def _installed_shortcuts(window: MainWindow) -> set[str]:
    """Pencerede gerçekten kurulu tuş dizileri (`QAction` + `QShortcut`)."""
    installed: set[str] = set()
    for action in window.findChildren(QAction):
        text = action.shortcut().toString()
        if text:
            installed.add(text)
    for shortcut in window.findChildren(QShortcut):
        text = shortcut.key().toString()
        if text:
            installed.add(text)
    return installed


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


def test_every_documented_shortcut_is_installed_on_the_running_window(
    window: MainWindow,
) -> None:
    """Kılavuzdaki bir tuş pencerede kurulu değilse kullanıcı boşa basar."""
    missing = _documented_shortcuts() - _installed_shortcuts(window)
    assert not missing, f"kilavuzda var, pencerede kurulu degil: {sorted(missing)}"


def test_every_installed_shortcut_is_documented(window: MainWindow) -> None:
    """Pencerede kurulu olup belgelenmemiş bir tuş, gizli davranıştır."""
    extra = _installed_shortcuts(window) - _documented_shortcuts()
    assert not extra, f"pencerede kurulu, kilavuzda yok: {sorted(extra)}"


def test_the_comparison_is_not_vacuous(window: MainWindow) -> None:
    """İki boş kümeyi karşılaştırmak her zaman geçerdi."""
    installed = _installed_shortcuts(window)
    assert len(installed) >= 20
    assert installed == _documented_shortcuts()


def test_the_unimplemented_command_palette_key_is_really_absent(
    window: MainWindow,
) -> None:
    """`Ctrl+K` kılavuzda "yok" diye yazıyor; pencerede de olmamalı."""
    assert "Ctrl+K" not in _installed_shortcuts(window)


def test_ctrl_e_is_installed_on_the_export_action_not_an_event_panel(
    window: MainWindow,
) -> None:
    """Bölüm 16'dan sapma gerçek: `Ctrl+E` dışa aktarmaya bağlı."""
    owners = [
        action.objectName()
        for action in window.findChildren(QAction)
        if action.shortcut().toString() == "Ctrl+E"
    ]
    assert owners == ["action_export"]

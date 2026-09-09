"""Uygulama girişi ve temiz kapanış — `F1-007`.

Kabul: pencere komutla açılır, kapanışta süreç sonlanır. Süreç sonlanmasını
gerçekten kanıtlamak için giriş noktası **ayrı bir süreçte** çalıştırılır ve
kendiliğinden çıkması beklenir; aynı süreçte test etmek asılı kalan bir olay
döngüsünü yakalayamazdı.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from sonar_analyzer import __version__
from sonar_analyzer.app import EXIT_OK, build_parser, main

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import WINDOW_TITLE, MainWindow

TIMEOUT_SECONDS = 60


def test_version_flag_does_not_need_qt() -> None:
    """--version, Qt yüklenmeden yanıt verir ve 0 ile çıkar."""
    result = subprocess.run(
        [sys.executable, "-m", "sonar_analyzer", "--version"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == EXIT_OK
    assert __version__ in result.stdout


def test_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.no_window is False


@pytest.mark.gui
def test_main_window_opens_and_closes(qtbot: QtBot) -> None:
    """Pencere açılır, başlığı doğrudur ve kapanır."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)
    assert window.isVisible()
    assert window.windowTitle() == WINDOW_TITLE
    # Durum artik gecici mesaj degil, kalici alanda (F1-028).
    assert window.status.field_value("status") == "Ready"

    assert window.close()
    assert not window.isVisible()


@pytest.mark.gui
def test_main_no_window_returns_ok(qapp: object) -> None:
    """--no-window yolu pencere göstermeden 0 döndürür."""
    del qapp  # QApplication'in var olmasi yeterli
    assert main(["--no-window"]) == EXIT_OK


@pytest.mark.gui
def test_process_exits_cleanly() -> None:
    """Ayrı süreçte başlatılan uygulama kendiliğinden sonlanır."""
    result = subprocess.run(
        [sys.executable, "-m", "sonar_analyzer", "--no-window"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env={"QT_QPA_PLATFORM": "offscreen", **_inherited_env()},
        check=False,
    )
    assert result.returncode == EXIT_OK, result.stderr


def _inherited_env() -> dict[str, str]:
    import os

    return dict(os.environ)

"""Pencere yaşam döngüsü kontrolü — `F1-005`.

Amaç, GUI test altyapısının (pytest-qt + offscreen Qt) gerçekten çalıştığını
kanıtlamaktır: pencere oluşur, gösterilir, kapanır ve nesne yok edilir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from pytestqt.qtbot import QtBot

pytestmark = pytest.mark.gui


def test_qapplication_instance_exists(qapp: QApplication) -> None:
    """pytest-qt tek bir QApplication örneği sağlar."""
    assert QApplication.instance() is qapp


def test_window_shows_and_closes(qtbot: QtBot) -> None:
    """Pencere açılır, görünür olur ve kapanınca görünürlüğü biter."""
    window = QMainWindow()
    window.setWindowTitle("SONAR Data Analyzer")
    window.setCentralWidget(QLabel("hazir"))
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window)
    assert window.isVisible()
    assert window.windowTitle() == "SONAR Data Analyzer"

    assert window.close()
    assert not window.isVisible()


def test_widget_is_destroyed_after_close(qtbot: QtBot) -> None:
    """Kapanışta pencere silinir; süreçte artık nesne kalmaz."""
    window = QMainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    qtbot.addWidget(window)

    destroyed: list[bool] = []

    def on_destroyed() -> None:
        destroyed.append(True)

    window.destroyed.connect(on_destroyed)

    window.show()
    qtbot.waitExposed(window)
    window.close()

    qtbot.waitUntil(lambda: bool(destroyed), timeout=2000)
    assert destroyed == [True]

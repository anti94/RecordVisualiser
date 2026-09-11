"""Connect / Disconnect eylemleri — `F5-019`.

Kabul: toolbar ve durum çubuğu **aynı** bağlantı durumunu gösterir.

İddia iki yönlü denetlenir: (a) her durumda iki yüzey birbiriyle
tutarlıdır, (b) durumu değiştiren her yol (eylem tetikleme, kaynağı
takma/çıkarma, kaynağın kendi kendine kopması) iki yüzeyi de tazeler.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.protocol import ConnectionState
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.actions import TOOLBAR_ACTION_NAMES
from sonar_analyzer.ui.main_window import CONNECTION_LABELS, MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _source() -> FileReplaySource:
    return FileReplaySource(MockRecordingRepository(duration_s=1.0), sleep=lambda _s: None)


def _surfaces(window: MainWindow) -> tuple[bool, bool, str]:
    """(connect etkin mi, disconnect etkin mi, durum çubuğu metni)."""
    return (
        window.action("action_connect").isEnabled(),
        window.action("action_disconnect").isEnabled(),
        window.status.field_value("connection"),
    )


# --------------------------------------------------------------------------- #
# eylemler var ve toolbar'da
# --------------------------------------------------------------------------- #


def test_both_actions_exist(win: MainWindow) -> None:
    assert win.action("action_connect") is not None
    assert win.action("action_disconnect") is not None


def test_both_actions_are_on_the_toolbar(win: MainWindow) -> None:
    assert "action_connect" in TOOLBAR_ACTION_NAMES
    assert "action_disconnect" in TOOLBAR_ACTION_NAMES
    toolbar_actions = {action.objectName() for action in win.toolbar.actions()}
    assert {"action_connect", "action_disconnect"} <= toolbar_actions


def test_the_actions_are_in_the_tools_menu(win: MainWindow) -> None:
    names = {action.objectName() for action in win.menu("menu_tools").actions()}
    assert {"action_connect", "action_disconnect"} <= names


# --------------------------------------------------------------------------- #
# kaynak yokken
# --------------------------------------------------------------------------- #


def test_without_a_source_both_actions_are_disabled(win: MainWindow) -> None:
    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert connect_enabled is False
    assert disconnect_enabled is False
    assert text in ("", "—")  # bos alan `—` gosterir


def test_connecting_without_a_source_is_logged_not_crashed(win: MainWindow) -> None:
    win.connect_live_source()
    assert any("Canli kaynak secili degil" in line for line in win.bottom_dock.log_lines())


def test_disconnecting_without_a_source_is_a_no_op(win: MainWindow) -> None:
    win.disconnect_live_source()  # istisna firlatmamali
    assert win.connection_state() is ConnectionState.DISCONNECTED


# --------------------------------------------------------------------------- #
# iki yuzey AYNI durumu gosterir
# --------------------------------------------------------------------------- #


def test_attaching_a_source_enables_connect_and_shows_disconnected(win: MainWindow) -> None:
    win.set_live_source(_source())
    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert connect_enabled is True  # baglanabilir
    assert disconnect_enabled is False  # kopartilacak bir sey yok
    assert text == CONNECTION_LABELS[ConnectionState.DISCONNECTED]


def test_connect_flips_both_surfaces_together(win: MainWindow) -> None:
    win.set_live_source(_source())
    win.action("action_connect").trigger()

    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert win.connection_state() is ConnectionState.CONNECTED
    assert connect_enabled is False
    assert disconnect_enabled is True
    assert text == CONNECTION_LABELS[ConnectionState.CONNECTED]


def test_disconnect_flips_both_surfaces_back(win: MainWindow) -> None:
    win.set_live_source(_source())
    win.action("action_connect").trigger()
    win.action("action_disconnect").trigger()

    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert win.connection_state() is ConnectionState.DISCONNECTED
    assert connect_enabled is True
    assert disconnect_enabled is False
    assert text == CONNECTION_LABELS[ConnectionState.DISCONNECTED]


def test_detaching_the_source_clears_both_surfaces(win: MainWindow) -> None:
    win.set_live_source(_source())
    win.action("action_connect").trigger()
    win.set_live_source(None)

    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert connect_enabled is False
    assert disconnect_enabled is False
    assert text in ("", "—")


@pytest.mark.parametrize("cycles", [1, 2, 5])
def test_repeated_connect_disconnect_keeps_the_surfaces_in_agreement(
    win: MainWindow, cycles: int
) -> None:
    """Her turda iki yüzey de aynı durumu göstermeli — biri geride kalmamalı."""
    win.set_live_source(_source())
    for _ in range(cycles):
        win.action("action_connect").trigger()
        assert _surfaces(win) == (False, True, CONNECTION_LABELS[ConnectionState.CONNECTED])
        win.action("action_disconnect").trigger()
        assert _surfaces(win) == (True, False, CONNECTION_LABELS[ConnectionState.DISCONNECTED])


def test_the_status_text_always_matches_the_reported_state(win: MainWindow) -> None:
    """Durum çubuğu metni, `connection_state()`'in karşılığından başkası olamaz."""
    source = _source()
    win.set_live_source(source)
    for _ in range(3):
        win.action("action_connect").trigger()
        assert win.status.field_value("connection") == CONNECTION_LABELS[win.connection_state()]
        win.action("action_disconnect").trigger()
        assert win.status.field_value("connection") == CONNECTION_LABELS[win.connection_state()]


def test_every_connection_state_has_a_label() -> None:
    """Eksik bir durum, arayüzde boş bir alan bırakırdı."""
    for state in ConnectionState:
        assert CONNECTION_LABELS[state].strip()


# --------------------------------------------------------------------------- #
# hatali baglanti gorunur olur
# --------------------------------------------------------------------------- #


class _FailingSource:
    """`connect()` her zaman hata veren kaynak."""

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED

    @property
    def state(self) -> ConnectionState:
        return self._state

    def connect(self) -> None:
        raise OSError("port acilamadi")

    def disconnect(self) -> None:
        self._state = ConnectionState.DISCONNECTED

    def channels(self) -> tuple[()]:
        return ()

    def packets(self) -> list[object]:
        return []

    def stats(self) -> object:
        return None


def test_a_failing_connect_is_logged_and_leaves_the_surfaces_consistent(
    win: MainWindow,
) -> None:
    win.set_live_source(_FailingSource())  # type: ignore[arg-type]
    win.action("action_connect").trigger()

    assert any("Baglanti kurulamadi" in line for line in win.bottom_dock.log_lines())
    connect_enabled, disconnect_enabled, text = _surfaces(win)
    assert connect_enabled is True  # yeniden denenebilir
    assert disconnect_enabled is False
    assert text == CONNECTION_LABELS[ConnectionState.DISCONNECTED]


def test_a_successful_connect_is_logged(win: MainWindow) -> None:
    win.set_live_source(_source())
    win.action("action_connect").trigger()
    assert any("Canli kaynaga baglanildi" in line for line in win.bottom_dock.log_lines())


def test_a_disconnect_is_logged(win: MainWindow) -> None:
    win.set_live_source(_source())
    win.action("action_connect").trigger()
    win.action("action_disconnect").trigger()
    assert any("Canli baglanti kapatildi" in line for line in win.bottom_dock.log_lines())

"""Boş workspace yönlendirmesi — `F1-033`.

Kabul: dosya açma ve kanal ekleme eylemleri görünürdür.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.empty_state import (
    CHANNEL_HINT,
    OPEN_BUTTON_TEXT,
    SIMULATION_BUTTON_TEXT,
    EmptyStatePanel,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


def test_empty_state_is_shown_before_a_recording(window: MainWindow) -> None:
    assert isinstance(window.empty_state, EmptyStatePanel)
    assert not window.center_shows_plot
    assert window.center_stack.currentWidget() is window.empty_state


def test_file_open_action_is_visible(window: MainWindow) -> None:
    """Kabul kriteri: dosya açma eylemi görünür."""
    assert OPEN_BUTTON_TEXT in window.empty_state.visible_actions()
    assert window.empty_state.open_button.isVisible()


def test_channel_adding_is_explained(window: MainWindow) -> None:
    """Kabul kriteri: kanal ekleme eylemi görünür."""
    assert "cift tikla" in CHANNEL_HINT
    assert window.empty_state.channel_hint.text() == CHANNEL_HINT
    assert window.empty_state.channel_hint.isVisible()


def test_simulation_action_is_offered(window: MainWindow) -> None:
    assert SIMULATION_BUTTON_TEXT in window.empty_state.visible_actions()


def test_open_button_triggers_the_shared_action(window: MainWindow, qtbot: QtBot) -> None:
    """Aynı iş için ikinci bir yol açılmamalı; ana eylem tetiklenmeli."""
    with qtbot.waitSignal(window.action("action_open").triggered, timeout=2000):
        window.empty_state.open_button.click()


def test_simulation_button_loads_data(window: MainWindow) -> None:
    window.empty_state.simulation_button.click()

    assert window.center_shows_plot is False, "veri geldi ama kanal secilmedi"
    assert len(window.left_dock.visible_channel_ids()) == 8


def test_selecting_a_channel_switches_to_the_plot(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    assert not window.center_shows_plot

    window.left_dock.channel_activated.emit("ch0")

    assert window.center_shows_plot
    assert window.center_stack.currentWidget() is window.dashboard


def test_new_recording_returns_to_guidance(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    window.left_dock.channel_activated.emit("ch0")
    assert window.center_shows_plot

    window.set_repository(MockRecordingRepository(duration_s=5.0))

    assert not window.center_shows_plot, "yeni kayitta yonlendirmeye donulmeli"


def test_panel_has_stable_object_name(window: MainWindow) -> None:
    assert window.empty_state.objectName() == "panel_empty_state"
    assert window.center_stack.objectName() == "center_stack"

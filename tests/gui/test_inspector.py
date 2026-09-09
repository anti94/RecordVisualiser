"""Inspector bağlamsal sekmesi — `F1-025`.

Kabul: kanal ayrıntısı sağdaki BIT, Analysis Tools ve Export düzenini
**bozmadan** açılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.inspector import EMPTY_VALUE, InspectorPanel
from sonar_analyzer.ui.docks.right_column import (
    CARD_SPECS,
    INSPECTOR_TAB_TITLE,
    OVERVIEW_TAB_TITLE,
    RightColumnDock,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

EXPECTED_CARDS = ["BIT / System Status", "Analysis Tools", "Data Export"]


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    # set_repository kullaniliyor: kanal cizimi repository'den veri cekiyor.
    win.set_repository(MockRecordingRepository(duration_s=10.0))
    return win


# -- sag sutun kartlari ----------------------------------------------------


def test_right_column_has_three_cards(window: MainWindow) -> None:
    assert isinstance(window.right_dock, RightColumnDock)
    assert window.right_dock.card_titles() == EXPECTED_CARDS
    assert len(CARD_SPECS) == 3


def test_cards_are_visible_before_inspector(window: MainWindow) -> None:
    for card in window.right_dock.cards.values():
        assert card.isVisible()


# -- Inspector -------------------------------------------------------------


def test_inspector_tab_is_absent_until_a_selection(window: MainWindow) -> None:
    assert isinstance(window.right_dock.inspector, InspectorPanel)
    assert not window.right_dock.inspector_is_open
    assert window.right_dock.tab_titles() == [OVERVIEW_TAB_TITLE]


def test_channel_activation_opens_inspector_tab(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch5")

    assert window.right_dock.inspector_is_open
    assert window.right_dock.tab_titles() == [OVERVIEW_TAB_TITLE, INSPECTOR_TAB_TITLE]
    assert window.right_dock.tabs.currentWidget() is window.right_dock.inspector

    inspector = window.right_dock.inspector
    assert inspector.field_value("Channel") == "Hydrophone 1"
    assert inspector.field_value("Path") == "Acoustic/Hydrophone 1"
    assert inspector.field_value("Unit") == "Pa"
    assert inspector.field_value("Sample rate") == "8 Hz"


def test_inspector_does_not_remove_the_cards(window: MainWindow) -> None:
    """Kabul kriteri: Inspector acilinca sag sutun duzeni bozulmamali."""
    titles_before = window.right_dock.card_titles()
    cards_before = list(window.right_dock.cards)

    window.left_dock.channel_activated.emit("ch0")

    assert window.right_dock.card_titles() == titles_before
    assert list(window.right_dock.cards) == cards_before
    assert len(window.right_dock.cards) == 3


def test_cards_are_intact_when_returning_to_overview(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    window.right_dock.tabs.setCurrentIndex(0)

    for card in window.right_dock.cards.values():
        assert card.isVisible()
    assert window.right_dock.card_titles() == EXPECTED_CARDS


def test_closing_inspector_keeps_cards(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    assert window.right_dock.inspector_is_open

    window.right_dock.close_inspector()

    assert not window.right_dock.inspector_is_open
    assert window.right_dock.tab_titles() == [OVERVIEW_TAB_TITLE]
    assert window.right_dock.card_titles() == EXPECTED_CARDS
    for card in window.right_dock.cards.values():
        assert card.isVisible()


def test_reopening_inspector_reuses_the_same_panel(window: MainWindow) -> None:
    """Panel her acilista yeniden kurulmamali."""
    panel = window.right_dock.inspector

    window.left_dock.channel_activated.emit("ch0")
    window.right_dock.close_inspector()
    window.left_dock.channel_activated.emit("ch1")

    assert window.right_dock.inspector is panel
    assert panel.field_value("Channel") == "Temperature"


def test_unknown_channel_is_ignored(window: MainWindow) -> None:
    window.show_channel_in_inspector("yok")
    assert not window.right_dock.inspector_is_open


def test_inspector_clear_returns_to_hint(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    inspector = window.right_dock.inspector

    inspector.clear()
    assert inspector.field_value("Channel") == EMPTY_VALUE
    assert inspector.hint.isVisible()
    assert not inspector.detail.isVisible()


def test_unknown_inspector_field_raises(window: MainWindow) -> None:
    with pytest.raises(KeyError, match="Tanimsiz Inspector alani"):
        window.right_dock.inspector.field_value("Yok")


# -- kayit acilinca ---------------------------------------------------------


def test_recording_enables_close_and_export(window: MainWindow) -> None:
    assert window.action("action_close").isEnabled()
    assert window.action("action_export").isEnabled()


def test_recording_fills_data_explorer(window: MainWindow) -> None:
    assert len(window.left_dock.visible_channel_ids()) == 8
    assert window.left_dock.summary_value("Duration") == "00:00:10"

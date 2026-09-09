"""Data Export kartı — `F1-037`.

Kabul: format, zaman aralığı, metadata ve export kontrolleri görünürdür.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.cards.data_export import EXPORT_FORMATS, DataExportCard
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def card(qtbot: QtBot) -> DataExportCard:
    widget = DataExportCard()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_all_mockup_controls_are_visible(card: DataExportCard) -> None:
    assert card.export_format.count() == len(EXPORT_FORMATS)
    assert "CSV" in EXPORT_FORMATS
    assert card.export_selected_range.text() == "Export selected time range"
    assert card.include_metadata.text() == "Include metadata"
    assert card.export_button.text() == "Export Data"


def test_defaults_match_safe_choices(card: DataExportCard) -> None:
    assert card.export_selected_range.isChecked()
    assert card.include_metadata.isChecked()
    assert card.export_format.currentText() == "CSV"


def test_export_button_is_disabled_with_reason(card: DataExportCard) -> None:
    """Dışa aktarma motoru henüz yok; buton pasif ve nedeni açık."""
    assert not card.export_button.isEnabled()
    assert card.export_button.toolTip() == NOT_YET_AVAILABLE


def test_card_is_used_in_the_right_column(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    assert isinstance(win.right_dock.data_export, DataExportCard)
    assert win.right_dock.cards["card_data_export"] is win.right_dock.data_export


def test_card_appears_after_analysis_tools_in_the_column(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    names = list(win.right_dock.cards)
    assert names.index("card_analysis_tools") < names.index("card_data_export")

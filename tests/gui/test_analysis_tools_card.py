"""Analysis Tools kartının sekmeleri — `F1-036`.

Kabul: Filter, FFT, Statistics ve Custom sekmeleri mockup sırasındadır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.cards.analysis_tools import (
    FILTER_TYPES,
    TAB_TITLES,
    AnalysisToolsCard,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def card(qtbot: QtBot) -> AnalysisToolsCard:
    widget = AnalysisToolsCard()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_tabs_are_in_mockup_order(card: AnalysisToolsCard) -> None:
    assert card.tab_titles() == list(TAB_TITLES)
    assert TAB_TITLES == ("Filter", "FFT", "Statistics", "Custom")


def test_card_is_used_in_the_right_column(qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    assert isinstance(win.right_dock.analysis_tools, AnalysisToolsCard)
    assert win.right_dock.cards["card_analysis_tools"] is win.right_dock.analysis_tools


# -- Filter sekmesi ----------------------------------------------------------


def test_filter_tab_has_mockup_fields(card: AnalysisToolsCard) -> None:
    assert list(FILTER_TYPES) == ["Butterworth", "Chebyshev", "Bessel"]
    assert card.filter_type.count() == 3
    assert card.cutoff_frequency.suffix() == " Hz"
    assert card.order.value() == 4
    assert card.apply_to_selected.isChecked()
    assert not card.show_filtered_data.isChecked()


def test_apply_filter_is_disabled_with_reason(card: AnalysisToolsCard) -> None:
    """İşlevi olmayan alan gizlenmiyor, pasif ve nedeni ipucunda (plan Bölüm 3.1)."""
    assert not card.apply_filter_button.isEnabled()
    assert card.apply_filter_button.toolTip() == NOT_YET_AVAILABLE
    assert card.apply_filter_button.isVisibleTo(card.tabs)


# -- diger sekmeler ------------------------------------------------------


def test_placeholder_labels_have_stable_object_names(card: AnalysisToolsCard) -> None:
    from PySide6.QtWidgets import QLabel

    for index, title in enumerate(("FFT", "Statistics", "Custom")):
        page = card.tabs.widget(index + 1)
        assert page is not None
        label = page.findChild(QLabel, f"label_{title.lower()}_placeholder")
        assert label is not None


def test_placeholder_text_mentions_availability(card: AnalysisToolsCard) -> None:
    from PySide6.QtWidgets import QLabel

    for index, title in enumerate(("FFT", "Statistics", "Custom")):
        page = card.tabs.widget(index + 1)
        assert page is not None
        labels = page.findChildren(QLabel)
        assert labels, f"{title} sekmesinde etiket yok"
        assert any(NOT_YET_AVAILABLE in label.text() for label in labels)


def test_no_fake_computed_result_is_shown(card: AnalysisToolsCard) -> None:
    """Hesaplama motoru yokken sahte sonuç gösterilmemeli."""
    from PySide6.QtWidgets import QLabel

    for index in range(1, card.tabs.count()):
        page = card.tabs.widget(index)
        assert page is not None
        for label in page.findChildren(QLabel):
            assert "Hz" not in label.text()
            assert "dB" not in label.text()

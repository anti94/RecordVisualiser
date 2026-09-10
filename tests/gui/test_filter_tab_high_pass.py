"""Filter sekmesi high-pass seçimi — `F4-032`.

Kabul: tür değişimi doğru parametrelerle zincire kaydedilir.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.filters import high_pass
from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.analysis_tools import FilterTabError
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0))
    window.open_channel("ch0")
    return window


def _card(win: MainWindow):
    return win.right_dock.analysis_tools


def test_response_selector_offers_low_and_high_pass(win: MainWindow) -> None:
    card = _card(win)
    values = [card.filter_response.itemText(i) for i in range(card.filter_response.count())]
    # Liste sonraki işlerle büyür; sıra ve varlık denetlenir.
    assert values[:2] == ["Low-pass", "High-pass"]


def test_selecting_high_pass_builds_a_high_pass_step(win: MainWindow) -> None:
    card = _card(win)
    card.filter_response.setCurrentText("High-pass")
    card.cutoff_frequency.setValue(20)
    card.order.setValue(3)

    step = card.build_filter_chain("ch0", 200.0).steps[0]
    assert step.kind is StepKind.HIGH_PASS
    assert step.parameters == {"sample_rate_hz": 200.0, "cutoff_hz": 20.0, "order": 3}


def test_changing_the_response_type_switches_the_step_kind(win: MainWindow) -> None:
    card = _card(win)
    card.cutoff_frequency.setValue(30)
    card.order.setValue(4)

    card.filter_response.setCurrentText("Low-pass")
    assert card.build_filter_chain("ch0", 200.0).steps[0].kind is StepKind.LOW_PASS

    card.filter_response.setCurrentText("High-pass")
    hp = card.build_filter_chain("ch0", 200.0).steps[0]
    assert hp.kind is StepKind.HIGH_PASS
    # Aynı cutoff / order alanları yeni türe taşınır.
    assert hp.parameters["cutoff_hz"] == 30.0
    assert hp.parameters["order"] == 4


def test_high_pass_invalid_cutoff_is_rejected(win: MainWindow) -> None:
    card = _card(win)
    card.filter_response.setCurrentText("High-pass")
    card.cutoff_frequency.setValue(120)  # Nyquist 100
    with pytest.raises(FilterTabError, match="Nyquist"):
        card.build_filter_chain("ch0", 200.0)


def test_apply_high_pass_from_the_filter_tab_draws_it(win: MainWindow, qtbot: QtBot) -> None:
    card = _card(win)
    card.tabs.setCurrentIndex(0)
    card.filter_response.setCurrentText("High-pass")
    card.cutoff_frequency.setValue(15)
    card.order.setValue(4)
    card.show_filtered_data.setChecked(True)

    _x, raw = win.plot_panel.curve_data()
    card.apply_filter_button.click()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    assert np.allclose(processed, high_pass(raw, 200.0, 15.0, 4), atol=1e-9)
    # Yüksek geçiren çıktısı sıfır toplamlı (DC gitti).
    assert abs(float(processed.sum())) < 1e-6 * float(np.abs(raw).sum())

"""Filter sekmesi low-pass alanları — `F4-029`.

Kabul: Mockup Filter kartından geçerli parametreyle sonuç çizilir.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.filters import low_pass
from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.analysis_tools import FILTER_RESPONSES, FilterTabError
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0))
    window.open_channel("ch0")
    return window


def _filter_card(win: MainWindow):
    return win.right_dock.analysis_tools


def test_filter_tab_exposes_a_response_selector(win: MainWindow) -> None:
    card = _filter_card(win)
    assert card.filter_response.count() == len(FILTER_RESPONSES)
    assert card.filter_response.currentText() == "Low-pass"


def test_build_filter_chain_produces_a_single_low_pass_step(win: MainWindow) -> None:
    card = _filter_card(win)
    card.cutoff_frequency.setValue(40)
    card.order.setValue(5)

    chain = card.build_filter_chain("ch0", 200.0)
    assert len(chain.steps) == 1
    step = chain.steps[0]
    assert step.kind is StepKind.LOW_PASS
    assert step.parameters == {"sample_rate_hz": 200.0, "cutoff_hz": 40.0, "order": 5}
    assert step.input_channel_id == "ch0"


def test_build_filter_chain_rejects_a_cutoff_beyond_nyquist(win: MainWindow) -> None:
    card = _filter_card(win)
    card.cutoff_frequency.setValue(150)  # Nyquist = 100
    with pytest.raises(FilterTabError, match="Nyquist"):
        card.build_filter_chain("ch0", 200.0)


def test_build_filter_chain_rejects_unimplemented_families(win: MainWindow) -> None:
    card = _filter_card(win)
    card.filter_type.setCurrentText("Chebyshev")
    with pytest.raises(FilterTabError, match="henüz uygulanmadı"):
        card.build_filter_chain("ch0", 200.0)


def test_apply_from_the_filter_tab_draws_the_low_pass_result(win: MainWindow, qtbot: QtBot) -> None:
    card = _filter_card(win)
    card.tabs.setCurrentIndex(0)  # Filter sekmesi
    card.cutoff_frequency.setValue(40)
    card.order.setValue(4)
    card.show_filtered_data.setChecked(True)

    _x, raw = win.plot_panel.curve_data()
    card.apply_filter_button.click()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    assert processed.shape == raw.shape
    assert np.allclose(processed, low_pass(raw, 200.0, 40.0, 4), atol=1e-9)
    # Ham seri değişmedi.
    _x2, raw_after = win.plot_panel.curve_data()
    assert np.array_equal(raw_after, raw)


def test_invalid_cutoff_is_reported_and_nothing_is_drawn(win: MainWindow) -> None:
    card = _filter_card(win)
    card.tabs.setCurrentIndex(0)
    card.cutoff_frequency.setValue(180)  # >= Nyquist

    card.apply_filter_button.click()

    assert not win.plot_panel.has_processed_overlay
    assert any("geçersiz" in line for line in win.bottom_dock.log_lines())


def test_custom_tab_chain_still_applies_when_it_is_active(win: MainWindow, qtbot: QtBot) -> None:
    tools = _filter_card(win)
    editor = tools.step_editor
    tools.tabs.setCurrentWidget(editor)
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.SCALE))
    editor.add_button.click()
    editor.list.setCurrentRow(0)
    editor.set_param_field("factor", 3.0)
    tools.show_filtered_data.setChecked(True)

    _x, raw = win.plot_panel.curve_data()
    tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    assert np.allclose(win.plot_panel.processed_overlay_values(), raw * 3.0)

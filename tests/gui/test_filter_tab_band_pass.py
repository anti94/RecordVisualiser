"""Filter sekmesi band-pass iki cutoff alanı — `F4-035`.

Kabul: iki sınır doğru sırayla hesaplamaya iletilir.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.filters import band_pass
from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.analysis_tools import (
    CUTOFF_LABEL_LOW,
    CUTOFF_LABEL_SINGLE,
    FilterTabError,
)
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


def _select_band_pass(win: MainWindow, low: int, high: int, order: int = 4) -> None:
    card = _card(win)
    card.filter_response.setCurrentText("Band-pass")
    card.cutoff_frequency.setValue(low)
    card.high_cutoff_frequency.setValue(high)
    card.order.setValue(order)


def test_band_pass_is_offered_in_the_response_selector(win: MainWindow) -> None:
    card = _card(win)
    values = [card.filter_response.itemText(i) for i in range(card.filter_response.count())]
    assert "Band-pass" in values


def test_the_second_cutoff_field_appears_only_for_band_pass(win: MainWindow) -> None:
    card = _card(win)

    card.filter_response.setCurrentText("Low-pass")
    assert card.high_cutoff_frequency.isHidden()

    card.filter_response.setCurrentText("Band-pass")
    assert not card.high_cutoff_frequency.isHidden()

    card.filter_response.setCurrentText("High-pass")
    assert card.high_cutoff_frequency.isHidden()


def test_the_first_cutoff_label_switches_to_low_cutoff(win: MainWindow) -> None:
    card = _card(win)

    card.filter_response.setCurrentText("Band-pass")
    assert card.cutoff_label_text() == CUTOFF_LABEL_LOW

    card.filter_response.setCurrentText("Low-pass")
    assert card.cutoff_label_text() == CUTOFF_LABEL_SINGLE


def test_both_bounds_reach_the_step_in_the_right_order(win: MainWindow) -> None:
    _select_band_pass(win, low=20, high=80, order=3)

    step = _card(win).build_filter_chain("ch0", 200.0).steps[0]
    assert step.kind is StepKind.BAND_PASS
    assert step.parameters == {
        "sample_rate_hz": 200.0,
        "low_cutoff_hz": 20.0,
        "high_cutoff_hz": 80.0,
        "order": 3,
    }


def test_the_bounds_are_not_swapped(win: MainWindow) -> None:
    _select_band_pass(win, low=15, high=65)
    params = _card(win).build_filter_chain("ch0", 200.0).steps[0].parameters
    assert params["low_cutoff_hz"] == 15.0
    assert params["high_cutoff_hz"] == 65.0
    assert params["low_cutoff_hz"] < params["high_cutoff_hz"]  # type: ignore[operator]


def test_a_reversed_band_is_rejected_before_processing(win: MainWindow) -> None:
    _select_band_pass(win, low=80, high=20)
    with pytest.raises(FilterTabError, match="ters bant"):
        _card(win).build_filter_chain("ch0", 200.0)


def test_an_upper_bound_beyond_nyquist_is_rejected(win: MainWindow) -> None:
    _select_band_pass(win, low=20, high=150)  # Nyquist 100
    with pytest.raises(FilterTabError, match="Nyquist"):
        _card(win).build_filter_chain("ch0", 200.0)


def test_apply_band_pass_from_the_filter_tab_draws_the_result(
    win: MainWindow, qtbot: QtBot
) -> None:
    card = _card(win)
    card.tabs.setCurrentIndex(0)
    _select_band_pass(win, low=20, high=80, order=4)
    card.show_filtered_data.setChecked(True)

    x, _raw = win.plot_panel.curve_data()
    card.apply_filter_button.click()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    source = MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0)
    full = source.query("ch0", source.metadata().time_range).values
    indices = np.rint(x * 200).astype(np.int64)
    assert np.allclose(processed, band_pass(full, 200.0, 20.0, 80.0, 4)[indices], atol=1e-9)


def test_a_reversed_band_is_reported_and_nothing_is_drawn(win: MainWindow) -> None:
    card = _card(win)
    card.tabs.setCurrentIndex(0)
    _select_band_pass(win, low=80, high=20)

    card.apply_filter_button.click()

    assert not win.plot_panel.has_processed_overlay
    assert any("geçersiz" in line for line in win.bottom_dock.log_lines())

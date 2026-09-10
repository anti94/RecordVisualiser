"""Seçili kanala işlem uygulama + filtreli veri görünümü — `F4-008`.

Kabul: Apply Filter ile seçili kanal işlenir; Show filtered data
görünürlüğü değiştirir.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4.0))
    window.open_channel("ch0")
    return window


def _select_custom_tab(win: MainWindow) -> None:
    tools = win.right_dock.analysis_tools
    tools.tabs.setCurrentWidget(tools.step_editor)


def _add_scale_step(win: MainWindow, factor: float) -> None:
    _select_custom_tab(win)
    editor = win.right_dock.analysis_tools.step_editor
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.SCALE))
    editor.add_button.click()
    editor.list.setCurrentRow(editor.step_count() - 1)
    editor.set_param_field("factor", factor)


def test_apply_filter_processes_the_selected_channel(win: MainWindow, qtbot: QtBot) -> None:
    _add_scale_step(win, 3.0)
    _x, raw = win.plot_panel.curve_data()

    win.right_dock.analysis_tools.show_filtered_data.setChecked(True)
    win.right_dock.analysis_tools.apply_requested.emit()

    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    assert processed.shape == raw.shape
    assert np.allclose(processed, raw * 3.0)
    # Ham seri değişmedi.
    _x2, raw_after = win.plot_panel.curve_data()
    assert np.array_equal(raw_after, raw)


def test_show_filtered_data_toggles_overlay_visibility(win: MainWindow, qtbot: QtBot) -> None:
    _add_scale_step(win, 2.0)
    card = win.right_dock.analysis_tools

    card.show_filtered_data.setChecked(True)
    card.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)
    assert win.plot_panel.processed_overlay_visible

    card.show_filtered_data.setChecked(False)
    assert not win.plot_panel.processed_overlay_visible

    card.show_filtered_data.setChecked(True)
    assert win.plot_panel.processed_overlay_visible


def test_apply_without_steps_is_a_no_op(win: MainWindow) -> None:
    # Editörde adım yok.
    _select_custom_tab(win)
    win.right_dock.analysis_tools.apply_requested.emit()
    assert not win.plot_panel.has_processed_overlay
    assert any("işlem adımı yok" in line for line in win.bottom_dock.log_lines())


def test_switching_channel_clears_the_overlay(win: MainWindow, qtbot: QtBot) -> None:
    _add_scale_step(win, 2.0)
    win.right_dock.analysis_tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    win.open_channel("ch1")
    assert not win.plot_panel.has_processed_overlay


def test_stale_channel_result_is_not_applied(win: MainWindow, qtbot: QtBot) -> None:
    """ch0 işi sürerken ch1'e geçilirse ch0 sonucu overlay'e yazılmaz."""
    win.set_repository(MockRecordingRepository(duration_s=200.0))  # büyük -> yavaş
    win.open_channel("ch0")
    _add_scale_step(win, 2.0)

    win.right_dock.analysis_tools.apply_requested.emit()
    win.open_channel("ch1")  # seçim değişti; ch0 işi eski

    qtbot.waitUntil(lambda: not win.dsp_runner.busy, timeout=15_000)
    win.dsp_runner.wait_all()
    assert not win.plot_panel.has_processed_overlay  # ch0 sonucu uygulanmadı

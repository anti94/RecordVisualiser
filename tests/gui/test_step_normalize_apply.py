"""Normalize seçimi işlem editörüne bağlı — `F4-020`.

Kabul: normalize adımı seçili kanal grafiğine uygulanır.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.steps import NORMALIZE_MODES, StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4.0))
    window.open_channel("ch0")
    return window


def _add_normalize_step(win: MainWindow, mode: str, reference: float) -> None:
    tools = win.right_dock.analysis_tools
    tools.tabs.setCurrentWidget(tools.step_editor)
    editor = tools.step_editor
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.NORMALIZE))
    editor.add_button.click()
    editor.list.setCurrentRow(editor.step_count() - 1)
    editor.set_param_field("mode", mode)
    editor.set_param_field("reference", reference)


def _peak(values: NDArray[np.float64]) -> float:
    finite = values[np.isfinite(values)]
    return float(np.abs(finite).max())


# --------------------------------------------------------------------------- #
# editör: tür ve alanlar
# --------------------------------------------------------------------------- #


def test_normalize_kind_is_offered_in_the_selector(qtbot: QtBot) -> None:
    editor = StepListEditor()
    qtbot.addWidget(editor)
    assert editor.kind_selector.findData(StepKind.NORMALIZE) >= 0


def test_normalize_step_shows_mode_combo_and_reference_field(qtbot: QtBot) -> None:
    editor = StepListEditor()
    qtbot.addWidget(editor)
    editor.set_input_channel("ch0")
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.NORMALIZE))
    editor.add_button.click()
    editor.list.setCurrentRow(0)

    assert editor.param_field_names() == ["mode", "reference"]
    mode = editor.param_field("mode")
    assert isinstance(mode, QComboBox)
    assert [mode.itemData(i) for i in range(mode.count())] == list(NORMALIZE_MODES)
    assert isinstance(editor.param_field("reference"), QDoubleSpinBox)


def test_nonpositive_reference_is_rejected_before_processing(qtbot: QtBot) -> None:
    editor = StepListEditor()
    qtbot.addWidget(editor)
    editor.set_input_channel("ch0")
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.NORMALIZE))
    editor.add_button.click()
    editor.list.setCurrentRow(0)

    editor.set_param_field("reference", 0.0)
    assert editor.has_parameter_error
    assert "reference" in editor.parameter_error()
    assert editor.chain().steps[0].parameters["reference"] == 1.0  # varsayılan korundu


# --------------------------------------------------------------------------- #
# uygulama: seçili kanal grafiğine
# --------------------------------------------------------------------------- #


def test_normalize_is_applied_to_the_selected_channel_plot(win: MainWindow, qtbot: QtBot) -> None:
    _add_normalize_step(win, "peak", 1.0)
    _x, raw = win.plot_panel.curve_data()

    win.right_dock.analysis_tools.show_filtered_data.setChecked(True)
    win.right_dock.analysis_tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    assert processed.shape == raw.shape
    # peak normalize: işlenmiş tepe tam olarak referans (1.0).
    assert abs(_peak(processed) - 1.0) < 1e-9
    # Ham seri değişmedi.
    _x2, raw_after = win.plot_panel.curve_data()
    assert np.array_equal(raw_after, raw)


def test_reference_amplitude_change_rescales_the_overlay(win: MainWindow, qtbot: QtBot) -> None:
    _add_normalize_step(win, "peak", 1.0)
    card = win.right_dock.analysis_tools
    card.show_filtered_data.setChecked(True)
    card.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)
    assert abs(_peak(win.plot_panel.processed_overlay_values()) - 1.0) < 1e-9

    editor = card.step_editor
    editor.list.setCurrentRow(0)
    editor.set_param_field("reference", 4.0)
    card.apply_requested.emit()
    qtbot.waitUntil(
        lambda: abs(_peak(win.plot_panel.processed_overlay_values()) - 4.0) < 1e-9,
        timeout=10_000,
    )


def test_rms_normalize_also_applies(win: MainWindow, qtbot: QtBot) -> None:
    _add_normalize_step(win, "rms", 2.0)
    win.right_dock.analysis_tools.show_filtered_data.setChecked(True)
    win.right_dock.analysis_tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    finite = processed[np.isfinite(processed)]
    rms = float(np.sqrt(np.mean(np.square(finite))))
    assert abs(rms - 2.0) < 1e-9

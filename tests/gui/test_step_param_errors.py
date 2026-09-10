"""Analiz parametre hataları alanlarda gösterilir — `F4-007`.

Kabul: geçersiz değer işlem başlamadan açıklanır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor

pytestmark = pytest.mark.gui


@pytest.fixture()
def editor(qtbot: QtBot) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    return widget


def _add(editor: StepListEditor, kind: StepKind) -> None:
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(kind))
    editor.add_button.click()


def test_selecting_a_step_shows_its_parameter_fields(editor: StepListEditor) -> None:
    _add(editor, StepKind.CLIP)
    editor.list.setCurrentRow(0)

    assert not editor.param_panel.isHidden()
    assert set(editor.param_field_names()) == {"lo", "hi"}


def test_no_panel_without_a_selection(editor: StepListEditor) -> None:
    _add(editor, StepKind.SCALE)
    editor.list.setCurrentRow(-1)
    assert editor.param_panel.isHidden()


def test_invalid_clip_bounds_are_explained_before_any_processing(editor: StepListEditor) -> None:
    _add(editor, StepKind.CLIP)
    editor.list.setCurrentRow(0)

    editor.set_param_field("lo", 5.0)
    editor.set_param_field("hi", 1.0)

    assert editor.has_parameter_error
    assert "lo, hi" in editor.parameter_error()
    # Geçersiz değer modele YAZILMADI — son geçerli adım korunur.
    assert editor.chain().steps[0].parameters == {"lo": 0.0, "hi": 1.0}


def test_zero_window_is_explained_and_not_committed(editor: StepListEditor) -> None:
    _add(editor, StepKind.MOVING_AVERAGE)
    editor.list.setCurrentRow(0)

    editor.set_param_field("window", 0)

    assert editor.has_parameter_error
    assert "window" in editor.parameter_error()
    assert editor.chain().steps[0].parameters["window"] == 3  # varsayılan korundu


def test_a_valid_edit_clears_the_error_and_updates_the_model(editor: StepListEditor) -> None:
    _add(editor, StepKind.CLIP)
    editor.list.setCurrentRow(0)

    editor.set_param_field("lo", 5.0)  # lo > hi, hata
    editor.set_param_field("hi", 9.0)  # düzeltir

    assert not editor.has_parameter_error
    assert editor.parameter_error() == ""
    assert editor.chain().steps[0].parameters == {"lo": 5.0, "hi": 9.0}


def test_valid_edit_emits_chain_changed(editor: StepListEditor, qtbot: QtBot) -> None:
    _add(editor, StepKind.SCALE)
    editor.list.setCurrentRow(0)
    with qtbot.waitSignal(editor.chain_changed):
        editor.set_param_field("factor", 7.5)
    assert editor.chain().steps[0].parameters["factor"] == 7.5


def test_switching_rows_reloads_the_fields(editor: StepListEditor) -> None:
    editor.set_chain(
        editor.chain().with_step(ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0}))
    )
    editor.set_chain(
        editor.chain().with_step(ProcessingStep(StepKind.OFFSET, "ch0", {"delta": 4.0}))
    )

    editor.list.setCurrentRow(0)
    assert set(editor.param_field_names()) == {"factor"}
    assert editor.param_field("factor").value() == 2.0

    editor.list.setCurrentRow(1)
    assert set(editor.param_field_names()) == {"delta"}
    assert editor.param_field("delta").value() == 4.0

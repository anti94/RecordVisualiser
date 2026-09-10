"""Moving average pencere kontrolü işlem editörüne bağlı — `F4-018`.

Kabul: sıfır veya aşırı pencere **işlem başlamadan** reddedilir —
alan içi açıklama görünür, geçersiz değer zincire yazılmaz.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QSpinBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.steps import MAX_MOVING_AVERAGE_WINDOW, StepKind
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor

pytestmark = pytest.mark.gui


@pytest.fixture()
def editor(qtbot: QtBot) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    widget.kind_selector.setCurrentIndex(widget.kind_selector.findData(StepKind.MOVING_AVERAGE))
    widget.add_button.click()
    widget.list.setCurrentRow(0)
    return widget


def _window_field(editor: StepListEditor) -> QSpinBox:
    field = editor.param_field("window")
    assert isinstance(field, QSpinBox)
    return field


def _committed_window(editor: StepListEditor) -> object:
    return editor.chain().steps[0].parameters["window"]


def test_window_field_allows_typing_out_of_policy_values(editor: StepListEditor) -> None:
    field = _window_field(editor)
    # 0 ve MAX+1 girilebilmeli ki reddedilip AÇIKLANABİLSİN (F4-007 felsefesi).
    assert field.minimum() <= 0
    assert field.maximum() > MAX_MOVING_AVERAGE_WINDOW


def test_zero_window_is_rejected_before_processing(editor: StepListEditor) -> None:
    editor.set_param_field("window", 0)
    assert editor.has_parameter_error
    assert "window" in editor.parameter_error()
    assert _committed_window(editor) == 3  # varsayılan korundu


def test_negative_window_is_rejected(editor: StepListEditor) -> None:
    editor.set_param_field("window", -4)
    assert editor.has_parameter_error
    assert _committed_window(editor) == 3


def test_excessive_window_is_rejected_with_explanation(editor: StepListEditor) -> None:
    editor.set_param_field("window", MAX_MOVING_AVERAGE_WINDOW + 1)
    assert editor.has_parameter_error
    message = editor.parameter_error()
    assert "aşırı" in message
    assert _committed_window(editor) == 3


def test_boundary_window_is_accepted(editor: StepListEditor) -> None:
    editor.set_param_field("window", MAX_MOVING_AVERAGE_WINDOW)
    assert not editor.has_parameter_error
    assert _committed_window(editor) == MAX_MOVING_AVERAGE_WINDOW


def test_valid_window_commits_and_emits(editor: StepListEditor, qtbot: QtBot) -> None:
    with qtbot.waitSignal(editor.chain_changed, timeout=1000):
        editor.set_param_field("window", 7)
    assert not editor.has_parameter_error
    assert _committed_window(editor) == 7


def test_fixing_the_window_clears_the_error(editor: StepListEditor) -> None:
    editor.set_param_field("window", 0)
    assert editor.has_parameter_error

    editor.set_param_field("window", 5)
    assert not editor.has_parameter_error
    assert editor.parameter_error() == ""
    assert _committed_window(editor) == 5

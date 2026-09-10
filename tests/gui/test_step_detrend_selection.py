"""Detrend türü seçimi işlem editörüne bağlı — `F4-016`.

Kabul: seçili tür (constant / linear) tekrar açılan zincirde korunur.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import DETREND_MODES, ProcessingStep, StepKind
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


def _mode_combo(editor: StepListEditor) -> QComboBox:
    field = editor.param_field("mode")
    assert isinstance(field, QComboBox)
    return field


def test_detrend_kind_is_offered_in_the_selector(editor: StepListEditor) -> None:
    assert editor.kind_selector.findData(StepKind.DETREND) >= 0


def test_detrend_step_shows_a_mode_combo(editor: StepListEditor) -> None:
    _add(editor, StepKind.DETREND)
    editor.list.setCurrentRow(0)

    assert editor.param_field_names() == ["mode"]
    combo = _mode_combo(editor)
    assert [combo.itemData(i) for i in range(combo.count())] == list(DETREND_MODES)


def test_default_detrend_mode_is_constant(editor: StepListEditor) -> None:
    _add(editor, StepKind.DETREND)
    editor.list.setCurrentRow(0)
    assert _mode_combo(editor).currentData() == "constant"
    assert editor.chain().steps[0].parameters["mode"] == "constant"


def test_choosing_linear_updates_chain(qtbot: QtBot, editor: StepListEditor) -> None:
    _add(editor, StepKind.DETREND)
    editor.list.setCurrentRow(0)
    combo = _mode_combo(editor)

    with qtbot.waitSignal(editor.chain_changed, timeout=1000):
        combo.setCurrentIndex(combo.findData("linear"))

    assert editor.chain().steps[0].parameters["mode"] == "linear"
    item = editor.list.item(0)
    assert item is not None
    assert "mode=linear" in item.text()


def test_selected_mode_survives_a_chain_roundtrip(qtbot: QtBot, editor: StepListEditor) -> None:
    _add(editor, StepKind.DETREND)
    editor.list.setCurrentRow(0)
    combo = _mode_combo(editor)
    combo.setCurrentIndex(combo.findData("linear"))

    # Zinciri serileştir → geri kur → yeni bir editöre yükle (tekrar açma).
    serialized = editor.chain().to_list()
    restored = ProcessingChain.from_list(serialized)

    reopened = StepListEditor()
    qtbot.addWidget(reopened)
    reopened.set_input_channel("ch0")
    reopened.set_chain(restored)
    reopened.list.setCurrentRow(0)

    assert _mode_combo(reopened).currentData() == "linear"
    assert reopened.chain().steps[0].parameters["mode"] == "linear"


@pytest.mark.parametrize("mode", list(DETREND_MODES))
def test_every_mode_round_trips_through_set_chain(
    qtbot: QtBot, editor: StepListEditor, mode: str
) -> None:
    chain = ProcessingChain([ProcessingStep(StepKind.DETREND, "ch0", {"mode": mode})])
    editor.set_chain(chain)
    editor.list.setCurrentRow(0)

    assert _mode_combo(editor).currentData() == mode
    assert editor.chain().steps[0].parameters["mode"] == mode


def test_switching_rows_rebuilds_the_mode_combo(editor: StepListEditor) -> None:
    editor.set_chain(
        ProcessingChain(
            [
                ProcessingStep(StepKind.SCALE, "ch0", {"factor": 2.0}),
                ProcessingStep(StepKind.DETREND, "ch0", {"mode": "linear"}),
            ]
        )
    )

    editor.list.setCurrentRow(0)
    assert isinstance(editor.param_field("factor"), QDoubleSpinBox)

    editor.list.setCurrentRow(1)
    assert _mode_combo(editor).currentData() == "linear"

    editor.list.setCurrentRow(0)
    assert "mode" not in editor.param_field_names()

"""Phase unwrap parametreleri işlem editörüne bağlı — `F4-024`.

Kabul: faz birimi ve eşik hataları işlem öncesi görünür.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import PHASE_UNWRAP_UNITS, StepKind
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor

pytestmark = pytest.mark.gui


@pytest.fixture()
def editor(qtbot: QtBot) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    widget.kind_selector.setCurrentIndex(widget.kind_selector.findData(StepKind.PHASE_UNWRAP))
    widget.add_button.click()
    widget.list.setCurrentRow(0)
    return widget


def _unit_combo(editor: StepListEditor) -> QComboBox:
    field = editor.param_field("unit")
    assert isinstance(field, QComboBox)
    return field


def _params(editor: StepListEditor) -> dict[str, object]:
    return dict(editor.chain().steps[0].parameters)


def _discontinuity(editor: StepListEditor) -> float:
    return float(editor.chain().steps[0].parameters["discontinuity"])  # type: ignore[arg-type]


def test_phase_unwrap_is_offered_in_the_selector(editor: StepListEditor) -> None:
    assert editor.kind_selector.findData(StepKind.PHASE_UNWRAP) >= 0


def test_fields_are_a_unit_combo_and_a_threshold_spinbox(editor: StepListEditor) -> None:
    assert set(editor.param_field_names()) == {"unit", "discontinuity"}
    combo = _unit_combo(editor)
    assert [combo.itemData(i) for i in range(combo.count())] == list(PHASE_UNWRAP_UNITS)
    assert isinstance(editor.param_field("discontinuity"), QDoubleSpinBox)


def test_default_is_radians_and_pi(editor: StepListEditor) -> None:
    assert _unit_combo(editor).currentData() == "radians"
    params = _params(editor)
    assert params["unit"] == "radians"
    assert abs(float(params["discontinuity"]) - math.pi) < 1e-9  # type: ignore[arg-type]


def test_choosing_degrees_updates_the_chain(qtbot: QtBot, editor: StepListEditor) -> None:
    combo = _unit_combo(editor)
    with qtbot.waitSignal(editor.chain_changed, timeout=1000):
        combo.setCurrentIndex(combo.findData("degrees"))
    assert _params(editor)["unit"] == "degrees"


def test_nonpositive_threshold_is_shown_before_processing(editor: StepListEditor) -> None:
    editor.set_param_field("discontinuity", 0.0)
    assert editor.has_parameter_error
    assert "discontinuity" in editor.parameter_error()
    assert abs(_discontinuity(editor) - math.pi) < 1e-9  # commit edilmedi


def test_threshold_at_or_above_a_full_period_is_shown(editor: StepListEditor) -> None:
    editor.set_param_field("discontinuity", 7.0)  # > 2*pi (radyan)
    assert editor.has_parameter_error
    assert "periyot" in editor.parameter_error()


def test_unit_switch_revalidates_the_threshold(editor: StepListEditor) -> None:
    # Radyanda 200 tam periyodun çok üstünde -> hata.
    editor.set_param_field("discontinuity", 200.0)
    assert editor.has_parameter_error

    # Dereceye geçince 200 < 360 -> hata temizlenir, değer commit edilir.
    combo = _unit_combo(editor)
    combo.setCurrentIndex(combo.findData("degrees"))
    assert not editor.has_parameter_error
    assert _params(editor)["unit"] == "degrees"
    assert abs(_discontinuity(editor) - 200.0) < 1e-9


def test_valid_threshold_edit_commits(editor: StepListEditor) -> None:
    editor.set_param_field("discontinuity", 2.5)
    assert not editor.has_parameter_error
    assert abs(_discontinuity(editor) - 2.5) < 1e-9


def test_selection_survives_a_chain_roundtrip(qtbot: QtBot, editor: StepListEditor) -> None:
    combo = _unit_combo(editor)
    combo.setCurrentIndex(combo.findData("degrees"))
    editor.set_param_field("discontinuity", 150.0)

    restored = ProcessingChain.from_list(editor.chain().to_list())
    reopened = StepListEditor()
    qtbot.addWidget(reopened)
    reopened.set_input_channel("ch0")
    reopened.set_chain(restored)
    reopened.list.setCurrentRow(0)

    assert _unit_combo(reopened).currentData() == "degrees"
    params = dict(reopened.chain().steps[0].parameters)
    assert params["unit"] == "degrees"
    assert abs(float(params["discontinuity"]) - 150.0) < 1e-9  # type: ignore[arg-type]

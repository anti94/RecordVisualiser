"""RMS / envelope pencere kontrolü süre alanı — `F4-022`.

Kabul: pencere süresi (saniye) sample rate üzerinden doğru örnek
sayısına dönüşür ve modele öyle yazılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def _editor(qtbot: QtBot, *, rate: float) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    widget.set_sample_rate(rate)
    return widget


def _add(editor: StepListEditor, kind: StepKind) -> None:
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(kind))
    editor.add_button.click()
    editor.list.setCurrentRow(editor.step_count() - 1)


def _window(editor: StepListEditor) -> object:
    return editor.chain().steps[0].parameters["window"]


def test_rms_window_is_a_seconds_field_when_a_rate_is_known(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add(editor, StepKind.WINDOWED_RMS)
    field = editor.param_field("window")
    assert isinstance(field, QDoubleSpinBox)
    assert field.suffix().strip() == "s"


def test_envelope_window_is_also_a_seconds_field(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add(editor, StepKind.ENVELOPE)
    assert isinstance(editor.param_field("window"), QDoubleSpinBox)


def test_seconds_value_converts_to_the_right_sample_count(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add(editor, StepKind.WINDOWED_RMS)

    editor.set_param_field("window", 0.01)  # 10 ms @ 48 kHz
    assert _window(editor) == 480

    editor.set_param_field("window", 0.02)
    assert _window(editor) == 960


def test_conversion_uses_the_channel_sample_rate(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=8.0)  # telemetri kadanjı
    _add(editor, StepKind.ENVELOPE)
    editor.set_param_field("window", 1.0)  # 1 s @ 8 Hz -> 8 örnek
    assert _window(editor) == 8


def test_nonpositive_duration_is_rejected_before_processing(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add(editor, StepKind.WINDOWED_RMS)
    default_window = _window(editor)

    editor.set_param_field("window", 0.0)
    assert editor.has_parameter_error
    assert "süre" in editor.parameter_error()
    assert _window(editor) == default_window  # commit edilmedi


def test_without_a_sample_rate_the_field_is_raw_samples(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=0.0)
    _add(editor, StepKind.WINDOWED_RMS)
    field = editor.param_field("window")
    assert isinstance(field, QSpinBox)

    editor.set_param_field("window", 7)
    assert _window(editor) == 7


def test_setting_the_rate_later_switches_the_field(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=0.0)
    _add(editor, StepKind.WINDOWED_RMS)
    assert isinstance(editor.param_field("window"), QSpinBox)

    editor.set_sample_rate(48_000.0)
    assert isinstance(editor.param_field("window"), QDoubleSpinBox)


def test_moving_average_window_stays_raw_samples(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add(editor, StepKind.MOVING_AVERAGE)
    assert isinstance(editor.param_field("window"), QSpinBox)
    editor.set_param_field("window", 9)
    assert _window(editor) == 9


def test_open_channel_wires_the_editor_sample_rate(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4.0))
    window.open_channel("ch0")

    editor = window.right_dock.analysis_tools.step_editor
    assert editor.sample_rate_hz == 8.0

    _add(editor, StepKind.WINDOWED_RMS)
    editor.set_param_field("window", 1.0)  # 1 s @ 8 Hz
    assert editor.chain().steps[0].parameters["window"] == 8

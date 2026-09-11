"""Resample hedef frekans kontrolü — `F4-026`.

Kabul: yeni sample rate türetilmiş kanal metadata'sında görünür.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

BASE = ChannelMetadata(
    id="ch0", path="p", name="Hydrophone 1", dtype="int16", sample_rate_hz=48_000.0
)


def _editor(qtbot: QtBot, *, rate: float) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    widget.set_sample_rate(rate)
    return widget


def _add_resample(editor: StepListEditor) -> None:
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.RESAMPLE))
    editor.add_button.click()
    editor.list.setCurrentRow(editor.step_count() - 1)


def test_resample_kind_is_offered(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    assert editor.kind_selector.findData(StepKind.RESAMPLE) >= 0


def test_adding_resample_autofills_the_source_rate(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add_resample(editor)
    assert editor.chain().steps[0].parameters["source_rate_hz"] == 48_000.0


def test_derived_rate_appears_after_setting_the_target(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add_resample(editor)
    editor.set_param_field("target_rate_hz", 12_000.0)

    assert not editor.derived_info.isHidden()
    assert "12000" in editor.derived_info.text()
    assert editor.derived_channel_metadata(BASE).sample_rate_hz == 12_000.0
    assert editor.derived_channel_metadata(BASE).source is ChannelSource.DERIVED


def test_changing_the_target_updates_the_derived_rate(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    _add_resample(editor)
    editor.set_param_field("target_rate_hz", 12_000.0)
    editor.set_param_field("target_rate_hz", 6_000.0)

    assert "6000" in editor.derived_info.text()
    assert editor.derived_channel_metadata(BASE).sample_rate_hz == 6_000.0


def test_derived_info_hidden_without_a_resample_step(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.SCALE))
    editor.add_button.click()
    assert editor.derived_info.isHidden()


def test_derived_info_hidden_without_a_sample_rate(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=0.0)
    _add_resample(editor)
    assert editor.derived_info.isHidden()


def test_disabled_resample_hides_the_derived_info(qtbot: QtBot) -> None:
    editor = _editor(qtbot, rate=48_000.0)
    editor.set_chain(
        ProcessingChain(
            [
                ProcessingStep(
                    StepKind.RESAMPLE,
                    "ch0",
                    {"source_rate_hz": 48_000.0, "target_rate_hz": 12_000.0},
                    enabled=False,
                )
            ]
        )
    )
    assert editor.derived_info.isHidden()


def test_apply_logs_the_derived_channel(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4.0))
    window.open_channel("ch0")

    tools = window.right_dock.analysis_tools
    editor = tools.step_editor
    _add_resample(editor)
    editor.set_param_field("target_rate_hz", 4.0)  # 8 Hz -> 4 Hz

    tools.select_custom_tab()
    tools.apply_requested.emit()

    log = "\n".join(window.bottom_dock.log_lines())
    assert "Türetilmiş kanal" in log
    assert "4 Hz" in log
    channel = window.plot_panel.channel
    assert channel is not None
    assert editor.derived_channel_metadata(channel).sample_rate_hz == 4.0

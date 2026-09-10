"""İşlem listesi editörü — `F4-006`.

Kabul: adım ekleme, silme ve sıralama modelde aynı sırayı oluşturur.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor

pytestmark = pytest.mark.gui


@pytest.fixture()
def editor(qtbot: QtBot) -> StepListEditor:
    widget = StepListEditor()
    qtbot.addWidget(widget)
    widget.set_input_channel("ch0")
    return widget


def _select_kind(editor: StepListEditor, kind: StepKind) -> None:
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(kind))


def test_add_appends_steps_in_click_order(editor: StepListEditor) -> None:
    for kind in (StepKind.SCALE, StepKind.ABS, StepKind.MOVING_AVERAGE):
        _select_kind(editor, kind)
        editor.add_button.click()

    chain = editor.chain()
    assert [s.kind for s in chain.steps] == [
        StepKind.SCALE,
        StepKind.ABS,
        StepKind.MOVING_AVERAGE,
    ]
    assert all(s.input_channel_id == "ch0" for s in chain.steps)
    assert editor.list.count() == 3


def test_remove_deletes_the_selected_step(editor: StepListEditor) -> None:
    for kind in (StepKind.SCALE, StepKind.OFFSET, StepKind.ABS):
        _select_kind(editor, kind)
        editor.add_button.click()

    editor.list.setCurrentRow(1)  # OFFSET
    editor.remove_button.click()

    assert [s.kind for s in editor.chain().steps] == [StepKind.SCALE, StepKind.ABS]


def test_move_up_and_down_reorder_the_model(editor: StepListEditor) -> None:
    for kind in (StepKind.SCALE, StepKind.OFFSET, StepKind.ABS):
        _select_kind(editor, kind)
        editor.add_button.click()

    editor.list.setCurrentRow(2)  # ABS
    editor.up_button.click()  # -> SCALE, ABS, OFFSET
    assert [s.kind for s in editor.chain().steps] == [
        StepKind.SCALE,
        StepKind.ABS,
        StepKind.OFFSET,
    ]

    editor.list.setCurrentRow(0)  # SCALE
    editor.down_button.click()  # -> ABS, SCALE, OFFSET
    assert [s.kind for s in editor.chain().steps] == [
        StepKind.ABS,
        StepKind.SCALE,
        StepKind.OFFSET,
    ]


def test_editor_round_trips_a_chain() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert app is not None
    editor = StepListEditor()
    chain = ProcessingChain(
        [
            ProcessingStep(StepKind.SCALE, "ch7", {"factor": 2.5}),
            ProcessingStep(StepKind.CLIP, "ch7", {"lo": -1.0, "hi": 1.0}),
            ProcessingStep(StepKind.MOVING_AVERAGE, "ch7", {"window": 8}, enabled=False),
        ]
    )
    editor.set_chain(chain)
    assert editor.chain().steps == chain.steps
    assert editor.list.count() == 3


def test_every_edit_emits_chain_changed(editor: StepListEditor, qtbot: QtBot) -> None:
    with qtbot.waitSignal(editor.chain_changed):
        _select_kind(editor, StepKind.SCALE)
        editor.add_button.click()
    with qtbot.waitSignal(editor.chain_changed):
        _select_kind(editor, StepKind.ABS)
        editor.add_button.click()
    editor.list.setCurrentRow(1)
    with qtbot.waitSignal(editor.chain_changed):
        editor.up_button.click()
    with qtbot.waitSignal(editor.chain_changed):
        editor.remove_button.click()


def test_add_is_disabled_without_an_input_channel(qtbot: QtBot) -> None:
    editor = StepListEditor()
    qtbot.addWidget(editor)
    assert not editor.add_button.isEnabled()

    _select_kind(editor, StepKind.ABS)
    editor.add_button.click()  # etkisiz
    assert editor.step_count() == 0

    editor.set_input_channel("ch3")
    assert editor.add_button.isEnabled()


def test_move_and_remove_are_disabled_without_a_selection(editor: StepListEditor) -> None:
    assert not editor.remove_button.isEnabled()
    assert not editor.up_button.isEnabled()
    assert not editor.down_button.isEnabled()

    _select_kind(editor, StepKind.SCALE)
    editor.add_button.click()
    editor.list.setCurrentRow(0)
    assert editor.remove_button.isEnabled()
    assert not editor.up_button.isEnabled()  # tek adım, yukarı yok
    assert not editor.down_button.isEnabled()

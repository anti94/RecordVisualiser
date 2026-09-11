"""İşlem zinciri ve işaret düzenlemelerinin geri alınması — `F4-079`.

Kabul: sıra değişikliği ve işaret düzenlemesi geri alınır.

Buradaki soru uçtan uca: kullanıcı gerçekten editörden bir adımı taşıdığında
ya da bir işareti düzenlediğinde, `Ctrl+Z` durumu **gerçekten** eski hâline
döndürüyor mu — hem modelde hem görünen listede/timeline'da.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.shortcuts import SHORTCUTS

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=50.0))
    window.open_channel("ch0")
    return window


def _editor(win: MainWindow) -> StepListEditor:
    return win.right_dock.analysis_tools.step_editor


def _seed_chain(win: MainWindow) -> None:
    """Editöre iki ayırt edilebilir adım koyar (sinyal üzerinden kaydedilir)."""
    scale = ProcessingStep.default(StepKind.SCALE, "ch0").with_parameters(factor=2.0)
    absolute = ProcessingStep.default(StepKind.ABS, "ch0")
    editor = _editor(win)
    editor.set_chain(ProcessingChain([scale, absolute]))
    win.record_edit("Zincir kuruldu")


def _add_mark(win: MainWindow, label: str, text: str = "") -> str:
    panel = win.bottom_dock.bookmarks
    panel.label_input.setText(label)
    panel.text_input.setText(text)
    panel.add_button.click()
    return next(item.id for item in win.annotations if item.label == label)


# --------------------------------------------------------------------------- #
# kisayollar
# --------------------------------------------------------------------------- #


def test_the_undo_shortcuts_are_installed() -> None:
    bindings = {spec.handler: spec.key for spec in SHORTCUTS}
    assert bindings["undo_edit"] == "Ctrl+Z"
    assert bindings["redo_edit"] == "Ctrl+Shift+Z"


def test_a_fresh_window_has_nothing_to_undo(win: MainWindow) -> None:
    assert not win.edit_history.can_undo
    assert not win.edit_history.can_redo
    assert win.undo_edit() is False
    assert win.redo_edit() is False


# --------------------------------------------------------------------------- #
# sira degisikligi geri alinir
# --------------------------------------------------------------------------- #


def test_reordering_a_step_is_recorded(win: MainWindow) -> None:
    _seed_chain(win)
    depth = len(win.edit_history)

    _editor(win).list.setCurrentRow(0)
    _editor(win).down_button.click()

    assert len(win.edit_history) == depth + 1
    assert win.edit_history.undo_label == "İşlem zinciri"


def test_undo_restores_the_previous_step_order(win: MainWindow) -> None:
    """Kabul kriterinin kendisi: sıra değişikliği geri alınır."""
    _seed_chain(win)
    editor = _editor(win)
    assert [step.kind for step in editor.chain().steps] == [StepKind.SCALE, StepKind.ABS]

    editor.list.setCurrentRow(0)
    editor.down_button.click()
    assert [step.kind for step in editor.chain().steps] == [StepKind.ABS, StepKind.SCALE]

    assert win.undo_edit() is True

    assert [step.kind for step in editor.chain().steps] == [StepKind.SCALE, StepKind.ABS]


def test_redo_reapplies_the_reordering(win: MainWindow) -> None:
    _seed_chain(win)
    editor = _editor(win)
    editor.list.setCurrentRow(0)
    editor.down_button.click()
    win.undo_edit()

    assert win.redo_edit() is True

    assert [step.kind for step in editor.chain().steps] == [StepKind.ABS, StepKind.SCALE]


def test_undoing_an_added_step_removes_it(win: MainWindow) -> None:
    editor = _editor(win)
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.SCALE))
    editor.add_button.click()
    assert editor.step_count() == 1

    assert win.undo_edit() is True
    assert editor.step_count() == 0


def test_undoing_a_removal_brings_the_step_back(win: MainWindow) -> None:
    _seed_chain(win)
    editor = _editor(win)
    editor.list.setCurrentRow(0)
    editor.remove_button.click()
    assert editor.step_count() == 1

    assert win.undo_edit() is True
    assert editor.step_count() == 2


def test_undo_is_logged(win: MainWindow) -> None:
    _seed_chain(win)
    _editor(win).list.setCurrentRow(0)
    _editor(win).down_button.click()
    win.undo_edit()
    assert any("Geri alındı" in line for line in win.bottom_dock.log_lines())


def test_redo_is_logged(win: MainWindow) -> None:
    _seed_chain(win)
    _editor(win).list.setCurrentRow(0)
    _editor(win).down_button.click()
    win.undo_edit()
    win.redo_edit()
    assert any("Yeniden uygulandı" in line for line in win.bottom_dock.log_lines())


# --------------------------------------------------------------------------- #
# isaret duzenlemesi geri alinir
# --------------------------------------------------------------------------- #


def test_undoing_an_annotation_edit_restores_the_old_label(win: MainWindow) -> None:
    """Kabul kriterinin kendisi: işaret düzenlemesi geri alınır."""
    mark_id = _add_mark(win, "Eski", "ilk not")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()
    edited = win.annotations.get(mark_id)
    assert edited is not None and edited.label == "Yeni"

    assert win.undo_edit() is True

    restored = win.annotations.get(mark_id)
    assert restored is not None
    assert restored.label == "Eski"
    assert restored.text == "ilk not"


def test_the_restored_label_is_shown_in_the_list(win: MainWindow) -> None:
    mark_id = _add_mark(win, "Eski")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()

    win.undo_edit()

    assert panel.row_texts(0)[2] == "Eski"


def test_undoing_an_added_bookmark_removes_it_from_the_timeline(win: MainWindow) -> None:
    _add_mark(win, "TX")
    assert win.plot_panel.bookmark_count() == 1

    assert win.undo_edit() is True

    assert len(win.annotations) == 0
    assert win.plot_panel.bookmark_count() == 0
    assert win.bottom_dock.bookmarks.row_count() == 0


def test_undoing_a_removal_brings_the_bookmark_back(win: MainWindow) -> None:
    mark_id = _add_mark(win, "Silinecek", "notu")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.remove_button.click()
    assert len(win.annotations) == 0

    assert win.undo_edit() is True

    restored = win.annotations.get(mark_id)
    assert restored is not None
    assert restored.text == "notu"
    assert win.plot_panel.bookmark_count() == 1


def test_redo_reapplies_an_annotation_edit(win: MainWindow) -> None:
    mark_id = _add_mark(win, "Eski")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()
    win.undo_edit()

    assert win.redo_edit() is True

    mark = win.annotations.get(mark_id)
    assert mark is not None and mark.label == "Yeni"


# --------------------------------------------------------------------------- #
# gecmisin butunlugu
# --------------------------------------------------------------------------- #


def test_undoing_does_not_record_itself(win: MainWindow) -> None:
    """Geri alma yeni bir geçmiş adımı yaratmamalı; yoksa ileri alma bozulurdu."""
    _add_mark(win, "TX")
    depth = len(win.edit_history)

    win.undo_edit()

    assert len(win.edit_history) == depth
    assert win.edit_history.can_redo


def test_a_new_edit_after_an_undo_drops_the_redo_branch(win: MainWindow) -> None:
    # Ayrı zamanlar: işaret listesi zamana göre sıralıdır (`F4-074`).
    win.playback_dock.set_position(1.0)
    _add_mark(win, "bir")
    win.playback_dock.set_position(2.0)
    _add_mark(win, "iki")
    win.undo_edit()
    assert win.edit_history.can_redo

    win.playback_dock.set_position(3.0)
    _add_mark(win, "başka dal")

    assert not win.edit_history.can_redo
    assert [item.label for item in win.annotations] == ["bir", "başka dal"]


def test_chain_and_bookmark_edits_share_one_history(win: MainWindow) -> None:
    """İki düzenleme türü tek bir sırada geri alınır."""
    _seed_chain(win)
    _add_mark(win, "TX")

    assert win.undo_edit() is True  # once isaret
    assert len(win.annotations) == 0
    assert _editor(win).step_count() == 2

    assert win.undo_edit() is True  # sonra zincir
    assert _editor(win).step_count() == 0


def test_opening_another_recording_clears_the_history(win: MainWindow) -> None:
    _add_mark(win, "Eski kayıt")
    assert win.edit_history.can_undo

    win.set_repository(MockRecordingRepository(duration_s=3.0))

    assert not win.edit_history.can_undo
    assert not win.edit_history.can_redo
    assert win.undo_edit() is False

"""Zincir ve işaret düzenlemeleri için undo/redo yığını — `F4-079`.

Kabul: sıra değişikliği ve işaret düzenlemesi geri alınır.

Yığın saf veridir; burada kuralları doğrudan sınanır — geri/ileri gitme,
aynı durumun yığına girmemesi, yeni bir düzenlemenin redo dalını silmesi
ve sınırın eskileri düşürmesi.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.application.edit_history import (
    MAX_EDIT_HISTORY,
    EditHistory,
    EditHistoryError,
    EditSnapshot,
)
from sonar_analyzer.domain.annotation import Annotation, AnnotationSet
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind

SECOND = 1_000_000_000


def _step(kind: StepKind = StepKind.SCALE, factor: float = 1.0) -> ProcessingStep:
    step = ProcessingStep.default(kind, "ch0")
    return step.with_parameters(factor=factor) if kind is StepKind.SCALE else step


def _snapshot(
    steps: tuple[ProcessingStep, ...] = (),
    marks: tuple[Annotation, ...] = (),
    label: str = "",
) -> EditSnapshot:
    return EditSnapshot(ProcessingChain(list(steps)), AnnotationSet(marks), label)


def _mark(label: str = "TX", start: int = SECOND, mark_id: str = "b1") -> Annotation:
    return Annotation.bookmark(label, start, annotation_id=mark_id)


# --------------------------------------------------------------------------- #
# baslangic
# --------------------------------------------------------------------------- #


def test_a_fresh_history_has_nothing_to_undo() -> None:
    history = EditHistory(_snapshot())
    assert not history.can_undo
    assert not history.can_redo
    assert history.undo_label is None
    assert history.redo_label is None
    assert history.undo() is None
    assert history.redo() is None
    assert len(history) == 1


def test_the_initial_state_is_the_current_one() -> None:
    initial = _snapshot((_step(),))
    assert EditHistory(initial).current is initial


def test_a_nonpositive_limit_is_refused() -> None:
    with pytest.raises(EditHistoryError, match="en az 1"):
        EditHistory(_snapshot(), max_history=0)


def test_the_default_limit_is_documented() -> None:
    assert MAX_EDIT_HISTORY == 100


# --------------------------------------------------------------------------- #
# kayit ve geri alma
# --------------------------------------------------------------------------- #


def test_recording_a_change_enables_undo() -> None:
    history = EditHistory(_snapshot())
    assert history.record(_snapshot((_step(),), label="Adım eklendi"))
    assert history.can_undo
    assert history.undo_label == "Adım eklendi"
    assert len(history) == 2


def test_undo_returns_the_previous_state() -> None:
    history = EditHistory(_snapshot())
    history.record(_snapshot((_step(),), label="Adım eklendi"))

    restored = history.undo()

    assert restored is not None
    assert restored.chain.steps == []
    assert not history.can_undo
    assert history.can_redo


def test_redo_returns_the_undone_state() -> None:
    history = EditHistory(_snapshot())
    history.record(_snapshot((_step(),), label="Adım eklendi"))
    history.undo()

    restored = history.redo()

    assert restored is not None
    assert len(restored.chain.steps) == 1
    assert history.can_undo
    assert not history.can_redo


def test_the_same_state_is_not_recorded_twice() -> None:
    """Aynı değere geri yazmak boş bir geri alma adımı üretmemeli."""
    history = EditHistory(_snapshot((_step(factor=2.0),)))
    assert not history.record(_snapshot((_step(factor=2.0),), label="Değişmedi"))
    assert not history.can_undo
    assert len(history) == 1


def test_a_label_alone_is_not_a_change() -> None:
    history = EditHistory(_snapshot(label="ilk"))
    assert not history.record(_snapshot(label="başka etiket"))
    assert not history.can_undo


def test_a_new_edit_drops_the_redo_branch() -> None:
    history = EditHistory(_snapshot())
    history.record(_snapshot((_step(factor=2.0),), label="bir"))
    history.record(_snapshot((_step(factor=3.0),), label="iki"))
    history.undo()
    assert history.can_redo

    history.record(_snapshot((_step(factor=9.0),), label="baska dal"))

    assert not history.can_redo
    assert history.undo_label == "baska dal"


def test_several_steps_can_be_walked_back_and_forth() -> None:
    history = EditHistory(_snapshot())
    for index in range(1, 4):
        history.record(_snapshot((_step(factor=float(index)),), label=f"adım {index}"))

    assert history.undo() is not None
    assert history.undo() is not None
    assert history.current.chain.steps[0].parameters["factor"] == 1.0
    assert history.redo() is not None
    assert history.current.chain.steps[0].parameters["factor"] == 2.0


def test_the_history_is_bounded() -> None:
    history = EditHistory(_snapshot(), max_history=3)
    for index in range(10):
        history.record(_snapshot((_step(factor=float(index + 1)),), label=str(index)))
    assert len(history) == 3
    # En eskiler dustu; en yeni uc durum kaldi.
    assert history.undo_label == "9"


def test_reset_clears_both_directions() -> None:
    history = EditHistory(_snapshot())
    history.record(_snapshot((_step(),), label="bir"))
    history.undo()

    history.reset(_snapshot(label="yeni kayıt"))

    assert not history.can_undo
    assert not history.can_redo
    assert len(history) == 1


# --------------------------------------------------------------------------- #
# sira degisikligi (kabul kriteri)
# --------------------------------------------------------------------------- #


def test_a_reordering_is_a_recordable_change() -> None:
    """Aynı adımlar, farklı sıra: geçmiş bunu bir değişiklik saymalı."""
    scale, absolute = _step(StepKind.SCALE), _step(StepKind.ABS)
    history = EditHistory(_snapshot((scale, absolute)))

    assert history.record(_snapshot((absolute, scale), label="Adım taşındı"))
    assert history.can_undo

    restored = history.undo()
    assert restored is not None
    assert [step.kind for step in restored.chain.steps] == [StepKind.SCALE, StepKind.ABS]


def test_undoing_a_reorder_restores_the_exact_order() -> None:
    first, second, third = (
        _step(factor=1.0),
        _step(factor=2.0),
        _step(factor=3.0),
    )
    history = EditHistory(_snapshot((first, second, third)))
    history.record(_snapshot((third, first, second), label="Adım taşındı"))

    restored = history.undo()

    assert restored is not None
    assert [step.parameters["factor"] for step in restored.chain.steps] == [1.0, 2.0, 3.0]


# --------------------------------------------------------------------------- #
# isaret duzenlemesi (kabul kriteri)
# --------------------------------------------------------------------------- #


def test_an_annotation_edit_is_a_recordable_change() -> None:
    history = EditHistory(_snapshot(marks=(_mark("Eski"),)))
    assert history.record(_snapshot(marks=(_mark("Yeni"),), label="İşaret düzenlendi"))

    restored = history.undo()

    assert restored is not None
    mark = restored.annotations.get("b1")
    assert mark is not None and mark.label == "Eski"


def test_undoing_an_annotation_removal_brings_it_back() -> None:
    history = EditHistory(_snapshot(marks=(_mark(),)))
    history.record(_snapshot(label="İşaret silindi"))
    assert len(history.current.annotations) == 0

    restored = history.undo()

    assert restored is not None
    assert len(restored.annotations) == 1


def test_moving_an_annotation_in_time_is_a_change() -> None:
    history = EditHistory(_snapshot(marks=(_mark(start=SECOND),)))
    assert history.record(_snapshot(marks=(_mark(start=5 * SECOND),), label="İşaret taşındı"))
    restored = history.undo()
    assert restored is not None
    mark = restored.annotations.get("b1")
    assert mark is not None and mark.start_ns == SECOND


def test_chain_and_annotations_are_undone_together() -> None:
    """Anlık görüntü ikisini birden taşır; geri alma ikisini birden döndürür."""
    history = EditHistory(_snapshot())
    history.record(_snapshot((_step(),), (_mark(),), label="ikisi birden"))

    restored = history.undo()

    assert restored is not None
    assert restored.chain.steps == []
    assert len(restored.annotations) == 0

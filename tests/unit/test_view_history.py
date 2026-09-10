"""Görünüm ayarları undo/redo yığını — `F3-041`."""

from __future__ import annotations

from sonar_analyzer.application.view_history import ViewCommand, ViewHistory


class _Box:
    def __init__(self) -> None:
        self.value = "start"
        self.applies = 0
        self.reverts = 0

    def command(self, new: str, old: str) -> ViewCommand:
        def _apply() -> None:
            self.value = new
            self.applies += 1

        def _revert() -> None:
            self.value = old
            self.reverts += 1

        return ViewCommand(label=f"{old}->{new}", apply=_apply, revert=_revert)


def test_push_runs_apply_immediately() -> None:
    box = _Box()
    history = ViewHistory()

    history.push(box.command("red", "start"))

    assert box.value == "red"
    assert box.applies == 1
    assert history.can_undo
    assert not history.can_redo


def test_undo_then_redo_round_trips() -> None:
    box = _Box()
    history = ViewHistory()
    history.push(box.command("red", "start"))

    assert history.undo() is True
    assert box.value == "start"
    assert history.can_redo

    assert history.redo() is True
    assert box.value == "red"
    assert history.can_undo
    assert not history.can_redo


def test_pushing_after_an_undo_discards_the_redo_branch() -> None:
    box = _Box()
    history = ViewHistory()
    history.push(box.command("red", "start"))
    history.undo()

    history.push(box.command("blue", "start"))

    assert box.value == "blue"
    assert not history.can_redo
    assert history.redo() is False


def test_undo_and_redo_on_empty_history_return_false() -> None:
    history = ViewHistory()

    assert history.undo() is False
    assert history.redo() is False


def test_labels_track_the_top_of_each_stack() -> None:
    box = _Box()
    history = ViewHistory()
    history.push(box.command("a", "start"))
    history.push(box.command("b", "a"))

    assert history.undo_label == "a->b"
    history.undo()
    assert history.redo_label == "a->b"
    assert history.undo_label == "start->a"


def test_history_is_capped_at_max() -> None:
    box = _Box()
    history = ViewHistory(max_history=3)
    for i in range(5):
        history.push(box.command(str(i), str(i - 1)))

    # 3 komut geri alinabilir olmali
    assert history.undo() and history.undo() and history.undo()
    assert history.undo() is False


def test_clear_empties_both_stacks() -> None:
    box = _Box()
    history = ViewHistory()
    history.push(box.command("red", "start"))
    history.undo()

    history.clear()

    assert not history.can_undo
    assert not history.can_redo

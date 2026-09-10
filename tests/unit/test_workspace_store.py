"""Workspace dosyasını atomik yaz / oku — `F3-068`."""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.workspace.model import PanelState, WorkspaceError, WorkspaceModel
from sonar_analyzer.workspace.store import load_workspace, save_workspace


def _model() -> WorkspaceModel:
    return WorkspaceModel(
        source_paths=["C:/data/a.bin"],
        panels=[PanelState(channel_ids=["ch0"], x_range=(0.0, 5.0))],
        sync_groups=[[0]],
        active_view_tab="Time Series",
        dock_state="Zm9v",
    )


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    dest = save_workspace(_model(), tmp_path / "w.json")
    assert dest.exists()
    assert load_workspace(dest) == _model()


def test_save_is_atomic_no_partial_left(tmp_path: Path) -> None:
    dest = tmp_path / "w.json"
    save_workspace(_model(), dest)
    assert not dest.with_name(dest.name + ".part").exists()


def test_save_creates_missing_directories(tmp_path: Path) -> None:
    dest = save_workspace(_model(), tmp_path / "a" / "b" / "w.json")
    assert dest.exists()


def test_load_missing_file_raises_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_workspace(tmp_path / "nope.json")


def test_load_corrupt_file_raises_workspace_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(WorkspaceError):
        load_workspace(bad)


def test_overwrite_replaces_the_previous_workspace(tmp_path: Path) -> None:
    dest = tmp_path / "w.json"
    save_workspace(WorkspaceModel(source_paths=["old.bin"]), dest)
    save_workspace(WorkspaceModel(source_paths=["new.bin"]), dest)
    assert load_workspace(dest).source_paths == ["new.bin"]

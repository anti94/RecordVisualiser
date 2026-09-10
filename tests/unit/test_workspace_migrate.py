"""Workspace şema sürüm geçişi — `F3-071`.

Kabul: eski örnek sürüm dönüştürülür; bilinmeyen yeni sürüm anlaşılır
reddedilir.
"""

from __future__ import annotations

import json

import pytest

from sonar_analyzer.workspace.migrate import migrate_document
from sonar_analyzer.workspace.model import (
    WORKSPACE_SCHEMA_VERSION,
    PanelState,
    UnsupportedWorkspaceVersion,
    WorkspaceError,
    WorkspaceModel,
)

#: Elle yazılmış bir v0 (legacy) belge örneği.
LEGACY_V0 = {
    "schema_version": 0,
    "open_files": ["C:/data/run1.bin"],
    "tab": "Transmission",
    "panels": [
        {"channels": ["ch0", "ch2"], "x_range": [0.0, 8.0], "zoom_mode": "x"},
        {"channels": ["ch1"]},
    ],
    "active_panel": 1,
}


def test_v0_document_migrates_to_the_current_schema() -> None:
    migrated = migrate_document(LEGACY_V0)
    assert migrated["schema_version"] == WORKSPACE_SCHEMA_VERSION

    model = WorkspaceModel.from_dict(migrated)
    assert model.source_paths == ["C:/data/run1.bin"]  # open_files -> source_paths
    assert model.active_view_tab == "Transmission"  # tab -> active_view_tab
    assert model.panels[0].channel_ids == ["ch0", "ch2"]  # channels -> channel_ids
    assert model.panels[0].x_range == (0.0, 8.0)
    assert model.panels[0].zoom_mode == "x"
    assert model.panels[1] == PanelState(channel_ids=["ch1"])
    # v0'da olmayan alanlar v1 varsayılanına düşer
    assert model.sync_groups == []
    assert model.dock_state is None


def test_loads_transparently_migrates_a_v0_file() -> None:
    model = WorkspaceModel.loads(json.dumps(LEGACY_V0))
    assert model.schema_version == WORKSPACE_SCHEMA_VERSION
    assert model.source_paths == ["C:/data/run1.bin"]


def test_current_version_document_passes_through_untouched() -> None:
    current = WorkspaceModel(source_paths=["a.bin"]).to_dict()
    assert migrate_document(current) == current


def test_newer_unknown_version_is_rejected_clearly() -> None:
    future = WorkspaceModel().to_dict()
    future["schema_version"] = WORKSPACE_SCHEMA_VERSION + 5
    with pytest.raises(UnsupportedWorkspaceVersion) as excinfo:
        migrate_document(future)
    message = str(excinfo.value)
    assert str(WORKSPACE_SCHEMA_VERSION + 5) in message
    assert "güncelleyin" in message.lower()


def test_loads_rejects_a_newer_version_via_migration() -> None:
    future = WorkspaceModel().to_dict()
    future["schema_version"] = 99
    with pytest.raises(UnsupportedWorkspaceVersion):
        WorkspaceModel.loads(json.dumps(future))


def test_missing_version_is_a_workspace_error() -> None:
    with pytest.raises(WorkspaceError, match="schema_version"):
        migrate_document({"panels": []})


def test_non_object_document_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="nesne olmalı"):
        migrate_document([1, 2, 3])


def test_v0_without_optional_keys_still_migrates() -> None:
    minimal = {"schema_version": 0}
    model = WorkspaceModel.from_dict(migrate_document(minimal))
    assert model == WorkspaceModel()

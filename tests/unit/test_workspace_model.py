"""Sürümlü workspace JSON modeli — `F3-067`.

Kabul: panel, kanal, görünüm ve filtre alanları serialize edilebilir.
"""

from __future__ import annotations

import json

import pytest

from sonar_analyzer.workspace.model import (
    WORKSPACE_SCHEMA_VERSION,
    EventFilterState,
    PanelState,
    UnsupportedWorkspaceVersion,
    ViewState,
    WorkspaceError,
    WorkspaceModel,
)


def _full() -> WorkspaceModel:
    return WorkspaceModel(
        source_paths=["C:/data/a.bin", "C:/data/b.bin"],
        panels=[
            PanelState(channel_ids=["ch0", "ch3"], x_range=(0.0, 12.5), zoom_mode="x"),
            PanelState(channel_ids=["ch1"], y_range=(-1.0, 1.0)),
        ],
        active_panel=1,
        layout_mode="split",
        sync_groups=[[0, 1]],
        active_view_tab="Transmission",
        dock_state="AAAA/wAAAAA=",
        view=ViewState(time_display_mode="utc", markers_visible=False, sync_x=False),
        event_filter=EventFilterState(
            source="BIT",
            min_severity="warning",
            text="thermal",
            start_ns=1_000,
            end_ns=9_000,
            group_near=True,
        ),
    )


# -- round-trip ---------------------------------------------------


def test_dict_round_trip_preserves_every_field() -> None:
    original = _full()
    assert WorkspaceModel.from_dict(original.to_dict()) == original


def test_json_round_trip_preserves_every_field() -> None:
    original = _full()
    assert WorkspaceModel.loads(original.dumps()) == original


def test_defaults_round_trip() -> None:
    empty = WorkspaceModel()
    assert WorkspaceModel.from_dict(empty.to_dict()) == empty
    assert empty.schema_version == WORKSPACE_SCHEMA_VERSION
    assert empty.layout_mode == "tabs"
    assert empty.view == ViewState()
    assert empty.event_filter == EventFilterState()


def test_to_dict_stamps_the_schema_version() -> None:
    doc = json.loads(_full().dumps())
    assert doc["schema_version"] == WORKSPACE_SCHEMA_VERSION
    # dört yön de belgede
    assert doc["panels"][0]["channel_ids"] == ["ch0", "ch3"]
    assert doc["panels"][0]["x_range"] == [0.0, 12.5]
    assert doc["view"]["time_display_mode"] == "utc"
    assert doc["event_filter"]["source"] == "BIT"


def test_document_contains_open_tabs_axes_and_sync_groups() -> None:
    """`F3-068` kabulü: belge açık tab, eksen ve senkronizasyon grupları taşır."""
    doc = json.loads(_full().dumps())
    assert doc["active_view_tab"] == "Transmission"  # açık tab
    assert doc["panels"][0]["x_range"] == [0.0, 12.5]  # eksen
    assert doc["panels"][1]["y_range"] == [-1.0, 1.0]
    assert doc["sync_groups"] == [[0, 1]]  # senkronizasyon grubu
    assert doc["dock_state"] == "AAAA/wAAAAA="  # dock yerleşimi


def test_sync_group_panel_index_out_of_range_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="sync_groups"):
        WorkspaceModel(panels=[PanelState()], sync_groups=[[0, 3]])


def test_bad_sync_groups_shape_is_rejected() -> None:
    doc = WorkspaceModel().to_dict()
    doc["sync_groups"] = [["a", "b"]]
    with pytest.raises(WorkspaceError, match="sync_groups"):
        WorkspaceModel.from_dict(doc)


# -- doğrulama --------------------------------------------------


def test_missing_schema_version_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="schema_version"):
        WorkspaceModel.from_dict({"panels": []})


def test_newer_schema_version_is_rejected_distinctly() -> None:
    doc = _full().to_dict()
    doc["schema_version"] = WORKSPACE_SCHEMA_VERSION + 1
    with pytest.raises(UnsupportedWorkspaceVersion):
        WorkspaceModel.from_dict(doc)


def test_older_or_equal_schema_version_is_accepted() -> None:
    doc = _full().to_dict()
    doc["schema_version"] = WORKSPACE_SCHEMA_VERSION
    assert WorkspaceModel.from_dict(doc).schema_version == WORKSPACE_SCHEMA_VERSION


def test_unknown_layout_mode_is_rejected() -> None:
    doc = WorkspaceModel().to_dict()
    doc["layout_mode"] = "cascade"
    with pytest.raises(WorkspaceError, match="layout_mode"):
        WorkspaceModel.from_dict(doc)


def test_unknown_zoom_mode_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="zoom_mode"):
        PanelState.from_dict({"channel_ids": [], "zoom_mode": "diagonal"})


def test_bad_channel_id_list_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="metin listesi"):
        PanelState.from_dict({"channel_ids": ["ch0", 3]})


def test_bad_range_pair_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="çift"):
        PanelState.from_dict({"channel_ids": [], "x_range": [1.0, 2.0, 3.0]})


def test_non_object_document_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="nesne olmalı"):
        WorkspaceModel.from_dict([1, 2, 3])


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="JSON"):
        WorkspaceModel.loads("{not json")


def test_active_panel_out_of_range_is_rejected() -> None:
    with pytest.raises(WorkspaceError, match="active_panel"):
        WorkspaceModel(panels=[PanelState()], active_panel=5)


def test_event_filter_start_ns_must_be_int() -> None:
    with pytest.raises(WorkspaceError, match="start_ns"):
        EventFilterState.from_dict({"start_ns": "soon"})


def test_bool_is_not_accepted_as_int_for_start_ns() -> None:
    with pytest.raises(WorkspaceError):
        EventFilterState.from_dict({"start_ns": True})

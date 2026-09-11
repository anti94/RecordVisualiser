"""Analiz oturumunda zincir ve annotation kaydı — `F4-076`.

Kabul: kaynaklar, işlemler, renkler ve bookmark'lar tek projede saklanır.

Dört şeyin de **tek dosyada** olduğu ve **geri yüklendiğinde aynı**
geldiği denetlenir. Ölçüt tur bütünlüğüdür: oturum kur → kaydet → yeni
bir pencere aç → geri yükle → dördü de yerinde mi.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.annotation import Annotation, AnnotationSet
from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.repository.derived_repository import DerivedChannelRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.migrate import migrate_document
from sonar_analyzer.workspace.model import (
    WORKSPACE_SCHEMA_VERSION,
    SeriesStyleState,
    WorkspaceError,
    WorkspaceModel,
)

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000
DURATION_S = 8.0


def _window(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=50.0))
    window.open_channel("ch0")
    return window


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    return _window(qtbot)


def _furnish(win: MainWindow) -> None:
    """Oturumu dört bileşenle de doldurur."""
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    repository.add(
        DerivedChannelDefinition(name="Fark", inputs=("ch0", "ch1"), expression="ch0 - ch1")
    )
    win.set_recording(repository.metadata(), repository.channels())
    win.open_channel("ch0")
    win.plot_panel.set_series_style("ch0", color="#FF00AA", width=3, line_style="dash")
    win.set_annotations(
        AnnotationSet(
            (
                Annotation.bookmark(
                    "TX", win.playback_dock.current_time_ns(), text="not", annotation_id="b1"
                ),
            )
        )
    )


# --------------------------------------------------------------------------- #
# model semasi
# --------------------------------------------------------------------------- #


def test_the_schema_version_moved_to_two() -> None:
    assert WORKSPACE_SCHEMA_VERSION == 2


def test_a_default_model_has_empty_session_records() -> None:
    model = WorkspaceModel()
    assert model.derived_channels == []
    assert model.annotations == []
    assert model.series_styles == {}


def test_the_document_carries_all_four_families() -> None:
    payload = WorkspaceModel(source_paths=["a.bin"]).to_dict()
    assert {"source_paths", "derived_channels", "annotations", "series_styles"} <= set(payload)


def test_a_model_round_trips_through_json() -> None:
    model = WorkspaceModel(
        source_paths=["a.bin"],
        derived_channels=[
            DerivedChannelDefinition(
                name="Fark", inputs=("ch0", "ch1"), expression="ch0 - ch1"
            ).to_dict()
        ],
        annotations=[Annotation.bookmark("TX", 3 * SECOND, annotation_id="b1").to_dict()],
        series_styles={"ch0": SeriesStyleState(color="#FF0000", width=2)},
    )
    restored = WorkspaceModel.loads(model.dumps())
    assert restored.source_paths == ["a.bin"]
    assert restored.derived_channels == model.derived_channels
    assert restored.annotations == model.annotations
    assert restored.series_styles == model.series_styles


def test_a_series_style_needs_a_colour() -> None:
    with pytest.raises(WorkspaceError, match="'color' boş olamaz"):
        SeriesStyleState(color="  ")


def test_a_series_style_needs_a_positive_width() -> None:
    with pytest.raises(WorkspaceError, match="'width' >= 1"):
        SeriesStyleState(color="#FF0000", width=0)


@pytest.mark.parametrize("field_name", ["derived_channels", "annotations"])
def test_a_non_list_record_family_is_refused(field_name: str) -> None:
    payload = WorkspaceModel().to_dict()
    payload[field_name] = "not a list"
    with pytest.raises(WorkspaceError, match="liste olmalı"):
        WorkspaceModel.from_dict(payload)


def test_a_record_that_is_not_an_object_is_refused() -> None:
    payload = WorkspaceModel().to_dict()
    payload["annotations"] = ["not an object"]
    with pytest.raises(WorkspaceError):
        WorkspaceModel.from_dict(payload)


# --------------------------------------------------------------------------- #
# eski dosyalar
# --------------------------------------------------------------------------- #


def test_a_version_one_document_migrates_without_losing_anything() -> None:
    """v1 alanları korunur, v2 alanları boş varsayılanla eklenir."""
    legacy: dict[str, object] = {
        "schema_version": 1,
        "source_paths": ["kayit.bin"],
        "panels": [{"channel_ids": ["ch0"], "zoom_mode": "x"}],
        "active_panel": 0,
        "layout_mode": "tabs",
        "active_view_tab": "Time Series",
    }
    migrated = migrate_document(legacy)

    assert migrated["schema_version"] == 2
    assert migrated["source_paths"] == ["kayit.bin"]
    assert migrated["derived_channels"] == []
    assert migrated["annotations"] == []
    assert migrated["series_styles"] == {}

    model = WorkspaceModel.from_dict(migrated)
    assert model.panels[0].channel_ids == ["ch0"]
    assert model.panels[0].zoom_mode == "x"


def test_a_legacy_v0_document_still_reaches_version_two() -> None:
    legacy: dict[str, object] = {
        "schema_version": 0,
        "open_files": ["eski.bin"],
        "panels": [{"channels": ["ch1"]}],
        "tab": "Transmission",
    }
    model = WorkspaceModel.from_dict(migrate_document(legacy))
    assert model.schema_version == 2
    assert model.source_paths == ["eski.bin"]
    assert model.annotations == []


# --------------------------------------------------------------------------- #
# uctan uca: dordu birden tek projede
# --------------------------------------------------------------------------- #


def test_the_capture_holds_all_four_families(win: MainWindow) -> None:
    _furnish(win)
    model = win.capture_workspace()

    assert model.panels[0].channel_ids == ["ch0"]
    assert [record["name"] for record in model.derived_channels] == ["Fark"]
    assert [record["label"] for record in model.annotations] == ["TX"]
    assert model.series_styles["ch0"].color == "#FF00AA"


def test_the_saved_file_holds_all_four_families(win: MainWindow, tmp_path: Path) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["schema_version"] == 2
    assert document["panels"][0]["channel_ids"] == ["ch0"]
    assert document["derived_channels"][0]["expression"] == "ch0 - ch1"
    assert document["annotations"][0]["label"] == "TX"
    assert document["series_styles"]["ch0"]["color"] == "#FF00AA"


def test_restoring_brings_back_the_derived_channel(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    other = _window(qtbot)
    other.restore_workspace(target)

    repository = other.repository
    assert isinstance(repository, DerivedChannelRepository)
    assert [definition.name for definition in repository.definitions()] == ["Fark"]
    assert any(channel.path == "Derived/Fark" for channel in repository.channels())


def test_the_restored_derived_channel_still_computes(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    other = _window(qtbot)
    other.restore_workspace(target)

    repository = other.repository
    assert isinstance(repository, DerivedChannelRepository)
    derived = next(channel for channel in repository.channels() if channel.name == "Fark")
    span = repository.metadata().time_range
    result = repository.query(derived.id, span)
    expected = repository.query("ch0", span).values - repository.query("ch1", span).values
    assert len(result) == len(expected)
    # Kaynak float32, türetilmiş sonuç float64; fark yalnız gösterim hassasiyeti.
    assert np.allclose(result.values, expected, rtol=1e-6, atol=1e-6)


def test_restoring_brings_back_the_bookmarks(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    original = next(iter(win.annotations))
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    other = _window(qtbot)
    other.restore_workspace(target)

    assert len(other.annotations) == 1
    restored = next(iter(other.annotations))
    assert restored == original
    assert other.bottom_dock.bookmarks.row_count() == 1
    assert other.plot_panel.bookmark_count() == 1


def test_restoring_brings_back_the_series_colour(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    other = _window(qtbot)
    other.restore_workspace(target)

    style = other.plot_panel.series_style("ch0")
    assert style.color == "#FF00AA"
    assert style.width == 3
    assert style.line_style == "dash"


def test_restoring_brings_back_the_sources(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    model = win.capture_workspace()
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    assert WorkspaceModel.loads(target.read_text(encoding="utf-8")).source_paths == (
        model.source_paths
    )


# --------------------------------------------------------------------------- #
# bozuk kayitlar oturumu dusurmez
# --------------------------------------------------------------------------- #


def test_a_broken_annotation_is_skipped_and_explained(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    document = json.loads(target.read_text(encoding="utf-8"))
    document["annotations"].append({"schema_version": 1, "id": "kirik", "label": ""})
    target.write_text(json.dumps(document), encoding="utf-8")

    other = _window(qtbot)
    other.restore_workspace(target)

    assert [item.label for item in other.annotations] == ["TX"]
    assert any("İşaret geri yüklenemedi" in line for line in other.bottom_dock.log_lines())


def test_a_derived_channel_with_a_missing_input_is_skipped_and_explained(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    document = json.loads(target.read_text(encoding="utf-8"))
    document["derived_channels"].append(
        DerivedChannelDefinition(name="Yetim", inputs=("chYok",), expression="chYok * 2").to_dict()
    )
    target.write_text(json.dumps(document), encoding="utf-8")

    other = _window(qtbot)
    other.restore_workspace(target)

    repository = other.repository
    assert isinstance(repository, DerivedChannelRepository)
    assert [definition.name for definition in repository.definitions()] == ["Fark"]
    assert any(
        "Türetilmiş kanal geri yüklenemedi" in line for line in other.bottom_dock.log_lines()
    )


def test_a_style_for_a_channel_that_is_not_plotted_is_ignored(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    document = json.loads(target.read_text(encoding="utf-8"))
    document["series_styles"]["ch7"] = {"color": "#123456", "width": 9, "line_style": "solid"}
    target.write_text(json.dumps(document), encoding="utf-8")

    other = _window(qtbot)
    other.restore_workspace(target)  # cizili olmayan kanal sessizce atlanir

    assert other.plot_panel.series_style("ch0").color == "#FF00AA"
    with pytest.raises(KeyError):
        other.plot_panel.series_style("ch7")

"""Taşınmış kaynağın çalışma alanında yeniden konumlandırılması — `F4-078`.

Kabul: yeni konum seçimi kaynak kimliğini doğrular; yanlış dosya sessizce
bağlanmaz.

Buradaki soru uçtan uca: çalışma alanı kaynak kimliğini gerçekten
saklıyor mu, taşınan dosya kabul ediliyor mu, yanlış dosya **reddedilip
model el değmemiş** kalıyor mu.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.migrate import migrate_document
from sonar_analyzer.workspace.model import (
    WORKSPACE_SCHEMA_VERSION,
    WorkspaceModel,
)
from sonar_analyzer.workspace.source_identity import RelocationError, SourceIdentity

pytestmark = pytest.mark.gui

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    target = tmp_path / "kayit.bin"
    shutil.copyfile(FIXTURE, target)
    return target


def _model(source: Path, win: MainWindow) -> WorkspaceModel:
    """Kaynağı ve kimliğini taşıyan bir çalışma alanı modeli."""
    from sonar_analyzer.workspace.source_identity import identity_for_path

    return WorkspaceModel(
        source_paths=[str(source)],
        source_identities={str(source): identity_for_path(source).to_dict()},
    )


# --------------------------------------------------------------------------- #
# sema
# --------------------------------------------------------------------------- #


def test_the_schema_version_moved_to_four() -> None:
    assert WORKSPACE_SCHEMA_VERSION == 4


def test_the_document_carries_the_source_identities() -> None:
    assert "source_identities" in WorkspaceModel().to_dict()
    assert WorkspaceModel().source_identities == {}


def test_a_version_three_document_migrates_without_losing_anything() -> None:
    legacy: dict[str, object] = {
        "schema_version": 3,
        "source_paths": ["kayit.bin"],
        "panels": [],
        "processing_chain": [{"kind": "abs", "input_channel_id": "ch0", "parameters": {}}],
    }
    migrated = migrate_document(legacy)
    assert migrated["schema_version"] == 4
    assert migrated["source_identities"] == {}
    assert migrated["processing_chain"] == legacy["processing_chain"]


def test_the_model_round_trips_the_identities(source: Path, win: MainWindow) -> None:
    model = _model(source, win)
    restored = WorkspaceModel.loads(model.dumps())
    assert restored.source_identities == model.source_identities
    identity = SourceIdentity.from_dict(restored.source_identities[str(source)])
    assert identity.size_bytes == source.stat().st_size


# --------------------------------------------------------------------------- #
# yakalama
# --------------------------------------------------------------------------- #


def test_saving_records_an_identity_for_every_source(
    win: MainWindow, qtbot: QtBot, source: Path, tmp_path: Path
) -> None:
    win.file_open._dialog = lambda _p, _s: [str(source)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    target = win.save_workspace(tmp_path / "oturum.sonarws")

    document = json.loads(target.read_text(encoding="utf-8"))
    assert len(document["source_paths"]) == 1
    recorded = document["source_identities"][document["source_paths"][0]]
    assert recorded["size_bytes"] == source.stat().st_size
    assert len(recorded["head_sha256"]) == 64


# --------------------------------------------------------------------------- #
# dogru dosya kabul edilir
# --------------------------------------------------------------------------- #


def test_the_same_recording_at_a_new_path_is_accepted(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    model = _model(source, win)
    moved = tmp_path / "arsiv" / "kayit.bin"
    moved.parent.mkdir()
    shutil.copyfile(source, moved)

    updated = win.relocate_source(model, str(source), moved)

    assert updated.source_paths == [str(moved)]
    assert str(moved) in updated.source_identities
    assert str(source) not in updated.source_identities


def test_a_renamed_copy_is_accepted(win: MainWindow, source: Path, tmp_path: Path) -> None:
    model = _model(source, win)
    renamed = tmp_path / "bambaska.bin"
    shutil.copyfile(source, renamed)
    assert win.relocate_source(model, str(source), renamed).source_paths == [str(renamed)]


def test_a_successful_relocation_is_logged(win: MainWindow, source: Path, tmp_path: Path) -> None:
    model = _model(source, win)
    moved = tmp_path / "yeni.bin"
    shutil.copyfile(source, moved)
    win.relocate_source(model, str(source), moved)
    assert any("yeniden konumlandırıldı" in line for line in win.bottom_dock.log_lines())


def test_only_the_named_source_moves(win: MainWindow, source: Path, tmp_path: Path) -> None:
    from sonar_analyzer.workspace.source_identity import identity_for_path

    other = tmp_path / "ikinci.bin"
    shutil.copyfile(FIXTURE, other)
    model = WorkspaceModel(
        source_paths=[str(source), str(other)],
        source_identities={
            str(source): identity_for_path(source).to_dict(),
            str(other): identity_for_path(other).to_dict(),
        },
    )
    moved = tmp_path / "yeni.bin"
    shutil.copyfile(source, moved)

    updated = win.relocate_source(model, str(source), moved)
    assert updated.source_paths == [str(moved), str(other)]


# --------------------------------------------------------------------------- #
# yanlis dosya SESSIZCE baglanmaz
# --------------------------------------------------------------------------- #


def test_a_different_recording_is_refused_and_the_model_is_untouched(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    model = _model(source, win)
    wrong = tmp_path / "baska.bin"
    wrong.write_bytes(b"\x00" * source.stat().st_size)

    with pytest.raises(RelocationError) as error:
        win.relocate_source(model, str(source), wrong)

    assert "baska.bin" in str(error.value)
    # Model degismedi: red bir istisnadir, sessiz bir kabul degil.
    assert model.source_paths == [str(source)]
    assert str(wrong) not in model.source_identities


def test_a_truncated_recording_is_refused(win: MainWindow, source: Path, tmp_path: Path) -> None:
    model = _model(source, win)
    truncated = tmp_path / "kirpik.bin"
    truncated.write_bytes(source.read_bytes()[:-1])
    with pytest.raises(RelocationError, match="dosya boyutu farklı"):
        win.relocate_source(model, str(source), truncated)


def test_a_recording_edited_in_place_is_refused(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    """Aynı boyut, değişmiş içerik — en sinsi durum."""
    model = _model(source, win)
    edited = tmp_path / "duzenlenmis.bin"
    data = bytearray(source.read_bytes())
    data[10] ^= 0xFF
    edited.write_bytes(bytes(data))
    with pytest.raises(RelocationError, match="başlangıcı farklı"):
        win.relocate_source(model, str(source), edited)


def test_a_path_that_is_not_in_the_workspace_is_refused(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    model = _model(source, win)
    with pytest.raises(RelocationError, match="böyle bir kaynak yok"):
        win.relocate_source(model, str(tmp_path / "hic-yok.bin"), source)


def test_a_workspace_without_a_recorded_identity_refuses_to_guess(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    """Eski (v3) belgede kimlik yok; doğrulanamayan bağlama reddedilir."""
    model = WorkspaceModel(source_paths=[str(source)])
    moved = tmp_path / "yeni.bin"
    shutil.copyfile(source, moved)

    with pytest.raises(RelocationError) as error:
        win.relocate_source(model, str(source), moved)
    assert "kayıtlı kimlik yok" in str(error.value)
    assert "bağlanmaz" in str(error.value)


def test_a_missing_candidate_is_refused(win: MainWindow, source: Path, tmp_path: Path) -> None:
    model = _model(source, win)
    with pytest.raises(RelocationError, match="Kaynak okunamadı"):
        win.relocate_source(model, str(source), tmp_path / "yok.bin")


# --------------------------------------------------------------------------- #
# eksik kaynak akisi
# --------------------------------------------------------------------------- #


def test_relocating_clears_the_path_from_the_missing_list(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    model = _model(source, win)
    win.last_missing_sources = [str(source)]
    moved = tmp_path / "yeni.bin"
    shutil.copyfile(source, moved)

    win.relocate_source(model, str(source), moved)

    assert win.last_missing_sources == []


def test_a_refused_relocation_leaves_the_missing_list_alone(
    win: MainWindow, source: Path, tmp_path: Path
) -> None:
    model = _model(source, win)
    win.last_missing_sources = [str(source)]
    wrong = tmp_path / "baska.bin"
    wrong.write_bytes(b"\x00" * 10)

    with pytest.raises(RelocationError):
        win.relocate_source(model, str(source), wrong)

    assert win.last_missing_sources == [str(source)]

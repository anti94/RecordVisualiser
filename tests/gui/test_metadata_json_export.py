"""Event/BIT metadata'sının JSON dışa aktarımı — uçtan uca `F4-084`.

Kabul: seçili aralık ve domain alanları kayıpsız çıkar.

Biçim ve alan denetimi `tests/unit/test_json_export.py`'de; burada
pencerenin gerçekten **seçili aralığı** kullandığı ve dosyanın açık
kayıttan doğru sayıları aldığı sınanır.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.export_controller import (
    FORMAT_TO_KIND,
    KIND_EXTENSION,
    ExportKind,
    kind_for_format,
)
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.data_export import EXPORT_FORMATS
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000
DURATION_S = 10.0


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=DURATION_S))
    window.open_channel("ch0")
    return window


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# bicim kaydi
# --------------------------------------------------------------------------- #


def test_json_is_an_offered_format() -> None:
    assert "JSON" in EXPORT_FORMATS
    assert kind_for_format("JSON") is ExportKind.JSON
    assert KIND_EXTENSION[ExportKind.JSON] == ".json"


def test_every_offered_kind_has_an_extension() -> None:
    for kind in FORMAT_TO_KIND.values():
        assert KIND_EXTENSION[kind].startswith(".")


# --------------------------------------------------------------------------- #
# uctan uca yazma
# --------------------------------------------------------------------------- #


def test_exporting_writes_the_open_recording(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"

    result = win.export_metadata_json(target, selected_range_only=False)

    document = _read(target)
    assert result.event_count == len(document["events"])  # type: ignore[arg-type]
    assert result.bit_count == len(document["bit_results"])  # type: ignore[arg-type]
    assert result.event_count > 0
    assert result.bit_count > 0


def test_the_document_names_the_recording(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    win.export_metadata_json(target, selected_range_only=False)

    repository = win.repository
    assert repository is not None
    recorded = _read(target)["recording"]
    assert recorded["recording_id"] == repository.metadata().recording_id  # type: ignore[index]


def test_the_full_recording_range_is_written(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    win.export_metadata_json(target, selected_range_only=False)

    repository = win.repository
    assert repository is not None
    span = repository.metadata().time_range
    recorded = _read(target)["range"]
    assert recorded["start_ns"] == span.start_ns  # type: ignore[index]
    assert recorded["end_ns"] == span.end_ns  # type: ignore[index]


def test_exporting_is_logged(win: MainWindow, tmp_path: Path) -> None:
    win.export_metadata_json(tmp_path / "metadata.json", selected_range_only=False)
    assert any("Metadata JSON" in line for line in win.bottom_dock.log_lines())


def test_without_a_recording_the_export_is_refused(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    with pytest.raises(ValueError, match="Acik kayit yok"):
        window.export_metadata_json(tmp_path / "metadata.json")


# --------------------------------------------------------------------------- #
# SECILI ARALIK
# --------------------------------------------------------------------------- #


def test_a_selected_region_narrows_the_export(win: MainWindow, tmp_path: Path) -> None:
    """Kabul kriterinin kendisi: seçili aralık dosyaya yansır."""
    whole = tmp_path / "tumu.json"
    win.export_metadata_json(whole, selected_range_only=False)

    win.plot_panel.set_time_region(1.0, 4.0)
    narrow = tmp_path / "dar.json"
    result = win.export_metadata_json(narrow, selected_range_only=True)

    assert result.event_count < len(_read(whole)["events"])  # type: ignore[arg-type]
    recorded = _read(narrow)["range"]
    region = win.plot_panel.time_region_range()
    assert region is not None
    assert recorded["start_ns"] == region.start_ns  # type: ignore[index]
    assert recorded["end_ns"] == region.end_ns  # type: ignore[index]


def test_every_exported_record_falls_inside_the_selection(win: MainWindow, tmp_path: Path) -> None:
    win.plot_panel.set_time_region(2.0, 6.0)
    target = tmp_path / "dar.json"
    win.export_metadata_json(target, selected_range_only=True)

    document = _read(target)
    span = document["range"]
    for key in ("events", "bit_results"):
        for record in document[key]:  # type: ignore[union-attr]
            assert span["start_ns"] <= record["timestamp_ns"] < span["end_ns"]  # type: ignore[index]


def test_ignoring_the_selection_exports_everything(win: MainWindow, tmp_path: Path) -> None:
    win.plot_panel.set_time_region(1.0, 2.0)

    narrow = win.export_metadata_json(tmp_path / "dar.json", selected_range_only=True)
    whole = win.export_metadata_json(tmp_path / "tumu.json", selected_range_only=False)

    assert whole.event_count > narrow.event_count


def test_without_a_region_the_whole_recording_is_used(win: MainWindow, tmp_path: Path) -> None:
    """Seçim yoksa "seçili aralık" isteği kaydın tamamına düşer."""
    assert win.plot_panel.time_region_range() is None
    asked = win.export_metadata_json(tmp_path / "a.json", selected_range_only=True)
    whole = win.export_metadata_json(tmp_path / "b.json", selected_range_only=False)
    assert asked.event_count == whole.event_count

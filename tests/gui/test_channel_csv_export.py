"""MainWindow üzerinden seçili kanal/aralık CSV dışa aktarımı — `F3-064`.

Kabul: satır sayısı, zaman, birim ve kaynak metadata doğru çıkar.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def _split(path: Path) -> tuple[dict[str, str], list[list[str]]]:
    meta: dict[str, str] = {}
    data_text: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("# "):
            key, _, value = raw[2:].partition("=")
            meta[key] = value
        else:
            data_text.append(raw)
    return meta, list(csv.reader(data_text))


@pytest.fixture()
def window(qtbot: QtBot) -> tuple[MainWindow, MockRecordingRepository]:
    win = MainWindow()
    qtbot.addWidget(win)
    repo = MockRecordingRepository(duration_s=4.0)
    win.set_repository(repo)
    win.open_channel("ch0")
    return win, repo


def test_full_range_export_row_count_matches_the_query(
    window: tuple[MainWindow, MockRecordingRepository], tmp_path: Path
) -> None:
    win, repo = window
    span = repo.metadata().time_range
    expected = len(repo.query("ch0", span))

    result = win.export_channel_csv(tmp_path / "ch0.csv")

    assert result.row_count == expected
    meta, rows = _split(result.path)
    assert len(rows) == 1 + expected  # başlık + veri
    assert meta["channel_id"] == "ch0"
    assert meta["unit"] == "bar"
    assert meta["source"] == "sensors"
    assert meta["recording_id"] == repo.metadata().recording_id
    assert meta["row_count"] == str(expected)


def test_selected_range_limits_the_rows(
    window: tuple[MainWindow, MockRecordingRepository], tmp_path: Path
) -> None:
    win, repo = window
    win.plot_panel.set_time_region(0.5, 1.5)
    region = win.plot_panel.time_region_range()
    assert region is not None
    expected = len(repo.query("ch0", region))

    result = win.export_channel_csv(tmp_path / "roi.csv", selected_range_only=True)

    assert result.row_count == expected
    assert expected < len(repo.query("ch0", repo.metadata().time_range))
    meta, _rows = _split(result.path)
    assert meta["range_ns"] == f"[{region.start_ns},{region.end_ns})"


def test_time_column_is_within_the_recording_span(
    window: tuple[MainWindow, MockRecordingRepository], tmp_path: Path
) -> None:
    win, repo = window
    span = repo.metadata().time_range

    result = win.export_channel_csv(tmp_path / "ch0.csv")
    _meta, rows = _split(result.path)

    stamps = [int(r[0]) for r in rows[1:]]
    assert stamps == sorted(stamps)
    assert span.start_ns <= stamps[0]
    assert stamps[-1] < span.end_ns


def test_metadata_toggle_off_writes_a_bare_csv(
    window: tuple[MainWindow, MockRecordingRepository], tmp_path: Path
) -> None:
    win, _repo = window
    result = win.export_channel_csv(tmp_path / "bare.csv", include_metadata=False)

    text = result.path.read_text(encoding="utf-8")
    assert not text.startswith("#")
    assert text.splitlines()[0] == "timestamp_ns,timestamp_utc,value"


def test_export_without_a_recording_raises(qtbot: QtBot, tmp_path: Path) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    with pytest.raises(ValueError, match="Acik kayit yok"):
        win.export_channel_csv(tmp_path / "x.csv")


def test_export_with_an_unknown_channel_raises(
    window: tuple[MainWindow, MockRecordingRepository], tmp_path: Path
) -> None:
    win, _repo = window
    with pytest.raises(ValueError, match="Bilinmeyen kanal"):
        win.export_channel_csv(tmp_path / "x.csv", channel_id="does-not-exist")

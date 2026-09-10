"""Data Export kartından uçtan uca dışa aktarma akışı — `F3-065`.

Kabul: var olan dosya onaysız değişmez; raw/processed seçimi açıktır.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.export_controller import DataVariant
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=3.0))
    win.open_channel("ch0")
    return win


def _use_target(win: MainWindow, target: Path, *, overwrite: bool) -> list[Path]:
    """Diyalog seam'lerini sabitler; onay istenen yolları döndürür."""
    asked: list[Path] = []
    win.export_save_dialog = lambda _caption, _filter: str(target)
    win.export_confirm_overwrite = lambda p: asked.append(p) or overwrite
    return asked


def _trigger(win: MainWindow) -> None:
    win.right_dock.data_export.export_requested.emit()


def test_new_file_is_written_without_asking(window: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "ch0.csv"
    asked = _use_target(window, target, overwrite=False)
    window.right_dock.data_export.export_format.setCurrentText("CSV")

    _trigger(window)

    assert target.exists()
    assert asked == []  # yeni dosya; onay sorulmadı


def test_existing_file_is_untouched_when_overwrite_is_declined(
    window: MainWindow, tmp_path: Path
) -> None:
    target = tmp_path / "ch0.csv"
    target.write_text("ESKI ICERIK", encoding="utf-8")
    asked = _use_target(window, target, overwrite=False)
    window.right_dock.data_export.export_format.setCurrentText("CSV")

    _trigger(window)

    assert asked == [target]  # onay soruldu
    assert target.read_text(encoding="utf-8") == "ESKI ICERIK"  # dokunulmadı


def test_existing_file_is_replaced_when_overwrite_is_confirmed(
    window: MainWindow, tmp_path: Path
) -> None:
    target = tmp_path / "ch0.csv"
    target.write_text("ESKI ICERIK", encoding="utf-8")
    _use_target(window, target, overwrite=True)
    window.right_dock.data_export.export_format.setCurrentText("CSV")

    _trigger(window)

    text = target.read_text(encoding="utf-8")
    assert "ESKI ICERIK" not in text
    assert "timestamp_ns,timestamp_utc,value" in text


def test_missing_extension_is_added_from_the_format(window: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "grafik"  # uzantısız
    _use_target(window, target, overwrite=False)
    window.right_dock.data_export.export_format.setCurrentText("PNG")

    _trigger(window)

    assert (tmp_path / "grafik.png").exists()
    assert not (tmp_path / "grafik").exists()


def test_raw_variant_is_carried_into_the_csv_metadata(window: MainWindow, tmp_path: Path) -> None:
    card = window.right_dock.data_export
    card.export_format.setCurrentText("CSV")
    card.data_variant.setCurrentIndex(1)  # Raw
    assert card.selected_variant() is DataVariant.RAW

    target = tmp_path / "raw.csv"
    _use_target(window, target, overwrite=False)
    _trigger(window)

    meta = [
        line[2:]
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.startswith("# ")
    ]
    assert "variant=raw" in meta


def test_processed_variant_is_the_default_in_metadata(window: MainWindow, tmp_path: Path) -> None:
    card = window.right_dock.data_export
    card.export_format.setCurrentText("CSV")

    target = tmp_path / "proc.csv"
    _use_target(window, target, overwrite=False)
    _trigger(window)

    text = target.read_text(encoding="utf-8")
    assert "# variant=processed" in text


def test_unsupported_format_is_reported_not_written(window: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    _use_target(window, target, overwrite=False)
    window.right_dock.data_export.export_format.setCurrentText("JSON")

    _trigger(window)

    assert not target.exists()


def test_cancelling_the_save_dialog_writes_nothing(window: MainWindow, tmp_path: Path) -> None:
    window.export_save_dialog = lambda _c, _f: ""  # kullanıcı iptal etti
    window.right_dock.data_export.export_format.setCurrentText("CSV")

    _trigger(window)

    assert list(tmp_path.iterdir()) == []

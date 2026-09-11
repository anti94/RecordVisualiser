"""Statik grafiğin PDF dışa aktarımı — `F4-086`.

Kabul: vektörel grafik başlık, kaynak ve işlem bilgisiyle açılır.

Çizilen metin PDF içinde sıkıştırılır ve baytlardan okunamaz; bu yüzden
aynı satırlar **XMP metadata**'sına da gömülür ve orada sıkıştırılmadan
durur. Böylece "başlık, kaynak ve işlem bilgisi belgede var" iddiası
dosyanın baytlarından doğrulanabilir — sayfada görünen ile metadata'da
duran aynı `PlotDocumentInfo.lines()` listesinden üretilir.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.application.export_controller import ExportKind, kind_for_format
from sonar_analyzer.export.pdf_export import (
    CREATOR,
    PdfExportError,
    PlotDocumentInfo,
    export_widget_pdf,
)
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.data_export import EXPORT_FORMATS
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

MOMENT = datetime(2026, 9, 11, 8, 30, tzinfo=timezone.utc)


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=50.0))
    window.open_channel("ch0")
    return window


# --------------------------------------------------------------------------- #
# baslik blogu (saf veri)
# --------------------------------------------------------------------------- #


def test_the_header_carries_title_source_and_processing() -> None:
    info = PlotDocumentInfo(
        title="Hydrophone 1 [Pa]",
        source="D:/kayit.bin (rec-1)",
        processing="2 adım: scale, abs",
        time_range="[0, 1000) ns",
        generated_at=MOMENT,
    )
    lines = info.lines()
    assert lines[0] == "Hydrophone 1 [Pa]"
    assert lines[1] == "Kaynak: D:/kayit.bin (rec-1)"
    assert lines[2] == "İşlem: 2 adım: scale, abs"
    assert lines[3] == "Aralık: [0, 1000) ns"
    assert lines[4] == "Üretildi: 2026-09-11T08:30:00+00:00"


def test_an_empty_processing_chain_is_stated_not_omitted() -> None:
    """Boş bırakmak, okuyucunun işlem olup olmadığını bilmemesine yol açardı."""
    info = PlotDocumentInfo(title="t", source="s", generated_at=MOMENT)
    assert "İşlem: İşlem uygulanmadı" in info.lines()


def test_the_range_line_is_dropped_when_unknown() -> None:
    lines = PlotDocumentInfo(title="t", source="s", generated_at=MOMENT).lines()
    assert not any(line.startswith("Aralık:") for line in lines)


@pytest.mark.parametrize(("title", "source"), [("  ", "s"), ("t", "  ")])
def test_a_blank_title_or_source_is_refused(title: str, source: str) -> None:
    with pytest.raises(PdfExportError):
        PlotDocumentInfo(title=title, source=source)


def test_the_metadata_repeats_every_header_line() -> None:
    """Sayfada yazan ile metadata'da duran ayrışamaz."""
    info = PlotDocumentInfo(
        title="Başlık", source="Kaynak", processing="scale", generated_at=MOMENT
    )
    xmp = info.xmp_metadata().decode("utf-8")
    for line in info.lines():
        assert line in xmp


def test_the_metadata_escapes_markup() -> None:
    info = PlotDocumentInfo(title="a<b>&c", source="s", generated_at=MOMENT)
    xmp = info.xmp_metadata().decode("utf-8")
    assert "a&lt;b&gt;&amp;c" in xmp
    assert "<b>" not in xmp


# --------------------------------------------------------------------------- #
# dosya gercekten PDF ve bilgiyi tasiyor
# --------------------------------------------------------------------------- #


def test_the_exported_file_is_a_pdf(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "grafik.pdf"
    win.export_plot_pdf(target)
    data = target.read_bytes()
    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")
    assert len(data) > 1_000


def test_the_document_carries_the_header_lines(win: MainWindow, tmp_path: Path) -> None:
    """Kabul kriterinin kendisi, dosyanın baytlarından."""
    target = tmp_path / "grafik.pdf"
    result = win.export_plot_pdf(target)
    text = target.read_bytes().decode("utf-8", errors="replace")
    for line in result.header_lines:
        assert line in text


def test_the_document_names_the_source_recording(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "grafik.pdf"
    win.export_plot_pdf(target)
    repository = win.repository
    assert repository is not None
    text = target.read_bytes().decode("utf-8", errors="replace")
    assert repository.metadata().recording_id in text


def test_the_document_names_the_creator(win: MainWindow, tmp_path: Path) -> None:
    """PDF `Info` sözlüğü metinleri UTF-16BE yazar; XMP ise UTF-8'dir."""
    target = tmp_path / "grafik.pdf"
    win.export_plot_pdf(target)
    data = target.read_bytes()
    assert CREATOR.encode("utf-16-be") in data or CREATOR.encode("utf-8") in data


def test_the_processing_chain_appears_in_the_document(win: MainWindow, tmp_path: Path) -> None:
    editor = win.right_dock.analysis_tools.step_editor
    editor.set_chain(
        ProcessingChain(
            [
                ProcessingStep.default(StepKind.SCALE, "ch0"),
                ProcessingStep.default(StepKind.ABS, "ch0"),
            ]
        )
    )
    target = tmp_path / "grafik.pdf"
    result = win.export_plot_pdf(target)

    assert "İşlem: 2 adım: scale, abs" in result.header_lines
    text = target.read_bytes().decode("utf-8", errors="replace")
    assert "2 adım: scale, abs" in text


def test_without_a_chain_the_document_says_so(win: MainWindow, tmp_path: Path) -> None:
    result = win.export_plot_pdf(tmp_path / "grafik.pdf")
    assert "İşlem: İşlem uygulanmadı" in result.header_lines


def test_the_title_follows_the_plotted_channel(win: MainWindow) -> None:
    info = win.plot_document_info()
    channel = win.plot_panel.channel
    assert channel is not None
    assert info.title.startswith(channel.display_label)


def test_a_second_channel_is_counted_in_the_title(win: MainWindow) -> None:
    win.left_dock.channels_add_requested.emit(["ch1"])
    assert "+1 kanal" in win.plot_document_info().title


def test_the_selected_region_narrows_the_recorded_range(win: MainWindow) -> None:
    whole = win.plot_document_info().time_range
    win.plot_panel.set_time_region(1.0, 3.0)
    narrowed = win.plot_document_info().time_range
    assert narrowed != whole


# --------------------------------------------------------------------------- #
# reddedilen durumlar ve bicim kaydi
# --------------------------------------------------------------------------- #


def test_an_empty_plot_is_refused(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    with pytest.raises(ValueError, match="Disa aktarilacak grafik yok"):
        window.export_plot_pdf(tmp_path / "bos.pdf")


def test_a_zero_sized_widget_is_refused(qtbot: QtBot, tmp_path: Path) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(0, 0)
    with pytest.raises(PdfExportError, match="boyutu sıfır"):
        export_widget_pdf(widget, tmp_path / "x.pdf", PlotDocumentInfo(title="t", source="s"))


def test_pdf_is_an_offered_format() -> None:
    assert "PDF" in EXPORT_FORMATS
    assert kind_for_format("PDF") is ExportKind.PDF


def test_a_missing_directory_is_created(win: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "raporlar" / "grafik.pdf"
    win.export_plot_pdf(target)
    assert target.exists()


def test_exporting_is_logged(win: MainWindow, tmp_path: Path) -> None:
    win.export_plot_pdf(tmp_path / "grafik.pdf")
    assert any("PDF olarak yazildi" in line for line in win.bottom_dock.log_lines())

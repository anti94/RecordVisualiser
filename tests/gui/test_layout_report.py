"""Ana ekran ölçüm raporu — `F6-031`.

`tools/mockup_compare.py` bu modülün *çıktısını* değerlendirir; buradaki
testler ölçümün **kendisini** denetler: gerçek bir pencerede dokuz bölge
bulunuyor mu, alanlar pencerenin yerleşiminden mi okunuyor, eksik bir
bölge gerçekten eksik olarak raporlanıyor mu.

Ölçüm aracının sessizce "her şey yerinde" demesi, yerleşim bozulduğunda
kimsenin haberi olmaması demektir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.layout_report import NINE_REGIONS, build_layout_report
from sonar_analyzer.ui.main_window import DEFAULT_WINDOW_SIZE, MainWindow

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records_v2.bin"


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.resize(*DEFAULT_WINDOW_SIZE)
    win.show()
    qtbot.waitExposed(win)
    win.apply_default_layout()
    return win


def test_a_shown_window_reports_all_nine_regions(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    assert len(report.data["regions"]) == len(NINE_REGIONS)
    for row in report.data["regions"]:
        assert row["found"], row["object_name"]
        assert row["visible"], row["object_name"]


def test_every_region_is_in_its_documented_area(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    for row in report.data["regions"]:
        assert row["actual_area"] == row["expected_area"], row["object_name"]


def test_the_report_is_ok_on_a_healthy_window(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    assert report.ok, report.failures
    assert "sonuc: TAMAM" in report.lines[-1]


def test_a_hidden_region_is_reported_as_a_failure(window: MainWindow) -> None:
    """Gizlenen bir bölge sessizce geçilmemeli."""
    from PySide6.QtWidgets import QWidget

    explorer = window.findChild(QWidget, "dock_data_explorer")
    assert explorer is not None
    explorer.hide()

    report = build_layout_report(window, FIXTURE)
    assert not report.ok
    assert any("gorunur degil" in failure for failure in report.failures)


def test_the_tab_bar_is_measured_from_the_window(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    tabs = report.data["tabs"]
    assert tabs["found"] is True
    assert len(tabs["titles"]) == 8
    assert tabs["current"] == "Time Series"


def test_the_theme_is_measured_not_assumed(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    theme = report.data["theme"]
    assert theme["stylesheet_chars"] > 0
    assert theme["background_lightness"] <= 127


def test_the_columns_are_measured(window: MainWindow) -> None:
    report = build_layout_report(window, FIXTURE)
    columns = report.data["columns"]
    assert set(columns) == {"dock_data_explorer", "dock_right_column"}
    for info in columns.values():
        assert info["width"] > 0


def test_the_analysis_check_runs_real_data_through_the_spectrum_panel(
    window: MainWindow,
) -> None:
    report = build_layout_report(window, FIXTURE)
    analysis = report.data["analysis"]
    assert analysis["samples"] == 8
    assert analysis["has_spectrum"] is True
    assert analysis["spectrum_points"] > 0


def test_without_a_recording_the_analysis_check_is_reported_as_missing(
    window: MainWindow,
) -> None:
    """Kayıt verilmezse analiz "geçti" sayılmamalı; ölçülmemiş sayılmalı."""
    report = build_layout_report(window, None)
    assert not report.ok
    assert any("kayit verilmedi" in failure for failure in report.failures)
    assert report.data["analysis"]["attempted"] is False

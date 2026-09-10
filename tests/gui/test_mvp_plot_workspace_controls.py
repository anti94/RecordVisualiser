"""MVP: kritik plot ve workspace GUI kontrolleri — `F3-076`.

Kabul: zoom, ROI ve workspace round-trip davranışları doğrulanır.
Bunlar tek tek başka dosyalarda da sınanır; buradaki senaryolar MVP
kapısı için birlikte çalıştırıldıklarını doğrular.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.model import WorkspaceModel
from sonar_analyzer.workspace.store import load_workspace


def _without_dock_state(model: WorkspaceModel) -> WorkspaceModel:
    """dock_state opak Qt blob'u; farklı pencerede byte-aynı olmaz."""
    return replace(model, dock_state=None)


pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    window.open_channel("ch0")
    return window


# -- zoom --------------------------------------------------------


def test_x_zoom_mode_scales_only_the_x_axis(win: MainWindow) -> None:
    win.set_zoom_mode_x()
    x0, x1, y0, y1 = win.plot_panel.visible_range()

    win.plot_panel.zoom(0.5)  # yakınlaş

    nx0, nx1, ny0, ny1 = win.plot_panel.visible_range()
    assert (nx1 - nx0) < (x1 - x0) - 1e-6  # X daraldı
    assert abs((ny1 - ny0) - (y1 - y0)) < 1e-6  # Y değişmedi


def test_y_zoom_mode_scales_only_the_y_axis(win: MainWindow) -> None:
    win.set_zoom_mode_y()
    x0, x1, y0, y1 = win.plot_panel.visible_range()

    win.plot_panel.zoom(0.5)

    nx0, nx1, ny0, ny1 = win.plot_panel.visible_range()
    assert abs((nx1 - nx0) - (x1 - x0)) < 1e-6
    assert (ny1 - ny0) < (y1 - y0) - 1e-6


def test_xy_zoom_mode_scales_both_axes(win: MainWindow) -> None:
    win.set_zoom_mode_xy()
    x0, x1, y0, y1 = win.plot_panel.visible_range()

    win.plot_panel.zoom(2.0)  # uzaklaş

    nx0, nx1, ny0, ny1 = win.plot_panel.visible_range()
    assert (nx1 - nx0) > (x1 - x0) + 1e-6
    assert (ny1 - ny0) > (y1 - y0) + 1e-6


def test_home_resets_zoom_to_the_captured_view(win: MainWindow) -> None:
    home = win.plot_panel.visible_x_range()
    win.plot_panel.set_x_range(1.0, 2.0)
    win.reset_plot_view()
    x0, x1 = win.plot_panel.visible_x_range()
    assert abs(x0 - home[0]) < 1e-6 and abs(x1 - home[1]) < 1e-6


# -- ROI (zaman bölgesi) --------------------------------------


def test_roi_maps_to_an_absolute_time_range(win: MainWindow) -> None:
    win.plot_panel.set_time_region(2.0, 5.0)
    tr = win.plot_panel.time_region_range()
    anchor = win.plot_panel.time_anchor_ns
    assert tr is not None and anchor is not None
    start_s = (tr.start_ns - anchor) / 1_000_000_000
    end_s = (tr.end_ns - anchor) / 1_000_000_000
    assert abs(start_s - 2.0) < 1e-6 and abs(end_s - 5.0) < 1e-6


def test_roi_toggle_shortcut_opens_and_clears_the_region(win: MainWindow) -> None:
    assert win.plot_panel.time_region_x() is None
    win.toggle_region_selection()
    assert win.plot_panel.time_region_x() is not None
    win.toggle_region_selection()
    assert win.plot_panel.time_region_x() is None


def test_roi_rescopes_the_statistics_card(win: MainWindow) -> None:
    plain = win.dashboard.statistics.title()
    win.plot_panel.set_time_region(1.0, 3.0)
    assert win.dashboard.statistics.title() != plain
    assert "1" in win.dashboard.statistics.title()


def test_zoom_to_region_narrows_the_view_to_the_roi(win: MainWindow) -> None:
    win.plot_panel.set_time_region(3.0, 4.0)
    win.plot_panel.zoom_to_time_region()
    x0, x1 = win.plot_panel.visible_x_range()
    assert abs(x0 - 3.0) < 0.05 and abs(x1 - 4.0) < 0.05


# -- workspace round-trip -----------------------------------


def test_workspace_round_trip_preserves_plot_and_view_state(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    win.left_dock.channels_add_requested.emit(["ch1"])
    win.plot_panel.set_zoom_mode("x")
    win.plot_panel.set_x_range(1.5, 6.5)
    win.plot_tool_bar.markers_checkbox.setChecked(False)
    win.plot_tool_bar.sync_checkbox.setChecked(False)
    win.bottom_dock.event_text_filter.setText("thermal")

    saved = win.save_workspace(tmp_path / "mvp.json")
    reference = win.capture_workspace()

    # Diskteki belge model ile aynı.
    assert load_workspace(saved) == reference

    # Yeni oturuma geri yükleyince aynı görünüm kurulur.
    fresh = MainWindow()
    qtbot.addWidget(fresh)
    fresh.set_repository(MockRecordingRepository(duration_s=10.0))
    fresh.restore_workspace(saved)

    assert fresh.plot_panel.plotted_channel_ids() == ["ch0", "ch1"]
    assert fresh.plot_panel.zoom_mode == "x"
    fx0, fx1 = fresh.plot_panel.visible_x_range()
    assert abs(fx0 - 1.5) < 1e-6 and abs(fx1 - 6.5) < 1e-6
    assert fresh.plot_tool_bar.markers_checkbox.isChecked() is False
    assert fresh.plot_tool_bar.sync_checkbox.isChecked() is False
    assert fresh.bottom_dock.event_text_filter.text() == "thermal"
    assert _without_dock_state(fresh.capture_workspace()) == _without_dock_state(reference)

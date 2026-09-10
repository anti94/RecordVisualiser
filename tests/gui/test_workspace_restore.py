"""Workspace dosyasını geri yükleme — `F3-069`.

Kabul: yeniden açılışta aynı düzen ve kanal görünümü oluşur.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.time_display import TimeDisplayMode
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.model import WorkspaceError

pytestmark = pytest.mark.gui


def _fresh_window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=6.0))
    return win


def test_saved_session_reopens_with_the_same_channels_and_axes(
    qtbot: QtBot, tmp_path: Path
) -> None:
    author = _fresh_window(qtbot)
    author.open_channel("ch0")
    author.left_dock.channels_add_requested.emit(["ch1"])
    author.plot_panel.set_zoom_mode("x")
    author.plot_panel.set_x_range(1.0, 4.0)
    author.plot_tool_bar.markers_checkbox.setChecked(False)
    author.plot_tool_bar.sync_checkbox.setChecked(False)
    author.status.set_cursor_time_mode(TimeDisplayMode.UTC)
    author.bottom_dock.event_text_filter.setText("thermal")

    saved = author.save_workspace(tmp_path / "s.json")

    # Yeni oturum: aynı kayıt açık, henüz hiçbir kanal çizili değil.
    reopened = _fresh_window(qtbot)
    assert reopened.plot_panel.plotted_channel_ids() == []

    reopened.restore_workspace(saved)

    assert reopened.plot_panel.plotted_channel_ids() == ["ch0", "ch1"]
    assert reopened.plot_panel.zoom_mode == "x"
    x0, x1 = reopened.plot_panel.visible_x_range()
    assert abs(x0 - 1.0) < 1e-6 and abs(x1 - 4.0) < 1e-6
    assert reopened.plot_tool_bar.markers_checkbox.isChecked() is False
    assert reopened.plot_tool_bar.sync_checkbox.isChecked() is False
    assert reopened.status.cursor_time_mode is TimeDisplayMode.UTC
    assert reopened.bottom_dock.event_text_filter.text() == "thermal"


def test_restore_round_trips_the_captured_model(qtbot: QtBot, tmp_path: Path) -> None:
    author = _fresh_window(qtbot)
    author.open_channel("ch2")
    author.plot_tool_bar.tx_checkbox.setChecked(False)
    saved = author.save_workspace(tmp_path / "s.json")

    reopened = _fresh_window(qtbot)
    model = reopened.restore_workspace(saved)

    # Geri yükleyen pencere yeniden dökümlenince aynı görünümü verir.
    recaptured = reopened.capture_workspace()
    assert recaptured.panels[0].channel_ids == model.panels[0].channel_ids
    assert recaptured.view.tx_visible is False
    assert recaptured.active_view_tab == model.active_view_tab


def test_restore_records_the_open_view_tab(qtbot: QtBot, tmp_path: Path) -> None:
    author = _fresh_window(qtbot)
    author.open_channel("ch0")
    titles = author.view_tabs.tab_titles()
    author.view_tabs.setCurrentIndex(titles.index("Transmission"))
    saved = author.save_workspace(tmp_path / "s.json")

    reopened = _fresh_window(qtbot)
    reopened.restore_workspace(saved)

    current = reopened.view_tabs.tabText(reopened.view_tabs.currentIndex())
    assert current == "Transmission"


def test_restore_rejects_a_corrupt_workspace_file(qtbot: QtBot, tmp_path: Path) -> None:
    win = _fresh_window(qtbot)
    bad = tmp_path / "bad.json"
    bad.write_text("{ broken", encoding="utf-8")

    with pytest.raises(WorkspaceError):
        win.restore_workspace(bad)


def test_apply_workspace_without_a_recording_is_safe(qtbot: QtBot, tmp_path: Path) -> None:
    author = _fresh_window(qtbot)
    author.open_channel("ch0")
    saved = author.save_workspace(tmp_path / "s.json")

    bare = MainWindow()
    qtbot.addWidget(bare)
    # Kayıt yok: kanal çizilemez ama görünüm/filtre durumu yine uygulanır.
    bare.restore_workspace(saved)
    assert bare.plot_panel.plotted_channel_ids() == []

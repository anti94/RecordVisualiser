"""MainWindow oturumunu workspace'e dökümleme — `F3-068`.

Kabul: dosya açık tabları, eksenleri ve senkronizasyon gruplarını içerir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.model import WORKSPACE_SCHEMA_VERSION
from sonar_analyzer.workspace.store import load_workspace

pytestmark = pytest.mark.gui


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=5.0))
    win.open_channel("ch0")
    return win


def test_capture_records_the_plotted_channel_and_axes(window: MainWindow) -> None:
    model = window.capture_workspace()

    assert model.schema_version == WORKSPACE_SCHEMA_VERSION
    assert len(model.panels) == 1
    assert model.panels[0].channel_ids == ["ch0"]
    # eksen aralığı yakalandı (bir seri var)
    assert model.panels[0].x_range is not None
    assert model.panels[0].y_range is not None
    assert model.panels[0].zoom_mode in ("x", "y", "xy")


def test_capture_records_sync_group_from_the_toolbar(window: MainWindow) -> None:
    window.plot_tool_bar.sync_checkbox.setChecked(True)
    assert window.capture_workspace().sync_groups == [[0]]

    window.plot_tool_bar.sync_checkbox.setChecked(False)
    captured = window.capture_workspace()
    assert captured.sync_groups == []
    assert captured.view.sync_x is False


def test_capture_records_the_open_view_tab(window: MainWindow) -> None:
    index = window.view_tabs.tab_titles().index("Transmission")
    window.view_tabs.setCurrentIndex(index)

    assert window.capture_workspace().active_view_tab == "Transmission"


def test_capture_records_marker_and_tx_visibility(window: MainWindow) -> None:
    window.plot_tool_bar.markers_checkbox.setChecked(False)
    window.plot_tool_bar.tx_checkbox.setChecked(True)

    view = window.capture_workspace().view
    assert view.markers_visible is False
    assert view.tx_visible is True


def test_capture_records_the_event_filter(window: MainWindow) -> None:
    window.bottom_dock.event_text_filter.setText("thermal")
    window.bottom_dock.event_group_check.setChecked(True)

    event_filter = window.capture_workspace().event_filter
    assert event_filter.text == "thermal"
    assert event_filter.group_near is True


def test_capture_includes_a_dock_state_blob(window: MainWindow) -> None:
    model = window.capture_workspace()
    assert isinstance(model.dock_state, str) and model.dock_state


def test_save_workspace_writes_a_loadable_file(window: MainWindow, tmp_path: Path) -> None:
    dest = window.save_workspace(tmp_path / "session.json")

    assert dest.exists()
    doc = json.loads(dest.read_text(encoding="utf-8"))
    assert doc["schema_version"] == WORKSPACE_SCHEMA_VERSION
    assert doc["panels"][0]["channel_ids"] == ["ch0"]

    reloaded = load_workspace(dest)
    assert reloaded == window.capture_workspace()


def test_save_workspace_records_open_source_files(qtbot: QtBot, tmp_path: Path) -> None:
    import shutil

    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"
    target = tmp_path / "kayit.bin"
    shutil.copyfile(fixture, target)

    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()

    model = win.capture_workspace()
    assert [Path(p).name for p in model.source_paths] == ["kayit.bin"]

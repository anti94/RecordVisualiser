"""Pan/zoom sonrası görünür örnekler ve mevcut analiz seçimi."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def test_pan_zoom_refresh_preserves_view_style_and_analysis(qtbot: QtBot) -> None:
    repo = MockRecordingRepository(duration_s=20.0, sample_rate_hz=1000.0)
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(repo)
    win.open_channel("ch0")
    win.plot_panel.set_series_style("ch0", color="#ff8800")
    selection = win.dashboard.selection()
    win.plot_panel.set_x_range(3.0, 3.05)
    qtbot.waitUntil(lambda: win.plot_panel.sample_count == 50, timeout=5000)
    x, values = win.plot_panel.curve_data()
    assert np.all(x >= 3) and np.all(x < 3.05)
    assert np.allclose(win.plot_panel.visible_x_range(), (3, 3.05))
    assert win.plot_panel.series_color("ch0") == "#ff8800"
    assert win.dashboard.selection() == selection
    expected = repo.query("ch0", repo.metadata().time_range).values[3000:3050]
    assert np.array_equal(values, expected)
    win.plot_panel.set_x_range(10, 15)
    win.refresh_plot_viewport()
    x, _values = win.plot_panel.curve_data()
    assert np.all(x >= 10) and np.all(x < 15)
    assert len(x) <= win.plot_point_budget()

"""Çizim bütçesi analiz doğruluğunu değiştirmez — F4-055."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import DEFAULT_CHANNELS, MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def test_narrowing_plot_preserves_fft_roi_and_filter_input(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = replace(DEFAULT_CHANNELS[0], frequency_hz=10.0, offset=0.0)
    repo = MockRecordingRepository(duration_s=10.0, sample_rate_hz=1000.0, specs=[spec])
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(repo)
    win.dashboard.fft.set_window(WindowKind.RECTANGULAR)
    raw = repo.query("ch0", repo.metadata().time_range)
    reference = one_sided_fft(raw.values, 1000.0)
    counts: list[int] = []
    for width in (500, 100):
        monkeypatch.setattr(win.plot_panel, "plot_pixel_width", lambda w=width: w)
        win.open_channel("ch0")
        counts.append(win.plot_panel.sample_count)
        assert counts[-1] <= 2 * width
        result = win.dashboard.fft.result()
        assert result is not None
        assert result.sample_count == len(raw)
        assert result.peak_frequency_hz == reference.peak_frequency_hz
        assert result.peak_frequency_hz == 10.0
    assert counts[1] < counts[0]

    win.plot_panel.set_time_region(2.0, 4.0)
    qtbot.waitUntil(
        lambda: (
            (selected := win.dashboard.selection()) is not None
            and selected.region_seconds == (2, 4)
        )
    )
    selection = win.dashboard.selection()
    assert selection is not None and selection.sample_count == 2000

    # Mean çıkarma tam girdi üzerinde yapılmalı; çizim örnekleri üzerinde değil.
    editor = win.right_dock.analysis_tools.step_editor
    win.right_dock.analysis_tools.tabs.setCurrentWidget(editor)
    editor.kind_selector.setCurrentIndex(editor.kind_selector.findData(StepKind.DETREND))
    editor.add_button.click()
    win.right_dock.analysis_tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)
    x, plotted = win.plot_panel.curve_data()
    indices = np.rint(x * 1000).astype(np.int64)
    assert np.allclose(
        win.plot_panel.processed_overlay_values(), raw.values[indices] - raw.values.mean()
    )
    assert np.array_equal(plotted, raw.values[indices])

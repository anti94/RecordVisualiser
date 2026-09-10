"""Merkez dashboard grafik hücreleri — `F1-039`.

Kabul: üst zaman serisi, orta spektrogram, alt FFT ve istatistik hücreleri
vardır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.dashboard import DashboardPanel
from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.statistics_panel import (
    EMPTY_VALUE,
    STAT_FIELDS,
    StatisticsPanel,
    compute_statistics,
)

pytestmark = pytest.mark.gui


@pytest.fixture()
def dashboard(qtbot: QtBot) -> DashboardPanel:
    widget = DashboardPanel()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


# -- dort hucre --------------------------------------------------------


def test_four_cells_exist(dashboard: DashboardPanel) -> None:
    assert isinstance(dashboard.time_series, PlotPanel)
    assert dashboard.spectrogram.title() == "Spectrogram"
    assert dashboard.fft.title() == "FFT"
    assert isinstance(dashboard.statistics, StatisticsPanel)


def test_row_order_is_time_series_spectrogram_bottom(dashboard: DashboardPanel) -> None:
    """Kabul kriteri: üst zaman serisi, orta spektrogram, alt FFT/istatistik."""
    top_y = dashboard.time_series.mapTo(dashboard, dashboard.time_series.rect().topLeft()).y()
    mid_y = dashboard.spectrogram.mapTo(dashboard, dashboard.spectrogram.rect().topLeft()).y()
    bottom_y = dashboard.fft.mapTo(dashboard, dashboard.fft.rect().topLeft()).y()

    assert top_y < mid_y < bottom_y


def test_fft_and_statistics_are_side_by_side(dashboard: DashboardPanel) -> None:
    fft_x = dashboard.fft.mapTo(dashboard, dashboard.fft.rect().topLeft()).x()
    stats_x = dashboard.statistics.mapTo(dashboard, dashboard.statistics.rect().topLeft()).x()
    assert fft_x < stats_x


def test_spectrogram_is_unavailable_with_reason(dashboard: DashboardPanel) -> None:
    """Spektrogram motoru henüz yok (`F4-046`+); hücre bunu açıkça söylüyor."""
    from PySide6.QtWidgets import QLabel

    spec_label = dashboard.spectrogram.findChild(QLabel, "cell_spectrogram_label")
    assert spec_label is not None and NOT_YET_AVAILABLE in spec_label.text()


def test_fft_cell_is_a_real_spectrum_panel(dashboard: DashboardPanel) -> None:
    """`F4-042`: FFT hücresi artık gerçek spektrumu çizer, yer tutucu değil."""
    from sonar_analyzer.ui.plots.spectrum_panel import SpectrumPanel

    assert isinstance(dashboard.fft, SpectrumPanel)
    assert dashboard.spectrum() is dashboard.fft
    # Veri gelmeden sonuç yok — sahte spektrum gösterilmiyor.
    assert not dashboard.fft.has_spectrum


def test_no_fake_spectral_result_is_shown(dashboard: DashboardPanel) -> None:
    from PySide6.QtWidgets import QLabel

    for label in dashboard.spectrogram.findChildren(QLabel):
        assert "dB" not in label.text()
        assert "Hz" not in label.text()
    # FFT paneli veri gelmeden yalnız "örnek yok" der; sayısal sonuç vermez.
    assert not dashboard.fft.has_spectrum


# -- istatistik hesaplari ------------------------------------------------


def test_compute_statistics_on_known_values() -> None:
    import numpy as np

    values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    stats = compute_statistics(values)
    assert stats["Mean"] == 2.5
    assert stats["Min"] == 1.0
    assert stats["Max"] == 4.0
    assert stats["Peak-Peak"] == 3.0
    assert abs(stats["Std"] - 1.1180339887) < 1e-6
    assert abs(stats["RMS"] - 2.7386127875) < 1e-6


def test_compute_statistics_on_empty_array_is_nan() -> None:
    import numpy as np

    stats = compute_statistics(np.empty(0, dtype=np.float64))
    assert all(v != v for v in stats.values())  # NaN != NaN


def test_statistics_panel_starts_empty(dashboard: DashboardPanel) -> None:
    assert dashboard.statistics.title() == "Statistics"
    for field in STAT_FIELDS:
        assert dashboard.statistics.field_value(field) == EMPTY_VALUE


def test_unknown_stat_field_raises(dashboard: DashboardPanel) -> None:
    with pytest.raises(KeyError, match="Tanimsiz istatistik alani"):
        dashboard.statistics.field_value("Yok")


# -- pencereye baglanma ----------------------------------------------------


def test_selecting_a_channel_fills_the_statistics(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    window.left_dock.channel_activated.emit("ch0")

    stats = window.dashboard.statistics
    assert stats.title() == "Statistics (Pressure)"
    assert "bar" in stats.field_value("Mean")
    assert stats.field_value("Mean") != EMPTY_VALUE


def test_new_recording_clears_the_statistics(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    window.left_dock.channel_activated.emit("ch0")
    assert window.dashboard.statistics.title() != "Statistics"

    window.set_repository(MockRecordingRepository(duration_s=5.0))
    assert window.dashboard.statistics.title() == "Statistics"
    assert window.dashboard.statistics.field_value("Mean") == EMPTY_VALUE

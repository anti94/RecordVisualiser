"""Sahte kanal seçiminin grafiğe bağlanması — `F1-032`.

Kabul: seçilen sahte kanal çizilir; veri kaynağı `Simülasyon` olarak görünür.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import (
    SIMULATION_LABEL,
    MockRecordingRepository,
)
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import EMPTY_TITLE

pytestmark = pytest.mark.gui


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win


@pytest.fixture()
def loaded(window: MainWindow) -> MainWindow:
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    return window


# -- baslangic -------------------------------------------------------------


def test_plot_is_in_the_center(window: MainWindow) -> None:
    """Grafik dashboard içinde; kayıt açılınca öne gelir (F1-033, F1-039)."""
    assert window.plot_panel is not None
    assert window.plot_panel is window.dashboard.time_series
    assert window.center_stack.indexOf(window.dashboard) >= 0
    assert window.center_stack.parent() is window.center


def test_plot_is_empty_before_loading(window: MainWindow) -> None:
    assert window.plot_panel.channel is None
    assert EMPTY_TITLE in window.plot_panel.title_text()
    assert not window.center_shows_plot, "kayit yokken yonlendirme gorunmeli"


# -- simulasyon yuklenmesi -------------------------------------------------


def test_load_simulation_action_fills_the_panels(window: MainWindow) -> None:
    window.action("action_load_simulation").trigger()

    assert len(window.left_dock.visible_channel_ids()) == 8
    assert window.playback_dock.duration_s == 60.0
    assert window.bottom_dock.event_row_count() > 0


def test_source_is_shown_as_simulation(loaded: MainWindow) -> None:
    """Kabul kriteri: veri kaynağı Simülasyon olarak görünür."""
    assert loaded.status.field_value("file") == SIMULATION_LABEL
    assert loaded.status.field_value("connection") == SIMULATION_LABEL
    assert loaded.left_dock.summary_value("File") == SIMULATION_LABEL
    assert loaded.left_dock.summary_value("Platform") == SIMULATION_LABEL


# -- secim -> cizim --------------------------------------------------------


def test_selecting_a_channel_draws_it(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch5")

    panel = loaded.plot_panel
    assert panel.channel is not None
    assert panel.channel.id == "ch5"
    assert panel.title_text() == "Hydrophone 1 [Pa]"
    assert panel.sample_count == 80  # 10 s x 8 Hz

    x, y = panel.curve_data()
    assert x.size == 80
    assert y.size == 80
    assert float(x[0]) == 0.0


def test_selecting_another_channel_replaces_the_curve(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch5")
    first_values = loaded.plot_panel.curve_data()[1].copy()

    loaded.left_dock.channel_activated.emit("ch0")

    assert loaded.plot_panel.channel is not None
    assert loaded.plot_panel.channel.id == "ch0"
    second_values = loaded.plot_panel.curve_data()[1]
    assert not (first_values == second_values).all()
    assert loaded.plot_panel.title_text() == "Pressure [bar]"


def test_selection_also_opens_the_inspector(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch6")

    assert loaded.right_dock.inspector_is_open
    assert loaded.right_dock.inspector.field_value("Channel") == "Depth"


def test_selection_is_logged(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch0")

    text = "\n".join(loaded.bottom_dock.log_lines())
    assert "Pressure [bar] cizildi" in text
    assert "80 ornek" in text


def test_unknown_channel_does_not_change_the_plot(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch0")
    before = loaded.plot_panel.curve_data()[1].copy()

    loaded.open_channel("bulunmayan")

    assert loaded.plot_panel.channel is not None
    assert loaded.plot_panel.channel.id == "ch0"
    assert (loaded.plot_panel.curve_data()[1] == before).all()


def test_selection_without_a_repository_is_ignored(window: MainWindow) -> None:
    """Kayıt açılmadan seçim gelirse çizim denenmemeli."""
    window.open_channel("ch0")
    assert window.plot_panel.channel is None


def test_loading_again_clears_the_previous_curve(loaded: MainWindow) -> None:
    loaded.left_dock.channel_activated.emit("ch0")
    assert loaded.plot_panel.channel is not None

    loaded.set_repository(MockRecordingRepository(duration_s=5.0))

    assert loaded.plot_panel.channel is None
    assert loaded.plot_panel.curve_data()[0].size == 0
    assert loaded.playback_dock.duration_s == 5.0

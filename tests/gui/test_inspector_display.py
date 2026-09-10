"""Inspector Display ayarlarının grafiğe bağlanması — `F3-036`.

Kabul: eksen ve min/max değişikliği seçilen grafiğe uygulanır.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.docks.inspector import InspectorPanel
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
_EPS = 1e-6


# -- PlotPanel.set_axis_range --------------------------------


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _channel(channel_id: str, unit: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"Sensors/{channel_id}",
        name=channel_id,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit=unit,
        sample_rate_hz=100.0,
    )


def test_set_axis_range_pins_the_left_y_axis(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "bar"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    panel.set_axis_range("left", -7.0, 7.0)

    _, _, y_min, y_max = panel.visible_range()
    assert abs(y_min - (-7.0)) < _EPS
    assert abs(y_max - 7.0) < _EPS


def test_set_axis_range_pins_the_right_y_axis(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "bar"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))
    panel.add_channel(_channel("ch1", "C"), sine("ch1", 100.0, 1.0, frequency_hz=3.0))
    assert panel.right_axis_visible

    panel.set_axis_range("right", 10.0, 40.0)

    right = panel.right_axis_y_range()
    assert right is not None
    assert abs(right[0] - 10.0) < _EPS
    assert abs(right[1] - 40.0) < _EPS


def test_set_axis_range_rejects_bad_input(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "bar"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    with pytest.raises(ValueError, match="Tanimsiz eksen"):
        panel.set_axis_range("middle", 0.0, 1.0)
    with pytest.raises(ValueError, match="artan sirada"):
        panel.set_axis_range("left", 5.0, 5.0)


def test_set_right_axis_range_without_a_right_axis_is_a_no_op(panel: PlotPanel) -> None:
    panel.add_channel(_channel("ch0", "bar"), sine("ch0", 100.0, 1.0, frequency_hz=2.0))

    panel.set_axis_range("right", 0.0, 1.0)  # crash olmamali

    assert not panel.right_axis_visible


# -- InspectorPanel Display kontrolleri -----------------------


def test_inspector_apply_emits_the_axis_range(qtbot: QtBot) -> None:
    inspector = InspectorPanel()
    qtbot.addWidget(inspector)
    seen: list[tuple[str, float, float]] = []

    def _rec(axis: str, y_min: float, y_max: float) -> None:
        seen.append((axis, y_min, y_max))

    inspector.axis_range_requested.connect(_rec)
    inspector.axis_combo.setCurrentIndex(0)  # Left axis
    inspector.y_min_spin.setValue(-5.0)
    inspector.y_max_spin.setValue(5.0)
    inspector.apply_button.click()

    assert seen == [("left", -5.0, 5.0)]


def test_inspector_can_target_the_right_axis(qtbot: QtBot) -> None:
    inspector = InspectorPanel()
    qtbot.addWidget(inspector)
    seen: list[tuple[str, float, float]] = []

    def _rec(axis: str, y_min: float, y_max: float) -> None:
        seen.append((axis, y_min, y_max))

    inspector.axis_range_requested.connect(_rec)
    inspector.axis_combo.setCurrentIndex(1)  # Right axis
    inspector.y_min_spin.setValue(0.0)
    inspector.y_max_spin.setValue(100.0)
    inspector.apply_button.click()

    assert seen == [("right", 0.0, 100.0)]


def test_inspector_ignores_an_inverted_range(qtbot: QtBot) -> None:
    inspector = InspectorPanel()
    qtbot.addWidget(inspector)
    seen: list[tuple[str, float, float]] = []

    def _rec(axis: str, y_min: float, y_max: float) -> None:
        seen.append((axis, y_min, y_max))

    inspector.axis_range_requested.connect(_rec)
    inspector.y_min_spin.setValue(5.0)
    inspector.y_max_spin.setValue(1.0)

    inspector.apply_button.click()

    assert seen == []


# -- uctan uca: Inspector -> secili grafik --------------------


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


def test_inspector_display_applies_to_the_selected_graph(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    inspector = window.right_dock.inspector

    inspector.axis_combo.setCurrentIndex(0)
    inspector.y_min_spin.setValue(-3.0)
    inspector.y_max_spin.setValue(9.0)
    inspector.apply_button.click()

    _, _, y_min, y_max = window.plot_panel.visible_range()
    assert abs(y_min - (-3.0)) < _EPS
    assert abs(y_max - 9.0) < _EPS

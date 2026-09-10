"""Seçili kanal metadata'sının Inspector'a bağlanması — `F3-035`.

Kabul: kanal değişince ID, birim, dtype ve kaynak güncellenir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.ui.docks.inspector import EMPTY_VALUE, InspectorPanel
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


# -- birim: InspectorPanel dogrudan --------------------------


def _channel(
    channel_id: str, name: str, unit: str, dtype: str, source: ChannelSource
) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"{source.value.title()}/{name}",
        name=name,
        dtype=dtype,
        source=source,
        unit=unit,
        sample_rate_hz=8.0,
    )


def test_inspector_shows_id_unit_dtype_and_source(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)

    panel.show_channel(_channel("ch0", "Pressure", "bar", "float32", ChannelSource.SENSORS))

    assert panel.field_value("ID") == "ch0"
    assert panel.field_value("Unit") == "bar"
    assert panel.field_value("Data type") == "float32"
    assert panel.field_value("Source") == "sensors"


def test_switching_channel_refreshes_every_field(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_channel(_channel("ch0", "Pressure", "bar", "float32", ChannelSource.SENSORS))

    panel.show_channel(_channel("ch5", "Hydrophone", "Pa", "int16", ChannelSource.ACOUSTIC))

    assert panel.field_value("ID") == "ch5"
    assert panel.field_value("Unit") == "Pa"
    assert panel.field_value("Data type") == "int16"
    assert panel.field_value("Source") == "acoustic"


def test_clear_blanks_the_id_field(qtbot: QtBot) -> None:
    panel = InspectorPanel()
    qtbot.addWidget(panel)
    panel.show_channel(_channel("ch0", "Pressure", "bar", "float32", ChannelSource.SENSORS))

    panel.clear()

    assert panel.field_value("ID") == EMPTY_VALUE


# -- uctan uca: secim degisince Inspector guncellenir --------


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


def test_activating_a_channel_binds_its_metadata_to_the_inspector(window: MainWindow) -> None:
    window.left_dock.channel_activated.emit("ch0")
    inspector = window.right_dock.inspector
    assert inspector.field_value("ID") == "ch0"
    assert inspector.field_value("Unit") == "bar"
    assert inspector.field_value("Source") == "sensors"

    window.left_dock.channel_activated.emit("ch5")

    assert inspector.field_value("ID") == "ch5"
    assert inspector.field_value("Unit") == "Pa"
    assert inspector.field_value("Data type") == "float32"
    assert inspector.field_value("Source") == "acoustic"

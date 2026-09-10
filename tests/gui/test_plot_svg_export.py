"""Seçili grafiği SVG olarak dışa aktarma — `F3-063`.

Kabul: vektörel çıktı açılır; seri ve eksenler görünür.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.signals import sine
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.plot_panel import PlotPanel

pytestmark = pytest.mark.gui


def _channel(cid: str, name: str, unit: str) -> ChannelMetadata:
    return ChannelMetadata(
        id=cid,
        path=f"Sensors/{name}",
        name=name,
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit=unit,
        sample_rate_hz=100.0,
    )


@pytest.fixture()
def panel(qtbot: QtBot) -> PlotPanel:
    widget = PlotPanel()
    qtbot.addWidget(widget)
    widget.resize(640, 400)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def _add(panel: PlotPanel, cid: str, name: str, unit: str) -> None:
    panel.add_channel(
        _channel(cid, name, unit),
        sine(cid, sample_rate_hz=100.0, duration_s=1.0, frequency_hz=2.0),
    )


def test_svg_output_is_well_formed_and_vector(panel: PlotPanel, tmp_path: Path) -> None:
    _add(panel, "ch0", "Pressure", "bar")

    dest = panel.export_svg(tmp_path / "plot.svg")
    text = dest.read_text(encoding="utf-8")

    assert text.lstrip().startswith("<?xml")
    assert "<svg" in text and "</svg>" in text
    # standart XML ayrıştırıcı açabilmeli (vektörel çıktı açılır)
    assert ET.parse(dest).getroot().tag.endswith("svg")
    # seriler vektörel yol; rasterleştirilmiş <image> DEĞİL
    assert "<path" in text
    assert "<image" not in text


def test_svg_contains_series_axis_and_unit_text(panel: PlotPanel, tmp_path: Path) -> None:
    _add(panel, "ch0", "Pressure", "bar")

    text = panel.export_svg(tmp_path / "plot.svg").read_text(encoding="utf-8")

    # başlık, eksen adı ve birimi vektörel metin olarak görünür
    assert "Pressure" in text
    assert "bar" in text
    assert "Time" in text


def test_svg_keeps_every_series(panel: PlotPanel, tmp_path: Path) -> None:
    _add(panel, "ch0", "Pressure", "bar")
    _add(panel, "ch1", "Temperature", "C")

    text = panel.export_svg(tmp_path / "multi.svg").read_text(encoding="utf-8")

    assert "Pressure" in text
    assert "Temperature" in text


def test_svg_creates_missing_parent_directories(panel: PlotPanel, tmp_path: Path) -> None:
    _add(panel, "ch0", "Pressure", "bar")

    dest = panel.export_svg(tmp_path / "a" / "b" / "c.svg")

    assert dest.exists() and dest.stat().st_size > 0


def test_svg_export_without_a_series_raises(panel: PlotPanel, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cizili kanal yok"):
        panel.export_svg(tmp_path / "empty.svg")

    assert not (tmp_path / "empty.svg").exists()


# -- entegrasyon: MainWindow.export_plot_svg ------------------


def test_main_window_exports_the_selected_plot_as_svg(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1200, 760)
    window.show()
    qtbot.waitExposed(window)
    window.load_simulation()
    window.open_channel("ch0")

    dest = window.export_plot_svg(tmp_path / "selected.svg")

    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert text.lstrip().startswith("<?xml")
    assert "<svg" in text
    assert ET.parse(dest).getroot().tag.endswith("svg")


def test_exporting_svg_without_a_plotted_channel_raises(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_simulation()

    with pytest.raises(ValueError, match="grafik yok"):
        window.export_plot_svg(tmp_path / "empty.svg")

    assert not (tmp_path / "empty.svg").exists()

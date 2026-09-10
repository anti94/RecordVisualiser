"""Seçili grafiği PNG olarak dışa aktarma — `F3-062`.

Kabul: dosya açılabilir; başlık ve birimler görünür.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.export.image_export import PNG_MAGIC, export_widget_png
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


# -- motor: export_widget_png ------------------------------------


def test_export_writes_an_openable_png(qtbot: QtBot, tmp_path: Path) -> None:
    label = QLabel("grafik")
    qtbot.addWidget(label)
    label.resize(240, 120)

    dest = export_widget_png(label, tmp_path / "out.png")

    assert dest.exists()
    data = dest.read_bytes()
    assert data[:8] == PNG_MAGIC
    reloaded = QPixmap()
    assert reloaded.load(str(dest))  # Qt dosyayı geri açabiliyor
    assert (reloaded.width(), reloaded.height()) == (240, 120)


def test_export_scale_multiplies_the_pixel_size(qtbot: QtBot, tmp_path: Path) -> None:
    label = QLabel("x")
    qtbot.addWidget(label)
    label.resize(200, 100)

    dest = export_widget_png(label, tmp_path / "big.png", scale=2.0)

    reloaded = QPixmap()
    assert reloaded.load(str(dest))
    assert (reloaded.width(), reloaded.height()) == (400, 200)


def test_export_rejects_a_non_positive_scale(qtbot: QtBot, tmp_path: Path) -> None:
    label = QLabel("x")
    qtbot.addWidget(label)
    label.resize(50, 50)
    with pytest.raises(ValueError, match="scale"):
        export_widget_png(label, tmp_path / "n.png", scale=0.0)


def test_export_rejects_a_zero_sized_widget(qtbot: QtBot, tmp_path: Path) -> None:
    label = QLabel("x")
    qtbot.addWidget(label)
    label.resize(0, 0)
    with pytest.raises(ValueError, match="boyut"):
        export_widget_png(label, tmp_path / "z.png")


def test_export_creates_missing_parent_directories(qtbot: QtBot, tmp_path: Path) -> None:
    label = QLabel("x")
    qtbot.addWidget(label)
    label.resize(60, 40)

    dest = export_widget_png(label, tmp_path / "a" / "b" / "c.png")

    assert dest.exists()


# -- entegrasyon: MainWindow.export_plot_png -------------------


def test_exported_plot_carries_the_title_and_unit(qtbot: QtBot, tmp_path: Path) -> None:
    panel = PlotPanel()
    qtbot.addWidget(panel)
    panel.resize(640, 400)
    panel.show()
    qtbot.waitExposed(panel)
    panel.add_channel(
        _channel("ch0", "Pressure", "bar"),
        sine("ch0", sample_rate_hz=100.0, duration_s=1.0, frequency_hz=2.0),
    )

    # Kabulün "başlık ve birimler" kısmı grafiğin kendi çiziminden gelir:
    # export yalnız o çizimi yakalar.
    assert "Pressure" in panel.title_text()
    assert "bar" in panel.axis_label("left")

    dest = export_widget_png(panel, tmp_path / "plot.png")

    reloaded = QPixmap()
    assert reloaded.load(str(dest))
    assert (reloaded.width(), reloaded.height()) == (640, 400)


def test_main_window_exports_the_selected_plot(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1200, 760)
    window.show()
    qtbot.waitExposed(window)
    window.load_simulation()
    window.open_channel("ch0")

    dest = window.export_plot_png(tmp_path / "selected.png")

    assert dest.exists()
    assert dest.read_bytes()[:8] == PNG_MAGIC
    reloaded = QPixmap()
    assert reloaded.load(str(dest))
    assert not reloaded.isNull()


def test_exporting_without_a_plotted_channel_raises(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.load_simulation()  # kayıt açık ama grafikte kanal yok

    with pytest.raises(ValueError, match="grafik yok"):
        window.export_plot_png(tmp_path / "empty.png")

    assert not (tmp_path / "empty.png").exists()

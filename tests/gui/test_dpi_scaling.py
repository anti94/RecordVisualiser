"""Windows ölçekleme ve kontrast kontrolü — `F3-074`.

Kabul: 100/125/150/200 yüzde ölçeklerde kritik metin ve kontroller
kesilmez.

Gerçek DPI oturum boyunca sabit (tek `QApplication`), bu yüzden ölçekleme
**uygulama fontu büyütülerek** taklit edilir — "metin kesilir mi"
sorusunun baskın sürücüsü budur. Her ölçekte kritik widget'ların
`minimumSizeHint`'lerinden küçük olmadığı ve düğme metinlerinin
sığdığı doğrulanır; ayrıca tema kontrastı (ölçekten bağımsız) sınanır.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QAbstractButton, QApplication, QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

#: Bölüm 6 / §16: doğrulanacak Windows ölçek yüzdeleri.
SCALE_PERCENTS = (100, 125, 150, 200)


@pytest.fixture()
def scale(request: pytest.FixtureRequest) -> Iterator[float]:
    """Uygulama fontunu `request.param` yüzdesine ölçekler, sonra geri alır."""
    percent: int = request.param
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    original = app.font()
    bigger = app.font()
    base = original.pointSizeF() if original.pointSizeF() > 0 else 9.0
    bigger.setPointSizeF(base * percent / 100.0)
    app.setFont(bigger)
    try:
        yield percent / 100.0
    finally:
        app.setFont(original)


def _critical_widgets(win: MainWindow) -> list[QWidget]:
    return [
        win.left_dock.open_button,
        win.left_dock.search,
        win.plot_tool_bar.sync_checkbox,
        win.plot_tool_bar.markers_checkbox,
        win.plot_tool_bar.tx_checkbox,
        win.playback_dock.buttons["button_play"],
        win.playback_dock.buttons["button_skip_start"],
        win.playback_dock.time_label,
        win.playback_dock.go_button,
        win.playback_dock.speed_selector,
        win.right_dock.data_export.export_button,
        win.right_dock.data_export.export_format,
        win.right_dock.data_export.data_variant,
        win.status.cursor_time_label,
    ]


@pytest.mark.parametrize("scale", SCALE_PERCENTS, indirect=True)
def test_critical_controls_are_not_clipped_at_scale(scale: float, qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    win.set_repository(MockRecordingRepository(duration_s=8.0))
    win.open_channel("ch0")
    win.resize(1400, 860)
    qtbot.wait(20)  # düzenin oturması için

    clipped: list[str] = []
    for widget in _critical_widgets(win):
        if not widget.isVisibleTo(win):
            continue
        hint = widget.minimumSizeHint()
        name = widget.objectName() or widget.__class__.__name__
        if hint.width() > 0 and widget.width() + 1 < hint.width():
            clipped.append(f"{name}(w {widget.width()}<{hint.width()})")
        if hint.height() > 0 and widget.height() + 1 < hint.height():
            clipped.append(f"{name}(h {widget.height()}<{hint.height()})")

    assert not clipped, f"ölçek {scale:.2f}x: kesilen kontroller {clipped}"


@pytest.mark.parametrize("scale", SCALE_PERCENTS, indirect=True)
def test_button_labels_fit_their_text_at_scale(scale: float, qtbot: QtBot) -> None:
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)

    labelled: list[QAbstractButton] = [
        win.left_dock.open_button,
        win.right_dock.data_export.export_button,
        win.playback_dock.go_button,
    ]
    for button in labelled:
        needed = button.fontMetrics().horizontalAdvance(button.text())
        assert button.sizeHint().width() >= needed, (
            f"ölçek {scale:.2f}x: {button.objectName()!r} metni sığmıyor"
        )


def test_theme_contrast_meets_wcag_for_critical_text() -> None:
    """Kontrast kontrolü ölçekten bağımsız; kritik metin zeminden ayırt edilir."""
    from sonar_analyzer.ui.theme import DARK, contrast_ratio

    assert contrast_ratio(DARK.text_primary, DARK.background) >= 4.5  # AA gövde
    assert contrast_ratio(DARK.text_secondary, DARK.background) >= 3.0  # AA büyük metin
    assert contrast_ratio(DARK.on_accent, DARK.accent) >= 3.0  # düğme etiketi

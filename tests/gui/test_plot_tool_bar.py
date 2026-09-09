"""Grafik hızlı araç şeridi — `F1-040`.

Kabul: zaman penceresi, kanal seçimi ve Sync kontrolü aynı şerittedir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plot_tool_bar import (
    DEFAULT_TIME_WINDOW,
    NO_CHANNEL_TEXT,
    TIME_WINDOWS,
    TOOL_BUTTONS,
    PlotToolBar,
)

pytestmark = pytest.mark.gui


@pytest.fixture()
def bar(qtbot: QtBot) -> PlotToolBar:
    widget = PlotToolBar()
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


# -- yerlesim: kabul kriteri -------------------------------------------------


def test_time_window_channel_and_sync_are_on_the_same_row(bar: PlotToolBar) -> None:
    """Kabul kriteri: üçü aynı şeritte. QHBoxLayout farklı widget türlerini
    dikeyde birkaç piksel farkla ortalayabilir; toleranslı karşılaştırılır.
    """
    tolerance = 6
    time_y = bar.time_window.mapTo(bar, bar.time_window.rect().topLeft()).y()
    channel_y = bar.channel_selector.mapTo(bar, bar.channel_selector.rect().topLeft()).y()
    sync_y = bar.sync_checkbox.mapTo(bar, bar.sync_checkbox.rect().topLeft()).y()
    assert abs(time_y - channel_y) <= tolerance
    assert abs(time_y - sync_y) <= tolerance


def test_tool_bar_is_between_view_tabs_and_center_stack(window: MainWindow, qtbot: QtBot) -> None:
    bar_top = window.plot_tool_bar.mapTo(window, window.plot_tool_bar.rect().topLeft()).y()
    tabs_top = window.view_tabs.mapTo(window, window.view_tabs.rect().topLeft()).y()
    stack_top = window.center_stack.mapTo(window, window.center_stack.rect().topLeft()).y()
    assert tabs_top < bar_top < stack_top


def test_fixed_height_matches_mockup(bar: PlotToolBar) -> None:
    assert bar.height() == 32


# -- zaman penceresi --------------------------------------------------------


def test_time_window_default_and_options(bar: PlotToolBar) -> None:
    assert bar.time_window.currentText() == DEFAULT_TIME_WINDOW == "1 s"
    assert [bar.time_window.itemText(i) for i in range(bar.time_window.count())] == list(
        TIME_WINDOWS
    )


def test_time_window_change_emits_signal(bar: PlotToolBar, qtbot: QtBot) -> None:
    seen: list[str] = []
    bar.time_window_changed.connect(seen.append)

    with qtbot.waitSignal(bar.time_window_changed, timeout=2000):
        bar.time_window.setCurrentText("10 s")
    assert seen == ["10 s"]


# -- kanal secici -------------------------------------------------------


def test_channel_selector_disabled_without_channels(bar: PlotToolBar) -> None:
    assert not bar.channel_selector.isEnabled()
    assert bar.channel_selector.currentText() == NO_CHANNEL_TEXT


def test_channel_selector_is_filled_after_loading(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))

    assert window.plot_tool_bar.channel_selector.isEnabled()
    assert window.plot_tool_bar.channel_selector.count() == 8
    assert window.plot_tool_bar.channel_selector.itemText(0) == "Pressure [bar]"


def test_selecting_from_the_toolbar_draws_the_channel(window: MainWindow) -> None:
    window.set_repository(MockRecordingRepository(duration_s=10.0))

    window.plot_tool_bar.channel_selector.setCurrentIndex(5)

    assert window.plot_panel.channel is not None
    assert window.plot_panel.channel.id == "ch5"
    assert window.center_shows_plot


def test_selecting_a_channel_elsewhere_updates_the_toolbar(window: MainWindow) -> None:
    """Ağaçtan seçim yapılırsa şeritteki seçici de eşleşmeli."""
    window.set_repository(MockRecordingRepository(duration_s=10.0))

    window.left_dock.channel_activated.emit("ch3")

    assert window.plot_tool_bar.channel_selector.currentText() == "Accel Y [g]"


def test_clear_channels_resets_the_selector(bar: PlotToolBar) -> None:
    from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource

    bar.set_channels(
        [
            ChannelMetadata(
                id="ch0", path="A/B", name="B", dtype="float32", source=ChannelSource.SENSORS
            )
        ]
    )
    assert bar.channel_selector.isEnabled()

    bar.clear_channels()

    assert not bar.channel_selector.isEnabled()
    assert bar.channel_selector.currentText() == NO_CHANNEL_TEXT


def test_unknown_current_channel_is_ignored(bar: PlotToolBar) -> None:
    """Var olmayan bir kanal id'si seçici durumunu bozmamalı."""
    bar.set_current_channel("yok")
    assert bar.channel_selector.currentText() == NO_CHANNEL_TEXT


# -- Sync --------------------------------------------------------------


def test_sync_is_checked_by_default(bar: PlotToolBar) -> None:
    assert bar.sync_checkbox.isChecked()


def test_sync_toggle_emits_signal(bar: PlotToolBar, qtbot: QtBot) -> None:
    seen: list[bool] = []
    bar.sync_toggled.connect(seen.append)

    with qtbot.waitSignal(bar.sync_toggled, timeout=2000):
        bar.sync_checkbox.setChecked(False)
    assert seen == [False]


# -- arac dugmeleri (henuz pasif) ---------------------------------------


def test_tool_buttons_exist_in_mockup_order(bar: PlotToolBar) -> None:
    assert list(bar.tool_buttons) == [name for name, _, _ in TOOL_BUTTONS]
    assert len(TOOL_BUTTONS) == 7


def test_tool_buttons_are_disabled_with_reason(bar: PlotToolBar) -> None:
    """Faz 3'e kadar (F3-021..F3-029) pasif; gizlenmiyor, nedeni ipucunda."""
    from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE

    for button in bar.tool_buttons.values():
        assert not button.isEnabled()
        assert NOT_YET_AVAILABLE in button.toolTip()
        assert button.text() != ""

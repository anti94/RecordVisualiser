"""Grafiği ayırma ve geri takma — `F4-082`.

Kabul: ayrılan panel veri ve X senkronizasyonunu korur.

Ayırma bir kopyalama değil, **yeniden ebeveynlemedir**: aynı `PlotPanel`
nesnesi yeni pencereye taşınır. Testler bunu hem yapısal olarak (nesne
kimliği), hem de sonuçlarıyla denetler — çizili seriler, stiller ve
işaretler yerinde kalır, ayrık penceredeki pan ana penceredeki timeline'a
ulaşır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.annotation import Annotation, AnnotationSet
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.detached_window import WINDOW_TITLE, DetachedPlotWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=50.0))
    window.open_channel("ch0")
    return window


def _cleanup(win: MainWindow) -> None:
    if win.plot_is_detached:
        win.reattach_plot()


# --------------------------------------------------------------------------- #
# ayirma
# --------------------------------------------------------------------------- #


def test_a_new_window_starts_attached(win: MainWindow) -> None:
    assert not win.plot_is_detached
    assert win.detached_window is None
    assert win.reattach_plot() is False


def test_detaching_moves_the_plot_into_its_own_window(win: MainWindow) -> None:
    panel = win.plot_panel

    assert win.detach_plot() is True

    window = win.detached_window
    assert isinstance(window, DetachedPlotWindow)
    assert window.windowTitle() == WINDOW_TITLE
    assert window.panel is panel
    assert panel.window() is window
    _cleanup(win)


def test_the_detached_panel_is_the_same_object(win: MainWindow) -> None:
    """Kopya değil, aynı widget — verinin korunmasının yapısal nedeni."""
    panel = win.plot_panel
    win.detach_plot()
    assert win.plot_panel is panel
    _cleanup(win)


def test_detaching_twice_is_refused(win: MainWindow) -> None:
    assert win.detach_plot() is True
    assert win.detach_plot() is False
    _cleanup(win)


def test_detaching_is_logged(win: MainWindow) -> None:
    win.detach_plot()
    assert any("ayrı pencereye" in line for line in win.bottom_dock.log_lines())
    _cleanup(win)


# --------------------------------------------------------------------------- #
# VERI korunur
# --------------------------------------------------------------------------- #


def test_the_plotted_series_survive_detaching(win: MainWindow) -> None:
    before = win.plot_panel.plotted_channel_ids()
    assert before

    win.detach_plot()

    assert win.plot_panel.plotted_channel_ids() == before
    _cleanup(win)


def test_the_series_style_survives_detaching(win: MainWindow) -> None:
    win.plot_panel.set_series_style("ch0", color="#FF00AA", width=3)
    win.detach_plot()
    style = win.plot_panel.series_style("ch0")
    assert (style.color, style.width) == ("#FF00AA", 3)
    _cleanup(win)


def test_the_bookmarks_survive_detaching(win: MainWindow) -> None:
    win.set_annotations(
        AnnotationSet((Annotation.bookmark("TX", win.playback_dock.current_time_ns()),))
    )
    assert win.plot_panel.bookmark_count() == 1

    win.detach_plot()

    assert win.plot_panel.bookmark_count() == 1
    _cleanup(win)


def test_the_time_anchor_survives_detaching(win: MainWindow) -> None:
    anchor = win.plot_panel.time_anchor_ns
    assert anchor is not None
    win.detach_plot()
    assert win.plot_panel.time_anchor_ns == anchor
    _cleanup(win)


def test_the_visible_range_survives_detaching(win: MainWindow) -> None:
    win.plot_panel.set_x_range(1.0, 4.0)
    before = win.plot_panel.visible_x_range()
    win.detach_plot()
    assert win.plot_panel.visible_x_range() == before
    _cleanup(win)


# --------------------------------------------------------------------------- #
# X SENKRONIZASYONU korunur
# --------------------------------------------------------------------------- #


def test_panning_in_the_detached_window_still_reaches_the_timeline(win: MainWindow) -> None:
    """Ayrık paneldeki pan ana penceredeki timeline viewport'una ulaşır."""
    win.detach_plot()

    win.plot_panel.set_x_range(2.0, 5.0)

    start_ns = win.plot_panel.timestamp_ns_for_x(2.0)
    end_ns = win.plot_panel.timestamp_ns_for_x(5.0)
    viewport = win.playback_dock.timeline.viewport_ns()
    assert viewport is not None
    assert abs(viewport[0] - start_ns) < SECOND // 10
    assert abs(viewport[1] - end_ns) < SECOND // 10
    _cleanup(win)


def test_the_x_range_signal_still_fires_when_detached(win: MainWindow, qtbot: QtBot) -> None:
    win.detach_plot()
    with qtbot.waitSignal(win.plot_panel.x_range_changed, timeout=1_000):
        win.plot_panel.set_x_range(0.5, 3.5)
    _cleanup(win)


def test_going_to_a_time_still_moves_the_detached_plot(win: MainWindow) -> None:
    """`go_to_time` ayrık panelde de çalışır — bağlantı widget'a aittir."""
    win.detach_plot()
    win.plot_panel.set_x_range(0.0, 1.0)

    assert win.go_to_time(win.plot_panel.timestamp_ns_for_x(6.0)) is True

    x_min, x_max = win.plot_panel.visible_x_range()
    assert x_min <= 6.0 <= x_max
    _cleanup(win)


# --------------------------------------------------------------------------- #
# geri takma
# --------------------------------------------------------------------------- #


def test_reattaching_puts_the_plot_back_in_the_dashboard(win: MainWindow) -> None:
    panel = win.plot_panel
    win.detach_plot()

    assert win.reattach_plot() is True

    assert not win.plot_is_detached
    assert win.detached_window is None
    assert win.plot_panel is panel
    assert win.dashboard.rows.widget(0) is panel


def test_reattaching_keeps_the_data(win: MainWindow) -> None:
    win.plot_panel.set_series_style("ch0", color="#00FF88")
    before = win.plot_panel.plotted_channel_ids()
    win.detach_plot()
    win.reattach_plot()

    assert win.plot_panel.plotted_channel_ids() == before
    assert win.plot_panel.series_style("ch0").color == "#00FF88"


def test_reattaching_keeps_the_x_synchronisation(win: MainWindow) -> None:
    win.detach_plot()
    win.reattach_plot()

    win.plot_panel.set_x_range(1.0, 3.0)

    viewport = win.playback_dock.timeline.viewport_ns()
    assert viewport is not None
    assert abs(viewport[0] - win.plot_panel.timestamp_ns_for_x(1.0)) < SECOND // 10


def test_closing_the_detached_window_reattaches(win: MainWindow) -> None:
    """Pencereyi kapatmak grafiği yok etmez; geri takar."""
    panel = win.plot_panel
    win.detach_plot()
    window = win.detached_window
    assert window is not None

    window.close()

    assert not win.plot_is_detached
    assert win.plot_panel is panel
    assert win.dashboard.rows.widget(0) is panel


def test_reattaching_is_logged(win: MainWindow) -> None:
    win.detach_plot()
    win.reattach_plot()
    assert any("geri takıldı" in line for line in win.bottom_dock.log_lines())


def test_detaching_and_reattaching_repeatedly_is_stable(win: MainWindow) -> None:
    panel = win.plot_panel
    before = win.plot_panel.plotted_channel_ids()
    for _ in range(3):
        assert win.detach_plot() is True
        assert win.reattach_plot() is True
    assert win.plot_panel is panel
    assert win.plot_panel.plotted_channel_ids() == before
    assert win.dashboard.rows.widget(0) is panel


# --------------------------------------------------------------------------- #
# pencere widget'i tek basina
# --------------------------------------------------------------------------- #


def test_an_empty_detached_window_holds_nothing(qtbot: QtBot) -> None:
    window = DetachedPlotWindow()
    qtbot.addWidget(window)
    assert window.panel is None
    assert window.release() is None


def test_the_window_emits_closed_once(qtbot: QtBot) -> None:
    window = DetachedPlotWindow()
    qtbot.addWidget(window)
    seen: list[int] = []
    window.closed.connect(lambda: seen.append(1))
    window.close()
    assert seen == [1]

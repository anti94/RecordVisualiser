"""Zaman bölgesi sürüklemesinde istatistik sorgularının debounce'u — `F3-060`.

Kabul: hızlı sürüklemede son konum çizilir; her ara konum için sorgu
yapılmaz.

Coalesce mantığı ve eski-sorgu koruması ayrıca `GUI olmadan`
`tests/unit/test_scrub_debounce.py` içinde doğrulanır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


class _CountingRepo(MockRecordingRepository):
    """`query` çağrılarını (kanal, aralık) olarak sayan sahte repo."""

    def __init__(self) -> None:
        super().__init__(duration_s=5.0)
        self.query_calls: list[tuple[str, TimeRange]] = []

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        self.query_calls.append((channel_id, time_range))
        return super().query(channel_id, time_range, max_points)


@pytest.fixture()
def window(qtbot: QtBot) -> tuple[MainWindow, _CountingRepo]:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    repo = _CountingRepo()
    win.set_repository(repo)
    win.left_dock.channel_activated.emit("ch0")
    # `F4-058`: kanal çizildikten sonra viewport yenilemesi bir kez daha
    # sorgu yapar (panel yerleşince piksel bütçesi değişir). Bu test ROI
    # debounce'unu sayar; o yenilemenin oturmasını bekleyip sayacı sıfırla.
    qtbot.wait(200)
    repo.query_calls.clear()
    return win, repo


def test_first_region_change_queries_immediately(
    window: tuple[MainWindow, _CountingRepo],
) -> None:
    win, repo = window

    win.plot_panel.set_time_region(0.25, 0.55)

    assert len(repo.query_calls) == 1
    assert "0.25" in win.dashboard.statistics.title()


def test_fast_drag_coalesces_to_the_last_region(
    window: tuple[MainWindow, _CountingRepo], qtbot: QtBot
) -> None:
    win, repo = window

    # hızlı sürükleme: art arda birçok ara bitiş konumu
    for end_s in (0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.31):
        win.plot_panel.set_time_region(0.10, end_s)

    qtbot.wait(250)  # sessizlik süresi (0.12 s) + zamanlayıcı payı

    # ilk (leading) + tek trailing = 2 sorgu; 7 ara konum için 7 değil
    assert len(repo.query_calls) == 2
    # son çizilen bölge sürüklemenin SON konumudur
    region = win.plot_panel.time_region_x()
    assert region is not None
    assert abs(region[0] - 0.10) < 1e-6 and abs(region[1] - 0.31) < 1e-6
    title = win.dashboard.statistics.title()
    assert "0.1" in title and "0.31" in title


def test_a_slow_sequence_of_changes_each_queries(
    window: tuple[MainWindow, _CountingRepo], qtbot: QtBot
) -> None:
    win, repo = window

    win.plot_panel.set_time_region(0.10, 0.20)
    qtbot.wait(200)  # sessizlik: bu ayrı bir sürükleme sayılır
    win.plot_panel.set_time_region(0.10, 0.40)
    qtbot.wait(200)

    assert len(repo.query_calls) == 2
    assert "0.4" in win.dashboard.statistics.title()


def test_closing_the_recording_leaves_no_pending_scrub(
    window: tuple[MainWindow, _CountingRepo], qtbot: QtBot
) -> None:
    win, repo = window
    win.plot_panel.set_time_region(0.10, 0.20)  # leading
    win.plot_panel.set_time_region(0.10, 0.30)  # bekleyen
    calls_before = len(repo.query_calls)

    win.action("action_close").trigger()
    qtbot.wait(250)  # bekleyen tik gelseydi burada sorgu yapardı

    # Kapanıştan sonra bekleyen scrub sorgusu yürütülmez.
    assert len(repo.query_calls) == calls_before

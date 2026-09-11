"""Canlı veri grafiklere bağlı — `F5-022`.

Kabul: grafikler ring buffer'dan güncellenir; **UI thread bloklanmaz**.

İkinci yarı ölçülerek kanıtlanır: kaynak kasıtlı olarak yavaşlatılır
(paket başına gerçek gecikme) ve UI tarafındaki `pump_live_stream()`
çağrısının o gecikmeden **bağımsız** olarak hızlı döndüğü ölçülür.
Okuma UI thread'inde olsaydı bu süre kaynağın hızına bağlı olurdu.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.packet_queue import DropPolicy
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.live_runner import LiveRunner
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

DURATION_S = 1.0  # 8 pencere


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _fast_source() -> FileReplaySource:
    return FileReplaySource(MockRecordingRepository(duration_s=DURATION_S), sleep=lambda _s: None)


def _slow_source() -> FileReplaySource:
    """Her paket için **gerçekten** 125 ms bekleyen kaynak — worker'ı meşgul eder."""
    return FileReplaySource(MockRecordingRepository(duration_s=DURATION_S), sleep=time.sleep)


def _pump_until(win: MainWindow, qtbot: QtBot, wanted: int) -> None:
    """`wanted` paket repository'ye yazılana kadar UI karelerini sürer.

    Gerçek arayüzde bunu bir zamanlayıcı yapar; testte kareleri elle
    sürmek zamanlayıcı beklemeden aynı yolu çalıştırır.
    """

    def pumped() -> bool:
        win.pump_live_stream()
        repository = win.live_repository
        return repository is not None and repository.packet_count >= wanted

    qtbot.waitUntil(pumped, timeout=5000)


# --------------------------------------------------------------------------- #
# worker kuyruga yazar, UI kuyrugu bosaltir
# --------------------------------------------------------------------------- #


def test_the_worker_fills_the_queue_and_the_ui_drains_it(win: MainWindow, qtbot: QtBot) -> None:
    win.set_live_source(_fast_source())
    win.connect_live_source()
    repository = win.start_live_stream(buffer_capacity=10_000)
    try:
        _pump_until(win, qtbot, wanted=8)
    finally:
        win.stop_live_stream()

    assert repository.packet_count == 8  # 1 sn / 125 ms
    assert len(repository.query("ch0", repository.metadata().time_range)) > 0


def test_the_plot_is_updated_from_the_ring_buffer(win: MainWindow, qtbot: QtBot) -> None:
    win.set_live_source(_fast_source())
    win.connect_live_source()
    win.set_live_plot_channel("ch0")
    repository = win.start_live_stream(buffer_capacity=10_000)
    try:
        _pump_until(win, qtbot, wanted=8)
    finally:
        win.stop_live_stream()

    assert "ch0" in win.plot_panel.plotted_channel_ids()
    plotted = win.plot_panel.sample_count
    assert plotted > 0
    assert plotted <= repository.buffer.count("ch0")


def test_without_a_selected_channel_the_plot_stays_empty(win: MainWindow, qtbot: QtBot) -> None:
    win.set_live_source(_fast_source())
    win.connect_live_source()
    win.start_live_stream(buffer_capacity=10_000)
    try:
        _pump_until(win, qtbot, wanted=4)
    finally:
        win.stop_live_stream()

    assert win.plot_panel.plotted_channel_ids() == []  # kanal secilmedi, cizim yok


# --------------------------------------------------------------------------- #
# UI THREAD BLOKLANMAZ
# --------------------------------------------------------------------------- #


def test_pumping_is_fast_even_when_the_source_is_slow(win: MainWindow, qtbot: QtBot) -> None:
    """Kaynak paket başına 125 ms beklese de UI tarafı milisaniyelerde döner."""
    win.set_live_source(_slow_source())
    win.connect_live_source()
    win.set_live_plot_channel("ch0")
    repository = win.start_live_stream(buffer_capacity=10_000)
    try:
        # Worker en az bir paket uretene kadar bekle (UI burada bilincli bekliyor).
        qtbot.waitUntil(lambda: win.live_repository is not None and _queued(win) > 0, timeout=5000)

        durations: list[float] = []
        for _ in range(20):  # yirmi "kare"
            started = time.perf_counter()
            win.pump_live_stream()
            durations.append(time.perf_counter() - started)
    finally:
        win.stop_live_stream()

    # Ilk kare bir defalik kurulum isi tasir (seri ekleme, otomatik olcek,
    # ilk boyama). Olculen sey "UI kaynagin yavasligini BEKLEMIYOR mu"
    # oldugu icin bu kurulum ayri degerlendirilir: kaynagin paket basina
    # harcadigi 125 ms'in altinda kalmasi yeterlidir, cunku beklemis olsaydi
    # en az o kadar surerdi.
    first, rest = durations[0], durations[1:]
    assert first < 0.125, f"ilk kare kaynagi beklemis olabilir: {first:.4f} s"

    # Kurulum bittikten sonraki kareler kaynagin onda birinden cok daha hizli.
    assert max(rest) < 0.0125, f"en yavas kare {max(rest):.4f} s"
    assert repository.packet_count > 0


def _queued(window: MainWindow) -> int:
    return window.live_queue_depth


def test_pumping_an_empty_queue_returns_immediately(win: MainWindow) -> None:
    win.set_live_source(_fast_source())
    win.start_live_stream()
    try:
        started = time.perf_counter()
        written = win.pump_live_stream()
        elapsed = time.perf_counter() - started
    finally:
        win.stop_live_stream()

    assert written == 0
    assert elapsed < 0.05  # beklemedi


def test_pump_without_a_stream_is_a_no_op(win: MainWindow) -> None:
    assert win.pump_live_stream() == 0


def test_starting_without_a_source_is_refused(win: MainWindow) -> None:
    with pytest.raises(RuntimeError, match="set_live_source"):
        win.start_live_stream()


# --------------------------------------------------------------------------- #
# kuyruk sinirli: burst UI'yi bogmaz
# --------------------------------------------------------------------------- #


def test_a_single_pump_processes_at_most_the_given_limit(win: MainWindow, qtbot: QtBot) -> None:
    """Büyük bir birikim tek karede arayüzü meşgul etmesin."""
    win.set_live_source(_fast_source())
    win.connect_live_source()
    repository = win.start_live_stream(buffer_capacity=10_000)
    try:
        qtbot.waitUntil(lambda: _queued(win) >= 5, timeout=5000)
        written = win.pump_live_stream(limit=2)
    finally:
        win.stop_live_stream()

    assert written == 2
    assert repository.packet_count == 2  # kalanlar kuyrukta bekliyor


def test_the_runner_queue_is_bounded_by_its_policy() -> None:
    runner = LiveRunner(queue_maxsize=4, policy=DropPolicy.DROP_OLDEST)
    assert runner.queue.maxsize == 4
    assert runner.queue.policy is DropPolicy.DROP_OLDEST
    assert runner.is_reading is False


# --------------------------------------------------------------------------- #
# durdurma ve hata
# --------------------------------------------------------------------------- #


def test_stopping_ends_the_worker(win: MainWindow, qtbot: QtBot) -> None:
    win.set_live_source(_fast_source())
    win.connect_live_source()
    win.start_live_stream()
    qtbot.waitUntil(lambda: _queued(win) > 0, timeout=5000)

    win.stop_live_stream()
    assert win.pump_live_stream() == 0  # runner birakildi


def test_a_failing_source_is_logged_without_crashing(win: MainWindow, qtbot: QtBot) -> None:
    class _Exploding(FileReplaySource):
        def packets(self):  # type: ignore[override]
            raise OSError("okuma koptu")
            yield  # pragma: no cover - uretici olmasi icin

    win.set_live_source(_Exploding(MockRecordingRepository(duration_s=0.5), sleep=lambda _s: None))
    win.connect_live_source()
    win.start_live_stream()
    try:
        qtbot.waitUntil(
            lambda: any("Canli okuma hatasi" in line for line in win.bottom_dock.log_lines()),
            timeout=5000,
        )
    finally:
        win.stop_live_stream()

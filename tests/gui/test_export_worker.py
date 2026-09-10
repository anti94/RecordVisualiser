"""Büyük export worker'ı ve iptal — `F3-066`.

Kabul: UI yanıt verir; iptal yarım dosyayı tamamlanmış diye sunmaz.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.export.csv_export import ExportCancelled
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.export_runner import ExportRunner
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

ShouldCancel = Callable[[], bool]
OnProgress = Callable[[int, int], None]


# -- ExportRunner tek başına ----------------------------------


def test_runner_emits_finished_with_the_job_result(qtbot: QtBot) -> None:
    def job(_should_cancel: ShouldCancel, _on_progress: OnProgress) -> object:
        return "done"

    got: list[object] = []
    runner = ExportRunner(job)
    runner.export_finished.connect(got.append)
    with qtbot.waitSignal(runner.export_finished, timeout=3000):
        runner.start()
    assert got == ["done"]
    assert runner.wait_done()


def test_runner_start_returns_immediately_and_reports_progress(qtbot: QtBot) -> None:
    ticks: list[tuple[int, int]] = []

    def _tick(written: int, total: int) -> None:
        ticks.append((written, total))

    def job(should_cancel: ShouldCancel, on_progress: OnProgress) -> object:
        for i in range(5):
            if should_cancel():
                raise ExportCancelled("iptal")
            time.sleep(0.01)
            on_progress(i + 1, 5)
        return "ok"

    runner = ExportRunner(job)
    runner.progress.connect(_tick)
    started = time.perf_counter()
    runner.start()
    assert time.perf_counter() - started < 0.2  # start() bloklamadı (iş ~50 ms)
    qtbot.waitSignal(runner.export_finished, timeout=3000).wait()
    assert ticks[-1] == (5, 5)


def test_runner_cancel_emits_cancelled(qtbot: QtBot) -> None:
    def job(should_cancel: ShouldCancel, on_progress: OnProgress) -> object:
        for _ in range(100_000):
            if should_cancel():
                raise ExportCancelled("iptal")
            on_progress(1, 100_000)
        return "should not reach"

    runner = ExportRunner(job)
    with qtbot.waitSignal(runner.cancelled, timeout=3000):
        runner.start()
        runner.cancel()
    assert runner.wait_done()


def test_runner_failure_emits_failed_with_message(qtbot: QtBot) -> None:
    def job(_should_cancel: ShouldCancel, _on_progress: OnProgress) -> object:
        raise OSError("disk dolu")

    messages: list[str] = []
    runner = ExportRunner(job)
    runner.failed.connect(messages.append)
    with qtbot.waitSignal(runner.failed, timeout=3000):
        runner.start()
    assert "disk dolu" in messages[0]


# -- MainWindow entegrasyonu --------------------------------
#
# Kayıt küçük tutulur: MockRepo olay sayısı süreyle ölçeklenir ve
# binlerce InfiniteLine pyqtgraph'ı boğar. İptalin yarım dosya
# bırakmama garantisi zaten `test_csv_export.py` + `ExportRunner`
# testlerinde deterministik doğrulanır; buradaki testler yalnız
# MainWindow'un worker'a doğru bağlandığını gösterir.


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    win.set_repository(MockRecordingRepository(duration_s=5.0))
    win.open_channel("ch0")
    return win


def test_csv_export_goes_through_a_worker_thread(
    window: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    target = tmp_path / "out.csv"
    runner = window.start_channel_csv_export(target)

    assert isinstance(runner, ExportRunner)
    qtbot.waitSignal(runner.export_finished, timeout=10_000).wait()

    assert target.exists()
    assert not target.with_name(target.name + ".part").exists()
    assert not window.right_dock.data_export.is_running


def test_export_button_toggles_to_cancel_while_running(
    window: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    card = window.right_dock.data_export
    assert card.export_button.text() == "Export Data"

    # set_running(True) start_channel_csv_export içinde senkron çağrılır.
    runner = window.start_channel_csv_export(tmp_path / "x.csv")
    assert card.export_button.text() == "İptal"

    qtbot.waitSignal(runner.export_finished, timeout=10_000).wait()
    qtbot.waitUntil(lambda: not card.is_running, timeout=2000)
    assert card.export_button.text() == "Export Data"


def test_cancel_export_forwards_to_the_runner_and_restores_ui(
    window: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    target = tmp_path / "maybe.csv"
    runner = window.start_channel_csv_export(target)
    window.cancel_export()  # -> runner.cancel()

    # Küçük kayıtta yarış kaybedilip iş bitmiş olabilir; her iki sonuç da
    # geçerli. Değişmez: yarım (.part) dosya asla kalmaz, UI eski hâline
    # döner ve süren worker referansı bırakılır.
    qtbot.waitUntil(lambda: not window.right_dock.data_export.is_running, timeout=10_000)
    assert runner.wait_done(10_000)
    assert not target.with_name(target.name + ".part").exists()
    assert window.right_dock.data_export.export_button.text() == "Export Data"

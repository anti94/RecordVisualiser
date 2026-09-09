"""Dosya yükleme worker'ı — `F3-002`.

Kabul: yükleme sırasında pencere etkileşimlere yanıt verir.

"Yanıt verir" burada ölçülebilir iki şeyle kanıtlanır: (1) yükleyici
**GUI thread'inden başka** bir thread'de çalışır, (2) yükleme sürerken GUI
thread'i olay döngüsünü işlemeye devam eder — zamanlayıcı tetiklenir ve
düğme tıklaması alınır.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from sonar_analyzer.application.file_loader import (
    FileLoadResult,
    FileLoadService,
    LoaderCallable,
    default_loader,
)
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


class ServiceFactory(Protocol):
    def __call__(self, *, loader: LoaderCallable | None = None) -> FileLoadService: ...


@pytest.fixture()
def service_factory() -> Iterator[ServiceFactory]:
    """Kurulan her servisi test sonunda düzgün kapatır (thread sızmasın)."""
    created: list[FileLoadService] = []

    def make(*, loader: LoaderCallable | None = None) -> FileLoadService:
        service = FileLoadService(loader=loader)
        created.append(service)
        return service

    yield make

    for service in created:
        service.shutdown()


# -- yukleme GUI thread'inde CALISMAZ --------------------------------------


def test_loader_runs_off_the_gui_thread(qtbot: QtBot, service_factory: ServiceFactory) -> None:
    """Kabul kriterinin temeli: yükleyici GUI thread'inde çalışmaz."""
    gui_thread = QThread.currentThread()
    seen_threads: list[QThread] = []

    def loader(path: Path) -> FileRecordingRepository:
        seen_threads.append(QThread.currentThread())
        return default_loader(path)

    service = service_factory(loader=loader)
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])

    assert len(seen_threads) == 1
    assert seen_threads[0] is not gui_thread


def test_submit_returns_immediately_without_waiting_for_the_load(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    """`submit()` bloklamaz: yavaş yükleyicide bile hemen döner."""

    def slow_loader(path: Path) -> FileRecordingRepository:
        time.sleep(0.4)
        return default_loader(path)

    service = service_factory(loader=slow_loader)

    started = time.perf_counter()
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])
        elapsed_after_submit = time.perf_counter() - started

    # submit() yuklemeyi beklemis olsaydi >= 0.4 s surerdi.
    assert elapsed_after_submit < 0.2


def test_gui_thread_keeps_processing_events_during_a_slow_load(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    """Kabul kriteri birebir: yükleme sürerken pencere etkileşimlere yanıt verir."""

    def slow_loader(path: Path) -> FileRecordingRepository:
        time.sleep(0.5)
        return default_loader(path)

    service = service_factory(loader=slow_loader)

    ticks: list[int] = []
    timer = QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: ticks.append(len(ticks)))

    clicks: list[str] = []
    button = QPushButton()
    qtbot.addWidget(button)
    button.clicked.connect(lambda: clicks.append("tiklandi"))

    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])
        timer.start()
        qtbot.wait(200)
        button.click()  # yukleme surerken kullanici etkilesimi
        qtbot.wait(100)
    timer.stop()

    # Yukleme GUI thread'ini dondursaydi ne zamanlayici tetiklenir ne de
    # tiklama islenirdi.
    assert len(ticks) >= 3
    assert clicks == ["tiklandi"]


# -- sonuclar GUI thread'ine doner -----------------------------------------


def test_successful_load_emits_a_repository(qtbot: QtBot, service_factory: ServiceFactory) -> None:
    service = service_factory()
    results: list[FileLoadResult] = []
    service.file_loaded.connect(results.append)

    with qtbot.waitSignal(service.request_finished, timeout=5000):
        request_id = service.submit([VALID_FIXTURE])

    assert len(results) == 1
    result = results[0]
    assert result.request_id == request_id
    assert result.succeeded
    assert result.path == VALID_FIXTURE
    assert result.repository is not None
    assert result.repository.metadata().record_count == 8
    result.repository.close()


def test_results_arrive_on_the_gui_thread(qtbot: QtBot, service_factory: ServiceFactory) -> None:
    """Sinyal kuyruklu bağlantıyla döndüğü için sonuç GUI thread'inde işlenir."""
    gui_thread = QThread.currentThread()
    handler_threads: list[QThread] = []

    def record_thread(_result: FileLoadResult) -> None:
        handler_threads.append(QThread.currentThread())

    service = service_factory()
    service.file_loaded.connect(record_thread)

    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])

    assert handler_threads == [gui_thread]


def test_multiple_files_produce_one_result_each_in_order(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    service = service_factory()
    results: list[FileLoadResult] = []
    service.file_loaded.connect(results.append)

    paths = [VALID_FIXTURE, FIXTURES_DIR / "gap_missing_record.bin"]
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit(paths)

    assert [result.path for result in results] == paths
    for result in results:
        assert result.succeeded
        assert result.repository is not None
        result.repository.close()


# -- hata bir dosyayi atlar, digerleri surer --------------------------------


def test_failing_file_is_reported_without_stopping_the_rest(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    """Fail-soft: bozuk dosya hata olarak raporlanır, kalanlar yüklenir."""
    service = service_factory()
    results: list[FileLoadResult] = []
    service.file_loaded.connect(results.append)

    paths = [FIXTURES_DIR / "truncated_header.bin", VALID_FIXTURE]
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit(paths)

    assert len(results) == 2
    failed, succeeded = results
    assert not failed.succeeded
    assert failed.error
    assert failed.error_type == "TruncatedHeaderError"
    assert succeeded.succeeded
    assert succeeded.repository is not None
    succeeded.repository.close()


def test_missing_file_is_reported_as_an_error(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    service = service_factory()
    results: list[FileLoadResult] = []
    service.file_loaded.connect(results.append)

    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([FIXTURES_DIR / "olmayan-dosya.bin"])

    assert len(results) == 1
    assert not results[0].succeeded
    assert results[0].error_type in {"FileNotFoundError", "OSError"}


# -- istek kimligi ve kapanis ----------------------------------------------


def test_request_ids_increase_for_each_submission(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    service = service_factory()
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        first = service.submit([VALID_FIXTURE])
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        second = service.submit([VALID_FIXTURE])

    assert second == first + 1


def test_shutdown_stops_the_worker_thread(qtbot: QtBot) -> None:
    service = FileLoadService()
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])

    service.shutdown()

    assert not service.is_running
    service.shutdown()  # tekrarli kapanis guvenli


# -- ana pencere baglantisi ------------------------------------------------


def test_main_window_loads_selection_through_the_worker(qtbot: QtBot, tmp_path: Path) -> None:
    """Seçim → worker → sonuç zinciri ana pencerede uçtan uca çalışır."""
    import shutil

    window = MainWindow()
    qtbot.addWidget(window)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)

    def stub_dialog(_parent: object, _start: str) -> list[str]:
        return [str(target)]

    window.file_open._dialog = stub_dialog  # type: ignore[assignment]

    with qtbot.waitSignal(window.file_loader.request_finished, timeout=5000):
        window.action("action_open").trigger()

    assert len(window.loaded_results) == 1
    assert window.loaded_results[0].path == target
    assert window.failed_results == ()
    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Yuklendi: kayit.bin" in log_text
    window.close()


def test_main_window_reports_a_failing_file_in_the_log(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    target = tmp_path / "bozuk.bin"
    target.write_bytes(b"gecersiz")

    def stub_dialog(_parent: object, _start: str) -> list[str]:
        return [str(target)]

    window.file_open._dialog = stub_dialog  # type: ignore[assignment]

    with qtbot.waitSignal(window.file_loader.request_finished, timeout=5000):
        window.action("action_open").trigger()

    assert window.loaded_results == ()
    assert len(window.failed_results) == 1
    assert "Yuklenemedi: bozuk.bin" in "\n".join(window.bottom_dock.log_lines())
    window.close()


# -- thread yasam dongusu: bosta thread calismaz ---------------------------


def test_thread_is_not_running_before_any_submission(service_factory: ServiceFactory) -> None:
    """Kurucu thread başlatmaz; boşta hiçbir thread çalışmaz."""
    service = service_factory()
    assert not service.is_running


def test_thread_stops_itself_after_the_request_finishes(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    service = service_factory()
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        service.submit([VALID_FIXTURE])

    assert not service.is_running


def test_thread_restarts_for_a_later_submission(
    qtbot: QtBot, service_factory: ServiceFactory
) -> None:
    """Durmuş thread yeniden başlatılabilir; ikinci açma da çalışır."""
    service = service_factory()
    results: list[FileLoadResult] = []
    service.file_loaded.connect(results.append)

    for _ in range(2):
        with qtbot.waitSignal(service.request_finished, timeout=5000):
            service.submit([VALID_FIXTURE])

    assert len(results) == 2
    for result in results:
        assert result.succeeded
        assert result.repository is not None
        result.repository.close()


def test_discarded_window_does_not_crash_the_process() -> None:
    """Regresyon: `close()` çağrılmadan çöpe giden pencere süreci çökertmemeli.

    Ayrı süreçte koşar — çökme olsaydı bu testi düşürür, tüm paketi değil
    (bu tam olarak bir kez yaşandı: `QThread: Destroyed while thread is
    still running` -> `0xC0000409`, GUI paketi baştan düştü).
    """
    import subprocess
    import sys

    script = (
        "import gc\n"
        "from PySide6.QtWidgets import QApplication\n"
        "from sonar_analyzer.ui.main_window import MainWindow\n"
        "app = QApplication([])\n"
        "window = MainWindow()\n"
        "del window\n"
        "gc.collect()\n"
        "print('ok')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout

"""Yükleme ilerlemesi ve iptal eylemi — `F3-003`.

Kabul: iptal worker'a ulaşır; yarım kayıt açık dosya listesine girmez.
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.file_loader import (
    FileLoadResult,
    FileLoadService,
    LoaderCallable,
    default_loader,
)
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.status_bar import CANCELLED_TEXT, LOADING_TEXT, READY_TEXT

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


class ServiceFactory(Protocol):
    def __call__(self, *, loader: LoaderCallable | None = None) -> FileLoadService: ...


@pytest.fixture()
def service_factory() -> Iterator[ServiceFactory]:
    created: list[FileLoadService] = []

    def make(*, loader: LoaderCallable | None = None) -> FileLoadService:
        service = FileLoadService(loader=loader)
        created.append(service)
        return service

    yield make

    for service in created:
        service.shutdown()


def _copies(tmp_path: Path, count: int) -> list[Path]:
    paths: list[Path] = []
    for index in range(count):
        target = tmp_path / f"kayit{index}.bin"
        shutil.copyfile(VALID_FIXTURE, target)
        paths.append(target)
    return paths


# -- ilerleme ---------------------------------------------------------------


def test_progress_reports_each_completed_file(
    qtbot: QtBot, service_factory: ServiceFactory, tmp_path: Path
) -> None:
    service = service_factory()
    updates: list[tuple[int, int, int]] = []

    def record(rid: int, done: int, total: int) -> None:
        updates.append((rid, done, total))

    service.progress.connect(record)

    paths = _copies(tmp_path, 3)
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        request_id = service.submit(paths)

    assert updates[0] == (request_id, 0, 3)
    assert updates[-1] == (request_id, 3, 3)
    assert [done for _rid, done, _total in updates] == [0, 1, 2, 3]


def test_status_bar_shows_and_hides_the_load_indicator(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    window.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]

    assert not window.status.load_in_progress

    with qtbot.waitSignal(window.file_loader.request_finished, timeout=5000):
        window.action("action_open").trigger()
        assert window.status.load_in_progress
        assert window.status.field_value("status") == LOADING_TEXT

    assert not window.status.load_in_progress
    assert window.status.field_value("status") == READY_TEXT
    window.close()


# -- iptal worker'a ULASIR --------------------------------------------------


def test_cancel_reaches_the_worker_and_stops_remaining_files(
    qtbot: QtBot, service_factory: ServiceFactory, tmp_path: Path
) -> None:
    """Kabul kriteri (ilk yarı): iptal worker'a ulaşır."""
    opened: list[Path] = []

    def slow_loader(path: Path) -> FileRecordingRepository:
        opened.append(path)
        time.sleep(0.25)
        return default_loader(path)

    service = service_factory(loader=slow_loader)
    paths = _copies(tmp_path, 5)

    with qtbot.waitSignal(service.request_finished, timeout=10_000):
        request_id = service.submit(paths)
        qtbot.wait(300)  # ilk dosya islenirken
        service.cancel(request_id)

    # Worker sıradaki dosyaya geçmeden bayrağı gördü: 5 dosyanın hepsi
    # açılmadı.
    assert 0 < len(opened) < len(paths)
    assert service.is_cancelled(request_id)


def test_cancel_before_any_file_stops_the_whole_request(
    qtbot: QtBot, service_factory: ServiceFactory, tmp_path: Path
) -> None:
    opened: list[Path] = []

    def counting_loader(path: Path) -> FileRecordingRepository:
        opened.append(path)
        return default_loader(path)

    service = service_factory(loader=counting_loader)
    paths = _copies(tmp_path, 3)

    request_id = service.submit(paths)
    service.cancel(request_id)
    with qtbot.waitSignal(service.request_finished, timeout=5000):
        pass

    assert opened == []


def test_cancel_emits_a_signal_for_the_ui(qtbot: QtBot, service_factory: ServiceFactory) -> None:
    service = service_factory()
    cancelled: list[int] = []

    def record(request_id: int) -> None:
        cancelled.append(request_id)

    service.request_cancelled.connect(record)
    with qtbot.waitSignal(service.request_cancelled, timeout=1000):
        service.cancel(7)

    assert cancelled == [7]


def test_cancelling_an_unstarted_request_is_ignored(service_factory: ServiceFactory) -> None:
    service = service_factory()
    service.cancel(0)
    assert not service.is_cancelled(0)


# -- yarim kayit ACIK DOSYA LISTESINE GIRMEZ -------------------------------


def test_cancelled_partial_results_do_not_enter_the_open_file_list(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Kabul kriteri (ikinci yarı): yarım kayıt açık dosya listesine girmez."""

    def slow_loader(path: Path) -> FileRecordingRepository:
        time.sleep(0.25)
        return default_loader(path)

    window = MainWindow(loader=slow_loader)
    qtbot.addWidget(window)
    paths = _copies(tmp_path, 4)
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]

    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()
        qtbot.wait(300)
        window.cancel_active_load()

    # Istek iptal edildi: hicbir dosya acik listeye girmedi.
    assert window.loaded_results == ()
    assert window.failed_results == ()
    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Iptal edildi, alinmadi" in log_text
    window.close()


def test_cancelled_result_repository_is_closed_not_leaked(qtbot: QtBot, tmp_path: Path) -> None:
    """İptal anında açılmış olan snapshot serbest bırakılır (kaynak sızmaz)."""
    window = MainWindow()
    qtbot.addWidget(window)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)

    repository = default_loader(target)
    window.file_loader.cancel(1)
    window.active_load_request_id = 1
    result = FileLoadResult(request_id=1, path=target, repository=repository)

    # Worker'in yayacagi sinyalin aynisi: iptal edilmis istegin sonucu.
    window.file_loader.file_loaded.emit(result)

    assert window.loaded_results == ()
    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        repository.metadata()
    window.close()


def test_status_bar_reports_cancellation(qtbot: QtBot, tmp_path: Path) -> None:
    def slow_loader(path: Path) -> FileRecordingRepository:
        time.sleep(0.2)
        return default_loader(path)

    window = MainWindow(loader=slow_loader)
    qtbot.addWidget(window)
    paths = _copies(tmp_path, 3)
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]

    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()
        qtbot.wait(250)
        window.status.cancel_button.click()  # kullanicinin gercek eylemi

    assert window.status.field_value("status") == CANCELLED_TEXT
    assert not window.status.load_in_progress
    assert window.loaded_results == ()
    window.close()

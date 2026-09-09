"""Eski istek sonucunun görünümü ezmesini önleme — `F3-004`.

Kabul: hızlı iki açma isteğinde yalnız güncel sonuç uygulanır.
"""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.file_loader import FileLoadResult, default_loader
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(VALID_FIXTURE, target)
    return target


def _slow_loader(delay: float):
    def loader(path: Path) -> FileRecordingRepository:
        time.sleep(delay)
        return default_loader(path)

    return loader


# -- iki hizli istek: yalniz guncel olan uygulanir -------------------------


def test_only_the_newest_request_is_applied(qtbot: QtBot, tmp_path: Path) -> None:
    """Kabul kriteri birebir: hızlı iki açma isteğinde yalnız güncel sonuç uygulanır."""
    window = MainWindow(loader=_slow_loader(0.25))
    qtbot.addWidget(window)

    first = _copy(tmp_path, "eski.bin")
    second = _copy(tmp_path, "guncel.bin")

    window.file_open._dialog = lambda _p, _s: [str(first)]  # type: ignore[assignment]
    window.action("action_open").trigger()
    first_request_id = window.active_load_request_id

    # Ilk istek daha bitmeden ikincisi geliyor.
    window.file_open._dialog = lambda _p, _s: [str(second)]  # type: ignore[assignment]
    window.action("action_open").trigger()
    second_request_id = window.active_load_request_id

    assert second_request_id != first_request_id

    # Iki istegin de bitmesini bekle.
    deadline = time.monotonic() + 10
    while window.active_load_request_id and time.monotonic() < deadline:
        qtbot.wait(50)
    qtbot.wait(300)

    applied = [result.path for result in window.loaded_results]
    assert applied == [second]
    window.close()


def test_stale_result_arriving_late_is_ignored(qtbot: QtBot, tmp_path: Path) -> None:
    """Worker geriden bir sonuç yollarsa güncel görünüm bozulmaz."""
    window = MainWindow()
    qtbot.addWidget(window)

    target = _copy(tmp_path, "kayit.bin")
    window.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=5000):
        window.action("action_open").trigger()

    applied_before = window.loaded_results
    assert len(applied_before) == 1

    # Artik aktif istek yok; eski kimlikli bir sonuc geliyor.
    stale_repository = default_loader(target)
    stale = FileLoadResult(request_id=99, path=target, repository=stale_repository)
    window.file_loader.file_loaded.emit(stale)

    assert window.loaded_results == applied_before
    assert "Eskimis sonuc yok sayildi" in "\n".join(window.bottom_dock.log_lines())
    window.close()


def test_stale_result_repository_is_closed_not_leaked(qtbot: QtBot, tmp_path: Path) -> None:
    """Uygulanmayan sonucun snapshot'ı bırakılır — açık kaynak sızmaz."""
    window = MainWindow()
    qtbot.addWidget(window)
    target = _copy(tmp_path, "kayit.bin")

    stale_repository = default_loader(target)
    window.active_load_request_id = 5
    window.file_loader.file_loaded.emit(
        FileLoadResult(request_id=4, path=target, repository=stale_repository)
    )

    assert window.loaded_results == ()
    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        stale_repository.metadata()
    window.close()


def test_superseded_request_is_cancelled_so_the_worker_stops(qtbot: QtBot, tmp_path: Path) -> None:
    """Eskiyen istek iptal edilir; worker boşuna dosya açmaya devam etmez."""
    opened: list[Path] = []
    lock = threading.Lock()

    def counting_loader(path: Path) -> FileRecordingRepository:
        with lock:
            opened.append(path)
        time.sleep(0.2)
        return default_loader(path)

    window = MainWindow(loader=counting_loader)
    qtbot.addWidget(window)

    many = [_copy(tmp_path, f"eski{i}.bin") for i in range(5)]
    fresh = _copy(tmp_path, "guncel.bin")

    window.file_open._dialog = lambda _p, _s: [str(path) for path in many]  # type: ignore[assignment]
    window.action("action_open").trigger()
    first_id = window.active_load_request_id
    qtbot.wait(250)

    window.file_open._dialog = lambda _p, _s: [str(fresh)]  # type: ignore[assignment]
    window.action("action_open").trigger()

    assert window.file_loader.is_cancelled(first_id)

    deadline = time.monotonic() + 10
    while window.active_load_request_id and time.monotonic() < deadline:
        qtbot.wait(50)
    qtbot.wait(200)

    with lock:
        opened_from_first = [path for path in opened if path in many]
    assert len(opened_from_first) < len(many)
    assert [result.path for result in window.loaded_results] == [fresh]
    window.close()


def test_superseding_discards_results_already_applied_from_the_old_request(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Eski istekten uygulanmış sonuçlar da geri alınır (görünüm karışmaz)."""
    window = MainWindow(loader=_slow_loader(0.15))
    qtbot.addWidget(window)

    first_batch = [_copy(tmp_path, f"eski{i}.bin") for i in range(3)]
    fresh = _copy(tmp_path, "guncel.bin")

    window.file_open._dialog = lambda _p, _s: [str(path) for path in first_batch]  # type: ignore[assignment]
    window.action("action_open").trigger()
    qtbot.wait(250)  # en az bir dosya tamamlansin
    assert len(window.loaded_results) >= 1

    window.file_open._dialog = lambda _p, _s: [str(fresh)]  # type: ignore[assignment]
    window.action("action_open").trigger()

    # Eskiyen istegin sonuclari hemen geri alindi.
    assert window.loaded_results == ()
    assert "Onceki yukleme istegi birakildi" in "\n".join(window.bottom_dock.log_lines())

    deadline = time.monotonic() + 10
    while window.active_load_request_id and time.monotonic() < deadline:
        qtbot.wait(50)
    qtbot.wait(200)
    assert [result.path for result in window.loaded_results] == [fresh]
    window.close()


def test_stale_request_finish_does_not_hide_the_active_progress(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Eskiyen istek bitince güncel isteğin ilerleme göstergesi kapanmaz."""
    # Ikinci istek uzun surer; birincisi (iptal edildigi icin) hemen biter.
    window = MainWindow(loader=_slow_loader(0.6))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    first = _copy(tmp_path, "eski.bin")
    second = _copy(tmp_path, "guncel.bin")

    window.file_open._dialog = lambda _p, _s: [str(first)]  # type: ignore[assignment]
    window.action("action_open").trigger()
    first_id = window.active_load_request_id
    window.file_open._dialog = lambda _p, _s: [str(second)]  # type: ignore[assignment]
    window.action("action_open").trigger()
    second_id = window.active_load_request_id

    # Eskiyen istek bitene kadar bekle (iptal edildigi icin hizli biter).
    finished: list[int] = []
    window.file_loader.request_finished.connect(finished.append)
    deadline = time.monotonic() + 5
    while first_id not in finished and time.monotonic() < deadline:
        qtbot.wait(20)
    assert first_id in finished
    assert second_id not in finished  # guncel istek hala suruyor

    # Eskiyen istek bitti ama gosterge guncel istek icin acik kalmali.
    assert window.status.load_in_progress

    deadline = time.monotonic() + 10
    while window.active_load_request_id and time.monotonic() < deadline:
        qtbot.wait(50)
    assert not window.status.load_in_progress
    window.close()

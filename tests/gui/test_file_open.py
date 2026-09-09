"""Tekli ve çoklu dosya açma seçicisi — `F3-001`.

Kabul: iptal mevcut oturumu korur; seçim dosya yükleme talebi üretir.

Yerel dosya diyaloğu offscreen Qt'de sürücülenemediği için `FileOpenController`
diyalog çağrısını dışarıdan alabiliyor; testler o seam'i kullanır.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.file_open import FileOpenController
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def _stub_dialog(paths: Sequence[str]) -> object:
    """Verilen yolları döndüren diyalog yerine geçen çağrı."""
    calls: list[str] = []

    def dialog(_parent: QWidget | None, start_directory: str) -> Sequence[str]:
        calls.append(start_directory)
        return paths

    dialog.calls = calls  # type: ignore[attr-defined]
    return dialog


# -- secim: yukleme talebi uretilir ---------------------------------------


def test_single_selection_emits_one_path(qtbot: QtBot, tmp_path: Path) -> None:
    """Kabul kriteri: seçim dosya yükleme talebi üretir."""
    target = tmp_path / "kayit.bin"
    target.write_bytes(b"x")
    controller = FileOpenController(dialog=_stub_dialog([str(target)]))  # type: ignore[arg-type]

    with qtbot.waitSignal(controller.load_requested, timeout=1000) as blocker:
        selected = controller.request_open()

    assert selected == (target,)
    emitted: list[str] = blocker.args[0]  # type: ignore[index]
    assert emitted == [str(target)]


def test_multi_selection_emits_all_paths_in_order(qtbot: QtBot, tmp_path: Path) -> None:
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    for path in (first, second):
        path.write_bytes(b"x")
    controller = FileOpenController(
        dialog=_stub_dialog([str(first), str(second)])  # type: ignore[arg-type]
    )

    with qtbot.waitSignal(controller.load_requested, timeout=1000) as blocker:
        selected = controller.request_open()

    assert selected == (first, second)
    emitted: list[str] = blocker.args[0]  # type: ignore[index]
    assert emitted == [str(first), str(second)]


def test_duplicate_selection_is_deduplicated_preserving_order(tmp_path: Path) -> None:
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    controller = FileOpenController(
        dialog=_stub_dialog([str(first), str(second), str(first)])  # type: ignore[arg-type]
    )

    assert controller.request_open() == (first, second)


# -- iptal: mevcut oturum korunur ------------------------------------------


def test_cancel_emits_no_signal_and_returns_empty(qtbot: QtBot) -> None:
    """Kabul kriteri: iptal talep üretmez — 'boş liste ile talep' de değil."""
    controller = FileOpenController(dialog=_stub_dialog([]))  # type: ignore[arg-type]

    with qtbot.assertNotEmitted(controller.load_requested):
        assert controller.request_open() == ()


def test_cancel_does_not_change_the_remembered_directory(tmp_path: Path) -> None:
    controller = FileOpenController(dialog=_stub_dialog([]))  # type: ignore[arg-type]
    controller.set_last_directory(str(tmp_path))

    controller.request_open()

    assert controller.last_directory == str(tmp_path)


def test_successful_selection_remembers_the_directory(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    controller = FileOpenController(dialog=_stub_dialog([str(target)]))  # type: ignore[arg-type]

    controller.request_open()

    assert controller.last_directory == str(tmp_path)


def test_remembered_directory_is_passed_back_to_the_dialog(tmp_path: Path) -> None:
    dialog = _stub_dialog([str(tmp_path / "kayit.bin")])
    controller = FileOpenController(dialog=dialog)  # type: ignore[arg-type]
    controller.set_last_directory(str(tmp_path))

    controller.request_open()

    assert dialog.calls == [str(tmp_path)]  # type: ignore[attr-defined]


# -- ana pencere baglantisi ------------------------------------------------


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_open_action_is_wired_to_the_picker(window: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    window.file_open._dialog = _stub_dialog([str(target)])  # type: ignore[assignment]

    window.action("action_open").trigger()

    assert window.pending_load_paths == (target,)


def test_cancel_preserves_the_open_session(window: MainWindow) -> None:
    """Kabul kriteri: iptal mevcut oturumu korur."""
    window.set_repository(MockRecordingRepository())
    opened_channel = window.left_dock.visible_channel_ids()[0]
    window.open_channel(opened_channel)
    before_title = window.windowTitle()
    before_channels = window.left_dock.visible_channel_ids()
    before_center_shows_plot = window.center_shows_plot
    before_summary = window.left_dock.summary_value("File")

    window.file_open._dialog = _stub_dialog([])  # type: ignore[assignment]
    window.action("action_open").trigger()

    assert window.pending_load_paths == ()
    assert window.windowTitle() == before_title
    assert window.left_dock.visible_channel_ids() == before_channels
    assert window.center_shows_plot == before_center_shows_plot
    assert window.left_dock.summary_value("File") == before_summary


def test_selection_is_logged_for_the_operator(window: MainWindow, tmp_path: Path) -> None:
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    window.file_open._dialog = _stub_dialog([str(first), str(second)])  # type: ignore[assignment]

    window.action("action_open").trigger()

    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Yukleme talebi: 2 dosya" in log_text
    assert "a.bin" in log_text
    assert "b.bin" in log_text


def test_empty_state_open_button_reaches_the_picker(window: MainWindow, tmp_path: Path) -> None:
    """Boş workspace düğmesi de aynı seçiciyi kullanır (F1-033 bağlantısı)."""
    target = tmp_path / "kayit.bin"
    window.file_open._dialog = _stub_dialog([str(target)])  # type: ignore[assignment]

    window.empty_state.open_requested.emit()

    assert window.pending_load_paths == (target,)


def test_data_explorer_open_button_reaches_the_picker(window: MainWindow, tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    window.file_open._dialog = _stub_dialog([str(target)])  # type: ignore[assignment]

    window.left_dock.open_requested.emit()

    assert window.pending_load_paths == (target,)

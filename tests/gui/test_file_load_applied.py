"""Dosya yükleme sonucunu repository ve ekrana bağlama — `F3-005`.

Kabul: açılan dosyanın metadata ve kanalları görünür.

Bu, uygulamanın gerçek bir `.bin` kaydını **ekranda** ilk gösterdiği yer:
seçici (`F3-001`) → worker (`F3-002`) → repository (`F2-033`) → paneller.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"

#: docs/format/channel-map.md §2 — acilan dosyanin kanallari.
EXPECTED_CHANNEL_PATHS = (
    "Sensors/Pressure",
    "Sensors/Temperature",
    "Sensors/Accelerometer/X",
    "Sensors/Accelerometer/Y",
    "Sensors/Accelerometer/Z",
    "Acoustic/Hydrophone 1",
    "Navigation/Depth",
    "Vehicle/Voltage",
)


def _open_in_window(qtbot: QtBot, window: MainWindow, paths: list[Path]) -> None:
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()


@pytest.fixture()
def window(qtbot: QtBot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(VALID_FIXTURE, target)
    return target


# -- metadata gorunur ------------------------------------------------------


def test_opened_file_metadata_is_visible(qtbot: QtBot, window: MainWindow, tmp_path: Path) -> None:
    """Kabul kriteri (ilk yarı): açılan dosyanın metadata'sı görünür."""
    target = _copy(tmp_path, "kayit.bin")

    _open_in_window(qtbot, window, [target])

    summary_file = window.left_dock.summary_value("File")
    assert "kayit.bin" in summary_file
    assert window.left_dock.summary_value("Size") != "—"
    assert window.left_dock.summary_value("Start") != "—"
    assert window.left_dock.summary_value("Duration") != "—"
    window.close()


def test_opened_file_replaces_the_empty_state(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    target = _copy(tmp_path, "kayit.bin")
    _open_in_window(qtbot, window, [target])

    assert window.left_dock.visible_channel_ids()
    window.close()


# -- kanallar gorunur ------------------------------------------------------


def test_opened_file_channels_are_visible_in_the_tree(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kabul kriteri (ikinci yarı): açılan dosyanın kanalları görünür."""
    target = _copy(tmp_path, "kayit.bin")

    _open_in_window(qtbot, window, [target])

    channel_ids = window.left_dock.visible_channel_ids()
    assert len(channel_ids) == 8
    assert channel_ids == [f"ch{index}" for index in range(8)]
    window.close()


def test_opened_channel_can_be_plotted_with_real_data(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Kanal gerçek `.bin` verisiyle çizilebiliyor — zincirin ucu."""
    target = _copy(tmp_path, "kayit.bin")
    _open_in_window(qtbot, window, [target])

    window.open_channel("ch0")

    assert window.center_shows_plot
    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "cizildi (8 ornek)" in log_text
    window.close()


def test_events_and_bit_results_reach_the_panels(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Dosyanın olayları ve BIT sonuçları da panellere dağıtılır."""
    target = _copy(tmp_path, "kayit.bin")

    _open_in_window(qtbot, window, [target])

    # fixture-valid-8records.md §5: 1 BIT arizasi ve 1 TX araligi var;
    # olay tablosu bos kalmamali.
    assert window.bottom_dock.event_row_count() > 0
    window.close()


# -- coklu secim -----------------------------------------------------------


def test_first_selected_file_becomes_the_active_view(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Çok dosyalı seçimde ilk kayıt görünür, diğerleri açık kalır."""
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")

    _open_in_window(qtbot, window, [first, second])

    assert "birinci.bin" in window.left_dock.summary_value("File")
    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Goruntulenen kayit: birinci.bin" in log_text
    assert "Ayrica acik: ikinci.bin" in log_text
    window.close()


# -- kaynak hijyeni --------------------------------------------------------


def test_previous_recording_is_closed_when_a_new_one_is_opened(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Yeni kayıt açılınca öncekinin snapshot'ı bırakılır."""
    first = _copy(tmp_path, "birinci.bin")
    second = _copy(tmp_path, "ikinci.bin")

    _open_in_window(qtbot, window, [first])
    first_repository = window.loaded_results[0].repository
    assert first_repository is not None
    assert first_repository.metadata().record_count == 8

    _open_in_window(qtbot, window, [second])

    with pytest.raises(RuntimeError, match="dosyasi acilmali"):
        first_repository.metadata()
    assert "ikinci.bin" in window.left_dock.summary_value("File")
    window.close()


def test_failed_only_request_leaves_the_view_untouched(
    qtbot: QtBot, window: MainWindow, tmp_path: Path
) -> None:
    """Hiçbir dosya açılamazsa mevcut görünüm bozulmaz."""
    good = _copy(tmp_path, "iyi.bin")
    _open_in_window(qtbot, window, [good])
    before_file = window.left_dock.summary_value("File")
    before_channels = window.left_dock.visible_channel_ids()

    bad = tmp_path / "bozuk.bin"
    bad.write_bytes(b"gecersiz")
    _open_in_window(qtbot, window, [bad])

    assert window.left_dock.summary_value("File") == before_file
    assert window.left_dock.visible_channel_ids() == before_channels
    assert "Acilabilen dosya yok" in "\n".join(window.bottom_dock.log_lines())
    window.close()

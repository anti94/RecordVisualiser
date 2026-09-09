"""Çift tıkla kanalı grafiğe ekleme — `F3-013`.

Kabul: gerçek dosyadan seçilen kanal doğru zaman ekseninde görünür.

Zincir `F3-001`'den beri parça parça kuruldu (seçici → worker → repository
→ ekran, `F3-005`; ağaç/kategori, `F3-009`–`F3-012`); bu dosya onu **uçtan
uca** ve **sayısal olarak** `docs/format/fixture-valid-8records.md` §1'deki
formüllere karşı doğrular — yalnız "bir şey çizildi" değil, doğru zaman
ekseninde doğru değerler.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
VALID_FIXTURE = FIXTURES_DIR / "valid_8records.bin"
PERIOD_S = 0.125

#: docs/format/fixture-valid-8records.md §1 — CH0 (Pressure) formülü: 100.0 + 0.5*n.
EXPECTED_CH0_VALUES = [100.0, 100.5, 101.0, 101.5, 102.0, 102.5, 103.0, 103.5]
#: CH5 (Hydrophone) formülü: +2.5 (çift n), -2.5 (tek n).
EXPECTED_CH5_VALUES = [2.5, -2.5, 2.5, -2.5, 2.5, -2.5, 2.5, -2.5]
EXPECTED_TIMES_S = [round(n * PERIOD_S, 3) for n in range(8)]


@pytest.fixture()
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    win = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(win)
    target = tmp_path / "kayit.bin"
    shutil.copyfile(VALID_FIXTURE, target)
    win.file_open._dialog = lambda _p, _s: [str(target)]  # type: ignore[assignment]
    with qtbot.waitSignal(win.file_loader.request_finished, timeout=10_000):
        win.action("action_open").trigger()
    return win


# -- dogru zaman ekseni: sayisal dogrulama ----------------------------------


def test_double_click_in_channels_tab_plots_the_correct_time_axis(
    window: MainWindow,
) -> None:
    """Kabul kriteri birebir: gerçek dosyadan seçilen kanal doğru zaman ekseninde görünür."""
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    assert window.center_shows_plot
    x, y = window.plot_panel.curve_data()
    assert [round(float(value), 3) for value in x] == EXPECTED_TIMES_S
    assert y.tolist() == EXPECTED_CH0_VALUES


def test_double_click_in_data_tree_tab_plots_the_same_correct_axis(
    window: MainWindow,
) -> None:
    """Data Tree sekmesindeki çift tıklama da aynı doğru sonucu üretir (F3-009)."""
    recording_item = window.left_dock.data_tree.topLevelItem(0)
    assert recording_item is not None
    device_item = recording_item.child(0)
    assert device_item is not None
    group_item = device_item.child(0)
    assert group_item is not None
    window.left_dock.data_tree.expandItem(group_item)  # F3-010: yapraklar lazy
    leaf = group_item.child(0)
    assert leaf is not None

    window.left_dock.data_tree.itemDoubleClicked.emit(leaf, 0)

    x, y = window.plot_panel.curve_data()
    assert [round(float(value), 3) for value in x] == EXPECTED_TIMES_S
    assert y.tolist() == EXPECTED_CH0_VALUES


def test_a_different_channel_produces_its_own_correct_values(window: MainWindow) -> None:
    """CH0 dışındaki bir kanal (Hydrophone, alternating ±2.5) da doğru çizilir."""
    leaf = window.left_dock.item_for_channel("ch5")
    assert leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    _x, y = window.plot_panel.curve_data()
    assert y.tolist() == EXPECTED_CH5_VALUES


def test_time_axis_starts_at_zero_relative_to_the_recording(window: MainWindow) -> None:
    """Zaman ekseni mutlak epoch değil, kayıt başına göre görecelidir (F1-031)."""
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    x, _y = window.plot_panel.curve_data()
    assert float(x[0]) == 0.0


# -- gorunum: baslik, birim, log ---------------------------------------


def test_plot_title_and_unit_match_the_real_channel(window: MainWindow) -> None:
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    assert window.plot_panel.title_text() == "Pressure [bar]"
    assert "Pressure (bar)" in window.plot_panel.axis_label("left")


def test_double_click_switches_center_from_empty_state_to_plot(window: MainWindow) -> None:
    assert not window.center_shows_plot  # dosya acildi ama henuz kanal secilmedi

    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None
    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    assert window.center_shows_plot


def test_double_click_logs_the_real_sample_count(window: MainWindow) -> None:
    leaf = window.left_dock.item_for_channel("ch0")
    assert leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(leaf, 0)

    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Pressure [bar] cizildi (8 ornek)" in log_text


def test_double_clicking_a_second_channel_replaces_the_first(window: MainWindow) -> None:
    """Sırayla iki farklı kanala çift tıklamak grafiği doğru şekilde günceller."""
    first_leaf = window.left_dock.item_for_channel("ch0")
    second_leaf = window.left_dock.item_for_channel("ch6")
    assert first_leaf is not None
    assert second_leaf is not None

    window.left_dock.tree.itemDoubleClicked.emit(first_leaf, 0)
    window.left_dock.tree.itemDoubleClicked.emit(second_leaf, 0)

    assert window.plot_panel.title_text() == "Depth [m]"
    _x, y = window.plot_panel.curve_data()
    # docs/format/fixture-valid-8records.md §1: CH6 = 10.0 + 0.25*n.
    assert y.tolist() == [10.0, 10.25, 10.5, 10.75, 11.0, 11.25, 11.5, 11.75]

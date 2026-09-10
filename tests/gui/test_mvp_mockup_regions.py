"""MVP ekran görüntüsü ↔ ana mockup karşılaştırması — `F3-079`.

Kabul: referans mockup'ın **dokuz bölgesi** ve üç sütunlu + alt şerit
yerleşimi eşleşir; FFT/spektrogram işlevleri **v2 olarak pasiftir**
(açıklamalı).

`docs/ui/layout-map.md` §2 tablosu bu testin sözleşmesidir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.main_window import DEFAULT_WINDOW_SIZE, MainWindow
from sonar_analyzer.ui.view_tab_bar import ENABLED_TABS, TAB_TITLES

pytestmark = pytest.mark.gui

#: `docs/ui/layout-map.md` §2: dokuz bölge → (etiket, alan).
#: alan ∈ {"left", "center", "right", "bottom"}
NINE_REGIONS: tuple[tuple[int, str, str], ...] = (
    (1, "Dosya ve Veri Yönetimi", "left"),
    (2, "Hızlı Araçlar", "center"),
    (3, "Görselleştirme Alanı", "center"),
    (4, "Donanım/BIT Durumu", "right"),
    (5, "Hesaplamalar ve Analiz", "right"),
    (6, "Çoklu Görünüm", "center"),
    (7, "Zaman Kontrolü", "bottom"),
    (8, "Log / Mesajlar", "bottom"),
    (9, "Ayarlar ve Dışa Aktarma", "right"),
)


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(*DEFAULT_WINDOW_SIZE)
    window.show()
    qtbot.waitExposed(window)
    window.apply_default_layout()
    # Bölge 3 (Görselleştirme Alanı) yalnız bir kanal çizilince öne gelir.
    window.set_repository(MockRecordingRepository(duration_s=6.0))
    window.open_channel("ch0")
    # Kanal açılışı sağ sütunda Inspector sekmesine geçer; mockup ise
    # BIT/Analysis/Export kartlarını gösterir — Overview'e geri dön.
    window.right_dock.tabs.setCurrentIndex(0)
    return window


def _region_widget(win: MainWindow, number: int) -> QWidget:
    return {
        1: win.left_dock,
        2: win.plot_tool_bar,
        3: win.dashboard,
        4: win.right_dock.bit_status,
        5: win.right_dock.cards["card_analysis_tools"],
        6: win.view_tabs,
        7: win.playback_dock,
        8: win.bottom_dock.log,
        9: win.right_dock.data_export,
    }[number]


def _area_of(win: MainWindow, widget: QWidget) -> str:
    centre: QPoint = widget.mapTo(win, widget.rect().center())
    mid_x, mid_y = win.width() / 2, win.height() / 2
    # Önce yatay sütun (sol / sağ), sonra dikey (merkez / alt şerit).
    if centre.x() < mid_x * 0.55:
        return "left"
    if centre.x() > mid_x * 1.45:
        return "right"
    return "bottom" if centre.y() > mid_y * 1.25 else "center"


def test_all_nine_regions_are_present_and_visible(win: MainWindow) -> None:
    for number, label, _area in NINE_REGIONS:
        widget = _region_widget(win, number)
        assert widget is not None, f"bölge {number} ({label}) yok"
        assert widget.isVisibleTo(win), f"bölge {number} ({label}) görünmüyor"


@pytest.mark.parametrize(("number", "label", "expected_area"), NINE_REGIONS)
def test_region_sits_in_its_mockup_area(
    win: MainWindow, number: int, label: str, expected_area: str
) -> None:
    widget = _region_widget(win, number)
    assert _area_of(win, widget) == expected_area, f"bölge {number} ({label}) yanlış alanda"


def test_three_column_plus_bottom_layout(win: MainWindow) -> None:
    left, center, right = win.column_widths()
    assert left < center and right < center  # merkez en geniş
    # alt şerit: playback üstte, log altta.
    assert win.playback_dock.isVisibleTo(win)
    assert win.bottom_dock.isVisibleTo(win)
    assert win.playback_dock.y() < win.bottom_dock.y()


def test_view_tab_bar_has_the_eight_mockup_tabs(win: MainWindow) -> None:
    assert win.view_tabs.tab_titles() == list(TAB_TITLES)
    assert len(TAB_TITLES) == 8


# -- v2 işlevleri pasif ve açıklamalı -----------------------


def test_remaining_v2_view_tabs_are_disabled_with_a_reason(win: MainWindow) -> None:
    # `F4-045` Spectrum, `F4-051` Spectrogram etkinleşti; kalanlar hâlâ v2.
    v2_tabs = [t for t in TAB_TITLES if t not in ENABLED_TABS]
    assert {"Cross Analysis", "3D View", "Report"} <= set(v2_tabs)
    assert "Spectrum" not in v2_tabs
    assert "Spectrogram" not in v2_tabs
    for index, title in enumerate(win.view_tabs.tab_titles()):
        if title in v2_tabs:
            assert not win.view_tabs.isTabEnabled(index), f"{title} pasif olmalı"
            assert win.view_tabs.tabToolTip(index) == NOT_YET_AVAILABLE


def test_fft_and_spectrogram_menu_actions_are_disabled_with_a_reason(win: MainWindow) -> None:
    for name in ("action_fft", "action_spectrogram"):
        action = win.action(name)
        assert not action.isEnabled(), f"{name} pasif olmalı"
        assert action.toolTip() == NOT_YET_AVAILABLE


def test_dashboard_analysis_cells_are_real_panels(win: MainWindow) -> None:
    # `F4-042` FFT, `F4-048` spektrogram: iki hücre de artık gerçek panel.
    assert win.dashboard.findChild(QWidget, "panel_spectrum") is not None
    assert win.dashboard.findChild(QWidget, "panel_spectrogram") is not None


def test_analysis_tools_v2_tabs_carry_the_note(win: MainWindow) -> None:
    card = win.right_dock.cards["card_analysis_tools"]
    notes = [lbl.text() for lbl in card.findChildren(QLabel) if NOT_YET_AVAILABLE in lbl.text()]
    # FFT ve Statistics sekmeleri v2 notu taşır (Custom `F4-006` ile aktif).
    assert len(notes) >= 2

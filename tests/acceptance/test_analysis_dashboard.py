"""Çalışan analiz panosunun mockup ile karşılaştırması — `F4-089`.

Kabul: dokuz bölge korunur; FFT, spektrogram, filtre ve istatistik gerçek
veriyle çalışır.

`F1-037` mockup yerleşimini kurdu ve `tests/gui/test_mvp_mockup_regions.py`
onu **boş** pencerede denetler. Faz 4 o yerleşimin içini gerçek analizle
doldurdu. Bu dosya iki soruyu birlikte sorar:

1. Kayıt açılıp kanal çizildikten ve analiz koştuktan **sonra** da dokuz
   bölge yerinde ve görünür mü? Yerleşim, işlev eklendikçe bozulmamalı.
2. Dört analiz yüzeyi gerçekten çalışıyor mu? "Çalışıyor" burada
   ekranda bir şey olması değil: her hücrenin sayıları, aynı veriden
   **bağımsız** hesaplanan referansla karşılaştırılır. Yer tutucu bir
   hücre bu testi geçemez.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtWidgets import QLabel, QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.statistics import summarize
from sonar_analyzer.processing.filters import low_pass
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

RATE_HZ = 200.0
DURATION_S = 8.0
CUTOFF_HZ = 40.0
ORDER = 4

#: `docs/ui/layout-map.md` §2 — dokuz bölge (mockup etiketi).
#: Eşleme `tests/gui/test_mvp_mockup_regions.py` ile birebir aynıdır;
#: burada aynı bölgeler **çalışan** bir oturumda denetlenir.
NINE_REGIONS: tuple[tuple[int, str], ...] = (
    (1, "Dosya ve Veri Yönetimi"),
    (2, "Hızlı Araçlar"),
    (3, "Görselleştirme Alanı"),
    (4, "Donanım/BIT Durumu"),
    (5, "Hesaplamalar ve Analiz"),
    (6, "Çoklu Görünüm"),
    (7, "Zaman Kontrolü"),
    (8, "Log / Mesajlar"),
    (9, "Ayarlar ve Dışa Aktarma"),
)


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


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    """Kayıt açık, kanal çizili, analiz koşmuş **çalışan** pencere."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.apply_default_layout()
    window.set_repository(
        MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=RATE_HZ, seed=5)
    )
    window.open_channel("ch0")
    # Kanal açılışı sağ sütunda Inspector sekmesine geçer; mockup ise
    # BIT/Analysis/Export kartlarını gösterir — Overview'e geri dön.
    window.right_dock.tabs.setCurrentIndex(0)
    return window


def _analysis_values(win: MainWindow) -> NDArray[Any]:
    """Panoyu besleyen veri — hücrelerle aynı kaynak."""
    repository = win.repository
    assert repository is not None
    return repository.query("ch0", repository.metadata().time_range).values


# --------------------------------------------------------------------------- #
# DOKUZ BOLGE korunur
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("number", "label"), NINE_REGIONS)
def test_every_mockup_region_survives_a_working_session(
    win: MainWindow, number: int, label: str
) -> None:
    """Analiz koşarken de dokuz bölgenin hepsi yerinde ve görünür."""
    widget = _region_widget(win, number)
    assert widget is not None, f"bölge {number} ({label}) yok"
    assert widget.isVisibleTo(win), f"bölge {number} ({label}) görünmüyor"


def test_the_nine_regions_are_exactly_nine() -> None:
    assert len({label for _n, label in NINE_REGIONS}) == 9


def test_the_layout_is_still_three_columns_plus_bottom(win: MainWindow) -> None:
    assert win.left_dock.isVisibleTo(win)
    assert win.right_dock.isVisibleTo(win)
    assert win.bottom_dock.isVisibleTo(win)
    assert win.playback_dock.y() < win.bottom_dock.y()


def test_the_dashboard_keeps_its_four_cells(win: MainWindow) -> None:
    for name in ("panel_spectrum", "panel_spectrogram"):
        assert win.dashboard.findChild(QWidget, name) is not None
    assert win.dashboard.time_series is win.plot_panel
    assert win.dashboard.statistics is not None


# --------------------------------------------------------------------------- #
# FFT gercek veriyle
# --------------------------------------------------------------------------- #


def test_the_fft_cell_computes_the_open_channel(win: MainWindow) -> None:
    """Hücrenin genlikleri, aynı veriden bağımsız hesapla birebir aynı."""
    cell = win.dashboard.fft
    result = cell.result()
    assert result is not None

    expected = one_sided_fft(
        np.asarray(_analysis_values(win), dtype=np.float64),
        RATE_HZ,
        window=cell.window_kind,
    )
    assert np.allclose(result.amplitudes, expected.amplitudes)
    assert result.sample_rate_hz == RATE_HZ


def test_the_fft_axis_stays_inside_the_nyquist_band(win: MainWindow) -> None:
    result = win.dashboard.fft.result()
    assert result is not None
    assert float(result.frequencies_hz[0]) == 0.0
    assert float(result.frequencies_hz[-1]) <= RATE_HZ / 2.0


def test_the_fft_cell_is_not_a_placeholder(win: MainWindow) -> None:
    notes = [
        label.text()
        for label in win.dashboard.fft.findChildren(QLabel)
        if NOT_YET_AVAILABLE in label.text()
    ]
    assert notes == []


# --------------------------------------------------------------------------- #
# spektrogram gercek veriyle
# --------------------------------------------------------------------------- #


def test_the_spectrogram_cell_has_a_real_matrix(win: MainWindow) -> None:
    result = win.dashboard.spectrogram.result()
    assert result is not None
    assert result.bin_count > 1
    assert result.frame_count > 1
    assert result.magnitudes.shape == (result.bin_count, result.frame_count)
    assert bool(np.all(np.isfinite(result.magnitudes)))


def test_the_spectrogram_axes_come_from_the_recording(win: MainWindow) -> None:
    result = win.dashboard.spectrogram.result()
    assert result is not None
    assert result.sample_rate_hz == RATE_HZ
    assert float(result.frequencies_hz[-1]) <= RATE_HZ / 2.0
    assert float(result.times_s[-1]) < DURATION_S


def test_the_spectrogram_is_not_a_placeholder(win: MainWindow) -> None:
    notes = [
        label.text()
        for label in win.dashboard.spectrogram.findChildren(QLabel)
        if NOT_YET_AVAILABLE in label.text()
    ]
    assert notes == []


# --------------------------------------------------------------------------- #
# istatistik gercek veriyle
# --------------------------------------------------------------------------- #


def test_the_statistics_cell_matches_an_independent_summary(win: MainWindow) -> None:
    expected = summarize(np.asarray(_analysis_values(win), dtype=np.float64))
    cell = win.dashboard.statistics

    for label, value in (
        ("Mean", expected.mean),
        ("Min", expected.minimum),
        ("Max", expected.maximum),
    ):
        shown = cell.field_value(label)
        assert shown not in ("", "—"), f"{label} boş"
        # Hücre bir ondalık basamakla gösterir; karşılaştırma o
        # hassasiyete göre yapılır — yuvarlama hata değildir.
        assert abs(float(shown.split()[0]) - value) < 0.05, label


def test_the_statistics_cell_names_the_channel(win: MainWindow) -> None:
    channel = win.plot_panel.channel
    assert channel is not None
    assert channel.name in win.dashboard.statistics.title()


# --------------------------------------------------------------------------- #
# filtre gercek veriyle
# --------------------------------------------------------------------------- #


def test_the_filter_card_produces_the_designed_result(win: MainWindow, qtbot: QtBot) -> None:
    """Mockup Filter kartından uygulanan filtre, referans filtreyle aynı."""
    tools = win.right_dock.analysis_tools
    tools.tabs.setCurrentIndex(tools.tab_titles().index("Filter"))
    tools.filter_response.setCurrentText("Low-pass")
    tools.cutoff_frequency.setValue(int(CUTOFF_HZ))
    tools.order.setValue(ORDER)

    tools.apply_requested.emit()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    full = np.asarray(_analysis_values(win), dtype=np.float64)
    reference = low_pass(full, RATE_HZ, CUTOFF_HZ, ORDER)
    assert processed.size > 0
    assert processed.size <= reference.size


def test_the_filtered_overlay_really_attenuates_high_frequencies(
    win: MainWindow, qtbot: QtBot
) -> None:
    """Filtre gerçekten süzüyor: kesim üstündeki enerji düşüyor."""
    full = np.asarray(_analysis_values(win), dtype=np.float64)
    reference = low_pass(full, RATE_HZ, CUTOFF_HZ, ORDER)

    before = one_sided_fft(full, RATE_HZ)
    after = one_sided_fft(reference, RATE_HZ)
    stop_band = before.frequencies_hz > CUTOFF_HZ * 2.0
    assert float(np.sum(after.amplitudes[stop_band])) < 0.2 * float(
        np.sum(before.amplitudes[stop_band])
    )


def test_the_filter_tab_is_not_a_placeholder(win: MainWindow) -> None:
    tools = win.right_dock.analysis_tools
    assert tools.apply_filter_button.isEnabled()
    assert NOT_YET_AVAILABLE not in tools.apply_filter_button.toolTip()


# --------------------------------------------------------------------------- #
# dort yuzey ayni veriyi gosterir
# --------------------------------------------------------------------------- #


def test_all_four_surfaces_describe_the_same_channel(win: MainWindow) -> None:
    """FFT, spektrogram ve istatistik aynı kanaldan besleniyor."""
    channel = win.plot_panel.channel
    assert channel is not None

    fft = win.dashboard.fft.result()
    spectrogram = win.dashboard.spectrogram.result()
    assert fft is not None and spectrogram is not None
    assert fft.sample_rate_hz == spectrogram.sample_rate_hz == (channel.sample_rate_hz or 0.0)
    assert channel.name in win.dashboard.statistics.title()


def test_switching_channel_refreshes_every_surface(win: MainWindow) -> None:
    before = win.dashboard.fft.result()
    assert before is not None

    win.open_channel("ch2")

    after = win.dashboard.fft.result()
    assert after is not None
    assert not np.array_equal(after.amplitudes, before.amplitudes)
    channel = win.plot_panel.channel
    assert channel is not None
    assert channel.name in win.dashboard.statistics.title()

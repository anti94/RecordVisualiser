"""Waterfall görünümü — `F4-051`.

Kabul: zaman dilimleri doğru sırayla çizilir; birimler açıktır.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.spectrum import amplitude_to_db
from sonar_analyzer.analysis.stft import stft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.plots.spectrogram_panel import (
    COLOR_BAR_LABEL,
    EMPTY_LEVELS_TEXT,
    PERCEPTUAL_COLORMAPS,
)
from sonar_analyzer.ui.plots.waterfall_panel import (
    MAX_HISTORY_SLICES,
    MIN_HISTORY_SLICES,
    NO_DATA_MESSAGE,
    NO_RATE_MESSAGE,
    WaterfallPanel,
)

pytestmark = pytest.mark.gui

FS = 1_000.0
N = 8_000
BIN_TONE_HZ = 250.0

HYDROPHONE = ChannelMetadata(
    id="ch0",
    path="Acoustic/Hydrophone 1",
    name="Hydrophone 1",
    dtype="float64",
    source=ChannelSource.ACOUSTIC,
    unit="Pa",
    sample_rate_hz=FS,
)


def _tone(amp: float = 1.0, freq_hz: float = BIN_TONE_HZ) -> NDArray[np.float64]:
    k = np.arange(N, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


def _chirp() -> NDArray[np.float64]:
    t = np.arange(N, dtype=np.float64) / FS
    duration = N / FS
    return np.sin(2.0 * math.pi * (50.0 * t + 0.5 * 350.0 / duration * t * t))


@pytest.fixture()
def panel(qtbot: QtBot) -> WaterfallPanel:
    widget = WaterfallPanel()
    qtbot.addWidget(widget)
    return widget


# --------------------------------------------------------------------------- #
# boş durum
# --------------------------------------------------------------------------- #


def test_starts_empty_without_a_fake_map(panel: WaterfallPanel) -> None:
    assert not panel.has_slices
    assert panel.slice_count() == 0
    assert panel.model() is None
    assert panel.levels() is None
    assert panel.levels_text() == EMPTY_LEVELS_TEXT
    assert panel.message_text() == NO_DATA_MESSAGE


def test_an_unknown_sample_rate_is_explained(panel: WaterfallPanel) -> None:
    rateless = ChannelMetadata(id="c", path="p", name="n", dtype="float64", sample_rate_hz=None)
    panel.set_channel_data(rateless, _tone())
    assert not panel.has_slices
    assert panel.message_text() == NO_RATE_MESSAGE


def test_an_empty_selection_is_explained(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, np.empty(0, dtype=np.float64))
    assert not panel.has_slices
    assert panel.message_text() == NO_DATA_MESSAGE


def test_appending_before_setup_is_rejected(panel: WaterfallPanel) -> None:
    with pytest.raises(ValueError, match="henüz kurulmadı"):
        panel.append_slice(0.0, np.zeros(5))


# --------------------------------------------------------------------------- #
# birimler açıktır
# --------------------------------------------------------------------------- #


def test_the_axes_carry_their_units(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone())
    assert "Frequency" in panel.frequency_axis_label()
    assert "Hz" in panel.frequency_axis_label()
    assert "Time" in panel.time_axis_label()
    assert "s" in panel.time_axis_label()


def test_the_colour_bar_is_labelled_in_db(panel: WaterfallPanel) -> None:
    assert panel.color_bar_label() == COLOR_BAR_LABEL == "dB"


def test_the_levels_text_reads_both_bounds(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    levels = panel.levels()
    assert levels is not None
    text = panel.levels_text()
    assert "dB" in text
    assert f"{levels[0]:.1f}" in text
    assert f"{levels[1]:.1f}" in text


def test_the_title_names_the_channel_and_region(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(), region_seconds=(2.0, 6.0))
    assert "Hydrophone 1" in panel.title()
    assert "2" in panel.title()
    assert "6" in panel.title()


def test_only_perceptual_colormaps_are_offered(panel: WaterfallPanel) -> None:
    listed = [panel.colormap_selector.itemText(i) for i in range(panel.colormap_selector.count())]
    assert listed == list(PERCEPTUAL_COLORMAPS)
    with pytest.raises(ValueError, match="algısal düzgün olmayan"):
        panel.set_colormap("jet")


# --------------------------------------------------------------------------- #
# dilimler doğru sırayla çizilir
# --------------------------------------------------------------------------- #


def test_the_slices_follow_the_stft_columns(panel: WaterfallPanel) -> None:
    signal = _chirp()
    panel.set_window(WindowKind.HANN)
    panel.set_channel_data(HYDROPHONE, signal)

    expected = stft(signal, FS, window=WindowKind.HANN)
    assert panel.slice_count() == expected.frame_count
    assert np.allclose(panel.times_s(), expected.times_s)
    assert np.allclose(panel.frequencies_hz(), expected.frequencies_hz)


def test_the_times_are_stored_oldest_first(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _chirp())
    times = panel.times_s()
    assert np.all(np.diff(times) > 0.0)


def test_the_image_is_frequency_by_time(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _chirp())
    model = panel.model()
    assert model is not None
    # pyqtgraph görüntüsü (x, y) = (frekans, zaman).
    assert panel.image_data().shape == (model.bin_count, len(model))


def test_the_image_rows_match_the_slice_order(panel: WaterfallPanel) -> None:
    panel.set_window(WindowKind.HANN)
    panel.set_channel_data(HYDROPHONE, _chirp())

    model = panel.model()
    assert model is not None
    # Görüntü, dilim matrisinin dB'sinin devriği: sütun sırası zaman sırası.
    assert np.allclose(panel.image_data(), amplitude_to_db(model.matrix()).T)


def test_a_rising_chirp_moves_up_the_image_over_time(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _chirp())
    model = panel.model()
    assert model is not None

    matrix = model.matrix()  # (dilim, bin), en eski önce
    frequencies = panel.frequencies_hz()
    first_peak = frequencies[int(np.argmax(matrix[0]))]
    last_peak = frequencies[int(np.argmax(matrix[-1]))]
    assert last_peak > first_peak  # zaman ilerledikçe frekans yükseliyor


def test_appending_a_slice_puts_it_at_the_newest_end(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone())
    model = panel.model()
    assert model is not None

    later = model.newest_time_s() + 1.0
    marker = np.full(model.bin_count, 5.0, dtype=np.float64)
    panel.append_slice(later, marker)

    assert panel.times_s()[-1] == later
    updated = panel.model()
    assert updated is not None
    assert np.allclose(updated.newest().magnitudes, marker)


# --------------------------------------------------------------------------- #
# geçmiş sınırı
# --------------------------------------------------------------------------- #


def test_the_history_limit_is_exposed_and_bounded(panel: WaterfallPanel) -> None:
    assert panel.history_spin.minimum() == MIN_HISTORY_SLICES
    assert panel.history_spin.maximum() == MAX_HISTORY_SLICES
    assert panel.history_limit == panel.history_spin.value()


def test_a_small_history_limit_keeps_only_the_newest_slices(panel: WaterfallPanel) -> None:
    signal = _chirp()
    full = stft(signal, FS, window=panel.window_kind)

    panel.set_history_limit(10)
    panel.set_channel_data(HYDROPHONE, signal)

    assert panel.slice_count() == 10
    assert np.allclose(panel.times_s(), full.times_s[-10:])


def test_changing_the_history_limit_clears_the_view(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone())
    assert panel.has_slices
    panel.history_spin.setValue(64)
    assert not panel.has_slices
    assert panel.history_limit == 64


def test_a_nonpositive_history_limit_is_rejected(panel: WaterfallPanel) -> None:
    with pytest.raises(ValueError, match="geçmiş sınırı"):
        panel.set_history_limit(0)


def test_clear_drops_everything(panel: WaterfallPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone())
    assert panel.has_slices
    panel.clear()
    assert not panel.has_slices
    assert panel.title() == "Waterfall"
    assert panel.levels_text() == EMPTY_LEVELS_TEXT


# --------------------------------------------------------------------------- #
# Spectrogram görünüm sekmesi
# --------------------------------------------------------------------------- #


@pytest.fixture()
def repo() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=60.0, sample_rate_hz=200.0)


@pytest.fixture()
def win(qtbot: QtBot, repo: MockRecordingRepository) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(repo)
    window.open_channel("ch0")
    window.view_tabs.setCurrentIndex(window.view_tabs.tab_titles().index("Spectrogram"))
    return window


def test_the_spectrogram_tab_is_enabled(win: MainWindow) -> None:
    assert "Spectrogram" in win.view_tabs.enabled_tabs()


def test_selecting_the_tab_shows_the_waterfall(win: MainWindow) -> None:
    titles = win.view_tabs.tab_titles()
    win.view_tabs.setCurrentIndex(titles.index("Spectrogram"))
    assert win.center_stack.currentWidget() is win.waterfall_view
    assert not win.center_shows_plot


def test_the_waterfall_follows_the_open_channel(win: MainWindow) -> None:
    assert win.waterfall_view.has_slices
    assert "Pressure" in win.waterfall_view.title()


def test_the_roi_narrows_the_waterfall(win: MainWindow, qtbot: QtBot) -> None:
    before = win.waterfall_view.slice_count()
    assert before > 0

    win.plot_panel.set_time_region(0.0, 15.0)
    qtbot.waitUntil(lambda: "0–15 s" in win.waterfall_view.title(), timeout=5_000)

    assert "15" in win.waterfall_view.title()
    assert 0 < win.waterfall_view.slice_count() < before

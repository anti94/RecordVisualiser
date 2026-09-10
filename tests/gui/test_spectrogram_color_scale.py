"""Spektrogram renk ölçeği kontrolleri — `F4-049`.

Kabul: algısal düzgün colormap ve dB sınırları okunabilir kalır.

"Algısal düzgün" bir iddia değil, ölçülen bir özelliktir: sunulan her
haritanın **parlaklığı tekdüze artmalıdır**. Test bunu her harita için
doğrudan hesaplar.
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
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.ui.plots.spectrogram_panel import (
    COLOR_MAP_NAME,
    DEFAULT_DYNAMIC_RANGE_DB,
    EMPTY_LEVELS_TEXT,
    MAX_DYNAMIC_RANGE_DB,
    MIN_DYNAMIC_RANGE_DB,
    PERCEPTUAL_COLORMAPS,
    SpectrogramPanel,
    colormap_luminance,
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


def _tone(amp: float, freq_hz: float = BIN_TONE_HZ) -> NDArray[np.float64]:
    k = np.arange(N, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * freq_hz * k / FS)


def _luminance(name: str) -> NDArray[np.float64]:
    """Renk haritasının BT.709 göreli parlaklık dizisi."""
    return colormap_luminance(name)


@pytest.fixture()
def panel(qtbot: QtBot) -> SpectrogramPanel:
    widget = SpectrogramPanel()
    qtbot.addWidget(widget)
    return widget


# --------------------------------------------------------------------------- #
# algısal düzgün colormap
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", list(PERCEPTUAL_COLORMAPS))
def test_every_offered_colormap_has_monotonic_luminance(name: str) -> None:
    luminance = _luminance(name)
    assert np.all(np.diff(luminance) > 0.0), f"{name} algısal düzgün değil"


@pytest.mark.parametrize("name", list(PERCEPTUAL_COLORMAPS))
def test_every_offered_colormap_spans_a_wide_luminance_range(name: str) -> None:
    luminance = _luminance(name)
    # Uçlar arası fark yeterince geniş olmazsa dB farkı okunmaz.
    assert float(luminance[-1] - luminance[0]) > 100.0


def test_rainbow_maps_are_not_offered() -> None:
    for banned in ("jet", "turbo", "hsv", "rainbow"):
        assert banned not in PERCEPTUAL_COLORMAPS


def test_the_selector_lists_exactly_the_perceptual_maps(panel: SpectrogramPanel) -> None:
    listed = [panel.colormap_selector.itemText(i) for i in range(panel.colormap_selector.count())]
    assert listed == list(PERCEPTUAL_COLORMAPS)


def test_the_default_map_is_viridis(panel: SpectrogramPanel) -> None:
    assert panel.colormap_name == COLOR_MAP_NAME == "viridis"
    assert panel.colormap_selector.currentText() == "viridis"


@pytest.mark.parametrize("name", list(PERCEPTUAL_COLORMAPS))
def test_selecting_a_map_applies_it(panel: SpectrogramPanel, name: str) -> None:
    panel.set_colormap(name)
    assert panel.colormap_name == name
    assert panel.colormap_selector.currentText() == name


def test_choosing_from_the_combo_updates_the_panel(panel: SpectrogramPanel) -> None:
    panel.colormap_selector.setCurrentText("magma")
    assert panel.colormap_name == "magma"


def test_a_non_perceptual_map_is_rejected(panel: SpectrogramPanel) -> None:
    with pytest.raises(ValueError, match="algısal düzgün olmayan"):
        panel.set_colormap("jet")


def test_changing_the_map_keeps_the_data_and_the_levels(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    before_levels = panel.levels()
    before_image = panel.image_data().copy()

    panel.set_colormap("inferno")

    assert panel.levels() == before_levels
    assert np.array_equal(panel.image_data(), before_image)
    assert panel.has_spectrogram


# --------------------------------------------------------------------------- #
# dB sınırları okunabilir
# --------------------------------------------------------------------------- #


def test_the_levels_text_is_empty_before_any_data(panel: SpectrogramPanel) -> None:
    assert panel.levels_text() == EMPTY_LEVELS_TEXT


def test_the_levels_text_shows_both_bounds_in_db(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    levels = panel.levels()
    assert levels is not None

    text = panel.levels_text()
    assert "dB" in text
    assert f"{levels[0]:.1f}" in text
    assert f"{levels[1]:.1f}" in text


def test_the_levels_text_clears_with_the_panel(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(1.0))
    assert panel.levels_text() != EMPTY_LEVELS_TEXT
    panel.clear()
    assert panel.levels_text() == EMPTY_LEVELS_TEXT


def test_the_spin_box_starts_at_the_default_range(panel: SpectrogramPanel) -> None:
    assert panel.dynamic_range_spin.value() == int(DEFAULT_DYNAMIC_RANGE_DB)
    assert panel.dynamic_range_spin.suffix() == " dB"
    assert panel.dynamic_range_spin.minimum() == MIN_DYNAMIC_RANGE_DB
    assert panel.dynamic_range_spin.maximum() == MAX_DYNAMIC_RANGE_DB


def test_the_spin_box_range_stays_readable(panel: SpectrogramPanel) -> None:
    # Çok dar bir pencere okunmaz, çok geniş olan gürültüyü boğar.
    assert MIN_DYNAMIC_RANGE_DB >= 10
    assert MAX_DYNAMIC_RANGE_DB <= 200
    assert panel.dynamic_range_spin.minimum() > 0


def test_changing_the_spin_box_reapplies_the_levels(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    before = panel.levels()
    assert before is not None

    panel.dynamic_range_spin.setValue(30)

    after = panel.levels()
    assert after is not None
    assert abs((after[1] - after[0]) - 30.0) < 1e-9
    assert abs(after[1] - before[1]) < 1e-9  # tepe aynı kalır, taban yükselir
    assert after[0] > before[0]
    assert "30" in panel.levels_text() or f"{after[0]:.1f}" in panel.levels_text()


def test_set_dynamic_range_moves_the_spin_box_too(panel: SpectrogramPanel) -> None:
    panel.set_dynamic_range_db(45.0)
    assert panel.dynamic_range_spin.value() == 45
    assert panel.dynamic_range_db == 45.0


def test_changing_the_range_does_not_recompute_the_stft(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    before = panel.result()
    panel.dynamic_range_spin.setValue(50)
    assert panel.result() is before  # aynı nesne: STFT yeniden hesaplanmadı


def test_the_upper_bound_still_tracks_the_peak(panel: SpectrogramPanel) -> None:
    panel.set_channel_data(HYDROPHONE, _tone(2.0))
    panel.dynamic_range_spin.setValue(25)

    result = panel.result()
    levels = panel.levels()
    assert result is not None and levels is not None
    peak_db = float(np.max(amplitude_to_db(result.magnitudes)))
    assert abs(levels[1] - peak_db) < 1e-9


def test_a_nonpositive_range_is_rejected(panel: SpectrogramPanel) -> None:
    with pytest.raises(ValueError, match="dinamik aralık"):
        panel.set_dynamic_range_db(0.0)
    with pytest.raises(ValueError, match="dinamik aralık"):
        panel.set_dynamic_range_db(-10.0)


def test_the_controls_survive_new_data(panel: SpectrogramPanel) -> None:
    panel.set_colormap("cividis")
    panel.dynamic_range_spin.setValue(35)

    panel.set_channel_data(HYDROPHONE, _tone(3.0))

    assert panel.colormap_name == "cividis"
    levels = panel.levels()
    assert levels is not None
    assert abs((levels[1] - levels[0]) - 35.0) < 1e-9

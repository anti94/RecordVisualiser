"""Waterfall görünümü — `F4-051`.

"Spectrogram" görünüm sekmesinin gövdesi: seçili kanalın spektrum
dilimleri zaman ekseninde **akar**. Dashboard'daki spektrogram hücresinden
farkı yönelimidir — sonar waterfall geleneği:

* X ekseni — ``Frequency [Hz]``
* Y ekseni — ``Time [s]``, yukarı doğru artar; bu yüzden **en yeni dilim
  en üsttedir**.
* Renk — genlik dB'si (``20*log10``), ``dB`` etiketli renk çubuğu.

Dilimler `analysis.waterfall.WaterfallModel` içinde tutulur: geçmiş
sınırlıdır (`history_limit`), sınır dolunca en eski dilim düşer ve
çizilen sıra her zaman zaman sırasıdır (`F4-050`).

`PlotPanel` gibi bu sınıf da bir **soyutlama sınırıdır** (ADR-002).
Sample rate bilinmiyorsa ya da seçim STFT'ye yetmiyorsa panel sahte
sonuç üretmek yerine nedeni yazar.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.analysis.spectrum import amplitude_to_db
from sonar_analyzer.analysis.stft import StftError, StftResult, stft
from sonar_analyzer.analysis.waterfall import DEFAULT_MAX_SLICES, WaterfallModel
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.plots.spectrogram_panel import (
    COLOR_BAR_LABEL,
    COLOR_MAP_NAME,
    DEFAULT_DYNAMIC_RANGE_DB,
    EMPTY_LEVELS_TEXT,
    MAX_DYNAMIC_RANGE_DB,
    MIN_DYNAMIC_RANGE_DB,
    PERCEPTUAL_COLORMAPS,
)
from sonar_analyzer.ui.theme import DARK

EMPTY_TITLE = "Waterfall"
TIME_AXIS_LABEL = "Time"
TIME_AXIS_UNIT = "s"
FREQUENCY_AXIS_LABEL = "Frequency"
FREQUENCY_AXIS_UNIT = "Hz"

#: Geçmiş sınırı denetiminin aralığı (dilim).
MIN_HISTORY_SLICES = 8
MAX_HISTORY_SLICES = 4_096

NO_RATE_MESSAGE = "Waterfall — kanalin sample rate'i bilinmiyor; eksenler kurulamaz."
NO_DATA_MESSAGE = "Waterfall — secili aralikta yeterli ornek yok."


class WaterfallPanel(QGroupBox):
    """Zaman dilimlerini akan bir zaman–frekans haritası olarak çizer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EMPTY_TITLE, parent)
        self.setObjectName("panel_waterfall")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.colormap_selector = QComboBox(self)
        self.colormap_selector.setObjectName("combo_waterfall_colormap")
        self.colormap_selector.addItems(PERCEPTUAL_COLORMAPS)
        self.colormap_selector.currentTextChanged.connect(self._on_colormap_changed)
        header.addWidget(self.colormap_selector)

        self.dynamic_range_spin = QSpinBox(self)
        self.dynamic_range_spin.setObjectName("spin_waterfall_dynamic_range")
        self.dynamic_range_spin.setRange(MIN_DYNAMIC_RANGE_DB, MAX_DYNAMIC_RANGE_DB)
        self.dynamic_range_spin.setValue(int(DEFAULT_DYNAMIC_RANGE_DB))
        self.dynamic_range_spin.setSuffix(" dB")
        self.dynamic_range_spin.valueChanged.connect(self._on_dynamic_range_changed)
        header.addWidget(self.dynamic_range_spin)

        self.history_spin = QSpinBox(self)
        self.history_spin.setObjectName("spin_waterfall_history")
        self.history_spin.setRange(MIN_HISTORY_SLICES, MAX_HISTORY_SLICES)
        self.history_spin.setValue(DEFAULT_MAX_SLICES)
        self.history_spin.setSuffix(" dilim")
        self.history_spin.setToolTip("Tutulan en fazla zaman dilimi (geçmiş sınırı)")
        self.history_spin.valueChanged.connect(self._on_history_changed)
        header.addWidget(self.history_spin)

        self.levels_label = QLabel(EMPTY_LEVELS_TEXT, self)
        self.levels_label.setObjectName("label_waterfall_levels")
        self.levels_label.setMinimumWidth(1)
        header.addWidget(self.levels_label)
        header.addStretch(1)
        layout.addLayout(header)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("stack_waterfall")

        self.message = QLabel(NO_DATA_MESSAGE, self.stack)
        self.message.setObjectName("label_waterfall_message")
        self.message.setWordWrap(True)
        self.message.setMinimumWidth(1)
        self.stack.addWidget(self.message)

        self.plot = pg.PlotWidget(parent=self.stack)
        self.plot.setObjectName("plot_waterfall")
        self.plot.setBackground(DARK.surface)
        self.plot.setLabel("bottom", FREQUENCY_AXIS_LABEL, units=FREQUENCY_AXIS_UNIT)
        self.plot.setLabel("left", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)

        self.image = pg.ImageItem()
        self.plot.addItem(self.image)

        self.color_bar = pg.ColorBarItem(
            colorMap=pg.colormap.get(COLOR_MAP_NAME),
            label=COLOR_BAR_LABEL,
            interactive=False,
        )
        self.color_bar.setImageItem(self.image, insert_in=self.plot.getPlotItem())

        self.stack.addWidget(self.plot)
        layout.addWidget(self.stack, 1)

        self._model: WaterfallModel | None = None
        self._frequencies: NDArray[np.float64] = np.zeros(0, dtype=np.float64)
        self._resolution_hz = 0.0
        self._time_step_s = 0.0
        self._window = WindowKind.HANN
        self._dynamic_range_db = DEFAULT_DYNAMIC_RANGE_DB
        self._colormap_name = COLOR_MAP_NAME
        self._history_limit = DEFAULT_MAX_SLICES
        self._levels: tuple[float, float] | None = None
        self.clear()

    # -- eksen etiketleri --------------------------------------------------

    def frequency_axis_label(self) -> str:
        return str(self.plot.getPlotItem().getAxis("bottom").labelString())

    def time_axis_label(self) -> str:
        return str(self.plot.getPlotItem().getAxis("left").labelString())

    def color_bar_label(self) -> str:
        return COLOR_BAR_LABEL

    # -- ayarlar -----------------------------------------------------------

    @property
    def window_kind(self) -> WindowKind:
        return self._window

    def set_window(self, window: WindowKind | str) -> None:
        self._window = window if isinstance(window, WindowKind) else WindowKind(str(window))

    @property
    def history_limit(self) -> int:
        """Tutulan en fazla dilim sayısı."""
        return self._history_limit

    def set_history_limit(self, value: int) -> None:
        """Geçmiş sınırını değiştirir; mevcut dilimler düşer (model yeniden kurulur)."""
        if value < 1:
            raise ValueError(f"geçmiş sınırı >= 1 olmalı: {value}")
        self._history_limit = int(value)
        clamped = min(max(int(value), MIN_HISTORY_SLICES), MAX_HISTORY_SLICES)
        if self.history_spin.value() != clamped:
            self.history_spin.blockSignals(True)
            self.history_spin.setValue(clamped)
            self.history_spin.blockSignals(False)
        self.clear()

    def _on_history_changed(self, value: int) -> None:
        self._history_limit = int(value)
        self.clear()

    @property
    def dynamic_range_db(self) -> float:
        return self._dynamic_range_db

    def set_dynamic_range_db(self, value: float) -> None:
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"dinamik aralık pozitif olmalı: {value}")
        self._dynamic_range_db = float(value)
        clamped = min(max(round(value), MIN_DYNAMIC_RANGE_DB), MAX_DYNAMIC_RANGE_DB)
        if self.dynamic_range_spin.value() != clamped:
            self.dynamic_range_spin.blockSignals(True)
            self.dynamic_range_spin.setValue(clamped)
            self.dynamic_range_spin.blockSignals(False)
        self._redraw()

    def _on_dynamic_range_changed(self, value: int) -> None:
        self._dynamic_range_db = float(value)
        self._redraw()

    @property
    def colormap_name(self) -> str:
        return self._colormap_name

    def set_colormap(self, name: str) -> None:
        if name not in PERCEPTUAL_COLORMAPS:
            raise ValueError(
                f"algısal düzgün olmayan renk haritası: {name!r} "
                f"(geçerli: {list(PERCEPTUAL_COLORMAPS)})"
            )
        index = self.colormap_selector.findText(name)
        if index >= 0 and self.colormap_selector.currentIndex() != index:
            self.colormap_selector.setCurrentIndex(index)
            return
        self._apply_colormap(name)

    def _on_colormap_changed(self, name: str) -> None:
        if name in PERCEPTUAL_COLORMAPS:
            self._apply_colormap(name)

    def _apply_colormap(self, name: str) -> None:
        self._colormap_name = name
        self.color_bar.setColorMap(pg.colormap.get(name))
        if self._levels is not None:
            self.color_bar.setLevels(self._levels)

    # -- veri --------------------------------------------------------------

    def set_channel_data(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """Seçimin STFT'sini alıp waterfall'ı bu dilimlerle yeniden kurar."""
        data = np.asarray(values, dtype=np.float64)
        title = f"Waterfall ({channel.name})"
        if region_seconds is not None:
            lo, hi = region_seconds
            title = f"Waterfall ({channel.name} · {lo:.3g}–{hi:.3g} s)"

        rate = channel.sample_rate_hz
        if rate is None or rate <= 0:
            self._show_message(NO_RATE_MESSAGE, title)
            return
        if data.size == 0:
            self._show_message(NO_DATA_MESSAGE, title)
            return

        try:
            result = stft(data, rate, window=self._window)
        except StftError as exc:
            self._show_message(f"Waterfall hesaplanamadi: {exc}", title)
            return

        self.set_stft(result, title=title)

    def set_stft(self, result: StftResult, *, title: str | None = None) -> None:
        """Waterfall'ı bir STFT sonucunun sütunlarıyla yeniden doldurur."""
        model = WaterfallModel(result.bin_count, max_slices=self._history_limit)
        model.extend_from_stft(result)
        self._model = model
        self._frequencies = np.asarray(result.frequencies_hz, dtype=np.float64)
        self._resolution_hz = result.resolution_hz
        self._time_step_s = result.time_step_s
        if title is not None:
            self.setTitle(title)
        self._redraw()

    def append_slice(self, time_s: float, magnitudes: NDArray[np.float64]) -> None:
        """Tek bir yeni dilim ekler (canlı akış yolu); en eskisi sınırda düşer."""
        if self._model is None:
            raise ValueError("waterfall henüz kurulmadı; önce set_stft/set_channel_data çağırın")
        self._model.append(time_s, magnitudes)
        self._redraw()

    def _redraw(self) -> None:
        model = self._model
        if model is None or len(model) == 0:
            self._levels = None
            self._show_levels(None)
            return

        decibels = amplitude_to_db(model.matrix())  # (dilim, bin)
        peak = float(np.max(decibels))
        levels = (peak - self._dynamic_range_db, peak)
        self._levels = levels

        # pyqtgraph görüntüsü (sütun, satır) = (x, y) = (frekans, zaman).
        self.image.setImage(decibels.T, levels=levels, autoLevels=False)
        self.image.setRect(self._image_rect(model))
        self.color_bar.setLevels(levels)
        self._show_levels(levels)
        self.plot.setXRange(0.0, float(self._frequencies[-1]), padding=0.0)
        self.plot.setYRange(model.oldest_time_s(), model.newest_time_s(), padding=0.0)
        self.stack.setCurrentWidget(self.plot)

    def _image_rect(self, model: WaterfallModel) -> QRectF:
        """Görüntüyü, piksel merkezleri eksen değerlerine denk gelecek şekilde yerleştirir."""
        times = model.times_s()
        x0 = float(self._frequencies[0]) - self._resolution_hz / 2.0
        y0 = float(times[0]) - self._time_step_s / 2.0
        width = model.bin_count * self._resolution_hz
        height = len(model) * self._time_step_s
        return QRectF(x0, y0, width, height)

    def _show_message(self, text: str, title: str) -> None:
        self._model = None
        self._levels = None
        self._show_levels(None)
        self.setTitle(title)
        self.message.setText(text)
        self.stack.setCurrentWidget(self.message)

    def _show_levels(self, levels: tuple[float, float] | None) -> None:
        self.levels_label.setText(
            EMPTY_LEVELS_TEXT if levels is None else f"{levels[0]:.1f} … {levels[1]:.1f} dB"
        )

    def clear(self) -> None:
        """Tüm dilimleri düşürür ve paneli boş duruma alır."""
        self._model = None
        self._levels = None
        self._show_levels(None)
        self.image.clear()
        self.setTitle(EMPTY_TITLE)
        self.message.setText(NO_DATA_MESSAGE)
        self.stack.setCurrentWidget(self.message)

    # -- sorgular ----------------------------------------------------------

    @property
    def has_slices(self) -> bool:
        return self._model is not None and len(self._model) > 0

    def slice_count(self) -> int:
        return 0 if self._model is None else len(self._model)

    def model(self) -> WaterfallModel | None:
        """Dilimleri tutan model (yoksa `None`) — testler ve dış gözlem."""
        return self._model

    def times_s(self) -> NDArray[np.float64]:
        """Çizilen dilim damgaları, **en eski önce**."""
        if self._model is None:
            return np.zeros(0, dtype=np.float64)
        return self._model.times_s()

    def frequencies_hz(self) -> NDArray[np.float64]:
        return self._frequencies

    def levels(self) -> tuple[float, float] | None:
        return self._levels

    def levels_text(self) -> str:
        return self.levels_label.text()

    def image_data(self) -> NDArray[np.float64]:
        """Çizilen dB matrisi ``(frekans, zaman)``; görüntü yoksa boş."""
        raw = self.image.image
        if raw is None:
            return np.empty((0, 0), dtype=np.float64)
        return np.asarray(raw, dtype=np.float64)

    def message_text(self) -> str:
        return self.message.text()

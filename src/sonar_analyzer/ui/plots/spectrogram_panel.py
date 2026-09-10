"""Dashboard spektrogram hücresi — `F4-048`.

Mockup satır 2 (`docs/ui/layout-map.md` §3): seçili hidrofonun (ve seçili
zaman aralığının) zaman–frekans haritası. Hesap tek kaynaktan gelir
(`analysis.stft.stft`, `F4-046`); bu panel yalnız çizer:

* X ekseni — ``Time [s]`` (STFT sütun merkezleri)
* Y ekseni — ``Frequency [Hz]`` (STFT satırları)
* Renk — genlik dB'si (``20*log10``), yanında ``dB`` etiketli renk
  çubuğu. Görüntü penceresi ``[tepe - dynamic_range, tepe]`` olarak
  kırpılır; böylece -200 dB tabanı tüm ölçeği yutmaz.

Görüntü, piksel **merkezleri** eksen değerlerine denk gelecek şekilde
yarım bin dışarı taşırılarak yerleştirilir (`F4-047` "eksenler kaymaz").

`PlotPanel` gibi bu sınıf da bir **soyutlama sınırıdır** (ADR-002):
dışarısı pyqtgraph görmez. Sample rate bilinmiyorsa ya da seçili aralık
STFT'ye yetmiyorsa panel sahte sonuç üretmek yerine nedeni yazar.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGroupBox, QLabel, QStackedWidget, QVBoxLayout, QWidget

from sonar_analyzer.analysis.spectrum import amplitude_to_db
from sonar_analyzer.analysis.stft import StftError, StftResult, stft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.theme import DARK

EMPTY_TITLE = "Spectrogram"
TIME_AXIS_LABEL = "Time"
TIME_AXIS_UNIT = "s"
FREQUENCY_AXIS_LABEL = "Frequency"
FREQUENCY_AXIS_UNIT = "Hz"
COLOR_BAR_LABEL = "dB"

#: Renk ölçeğinin tepe değerinden aşağı doğru kapsadığı aralık (dB).
DEFAULT_DYNAMIC_RANGE_DB = 80.0
#: pyqtgraph renk haritası adı.
COLOR_MAP_NAME = "viridis"

NO_RATE_MESSAGE = "Spectrogram — kanalin sample rate'i bilinmiyor; eksenler kurulamaz."
NO_DATA_MESSAGE = "Spectrogram — secili aralikta yeterli ornek yok."


class SpectrogramPanel(QGroupBox):
    """Seçili kanalın/aralığın zaman–frekans haritasını dB ölçeğinde çizer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EMPTY_TITLE, parent)
        self.setObjectName("panel_spectrogram")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("stack_spectrogram")

        self.message = QLabel(NO_DATA_MESSAGE, self.stack)
        self.message.setObjectName("label_spectrogram_message")
        self.message.setWordWrap(True)
        self.message.setMinimumWidth(1)
        self.stack.addWidget(self.message)

        self.plot = pg.PlotWidget(parent=self.stack)
        self.plot.setObjectName("plot_spectrogram")
        self.plot.setBackground(DARK.surface)
        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)
        self.plot.setLabel("left", FREQUENCY_AXIS_LABEL, units=FREQUENCY_AXIS_UNIT)

        self.image = pg.ImageItem()
        self.plot.addItem(self.image)

        self.color_bar = pg.ColorBarItem(
            colorMap=pg.colormap.get(COLOR_MAP_NAME),
            label=COLOR_BAR_LABEL,
            interactive=False,
        )
        self.color_bar.setImageItem(self.image, insert_in=self.plot.getPlotItem())

        self.stack.addWidget(self.plot)
        layout.addWidget(self.stack)

        self._result: StftResult | None = None
        self._window = WindowKind.HANN
        self._dynamic_range_db = DEFAULT_DYNAMIC_RANGE_DB
        self._levels: tuple[float, float] | None = None
        self.clear()

    # -- eksen etiketleri --------------------------------------------------

    def time_axis_label(self) -> str:
        """X ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("bottom").labelString())

    def frequency_axis_label(self) -> str:
        """Y ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("left").labelString())

    def color_bar_label(self) -> str:
        """Renk çubuğunun birimi — kabul kontrolü için."""
        return COLOR_BAR_LABEL

    # -- ayarlar -----------------------------------------------------------

    @property
    def window_kind(self) -> WindowKind:
        return self._window

    def set_window(self, window: WindowKind | str) -> None:
        self._window = window if isinstance(window, WindowKind) else WindowKind(str(window))

    @property
    def dynamic_range_db(self) -> float:
        return self._dynamic_range_db

    def set_dynamic_range_db(self, value: float) -> None:
        """Renk ölçeğinin kapsadığı dB aralığı (tepe değerinden aşağı)."""
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"dinamik aralık pozitif olmalı: {value}")
        self._dynamic_range_db = float(value)

    # -- veri --------------------------------------------------------------

    def set_channel_data(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """Kanalın (ya da seçili aralığın) spektrogramını hesaplar ve çizer."""
        data = np.asarray(values, dtype=np.float64)
        title = f"Spectrogram ({channel.name})"
        if region_seconds is not None:
            lo, hi = region_seconds
            title = f"Spectrogram ({channel.name} · {lo:.3g}–{hi:.3g} s)"

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
            self._show_message(f"Spectrogram hesaplanamadi: {exc}", title)
            return

        decibels = amplitude_to_db(result.magnitudes)
        peak = float(np.max(decibels))
        levels = (peak - self._dynamic_range_db, peak)

        self._result = result
        self._levels = levels
        self.setTitle(title)
        # pyqtgraph görüntüsü (sütun, satır) düzeninde: (zaman, frekans).
        self.image.setImage(decibels.T, levels=levels, autoLevels=False)
        self.image.setRect(_image_rect(result))
        self.color_bar.setLevels(levels)
        self.plot.setXRange(result.times_s[0], result.times_s[-1], padding=0.0)
        self.plot.setYRange(0.0, result.nyquist_hz, padding=0.0)
        self.stack.setCurrentWidget(self.plot)

    def _show_message(self, text: str, title: str) -> None:
        self._result = None
        self._levels = None
        self.setTitle(title)
        self.message.setText(text)
        self.stack.setCurrentWidget(self.message)

    def clear(self) -> None:
        """Paneli boş duruma alır."""
        self._result = None
        self._levels = None
        self.image.clear()
        self.setTitle(EMPTY_TITLE)
        self.message.setText(NO_DATA_MESSAGE)
        self.stack.setCurrentWidget(self.message)

    # -- sorgular ----------------------------------------------------------

    @property
    def has_spectrogram(self) -> bool:
        return self._result is not None

    def result(self) -> StftResult | None:
        """Son hesaplanan STFT (yoksa `None`) — testler ve dış gözlem."""
        return self._result

    def levels(self) -> tuple[float, float] | None:
        """Renk ölçeğinin ``(alt, üst)`` dB sınırları."""
        return self._levels

    def image_data(self) -> NDArray[np.float64]:
        """Çizilen dB matrisi ``(zaman, frekans)``; görüntü yoksa boş."""
        raw = self.image.image
        if raw is None:
            return np.empty((0, 0), dtype=np.float64)
        return np.asarray(raw, dtype=np.float64)

    def message_text(self) -> str:
        return self.message.text()


def _image_rect(result: StftResult) -> QRectF:
    """Görüntüyü, piksel merkezleri eksen değerlerine denk gelecek şekilde yerleştirir."""
    time_step = result.time_step_s
    frequency_step = result.resolution_hz
    x0 = float(result.times_s[0]) - time_step / 2.0
    y0 = float(result.frequencies_hz[0]) - frequency_step / 2.0
    width = result.frame_count * time_step
    height = result.bin_count * frequency_step
    return QRectF(x0, y0, width, height)

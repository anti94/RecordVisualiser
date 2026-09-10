"""Dashboard FFT hücresi — `F4-042`.

Mockup satır 3'ün sol hücresi: seçili kanalın (ve seçili zaman aralığının)
tek taraflı genlik spektrumu. Hesap tek kaynaktan gelir
(`analysis.spectrum.one_sided_fft`, `F4-040`); bu panel yalnız çizer ve
eksenleri **birimiyle** etiketler:

* X ekseni — ``Frequency [Hz]``
* Y ekseni — kanalın birimi (ör. ``Amplitude [Pa]``); birim bilinmiyorsa
  yalnız ``Amplitude``.

ROI (zaman bölgesi) değişince `set_channel_data` yeniden çağrılır ve
spektrum o pencerenin örnekleriyle yenilenir. `PlotPanel` gibi bu sınıf da
bir **soyutlama sınırıdır** (ADR-002): dışarısı pyqtgraph görmez.

Sample rate bilinmiyorsa (kanal `sample_rate_hz` taşımıyorsa) frekans
ekseni kurulamaz; panel sahte sonuç üretmek yerine bunu açıkça yazar.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtWidgets import QGroupBox, QLabel, QStackedWidget, QVBoxLayout, QWidget

from sonar_analyzer.analysis.spectrum import SpectrumError, SpectrumResult, one_sided_fft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.theme import DARK

EMPTY_TITLE = "FFT"
FREQUENCY_AXIS_LABEL = "Frequency"
FREQUENCY_AXIS_UNIT = "Hz"
AMPLITUDE_AXIS_LABEL = "Amplitude"

#: Sample rate bilinmediğinde gösterilen açıklama.
NO_RATE_MESSAGE = "FFT — kanalin sample rate'i bilinmiyor; frekans ekseni kurulamaz."
#: Seçili pencerede yeterli örnek olmadığında gösterilen açıklama.
NO_DATA_MESSAGE = "FFT — secili aralikta ornek yok."

GRID_ALPHA = 0.15


class SpectrumPanel(QGroupBox):
    """Seçili kanalın/aralığın tek taraflı genlik spektrumunu çizer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EMPTY_TITLE, parent)
        self.setObjectName("panel_spectrum")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("stack_spectrum")

        self.message = QLabel(NO_DATA_MESSAGE, self.stack)
        self.message.setObjectName("label_spectrum_message")
        self.message.setWordWrap(True)
        self.message.setMinimumWidth(1)
        self.stack.addWidget(self.message)

        self.plot = pg.PlotWidget(parent=self.stack)
        self.plot.setObjectName("plot_spectrum")
        self.plot.setBackground(DARK.surface)
        self.plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
        self.stack.addWidget(self.plot)

        layout.addWidget(self.stack)

        self._curve: pg.PlotDataItem | None = None
        self._result: SpectrumResult | None = None
        self._window = WindowKind.HANN
        self._set_axis_labels(unit=None)
        self.clear()

    # -- eksen etiketleri --------------------------------------------------

    def _set_axis_labels(self, *, unit: str | None) -> None:
        self.plot.setLabel("bottom", FREQUENCY_AXIS_LABEL, units=FREQUENCY_AXIS_UNIT)
        if unit:
            self.plot.setLabel("left", AMPLITUDE_AXIS_LABEL, units=unit)
        else:
            self.plot.setLabel("left", AMPLITUDE_AXIS_LABEL)

    def frequency_axis_label(self) -> str:
        """X ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("bottom").labelString())

    def amplitude_axis_label(self) -> str:
        """Y ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("left").labelString())

    # -- pencere seçimi ----------------------------------------------------

    @property
    def window_kind(self) -> WindowKind:
        return self._window

    def set_window(self, window: WindowKind | str) -> None:
        """FFT penceresini değiştirir; varsa görünen spektrum yenilenmez."""
        self._window = window if isinstance(window, WindowKind) else WindowKind(str(window))

    # -- veri --------------------------------------------------------------

    def set_channel_data(
        self,
        channel: ChannelMetadata,
        values: NDArray[np.float64],
        region_seconds: tuple[float, float] | None = None,
    ) -> None:
        """Kanalın (ya da seçili aralığın) spektrumunu hesaplar ve çizer.

        `region_seconds` verilirse başlığa aralık yazılır ve `values`
        yalnız o pencerenin örnekleri olmalıdır (`F4-042` ROI yolu).
        """
        rate = channel.sample_rate_hz
        title = f"FFT ({channel.name})"
        if region_seconds is not None:
            lo, hi = region_seconds
            title = f"FFT ({channel.name} · {lo:.3g}–{hi:.3g} s)"

        data = np.asarray(values, dtype=np.float64)
        if rate is None or rate <= 0:
            self._show_message(NO_RATE_MESSAGE, title)
            return
        if data.size == 0:
            self._show_message(NO_DATA_MESSAGE, title)
            return

        try:
            result = one_sided_fft(data, rate, window=self._window)
        except SpectrumError as exc:
            self._show_message(f"FFT hesaplanamadi: {exc}", title)
            return

        self._result = result
        self.setTitle(title)
        self._set_axis_labels(unit=channel.unit)
        if self._curve is None:
            self._curve = self.plot.plot(
                result.frequencies_hz,
                result.amplitudes,
                pen=pg.mkPen(DARK.accent, width=1),
            )
        else:
            self._curve.setData(result.frequencies_hz, result.amplitudes)
        self.plot.setXRange(0.0, result.nyquist_hz, padding=0.0)
        self.stack.setCurrentWidget(self.plot)

    def _show_message(self, text: str, title: str) -> None:
        self._result = None
        self.setTitle(title)
        self.message.setText(text)
        self.stack.setCurrentWidget(self.message)

    def clear(self) -> None:
        """Paneli boş duruma alır."""
        self._result = None
        if self._curve is not None:
            self._curve.setData(np.empty(0), np.empty(0))
        self.setTitle(EMPTY_TITLE)
        self.message.setText(NO_DATA_MESSAGE)
        self.stack.setCurrentWidget(self.message)

    # -- sorgular ----------------------------------------------------------

    @property
    def has_spectrum(self) -> bool:
        return self._result is not None

    def result(self) -> SpectrumResult | None:
        """Son hesaplanan spektrum (yoksa `None`) — testler ve dış gözlem."""
        return self._result

    def message_text(self) -> str:
        return self.message.text()

    def curve_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Çizilen (frekans, genlik) dizileri; seri yoksa boş."""
        if self._curve is None:
            return (np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64))
        x, y = self._curve.getData()
        if x is None or y is None:
            return (np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64))
        return (
            np.asarray(x, dtype=np.float64),
            np.asarray(y, dtype=np.float64),
        )

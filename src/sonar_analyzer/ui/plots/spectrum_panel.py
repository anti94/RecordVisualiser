"""Spektrum paneli — `F4-042` (FFT), `F4-045` (PSD görünümü).

Mockup satır 3'ün sol hücresi ve "Spectrum" görünüm sekmesi bu paneli
kullanır: seçili kanalın (ve seçili zaman aralığının) spektrumu. Hesap
tek kaynaktan gelir (`analysis.spectrum.one_sided_fft`,
`analysis.psd.welch_psd`); bu panel yalnız çizer ve eksenleri
**birimiyle** etiketler:

* X ekseni — ``Frequency [Hz]`` (iki kipte de).
* Y ekseni — ``FFT`` kipinde kanalın birimi (``Amplitude [Pa]``),
  ``PSD`` kipinde güç yoğunluğu (``PSD [Pa²/Hz]``).

`F4-045`: kipi `mode_selector` değiştirir; kip değişince hem eksen
etiketi hem **hesaplanan sonuç** değişir (aynı veri yeniden işlenir).

ROI (zaman bölgesi) değişince `set_channel_data` yeniden çağrılır ve
spektrum o pencerenin örnekleriyle yenilenir. `PlotPanel` gibi bu sınıf
da bir **soyutlama sınırıdır** (ADR-002): dışarısı pyqtgraph görmez.

Sample rate bilinmiyorsa (kanal `sample_rate_hz` taşımıyorsa) frekans
ekseni kurulamaz; panel sahte sonuç üretmek yerine bunu açıkça yazar.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.analysis.psd import PsdError, PsdResult, welch_psd
from sonar_analyzer.analysis.spectrum import SpectrumError, SpectrumResult, one_sided_fft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.theme import DARK

EMPTY_TITLE = "FFT"
FREQUENCY_AXIS_LABEL = "Frequency"
FREQUENCY_AXIS_UNIT = "Hz"
AMPLITUDE_AXIS_LABEL = "Amplitude"
PSD_AXIS_LABEL = "PSD"

#: Sample rate bilinmediğinde gösterilen açıklama.
NO_RATE_MESSAGE = "FFT — kanalin sample rate'i bilinmiyor; frekans ekseni kurulamaz."
#: Seçili pencerede yeterli örnek olmadığında gösterilen açıklama.
NO_DATA_MESSAGE = "FFT — secili aralikta ornek yok."

GRID_ALPHA = 0.15


class SpectrumMode(str, Enum):
    """Panelin hesap kipi — `F4-045`."""

    FFT = "fft"
    PSD = "psd"


#: Combobox etiketleri (sıra mockup'taki gibi FFT önce).
MODE_LABELS: dict[SpectrumMode, str] = {SpectrumMode.FFT: "FFT", SpectrumMode.PSD: "PSD"}
SPECTRUM_MODES: tuple[str, ...] = tuple(mode.value for mode in SpectrumMode)


def psd_unit(unit: str | None) -> str:
    """PSD ekseninin birimi: ``<birim>²/Hz`` (birim bilinmiyorsa boş)."""
    return f"{unit}²/Hz" if unit else ""


class SpectrumPanel(QGroupBox):
    """Seçili kanalın/aralığın FFT ya da PSD spektrumunu çizer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(EMPTY_TITLE, parent)
        self.setObjectName("panel_spectrum")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.mode_selector = QComboBox(self)
        self.mode_selector.setObjectName("combo_spectrum_mode")
        for mode in SpectrumMode:
            self.mode_selector.addItem(MODE_LABELS[mode], mode)
        self.mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        header.addWidget(self.mode_selector)
        header.addStretch(1)
        layout.addLayout(header)

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

        layout.addWidget(self.stack, 1)

        self._curve: pg.PlotDataItem | None = None
        self._result: SpectrumResult | None = None
        self._psd: PsdResult | None = None
        self._window = WindowKind.HANN
        self._mode = SpectrumMode.FFT
        #: Kip değişince yeniden hesaplamak için son veri.
        self._last: tuple[ChannelMetadata, NDArray[np.float64], tuple[float, float] | None] | None
        self._last = None
        self._set_axis_labels(unit=None)
        self.clear()

    # -- eksen etiketleri --------------------------------------------------

    def _set_axis_labels(self, *, unit: str | None) -> None:
        self.plot.setLabel("bottom", FREQUENCY_AXIS_LABEL, units=FREQUENCY_AXIS_UNIT)
        if self._mode is SpectrumMode.PSD:
            density_unit = psd_unit(unit)
            if density_unit:
                self.plot.setLabel("left", PSD_AXIS_LABEL, units=density_unit)
            else:
                self.plot.setLabel("left", PSD_AXIS_LABEL)
        elif unit:
            self.plot.setLabel("left", AMPLITUDE_AXIS_LABEL, units=unit)
        else:
            self.plot.setLabel("left", AMPLITUDE_AXIS_LABEL)

    def frequency_axis_label(self) -> str:
        """X ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("bottom").labelString())

    def amplitude_axis_label(self) -> str:
        """Y ekseninin görünen metni — kabul kontrolü için."""
        return str(self.plot.getPlotItem().getAxis("left").labelString())

    # -- kip ve pencere ----------------------------------------------------

    @property
    def mode(self) -> SpectrumMode:
        return self._mode

    def set_mode(self, mode: SpectrumMode | str) -> None:
        """Hesap kipini değiştirir ve varsa görünen sonucu yeniden üretir."""
        resolved = mode if isinstance(mode, SpectrumMode) else SpectrumMode(str(mode))
        index = self.mode_selector.findData(resolved)
        if index >= 0 and self.mode_selector.currentIndex() != index:
            self.mode_selector.setCurrentIndex(index)  # sinyal `_on_mode_changed`'i çağırır
            return
        self._apply_mode(resolved)

    def _on_mode_changed(self) -> None:
        data = self.mode_selector.currentData()
        self._apply_mode(data if isinstance(data, SpectrumMode) else SpectrumMode(str(data)))

    def _apply_mode(self, mode: SpectrumMode) -> None:
        if mode is self._mode:
            return
        self._mode = mode
        if self._last is None:
            self._set_axis_labels(unit=None)
            return
        channel, values, region = self._last
        self.set_channel_data(channel, values, region_seconds=region)

    @property
    def window_kind(self) -> WindowKind:
        return self._window

    def set_window(self, window: WindowKind | str) -> None:
        """FFT/PSD penceresini değiştirir; görünen spektrum yenilenmez."""
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
        data = np.asarray(values, dtype=np.float64)
        self._last = (channel, data, region_seconds)

        rate = channel.sample_rate_hz
        label = MODE_LABELS[self._mode]
        title = f"{label} ({channel.name})"
        if region_seconds is not None:
            lo, hi = region_seconds
            title = f"{label} ({channel.name} · {lo:.3g}–{hi:.3g} s)"

        if rate is None or rate <= 0:
            self._show_message(NO_RATE_MESSAGE, title)
            return
        if data.size == 0:
            self._show_message(NO_DATA_MESSAGE, title)
            return

        try:
            frequencies, magnitudes, nyquist = self._compute(data, rate)
        except (SpectrumError, PsdError) as exc:
            self._show_message(f"{label} hesaplanamadi: {exc}", title)
            return

        self.setTitle(title)
        self._set_axis_labels(unit=channel.unit)
        if self._curve is None:
            self._curve = self.plot.plot(
                frequencies, magnitudes, pen=pg.mkPen(DARK.accent, width=1)
            )
        else:
            self._curve.setData(frequencies, magnitudes)
        self.plot.setXRange(0.0, nyquist, padding=0.0)
        self.stack.setCurrentWidget(self.plot)

    def _compute(
        self, data: NDArray[np.float64], rate: float
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], float]:
        """Kipe göre hesaplar; ilgili sonucu saklar ve çizilecek dizileri verir."""
        if self._mode is SpectrumMode.PSD:
            psd = welch_psd(data, rate, window=self._window)
            self._psd = psd
            self._result = None
            return (psd.frequencies_hz, psd.density, psd.nyquist_hz)
        spectrum = one_sided_fft(data, rate, window=self._window)
        self._result = spectrum
        self._psd = None
        return (spectrum.frequencies_hz, spectrum.amplitudes, spectrum.nyquist_hz)

    def _show_message(self, text: str, title: str) -> None:
        self._result = None
        self._psd = None
        self.setTitle(title)
        self.message.setText(text)
        self.stack.setCurrentWidget(self.message)

    def clear(self) -> None:
        """Paneli boş duruma alır."""
        self._result = None
        self._psd = None
        self._last = None
        if self._curve is not None:
            self._curve.setData(np.empty(0), np.empty(0))
        self.setTitle(MODE_LABELS[self._mode])
        self.message.setText(NO_DATA_MESSAGE)
        self.stack.setCurrentWidget(self.message)

    # -- sorgular ----------------------------------------------------------

    @property
    def has_spectrum(self) -> bool:
        return self._result is not None or self._psd is not None

    def result(self) -> SpectrumResult | None:
        """Son FFT sonucu (PSD kipinde `None`) — testler ve dış gözlem."""
        return self._result

    def psd_result(self) -> PsdResult | None:
        """Son PSD sonucu (FFT kipinde `None`) — testler ve dış gözlem."""
        return self._psd

    def message_text(self) -> str:
        return self.message.text()

    def curve_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Çizilen (frekans, büyüklük) dizileri; seri yoksa boş."""
        if self._curve is None:
            return (np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64))
        x, y = self._curve.getData()
        if x is None or y is None:
            return (np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64))
        return (
            np.asarray(x, dtype=np.float64),
            np.asarray(y, dtype=np.float64),
        )

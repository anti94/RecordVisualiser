"""Tek taraflı (single-sided) FFT genlik spektrumu — `F4-040`.

Gerçek bir sinyalin spektrumu simetriktir; yalnız ``0 .. Nyquist``
aralığı taşınır (`numpy.fft.rfft`). Genlik ölçeklemesi, **bilinen bir
sinüsün tepe genliğini geri verecek** biçimde seçilir::

    amplitude[k] = 2 * |X[k]| / sum(w)      (0 < k < Nyquist)
    amplitude[k] =     |X[k]| / sum(w)      (DC ve çift N'de Nyquist)

``sum(w)`` bölmesi pencere kaybını (coherent gain) da düzeltir; bu
yüzden dikdörtgen pencerede de, Hann/Hamming/Blackman'da da tam bir
bine oturan bir tonun genliği **birebir** geri gelir (`F4-039`).

DC ve Nyquist binlerinin iki katı alınmaz: bu ikisinin aynada eşi
yoktur, enerjileri zaten tek binde durur.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır. dB dönüşümü ve sınır
doğrulamaları `F4-041`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.windows import WindowKind, window_values

FloatArray = NDArray[np.float64]

#: `amplitude_to_db` için öntanımlı taban — sıfır genlik burada durur.
DEFAULT_DB_FLOOR = -200.0


class SpectrumError(ValueError):
    """Spektrum parametresi geçersiz (boş sinyal, pozitif olmayan oran, vb.)."""


@dataclass(frozen=True)
class SpectrumResult:
    """Tek taraflı genlik spektrumu ve ekseni."""

    frequencies_hz: FloatArray
    amplitudes: FloatArray
    sample_rate_hz: float
    sample_count: int
    window_kind: str = WindowKind.RECTANGULAR.value

    def __len__(self) -> int:
        return int(self.amplitudes.shape[0])

    @property
    def resolution_hz(self) -> float:
        """Bin genişliği ``fs / N``."""
        return self.sample_rate_hz / float(self.sample_count)

    @property
    def nyquist_hz(self) -> float:
        return self.sample_rate_hz / 2.0

    @property
    def peak_index(self) -> int:
        """En büyük genliğin bin indeksi (boş spektrumda 0)."""
        if self.amplitudes.size == 0:  # pragma: no cover - boş spektrum üretilmez
            return 0
        return int(np.argmax(self.amplitudes))

    @property
    def peak_frequency_hz(self) -> float:
        return float(self.frequencies_hz[self.peak_index])

    @property
    def peak_amplitude(self) -> float:
        return float(self.amplitudes[self.peak_index])


def _as_1d_float64(values: NDArray[np.generic] | FloatArray) -> FloatArray:
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise SpectrumError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    return data


def one_sided_fft(
    values: NDArray[np.generic] | FloatArray,
    sample_rate_hz: float,
    *,
    window: WindowKind | str = WindowKind.RECTANGULAR,
) -> SpectrumResult:
    """`values`'ın tek taraflı genlik spektrumu.

    Tam bir bine oturan ``A * sin(2*pi*f*t)`` tonu için tepe bininde
    genlik **tam olarak** ``A`` çıkar.
    """
    data = _as_1d_float64(values)
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise SpectrumError(f"sample rate pozitif olmalı: {sample_rate_hz}")
    count = data.size
    if count == 0:
        raise SpectrumError("boş sinyalin spektrumu tanımsız")

    coefficients = window_values(window, count)
    total = float(coefficients.sum())
    if total == 0.0:  # pragma: no cover - desteklenen pencerelerde olmaz
        raise SpectrumError("pencere toplamı sıfır; genlik ölçeklemesi tanımsız")

    spectrum = np.fft.rfft(data * coefficients)
    amplitudes = np.abs(spectrum) / total
    # DC dışındaki binler aynadaki eşiyle birlikte iki kat taşır.
    if amplitudes.size > 1:
        amplitudes[1:] *= 2.0
        # Çift N'de son bin tam Nyquist'tir ve aynası yoktur.
        if count % 2 == 0:
            amplitudes[-1] /= 2.0

    return SpectrumResult(
        frequencies_hz=np.fft.rfftfreq(count, d=1.0 / sample_rate_hz),
        amplitudes=np.asarray(amplitudes, dtype=np.float64),
        sample_rate_hz=float(sample_rate_hz),
        sample_count=count,
        window_kind=WindowKind(str(window)).value
        if not isinstance(window, WindowKind)
        else window.value,
    )


def amplitude_to_db(
    amplitudes: NDArray[np.generic] | FloatArray,
    *,
    reference: float = 1.0,
    floor_db: float = DEFAULT_DB_FLOOR,
) -> FloatArray:
    """Genliği dB'ye çevirir: ``20 * log10(|a| / reference)``.

    Sıfır (ve referansa göre çok küçük) genlikler ``-inf`` yerine
    ``floor_db``'de durur — grafik ekseni patlamaz, veri de uydurulmaz.
    """
    values = np.abs(np.asarray(amplitudes, dtype=np.float64))
    if not np.isfinite(reference) or reference <= 0:
        raise SpectrumError(f"dB referansı pozitif olmalı: {reference}")

    floor_amplitude = reference * 10.0 ** (floor_db / 20.0)
    clipped = np.maximum(values, floor_amplitude)
    result = 20.0 * np.log10(clipped / reference)
    # NaN girdi NaN kalır (sessizce tabana çekilmez).
    return np.asarray(np.where(np.isnan(values), np.nan, result), dtype=np.float64)

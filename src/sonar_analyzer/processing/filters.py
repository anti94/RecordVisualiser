"""FFT alanında sıfır-fazlı Butterworth-genlik filtreleri — `F4-027`+.

Bu modül filtreleri **frekans alanında** uygular: gerçek FFT alınır,
spektrum Butterworth genlik yanıtıyla (gerçek, faz kaydırmasız)
çarpılır, ters FFT ile zaman alanına dönülür. Sonuç **sıfır-fazlıdır**
(grup gecikmesi yok) ve yanıtın her noktası analitik olarak bilinir:

* Alçak geçiren:  ``H(f) = 1 / sqrt(1 + (f / fc)^(2n))``
* Yüksek geçiren: ``H(f) = 1 / sqrt(1 + (fc / f)^(2n))``  (``H(0) = 0``)

``fc``'de kazanç her ``n`` için tam ``1/sqrt(2)`` (−3 dB) — Butterworth'un
tanımlayıcı özelliği.

FFT dairesel evrişim varsayar: tam periyot içeren sinyallerde kenar
etkisi yoktur; genel sinyallerde uçlarda hafif sızma olabilir. FFT
küreseldir: bir ``NaN`` tüm çıktıyı ``NaN`` yapar. Saf NumPy — Qt yok,
`GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Samples = NDArray[np.float64]
FloatArray = NDArray[np.float64]

#: Kabul edilen filtre order aralığı. 8'in üstü FFT-genlik yaklaşımında
#: sayısal olarak anlamsız (yanıt tuğla duvara yakınsar) ve reddedilir.
FILTER_MIN_ORDER = 1
FILTER_MAX_ORDER = 8


class FilterError(ValueError):
    """Filtre parametresi geçersiz (cutoff Nyquist dışı, order aralık dışı vb.)."""


def nyquist_hz(sample_rate_hz: float) -> float:
    return sample_rate_hz / 2.0


def validate_sample_rate(sample_rate_hz: float) -> None:
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise FilterError(f"sample rate pozitif olmalı: {sample_rate_hz}")


def validate_order(order: object) -> None:
    if isinstance(order, bool) or not isinstance(order, int):
        raise FilterError(f"filtre order bir tam sayı olmalı: {order!r}")
    if not FILTER_MIN_ORDER <= order <= FILTER_MAX_ORDER:
        raise FilterError(
            f"filtre order {FILTER_MIN_ORDER}..{FILTER_MAX_ORDER} aralığında olmalı: {order}"
        )


def validate_cutoff(cutoff_hz: float, sample_rate_hz: float) -> None:
    """``0 < cutoff < Nyquist`` — aksi halde `FilterError`."""
    validate_sample_rate(sample_rate_hz)
    nyq = nyquist_hz(sample_rate_hz)
    if not np.isfinite(cutoff_hz) or cutoff_hz <= 0.0 or cutoff_hz >= nyq:
        raise FilterError(f"cutoff 0 < f < Nyquist ({nyq:g} Hz) olmalı: {cutoff_hz}")


def butterworth_lowpass_response(freqs_hz: FloatArray, cutoff_hz: float, order: int) -> FloatArray:
    """Alçak geçiren Butterworth genlik yanıtı ``1/sqrt(1 + (f/fc)^(2n))``."""
    ratio = np.abs(np.asarray(freqs_hz, dtype=np.float64)) / cutoff_hz
    return np.asarray(1.0 / np.sqrt(1.0 + ratio ** (2 * order)), dtype=np.float64)


def butterworth_highpass_response(freqs_hz: FloatArray, cutoff_hz: float, order: int) -> FloatArray:
    """Yüksek geçiren Butterworth genlik yanıtı ``1/sqrt(1 + (fc/f)^(2n))``.

    ``f = 0``'da yanıt tam olarak ``0``'dır (DC tümüyle bloklanır);
    ``f = fc``'de ``1/sqrt(2)``. Alçak geçirenle güç-tümleyicidir:
    ``H_lp^2 + H_hp^2 == 1``.
    """
    freqs = np.abs(np.asarray(freqs_hz, dtype=np.float64))
    response = np.zeros_like(freqs)
    nonzero = freqs > 0.0
    ratio = cutoff_hz / freqs[nonzero]
    response[nonzero] = 1.0 / np.sqrt(1.0 + ratio ** (2 * order))
    return response


def _apply_response(
    data: Samples,
    sample_rate_hz: float,
    response: FloatArray,
) -> Samples:
    """`data`'yı rfft alıp `response` ile çarpıp irfft ederek filtreler."""
    n = data.size
    spectrum = np.fft.rfft(data)
    filtered = np.fft.irfft(spectrum * response, n=n)
    return np.asarray(filtered, dtype=np.float64)


def _as_1d_float64(values: NDArray[np.generic] | Samples) -> Samples:
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise FilterError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    return data


def low_pass(
    values: NDArray[np.generic] | Samples,
    sample_rate_hz: float,
    cutoff_hz: float,
    order: int,
) -> Samples:
    """`values`'a sıfır-fazlı Butterworth alçak geçiren filtre uygular.

    ``cutoff_hz`` altındaki bileşenler ~korunur, üstündekiler
    ``-20n dB/dekad`` eğimiyle bastırılır. **Her zaman yeni** bir dizi
    döndürür.
    """
    data = _as_1d_float64(values)
    validate_cutoff(cutoff_hz, sample_rate_hz)
    validate_order(order)
    if data.size == 0:
        return data.copy()
    freqs = np.fft.rfftfreq(data.size, d=1.0 / sample_rate_hz)
    response = butterworth_lowpass_response(freqs, cutoff_hz, order)
    return _apply_response(data, sample_rate_hz, response)


def high_pass(
    values: NDArray[np.generic] | Samples,
    sample_rate_hz: float,
    cutoff_hz: float,
    order: int,
) -> Samples:
    """`values`'a sıfır-fazlı Butterworth yüksek geçiren filtre uygular.

    DC ve ``cutoff_hz`` altındaki bileşenler ``-20n dB/dekad`` eğimiyle
    bastırılır (DC tam olarak sıfırlanır), üstündekiler ~korunur. **Her
    zaman yeni** bir dizi döndürür.
    """
    data = _as_1d_float64(values)
    validate_cutoff(cutoff_hz, sample_rate_hz)
    validate_order(order)
    if data.size == 0:
        return data.copy()
    freqs = np.fft.rfftfreq(data.size, d=1.0 / sample_rate_hz)
    response = butterworth_highpass_response(freqs, cutoff_hz, order)
    return _apply_response(data, sample_rate_hz, response)

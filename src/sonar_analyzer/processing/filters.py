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

import math

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


def validate_band(low_cutoff_hz: float, high_cutoff_hz: float, sample_rate_hz: float) -> None:
    """Her iki sınır Nyquist içinde ve ``low < high`` olmalı — `F4-033`/`F4-034`."""
    validate_cutoff(low_cutoff_hz, sample_rate_hz)
    validate_cutoff(high_cutoff_hz, sample_rate_hz)
    if low_cutoff_hz >= high_cutoff_hz:
        raise FilterError(
            f"bant alt sınırı üst sınırdan küçük olmalı (ters bant): "
            f"{low_cutoff_hz:g} >= {high_cutoff_hz:g}"
        )


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


def validate_quality_factor(q: float) -> None:
    """Notch kalite katsayısı ``Q > 0`` ve sonlu olmalı — `F4-036`/`F4-037`."""
    if not np.isfinite(q) or q <= 0.0:
        raise FilterError(f"Q pozitif ve sonlu olmalı: {q}")


def validate_notch(center_hz: float, q: float, sample_rate_hz: float) -> None:
    """Notch merkez frekansı Nyquist içinde, ``Q`` pozitif olmalı."""
    validate_cutoff(center_hz, sample_rate_hz)
    validate_quality_factor(q)


def band_center_hz(low_cutoff_hz: float, high_cutoff_hz: float) -> float:
    """Bandın geometrik merkezi ``sqrt(f_lo * f_hi)`` — yanıtın tepe noktası."""
    return float(np.sqrt(low_cutoff_hz * high_cutoff_hz))


def notch_bandwidth_hz(center_hz: float, q: float) -> float:
    """Notch −3 dB bant genişliği ``f0 / Q``."""
    return center_hz / q


def notch_edges_hz(center_hz: float, q: float) -> tuple[float, float]:
    """Notch'un −3 dB kenarları ``(f1, f2)``.

    ``f2 - f1 = BW`` ve ``f1 * f2 = f0^2`` (geometrik çift) olacak şekilde
    çözülür; bu iki noktada kazanç tam ``1/sqrt(2)``'dir.
    """
    half = notch_bandwidth_hz(center_hz, q) / 2.0
    root = math.sqrt(half * half + center_hz * center_hz)
    return (root - half, root + half)


def butterworth_bandpass_response(
    freqs_hz: FloatArray,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
    order: int,
) -> FloatArray:
    """Bant geçiren Butterworth genlik yanıtı.

    Alçak geçiren prototipin bant geçiren dönüşümü::

        H(f) = 1 / sqrt(1 + |(f^2 - f0^2) / (f * BW)|^(2n))

    ``f0 = sqrt(f_lo * f_hi)`` (geometrik merkez), ``BW = f_hi - f_lo``.
    Değişmezler: ``H(f0) = 1``, ``H(f_lo) = H(f_hi) = 1/sqrt(2)`` (her
    ``n`` için), ``H(0) = 0``, ``f -> inf`` iken ``H -> 0``. Yanıt
    log-frekansta ``f0`` etrafında simetriktir.
    """
    freqs = np.abs(np.asarray(freqs_hz, dtype=np.float64))
    center_squared = low_cutoff_hz * high_cutoff_hz
    bandwidth = high_cutoff_hz - low_cutoff_hz
    response = np.zeros_like(freqs)
    nonzero = freqs > 0.0
    active = freqs[nonzero]
    ratio = np.abs((active**2 - center_squared) / (active * bandwidth))
    response[nonzero] = 1.0 / np.sqrt(1.0 + ratio ** (2 * order))
    return response


def butterworth_notch_response(
    freqs_hz: FloatArray,
    center_hz: float,
    q: float,
    order: int,
) -> FloatArray:
    """Bant söndüren (notch) Butterworth genlik yanıtı.

    Bant geçirenin tümleyeni::

        H(f) = 1 / sqrt(1 + |(f * BW) / (f^2 - f0^2)|^(-2n))
             = 1 / sqrt(1 + |(f^2 - f0^2) / (f * BW)|^(-2n))

    Uygulamada ``|(f * BW) / (f^2 - f0^2)|^(2n)`` biçiminde hesaplanır.
    ``BW = f0 / Q``. Değişmezler: ``H(f0) = 0`` (hedef ton tümüyle
    bastırılır), ``H(0) = 1`` (DC geçer), −3 dB kenarları
    `notch_edges_hz`'de, ``f`` uzaklaştıkça ``H -> 1``. Bant geçirenle
    güç-tümleyicidir.
    """
    freqs = np.abs(np.asarray(freqs_hz, dtype=np.float64))
    bandwidth = notch_bandwidth_hz(center_hz, q)
    denominator = freqs**2 - center_hz**2
    response = np.zeros_like(freqs)
    off_center = denominator != 0.0
    ratio = np.abs((freqs[off_center] * bandwidth) / denominator[off_center])
    response[off_center] = 1.0 / np.sqrt(1.0 + ratio ** (2 * order))
    # denominator == 0 yalnız f == f0'da olur; orada yanıt tam sıfır kalır.
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


def band_pass(
    values: NDArray[np.generic] | Samples,
    sample_rate_hz: float,
    low_cutoff_hz: float,
    high_cutoff_hz: float,
    order: int,
) -> Samples:
    """`values`'a sıfır-fazlı Butterworth bant geçiren filtre uygular.

    ``[low_cutoff_hz, high_cutoff_hz]`` bandı ~korunur; bandın altı ve
    üstü ``-20n dB/dekad`` eğimiyle bastırılır. **Her zaman yeni** bir
    dizi döndürür.
    """
    data = _as_1d_float64(values)
    validate_band(low_cutoff_hz, high_cutoff_hz, sample_rate_hz)
    validate_order(order)
    if data.size == 0:
        return data.copy()
    freqs = np.fft.rfftfreq(data.size, d=1.0 / sample_rate_hz)
    response = butterworth_bandpass_response(freqs, low_cutoff_hz, high_cutoff_hz, order)
    return _apply_response(data, sample_rate_hz, response)


def notch(
    values: NDArray[np.generic] | Samples,
    sample_rate_hz: float,
    center_hz: float,
    q: float,
    order: int,
) -> Samples:
    """`values`'a sıfır-fazlı Butterworth notch (bant söndüren) filtre uygular.

    ``center_hz`` çevresindeki dar bant (``BW = center_hz / q``)
    bastırılır; bandın dışı ~korunur. ``center_hz`` tam bir FFT binine
    denk düşerse o bileşen tümüyle sıfırlanır. **Her zaman yeni** bir
    dizi döndürür.
    """
    data = _as_1d_float64(values)
    validate_notch(center_hz, q, sample_rate_hz)
    validate_order(order)
    if data.size == 0:
        return data.copy()
    freqs = np.fft.rfftfreq(data.size, d=1.0 / sample_rate_hz)
    response = butterworth_notch_response(freqs, center_hz, q, order)
    return _apply_response(data, sample_rate_hz, response)

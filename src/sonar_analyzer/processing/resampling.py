"""Fourier tabanlı yeniden örnekleme / desimasyon — `F4-025`.

`fourier_resample` bir diziyi frekans alanında yeniden örnekler: gerçek
FFT alınır, spektrum hedef uzunluğa göre kırpılır (aşağı örnekleme) ya
da sıfırla doldurulur (yukarı örnekleme), ters FFT ile zaman alanına
dönülür. Spektrumun hedef Nyquist üstündeki kısmı **atıldığı** için
aşağı örneklemede ideal (tuğla duvar) anti-alias filtresi yerleşiktir —
yüksek frekanslı bileşenler düşük frekansa katlanmaz.

Bu `scipy.signal.resample` ile aynı yöntemdir; periyodik (tam periyot
içeren) sinyallerde yeni örnek noktalarında sürekli sinyali makine
hassasiyetinde yeniden üretir.

`fourier_resample` **çıktı uzunluğunu değiştirir**. Zincir bunu taşır
(`ChainResult.values` yeni uzunluktadır); türetilmiş kanal metadata'sına
bağlama `F4-026`.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır. FFT küreseldir: bir
``NaN`` tüm çıktıyı ``NaN`` yapar.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Samples = NDArray[np.float64]


class ResampleError(ValueError):
    """Yeniden örnekleme parametresi geçersiz (hedef uzunluk / oran <= 0 vb.)."""


def resampled_length(source_length: int, source_rate_hz: float, target_rate_hz: float) -> int:
    """`source_length` örneğin hedef orandaki uzunluğu: ``round(n * hedef / kaynak)``.

    En az 1 (kaynak boş değilse). Kaynak boşsa 0.
    """
    if source_rate_hz <= 0 or not np.isfinite(source_rate_hz):
        raise ResampleError(f"kaynak sample rate pozitif olmalı: {source_rate_hz}")
    if target_rate_hz <= 0 or not np.isfinite(target_rate_hz):
        raise ResampleError(f"hedef sample rate pozitif olmalı: {target_rate_hz}")
    if source_length <= 0:
        return 0
    scaled = source_length * float(target_rate_hz) / float(source_rate_hz)
    return max(1, int(scaled + 0.5))


def fourier_resample(values: NDArray[np.generic] | Samples, num: int) -> Samples:
    """`values`'ı `num` örneğe Fourier yöntemiyle yeniden örnekler.

    ``num == len(values)`` ise girdinin kopyası döner. **Her zaman yeni**
    bir `float64` dizi döndürür.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise ResampleError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    if num <= 0:
        raise ResampleError(f"hedef örnek sayısı pozitif olmalı: {num}")

    n = data.size
    if n == 0:
        return np.zeros(0, dtype=np.float64)
    if num == n:
        return data.copy()

    spectrum = np.fft.rfft(data)
    target_bins = num // 2 + 1
    resized = np.zeros(target_bins, dtype=np.complex128)
    keep = min(spectrum.size, target_bins)
    resized[:keep] = spectrum[:keep]

    # Aşağı örneklemede yeni dizi çift uzunluktaysa Nyquist bini gerçek
    # olmalı; kırpma sırasında oradaki enerji ikiye bölünmüş sayılır.
    if num < n and num % 2 == 0 and keep == target_bins:
        resized[-1] = resized[-1].real

    result = np.fft.irfft(resized, n=num) * (float(num) / float(n))
    return np.asarray(result, dtype=np.float64)


def resample_to_rate(
    values: NDArray[np.generic] | Samples,
    source_rate_hz: float,
    target_rate_hz: float,
) -> Samples:
    """`values`'ı `source_rate_hz`'ten `target_rate_hz`'e yeniden örnekler.

    Oranlar eşitse (ya da girdi boşsa) girdinin kopyası döner.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise ResampleError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    if source_rate_hz <= 0 or not np.isfinite(source_rate_hz):
        raise ResampleError(f"kaynak sample rate pozitif olmalı: {source_rate_hz}")
    if target_rate_hz <= 0 or not np.isfinite(target_rate_hz):
        raise ResampleError(f"hedef sample rate pozitif olmalı: {target_rate_hz}")

    if data.size == 0 or source_rate_hz == target_rate_hz:
        return data.copy()
    num = resampled_length(data.size, source_rate_hz, target_rate_hz)
    return fourier_resample(data, num)

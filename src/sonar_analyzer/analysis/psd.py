"""Welch yöntemiyle güç spektral yoğunluğu (PSD) — `F4-043`.

Sinyal örtüşen parçalara bölünür, her parça pencerelenip periyodogramı
alınır ve periyodogramlar **ortalanır**. Tek bir uzun FFT'ye göre
varyansı düşer; bedeli frekans çözünürlüğüdür (``fs / segment_length``).

Ölçekleme **yoğunluktur** (birim² / Hz)::

    P[k] = |FFT(x_seg * w)[k]|^2 / (fs * sum(w^2))

DC ve (çift parça uzunluğunda) Nyquist dışındaki binler aynadaki eşiyle
birlikte iki kat taşır. ``sum(w^2)`` bölmesi pencere güç kaybını
düzeltir; bu yüzden **entegre güç pencereden bağımsızdır**::

    sum(P) * df  ==  pencere-ağırlıklı mean(x^2)

Tam bir bine oturan ``A*sin`` tonu için bu değer tam ``A^2 / 2``'dir
(dikdörtgen pencerede de, Hann/Hamming/Blackman'da da).

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır. Sınır doğrulamaları
`F4-044`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.windows import (
    WindowError,
    WindowKind,
    resolve_kind,
    window_values,
)

FloatArray = NDArray[np.float64]

#: Parça uzunluğu verilmezse denenen üst sınır (sinyalden uzun olamaz).
DEFAULT_SEGMENT_LENGTH = 256
#: Öntanımlı örtüşme oranı (Welch'in klasik %50'si).
DEFAULT_OVERLAP = 0.5
#: `power_to_db` için öntanımlı taban.
DEFAULT_DB_FLOOR = -200.0


class PsdError(ValueError):
    """PSD parametresi geçersiz (örtüşme aralık dışı, parça sinyalden uzun, vb.)."""


@dataclass(frozen=True)
class PsdResult:
    """Welch PSD sonucu ve ekseni."""

    frequencies_hz: FloatArray
    #: Güç spektral yoğunluğu (birim^2 / Hz).
    density: FloatArray
    sample_rate_hz: float
    segment_length: int
    segment_count: int
    overlap: float
    window_kind: str

    def __len__(self) -> int:
        return int(self.density.shape[0])

    @property
    def resolution_hz(self) -> float:
        """Bin genişliği ``fs / segment_length``."""
        return self.sample_rate_hz / float(self.segment_length)

    @property
    def nyquist_hz(self) -> float:
        return self.sample_rate_hz / 2.0

    @property
    def integrated_power(self) -> float:
        """``sum(P) * df`` — bandın toplam gücü (birim^2)."""
        return float(np.sum(self.density)) * self.resolution_hz

    @property
    def peak_index(self) -> int:
        if self.density.size == 0:  # pragma: no cover - boş sonuç üretilmez
            return 0
        return int(np.argmax(self.density))

    @property
    def peak_frequency_hz(self) -> float:
        return float(self.frequencies_hz[self.peak_index])

    @property
    def peak_density(self) -> float:
        return float(self.density[self.peak_index])


def segment_step(segment_length: int, overlap: float) -> int:
    """Ardışık parçalar arasındaki kayma (örnek)."""
    # İki çarpan da negatif değil: en yakın tam sayıya yuvarla (yarımı yukarı).
    overlapped = int(float(overlap) * float(segment_length) + 0.5)
    return max(1, segment_length - overlapped)


def segment_starts(total: int, segment_length: int, overlap: float) -> list[int]:
    """Sinyale sığan tam parçaların başlangıç indeksleri."""
    step = segment_step(segment_length, overlap)
    if total < segment_length:
        return []
    return list(range(0, total - segment_length + 1, step))


def validate_overlap(overlap: float) -> None:
    """``0 <= overlap < 1`` — aksi halde `PsdError`."""
    if not np.isfinite(overlap) or overlap < 0.0 or overlap >= 1.0:
        raise PsdError(f"örtüşme 0 <= overlap < 1 aralığında olmalı: {overlap}")


def welch_psd(
    values: NDArray[np.generic] | FloatArray,
    sample_rate_hz: float,
    *,
    segment_length: int | None = None,
    overlap: float = DEFAULT_OVERLAP,
    window: WindowKind | str = WindowKind.HANN,
    detrend: bool = False,
) -> PsdResult:
    """Welch PSD'si.

    `segment_length` verilmezse ``min(len(values), 256)`` kullanılır.
    `detrend=True` her parçanın ortalamasını çıkarır (DC sızıntısını
    keser). Parça sinyalden uzunsa `PsdError` yükseltilir — sessizce
    kısaltılmaz.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise PsdError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise PsdError(f"sample rate pozitif olmalı: {sample_rate_hz}")
    if data.size == 0:
        raise PsdError("boş sinyalin PSD'si tanımsız")
    validate_overlap(overlap)

    length = min(data.size, DEFAULT_SEGMENT_LENGTH) if segment_length is None else segment_length
    if length < 1:
        raise PsdError(f"parça uzunluğu >= 1 olmalı: {length}")
    if length > data.size:
        raise PsdError(f"parça uzunluğu ({length}) sinyalden ({data.size}) uzun olamaz")

    try:
        resolved_window = resolve_kind(window)
        coefficients = window_values(resolved_window, length)
    except WindowError as exc:
        raise PsdError(str(exc)) from exc
    window_power = float(np.square(coefficients).sum())
    if window_power == 0.0:  # pragma: no cover - desteklenen pencerelerde olmaz
        raise PsdError("pencere gücü sıfır; yoğunluk ölçeklemesi tanımsız")

    starts = segment_starts(data.size, length, overlap)
    bins = length // 2 + 1
    accumulator = np.zeros(bins, dtype=np.float64)
    for start in starts:
        segment = data[start : start + length]
        if detrend:
            segment = segment - segment.mean()
        spectrum = np.fft.rfft(segment * coefficients)
        accumulator += np.square(np.abs(spectrum))

    density = accumulator / (len(starts) * sample_rate_hz * window_power)
    if bins > 1:
        density[1:] *= 2.0
        if length % 2 == 0:
            density[-1] /= 2.0

    return PsdResult(
        frequencies_hz=np.fft.rfftfreq(length, d=1.0 / sample_rate_hz),
        density=np.asarray(density, dtype=np.float64),
        sample_rate_hz=float(sample_rate_hz),
        segment_length=length,
        segment_count=len(starts),
        overlap=float(overlap),
        window_kind=resolved_window.value,
    )


def power_to_db(
    density: NDArray[np.generic] | FloatArray,
    *,
    reference: float = 1.0,
    floor_db: float = DEFAULT_DB_FLOOR,
) -> FloatArray:
    """Gücü dB'ye çevirir: ``10 * log10(P / reference)``.

    Genlik değil **güç** ölçeklendiği için katsayı 10'dur (genlik için
    `analysis.spectrum.amplitude_to_db` 20 kullanır). Sıfır güç ``-inf``
    yerine `floor_db`'de durur; NaN girdi NaN kalır.
    """
    values = np.asarray(density, dtype=np.float64)
    if not np.isfinite(reference) or reference <= 0:
        raise PsdError(f"dB referansı pozitif olmalı: {reference}")
    if np.any(values[np.isfinite(values)] < 0.0):
        raise PsdError("güç negatif olamaz")

    floor_power = reference * 10.0 ** (floor_db / 10.0)
    clipped = np.maximum(values, floor_power)
    result = 10.0 * np.log10(clipped / reference)
    return np.asarray(np.where(np.isnan(values), np.nan, result), dtype=np.float64)

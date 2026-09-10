"""Kısa zamanlı Fourier dönüşümü (STFT) ve spektrogram matrisi — `F4-046`.

Sinyal örtüşen parçalara bölünür, her parça pencerelenip tek taraflı
FFT'si alınır ve sonuçlar bir **matris** hâline getirilir::

    magnitudes[frekans_satiri, zaman_sutunu]

* Satırlar (`frequencies_hz`) — ``numpy.fft.rfftfreq(segment_length, 1/fs)``.
* Sütunlar (`times_s`) — her parçanın **merkezinin** zamanı:
  ``(start + segment_length / 2) / fs``. Merkez seçimi, bir tonun
  spektrogramdaki konumunun zaman ekseninde kaymamasını sağlar
  (`F4-047`).

Büyüklük ölçeklemesi `analysis.spectrum.one_sided_fft` ile aynıdır
(genlik): tam bine oturan ``A*sin`` tonu ilgili hücrede ``A`` okur. DC ve
(çift parça uzunluğunda) Nyquist satırı iki katı alınmaz.

Parçalama `analysis.psd` ile ortaktır (`segment_starts`); PSD zaten
STFT büyüklüklerinin karesinin ortalamasıdır.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır. Kenar/eksen doğrulamaları
`F4-047`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.psd import segment_starts, segment_step, validate_overlap
from sonar_analyzer.analysis.windows import (
    WindowError,
    WindowKind,
    resolve_kind,
    window_values,
)

FloatArray = NDArray[np.float64]
Matrix = NDArray[np.float64]

#: Parça uzunluğu verilmezse denenen üst sınır (sinyalden uzun olamaz).
DEFAULT_SEGMENT_LENGTH = 256
#: Öntanımlı örtüşme oranı.
DEFAULT_OVERLAP = 0.5


class StftError(ValueError):
    """STFT parametresi geçersiz (parça sinyalden uzun, örtüşme aralık dışı, vb.)."""


@dataclass(frozen=True)
class StftResult:
    """Spektrogram matrisi ve iki ekseni."""

    #: Satır ekseni (Hz), uzunluk ``segment_length // 2 + 1``.
    frequencies_hz: FloatArray
    #: Sütun ekseni (s) — parça merkezleri.
    times_s: FloatArray
    #: ``(frekans, zaman)`` biçiminde genlik matrisi.
    magnitudes: Matrix
    sample_rate_hz: float
    segment_length: int
    hop: int
    overlap: float
    window_kind: str

    @property
    def bin_count(self) -> int:
        return int(self.magnitudes.shape[0])

    @property
    def frame_count(self) -> int:
        return int(self.magnitudes.shape[1])

    @property
    def resolution_hz(self) -> float:
        """Satır aralığı ``fs / segment_length``."""
        return self.sample_rate_hz / float(self.segment_length)

    @property
    def time_step_s(self) -> float:
        """Sütun aralığı ``hop / fs``."""
        return self.hop / self.sample_rate_hz

    @property
    def nyquist_hz(self) -> float:
        return self.sample_rate_hz / 2.0

    def peak_frequencies_hz(self) -> FloatArray:
        """Her zaman sütununun en güçlü frekans satırı."""
        if self.frame_count == 0:  # pragma: no cover - boş sonuç üretilmez
            return np.empty(0, dtype=np.float64)
        rows = np.argmax(self.magnitudes, axis=0)
        return np.asarray(self.frequencies_hz[rows], dtype=np.float64)

    def frame(self, index: int) -> FloatArray:
        """`index`. zaman sütununun spektrumu."""
        return np.asarray(self.magnitudes[:, index], dtype=np.float64)


def stft(
    values: NDArray[np.generic] | FloatArray,
    sample_rate_hz: float,
    *,
    segment_length: int | None = None,
    overlap: float = DEFAULT_OVERLAP,
    window: WindowKind | str = WindowKind.HANN,
) -> StftResult:
    """`values`'ın spektrogram matrisi.

    `segment_length` verilmezse ``min(len(values), 256)`` kullanılır.
    Parça sinyalden uzunsa `StftError` yükseltilir — sessizce
    kısaltılmaz. Yalnız **tam** parçalar kullanılır; sinyalin sonunda
    artan kısım (bir parçaya yetmiyorsa) sütun üretmez.
    """
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise StftError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise StftError(f"sample rate pozitif olmalı: {sample_rate_hz}")
    if data.size == 0:
        raise StftError("boş sinyalin STFT'si tanımsız")
    try:
        validate_overlap(overlap)
    except ValueError as exc:
        raise StftError(str(exc)) from exc

    length = min(data.size, DEFAULT_SEGMENT_LENGTH) if segment_length is None else segment_length
    if length < 1:
        raise StftError(f"parça uzunluğu >= 1 olmalı: {length}")
    if length > data.size:
        raise StftError(f"parça uzunluğu ({length}) sinyalden ({data.size}) uzun olamaz")

    try:
        resolved_window = resolve_kind(window)
        coefficients = window_values(resolved_window, length)
    except WindowError as exc:
        raise StftError(str(exc)) from exc
    total = float(coefficients.sum())
    if total == 0.0:  # pragma: no cover - desteklenen pencerelerde olmaz
        raise StftError("pencere toplamı sıfır; genlik ölçeklemesi tanımsız")

    starts = segment_starts(data.size, length, overlap)
    bins = length // 2 + 1
    magnitudes = np.empty((bins, len(starts)), dtype=np.float64)
    for column, start in enumerate(starts):
        spectrum = np.fft.rfft(data[start : start + length] * coefficients)
        magnitudes[:, column] = np.abs(spectrum) / total
    if bins > 1:
        magnitudes[1:, :] *= 2.0
        if length % 2 == 0:
            magnitudes[-1, :] /= 2.0

    centers = (np.asarray(starts, dtype=np.float64) + length / 2.0) / sample_rate_hz
    return StftResult(
        frequencies_hz=np.fft.rfftfreq(length, d=1.0 / sample_rate_hz),
        times_s=np.asarray(centers, dtype=np.float64),
        magnitudes=magnitudes,
        sample_rate_hz=float(sample_rate_hz),
        segment_length=length,
        hop=segment_step(length, overlap),
        overlap=float(overlap),
        window_kind=resolved_window.value,
    )

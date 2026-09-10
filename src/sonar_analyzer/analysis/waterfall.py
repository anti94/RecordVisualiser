"""Waterfall zaman dilimi modeli — `F4-050`.

Bir waterfall, art arda gelen spektrum **dilimlerini** zaman sırasıyla
biriktirir. Kayıt uzadıkça bellek büyümesin diye geçmiş **sınırlıdır**:
model kurulurken verilen `max_slices` kadar dilim tutulur; sınır dolduktan
sonra her yeni dilim en eskisini düşürür (FIFO).

İki değişmez:

1. **Yeni dilim her zaman eklenir.** Sınır dolu olsa bile `append`
   sessizce düşmez; en yeni dilim daima modeldedir.
2. **Sınır korunur.** ``len(model) <= max_slices`` her zaman doğrudur;
   `capacity` hiç değişmez.

Dilimler zamanda **ileri** gelmelidir; geriye giden bir damga
`WaterfallError` verir (seçim değiştiğinde çağıran `clear()` eder).
Halka tampon kullanılır: ekleme O(1)'dir, dizi kopyalanmaz.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.stft import StftResult

FloatArray = NDArray[np.float64]

#: Öntanımlı geçmiş sınırı (dilim sayısı).
DEFAULT_MAX_SLICES = 256


class WaterfallError(ValueError):
    """Waterfall dilimi ya da yapılandırması geçersiz."""


@dataclass(frozen=True)
class WaterfallSlice:
    """Tek bir zaman dilimi: damgası ve spektrumu."""

    time_s: float
    magnitudes: FloatArray


class WaterfallModel:
    """Sınırlı geçmişli, zaman sıralı spektrum dilimi tamponu."""

    def __init__(self, bin_count: int, max_slices: int = DEFAULT_MAX_SLICES) -> None:
        if bin_count < 1:
            raise WaterfallError(f"bin sayısı >= 1 olmalı: {bin_count}")
        if max_slices < 1:
            raise WaterfallError(f"geçmiş sınırı >= 1 olmalı: {max_slices}")
        self._bin_count = int(bin_count)
        self._capacity = int(max_slices)
        self._buffer: FloatArray = np.zeros((self._capacity, self._bin_count), dtype=np.float64)
        self._times: FloatArray = np.zeros(self._capacity, dtype=np.float64)
        self._count = 0
        self._start = 0

    # -- yapılandırma ------------------------------------------------------

    @property
    def bin_count(self) -> int:
        return self._bin_count

    @property
    def capacity(self) -> int:
        """Tutulan en fazla dilim sayısı — kurulduktan sonra değişmez."""
        return self._capacity

    @property
    def is_full(self) -> bool:
        return self._count == self._capacity

    def __len__(self) -> int:
        return self._count

    # -- ekleme ------------------------------------------------------------

    def append(self, time_s: float, magnitudes: NDArray[np.generic] | FloatArray) -> None:
        """Yeni bir dilim ekler; sınır doluysa en eskisini düşürür.

        `magnitudes` uzunluğu `bin_count` olmalı ve `time_s` son dilimden
        büyük olmalıdır; aksi halde `WaterfallError`.
        """
        values = np.asarray(magnitudes, dtype=np.float64)
        if values.ndim != 1:
            raise WaterfallError(f"dilim tek boyutlu olmalı, boyut {values.ndim}")
        if values.shape[0] != self._bin_count:
            raise WaterfallError(f"dilim {self._bin_count} bin taşımalı, {values.shape[0]} geldi")
        if not np.isfinite(time_s):
            raise WaterfallError(f"dilim zamanı sonlu olmalı: {time_s}")
        if self._count and float(time_s) <= self.newest_time_s():
            raise WaterfallError(
                f"dilimler zamanda ileri gelmeli: {time_s} <= {self.newest_time_s()}"
            )

        index = (self._start + self._count) % self._capacity
        if self.is_full:
            # En eski dilim düşer; yazma konumu tam onun yeri.
            index = self._start
            self._start = (self._start + 1) % self._capacity
        else:
            self._count += 1
        self._buffer[index] = values
        self._times[index] = float(time_s)

    def extend_from_stft(self, result: StftResult) -> int:
        """Bir STFT sonucunun tüm sütunlarını dilim olarak ekler.

        Eklenen dilim sayısını döndürür. Satır sayısı modelin
        `bin_count`'una uymuyorsa `WaterfallError`.
        """
        if result.bin_count != self._bin_count:
            raise WaterfallError(
                f"STFT {result.bin_count} bin taşıyor, model {self._bin_count} bekliyor"
            )
        for column in range(result.frame_count):
            self.append(float(result.times_s[column]), result.magnitudes[:, column])
        return result.frame_count

    def clear(self) -> None:
        """Tüm geçmişi düşürür; kapasite değişmez."""
        self._count = 0
        self._start = 0

    # -- okuma -------------------------------------------------------------

    def _order(self) -> NDArray[np.intp]:
        return np.asarray(
            (self._start + np.arange(self._count, dtype=np.intp)) % self._capacity, dtype=np.intp
        )

    def matrix(self) -> FloatArray:
        """Dilimler ``(dilim, bin)`` biçiminde, **en eski önce**."""
        if self._count == 0:
            return np.zeros((0, self._bin_count), dtype=np.float64)
        return np.asarray(self._buffer[self._order()], dtype=np.float64)

    def times_s(self) -> FloatArray:
        """Dilim damgaları, en eski önce."""
        if self._count == 0:
            return np.zeros(0, dtype=np.float64)
        return np.asarray(self._times[self._order()], dtype=np.float64)

    def slice_at(self, index: int) -> WaterfallSlice:
        """`index`. dilim (0 = en eski)."""
        if not 0 <= index < self._count:
            raise WaterfallError(f"dilim indeksi aralık dışı: {index}")
        position = int((self._start + index) % self._capacity)
        return WaterfallSlice(
            time_s=float(self._times[position]),
            magnitudes=np.asarray(self._buffer[position], dtype=np.float64).copy(),
        )

    def newest(self) -> WaterfallSlice:
        """En son eklenen dilim."""
        if self._count == 0:
            raise WaterfallError("waterfall boş; en yeni dilim yok")
        return self.slice_at(self._count - 1)

    def oldest(self) -> WaterfallSlice:
        """Tutulan en eski dilim."""
        if self._count == 0:
            raise WaterfallError("waterfall boş; en eski dilim yok")
        return self.slice_at(0)

    def newest_time_s(self) -> float:
        """En son dilimin damgası."""
        if self._count == 0:
            raise WaterfallError("waterfall boş; en yeni damga yok")
        return float(self._times[(self._start + self._count - 1) % self._capacity])

    def oldest_time_s(self) -> float:
        if self._count == 0:
            raise WaterfallError("waterfall boş; en eski damga yok")
        return float(self._times[self._start])

    def time_span_s(self) -> float:
        """Tutulan geçmişin süresi (tek dilimde 0)."""
        if self._count == 0:
            raise WaterfallError("waterfall boş; süre tanımsız")
        return self.newest_time_s() - self.oldest_time_s()

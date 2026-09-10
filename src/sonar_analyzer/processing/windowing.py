"""Kayan pencere hesapları — `F4-017` (moving average), `F4-021`+ (RMS/envelope).

`moving_average` **merkezli** bir kayan pencere ortalamasıdır ve çıktı
uzunluğu girdiyle birebir aynıdır. Pencere ve kenar davranışı tam olarak
tanımlıdır:

Pencere yerleşimi
    ``i``. örneğin penceresi ``[i - window // 2, i + (window - 1) // 2]``
    aralığını (kapsayıcı) örter, dizi sınırlarına kırpılır. Tek pencerede
    aralık simetriktir; **çift** pencerede sola yaslanır (bir fazladan
    *geçmiş* örnek girer) — ``numpy.convolve(..., "same")`` ile aynı
    merkezleme.

Kenar davranışı (``edges``)
    * ``"shrink"`` (öntanımlı) — sınıra yakın konumlarda pencere yalnız
      dizideki mevcut örneklere daralır (kısmi ortalama). Uzunluk korunur.
    * ``"nan"`` — tam pencerenin sığmadığı sınır konumları ``NaN`` olur.

``NaN`` yayılımı
    Girdideki bir ``NaN``, penceresi onu içeren **her** çıktı konumuna
    yayılır (``window`` komşuya kadar). Etrafından ortalama alınıp
    "iyileştirilmez" — `F4-005` politikasıyla tutarlı. Yayılım
    **yereldir**: kümülatif toplam kullanılmaz, bu yüzden ``NaN`` pencere
    dışındaki konumları etkilemez.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Samples = NDArray[np.float64]

EDGE_SHRINK = "shrink"
EDGE_NAN = "nan"
#: `moving_average` için geçerli kenar modları.
EDGE_MODES: tuple[str, ...] = (EDGE_SHRINK, EDGE_NAN)

#: Kabul edilen en küçük pencere.
MIN_WINDOW = 1
#: Mutlak üst sınır. Bunun ötesindeki pencere "aşırı" sayılır ve
#: `validate_window` tarafından reddedilir (`F4-018` bunu işlem öncesi
#: kontrole bağlar).
MAX_WINDOW = 1_000_000


class WindowingError(ValueError):
    """Pencere parametresi geçersiz (aralık dışı, tam sayı değil, vb.)."""


def validate_window(window: int, *, maximum: int = MAX_WINDOW) -> int:
    """`window`'u sınırlara karşı doğrular; sorun varsa `WindowingError`.

    Sıfır, negatif, `bool` ve `maximum`'u aşan pencereler reddedilir —
    "sıfır veya aşırı pencere işlem başlamadan reddedilir" (`F4-018`).
    """
    if isinstance(window, bool):
        raise WindowingError(f"pencere tam sayı olmalı: {window!r}")
    if window < MIN_WINDOW:
        raise WindowingError(f"pencere >= {MIN_WINDOW} olmalı: {window}")
    if window > maximum:
        raise WindowingError(f"pencere <= {maximum} olmalı (aşırı pencere): {window}")
    return window


def _as_1d_float64(values: NDArray[np.generic] | Samples) -> Samples:
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise WindowingError(f"örnek dizisi tek boyutlu olmalı, boyut {data.ndim}")
    return data


def moving_average(
    values: NDArray[np.generic] | Samples,
    window: int,
    *,
    edges: str = EDGE_SHRINK,
) -> Samples:
    """Merkezli kayan pencere ortalaması; **her zaman yeni** bir dizi döndürür.

    Ayrıntılı sözleşme için modül belge metnine bakın.
    """
    data = _as_1d_float64(values)
    validate_window(window)
    if edges not in EDGE_MODES:
        raise WindowingError(f"bilinmeyen kenar modu: {edges!r} (geçerli: {list(EDGE_MODES)})")

    if window == 1 or data.size == 0:
        return data.copy()

    # `mode="same"` çekirdek diziden uzunken çıktı uzunluğunu bozar
    # (max(M, N) döndürür). Bunun yerine tam evrişimden merkezlenmiş
    # `data.size` uzunluğunda dilim alınır — her pencere boyutu için
    # doğru merkezleme: `[i - window // 2, i + (window - 1) // 2]`.
    kernel = np.ones(window, dtype=np.float64)
    start = (window - 1) // 2
    stop = start + data.size
    totals = np.convolve(data, kernel)[start:stop]
    counts = np.convolve(np.ones(data.size, dtype=np.float64), kernel)[start:stop]
    result = totals / counts

    if edges == EDGE_NAN:
        result = np.where(counts < window, np.nan, result)
    return np.asarray(result, dtype=np.float64)

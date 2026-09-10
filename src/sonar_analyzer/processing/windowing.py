"""Kayan pencere hesapları — `F4-017` (moving average), `F4-021` (RMS/zarf).

`moving_average` **merkezli** bir kayan pencere ortalamasıdır ve çıktı
uzunluğu girdiyle birebir aynıdır. `windowed_rms` ve `windowed_envelope`
aynı merkezleme, kenar ve NaN sözleşmesini paylaşır:

* ``windowed_rms(x, w)`` = ``sqrt(moving_average(x**2, w))`` — pencere
  içindeki karesel ortalamanın kökü. Sabit genlikli sinyalde (DC ya da
  kare dalga) sonuç genliğin kendisidir; genlik ``A`` sinüste ``A/√2``.
* ``windowed_envelope(x, w)`` = kayan pencerede ``|x|`` **tepesi**
  (peak-hold zarf). Sabit genlikli sinyalde sonuç genliğin kendisidir.

Pencere ve kenar davranışı tam olarak tanımlıdır:

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


def samples_for_duration(
    duration_s: float,
    sample_rate_hz: float,
    *,
    minimum: int = MIN_WINDOW,
) -> int:
    """Bir pencere **süresini** (saniye) örnek sayısına çevirir — `F4-022`.

    ``round(duration_s * sample_rate_hz)`` (en yakın örnek), en az
    ``minimum``. Üst sınır burada uygulanmaz; "aşırı pencere" denetimi
    `ProcessingStep` / `validate_window` işidir.
    """
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise WindowingError(f"pencere süresi pozitif olmalı: {duration_s}")
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise WindowingError(f"sample rate pozitif olmalı: {sample_rate_hz}")
    # Her iki çarpan da pozitif: en yakın tam sayıya yuvarla (yarımı yukarı).
    return max(minimum, int(float(duration_s) * float(sample_rate_hz) + 0.5))


def duration_for_samples(window: int, sample_rate_hz: float) -> float:
    """`window` örneğin `sample_rate_hz`'te karşılık geldiği süre (saniye)."""
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise WindowingError(f"sample rate pozitif olmalı: {sample_rate_hz}")
    return window / sample_rate_hz


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


def _full_window_mask(size: int, window: int) -> NDArray[np.bool_]:
    """Tam pencerenin sığdığı konumlar için `True` (kenar `nan` modu)."""
    mask = np.zeros(size, dtype=np.bool_)
    left = window // 2
    right = window - 1 - left
    if left + right < size:
        mask[left : size - right] = True
    return mask


def windowed_rms(
    values: NDArray[np.generic] | Samples,
    window: int,
    *,
    edges: str = EDGE_SHRINK,
) -> Samples:
    """Merkezli kayan pencere RMS'i: ``sqrt(mean(x**2))`` pencere içinde.

    Sabit genlikli sinyalde (DC / kare dalga) sonuç genliğin kendisidir.
    Kenar ve NaN davranışı `moving_average` ile aynıdır (kare alınmış
    diziye uygulanır). **Her zaman yeni** bir dizi döndürür.
    """
    data = _as_1d_float64(values)
    mean_square = moving_average(np.square(data), window, edges=edges)
    # Kare ortalaması negatif olamaz; kayan-nokta gürültüsüne karşı kırp.
    return np.sqrt(np.maximum(mean_square, 0.0))


def windowed_envelope(
    values: NDArray[np.generic] | Samples,
    window: int,
    *,
    edges: str = EDGE_SHRINK,
) -> Samples:
    """Merkezli kayan pencere tepe-tutma zarfı: pencere içinde ``max(|x|)``.

    Sabit genlikli sinyalde sonuç genliğin kendisidir; genlik ``A``
    sinüste, pencere en az yarım periyot ise ``A``'ya yakınsar.

    Kenar davranışı `moving_average` ile aynı: ``"shrink"`` uçlarda
    pencereyi mevcut örneklere daraltır, ``"nan"`` tam pencerenin
    sığmadığı konumları ``NaN`` yapar. Bir girdi ``NaN``'ı yalnız
    penceresi onu içeren konumlara yayılır (yerel). **Her zaman yeni**
    bir dizi döndürür.
    """
    data = _as_1d_float64(values)
    validate_window(window)
    if edges not in EDGE_MODES:
        raise WindowingError(f"bilinmeyen kenar modu: {edges!r} (geçerli: {list(EDGE_MODES)})")

    if window == 1 or data.size == 0:
        return np.abs(data)

    magnitude = np.abs(data)
    left = window // 2
    right = window - 1 - left
    # Kenarları -inf ile doldur: kısmi pencerelerde yalnız gerçek örnekler
    # tepeyi belirler (-inf asla kazanmaz). NaN pencerede kalırsa `max`
    # onu yayar (yerel kontaminasyon).
    padded = np.concatenate(
        [
            np.full(left, -np.inf, dtype=np.float64),
            magnitude,
            np.full(right, -np.inf, dtype=np.float64),
        ]
    )
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)
    result = np.asarray(windows.max(axis=-1), dtype=np.float64)

    if edges == EDGE_NAN:
        result = np.where(_full_window_mask(data.size, window), result, np.nan)
    return np.asarray(result, dtype=np.float64)

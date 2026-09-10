"""Spektral analiz pencereleri ve normalizasyon katsayıları — `F4-039`.

Bir FFT penceresi sinyali kırparken kenarları yumuşatır; bunun bedeli
**kazanç kaybıdır**. İki farklı düzeltme kullanılır:

Genlik (coherent gain) düzeltmesi
    Pencerelenmiş bir **tek tonun** tepe genliğini geri kazandırır.
    ``CG = mean(w)``; düzeltme katsayısı ``1 / CG``.

Enerji (power) düzeltmesi
    Pencerelenmiş bir **geniş bantlı** sinyalin toplam gücünü geri
    kazandırır. ``mean(w^2)``'nin karekökü kadar kayıp olur; düzeltme
    katsayısı ``1 / sqrt(mean(w^2))``.

Eşdeğer gürültü bant genişliği (ENBW)
    ``N * sum(w^2) / (sum(w))^2`` — PSD'de bin genişliğinin kaç katının
    gürültüye açık olduğunu verir (`F4-043`).

Bu modül **periyodik** (``sym=False``) pencere üretir; spektral analizin
standardı budur ve katsayıları tam sayısal değerlere oturur (örn.
periyodik Hann için ``mean(w) = 0.5`` ve ``mean(w^2) = 0.375``
**birebir**). `REFERENCE_COHERENT_GAIN` / `REFERENCE_MEAN_SQUARE` /
`REFERENCE_ENBW` tabloları bu bilinen referans değerleri taşır.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class WindowError(ValueError):
    """Pencere parametresi geçersiz (bilinmeyen tür, uzunluk < 1, vb.)."""


class WindowKind(str, Enum):
    """Desteklenen pencere türleri."""

    RECTANGULAR = "rectangular"
    HANN = "hann"
    HAMMING = "hamming"
    BLACKMAN = "blackman"


#: Combobox / serileştirme sırası.
WINDOW_KINDS: tuple[str, ...] = tuple(kind.value for kind in WindowKind)


class WindowNormalization(str, Enum):
    """Pencereye uygulanan normalizasyon."""

    NONE = "none"
    AMPLITUDE = "amplitude"
    ENERGY = "energy"


WINDOW_NORMALIZATIONS: tuple[str, ...] = tuple(mode.value for mode in WindowNormalization)

#: Periyodik pencerelerin bilinen ``mean(w)`` (coherent gain) değerleri.
REFERENCE_COHERENT_GAIN: dict[WindowKind, float] = {
    WindowKind.RECTANGULAR: 1.0,
    WindowKind.HANN: 0.5,
    WindowKind.HAMMING: 0.54,
    WindowKind.BLACKMAN: 0.42,
}

#: Periyodik pencerelerin bilinen ``mean(w^2)`` değerleri.
#: Hann: 0.375; Hamming: 0.54^2 + 0.46^2/2; Blackman: 0.42^2 + 0.5^2/2 + 0.08^2/2.
REFERENCE_MEAN_SQUARE: dict[WindowKind, float] = {
    WindowKind.RECTANGULAR: 1.0,
    WindowKind.HANN: 0.375,
    WindowKind.HAMMING: 0.54**2 + 0.46**2 / 2.0,
    WindowKind.BLACKMAN: 0.42**2 + 0.5**2 / 2.0 + 0.08**2 / 2.0,
}

#: ``ENBW = mean(w^2) / mean(w)^2`` — yukarıdaki iki tablodan türer.
REFERENCE_ENBW: dict[WindowKind, float] = {
    kind: REFERENCE_MEAN_SQUARE[kind] / REFERENCE_COHERENT_GAIN[kind] ** 2 for kind in WindowKind
}


def resolve_kind(kind: WindowKind | str) -> WindowKind:
    """Metin ya da enum'u `WindowKind`'e çevirir; tanınmazsa `WindowError`."""
    if isinstance(kind, WindowKind):
        return kind
    try:
        return WindowKind(str(kind))
    except ValueError as exc:
        raise WindowError(
            f"bilinmeyen pencere türü: {kind!r} (geçerli: {list(WINDOW_KINDS)})"
        ) from exc


def window_values(
    kind: WindowKind | str,
    length: int,
    *,
    periodic: bool = True,
) -> FloatArray:
    """`length` örneklik pencere katsayıları.

    ``periodic=True`` (öntanımlı) spektral analizin standardıdır:
    ``cos`` argümanı ``2*pi*n/N`` ile ilerler ve pencerenin son örneği
    ilk örneğe **eşit değildir** (dairesel sürekli). ``periodic=False``
    simetrik (filtre tasarımı) biçimi verir.
    """
    resolved = resolve_kind(kind)
    if length < 1:
        raise WindowError(f"pencere uzunluğu >= 1 olmalı: {length}")
    if length == 1:
        return np.ones(1, dtype=np.float64)

    denominator = float(length) if periodic else float(length - 1)
    n = np.arange(length, dtype=np.float64)
    angle = 2.0 * np.pi * n / denominator

    if resolved is WindowKind.RECTANGULAR:
        return np.ones(length, dtype=np.float64)
    if resolved is WindowKind.HANN:
        return np.asarray(0.5 - 0.5 * np.cos(angle), dtype=np.float64)
    if resolved is WindowKind.HAMMING:
        return np.asarray(0.54 - 0.46 * np.cos(angle), dtype=np.float64)
    # BLACKMAN
    return np.asarray(0.42 - 0.5 * np.cos(angle) + 0.08 * np.cos(2.0 * angle), dtype=np.float64)


def coherent_gain(window: FloatArray) -> float:
    """``mean(w)`` — pencerelenmiş tek tonun genlik kaybı çarpanı."""
    values = np.asarray(window, dtype=np.float64)
    if values.size == 0:
        raise WindowError("boş pencere için kazanç tanımsız")
    return float(values.mean())


def mean_square(window: FloatArray) -> float:
    """``mean(w^2)`` — pencerelenmiş geniş bantlı sinyalin güç kaybı çarpanı."""
    values = np.asarray(window, dtype=np.float64)
    if values.size == 0:
        raise WindowError("boş pencere için güç tanımsız")
    return float(np.mean(np.square(values)))


def amplitude_correction(window: FloatArray) -> float:
    """Genlik düzeltme katsayısı ``1 / mean(w)``."""
    gain = coherent_gain(window)
    if gain == 0.0:
        raise WindowError("coherent gain sıfır; genlik düzeltmesi tanımsız")
    return 1.0 / gain


def energy_correction(window: FloatArray) -> float:
    """Enerji düzeltme katsayısı ``1 / sqrt(mean(w^2))``."""
    power = mean_square(window)
    if power <= 0.0:
        raise WindowError("pencere gücü sıfır; enerji düzeltmesi tanımsız")
    return 1.0 / float(np.sqrt(power))


def equivalent_noise_bandwidth(window: FloatArray) -> float:
    """``N * sum(w^2) / (sum(w))^2`` — bin cinsinden eşdeğer gürültü bandı."""
    values = np.asarray(window, dtype=np.float64)
    if values.size == 0:
        raise WindowError("boş pencere için ENBW tanımsız")
    total = float(values.sum())
    if total == 0.0:
        raise WindowError("pencere toplamı sıfır; ENBW tanımsız")
    return float(values.size) * float(np.square(values).sum()) / (total * total)


def correction_factor(
    window: FloatArray,
    normalization: WindowNormalization | str = WindowNormalization.NONE,
) -> float:
    """`normalization` için uygulanacak çarpan."""
    mode = (
        normalization
        if isinstance(normalization, WindowNormalization)
        else _resolve_normalization(normalization)
    )
    if mode is WindowNormalization.NONE:
        return 1.0
    if mode is WindowNormalization.AMPLITUDE:
        return amplitude_correction(window)
    return energy_correction(window)


def _resolve_normalization(mode: str) -> WindowNormalization:
    try:
        return WindowNormalization(str(mode))
    except ValueError as exc:
        raise WindowError(
            f"bilinmeyen normalizasyon: {mode!r} (geçerli: {list(WINDOW_NORMALIZATIONS)})"
        ) from exc


def normalized_window(
    kind: WindowKind | str,
    length: int,
    *,
    normalization: WindowNormalization | str = WindowNormalization.NONE,
    periodic: bool = True,
) -> FloatArray:
    """Düzeltme katsayısı uygulanmış pencere.

    ``amplitude`` normalizasyonunda ``mean(w) == 1``, ``energy``
    normalizasyonunda ``mean(w^2) == 1`` olur.
    """
    values = window_values(kind, length, periodic=periodic)
    return values * correction_factor(values, normalization)

"""Piksel genişliğine göre nokta bütçesi — `F4-055`.

Bir grafik, ekranda kaç piksel genişse en fazla o kadar **ayırt edilebilir**
sütun gösterebilir. Her sütun için bir min ve bir max noktası yeterlidir
(dar impulslar böyle görünür kalır, `F4-056`); bu yüzden bütçe
``2 × piksel`` olarak seçilir. Daha fazlasını çekmek ne çözünürlük
kazandırır ne de görünümü değiştirir — yalnız okuma ve çizim maliyeti
artar.

    max_points = clamp(pixels * POINTS_PER_PIXEL, MIN_POINTS, MAX_POINTS)

Alt sınır, panel henüz yerleşmemişken (genişlik birkaç piksel) grafiğin
tamamen boşalmamasını sağlar; üst sınır, çok geniş ekranlarda tek
sorgunun sınırsız büyümesini engeller.

Saf aritmetik — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

#: Piksel başına nokta: bir min + bir max.
POINTS_PER_PIXEL = 2
#: Panel yerleşmemişken bile anlamlı bir görünüm için alt sınır.
MIN_POINTS = 64
#: Tek sorgunun üst sınırı (çok geniş ekranlarda bile).
MAX_POINTS = 20_000


class PointBudgetError(ValueError):
    """Piksel genişliği geçersiz (pozitif değil)."""


def points_for_width(
    pixel_width: int,
    *,
    points_per_pixel: int = POINTS_PER_PIXEL,
    minimum: int = MIN_POINTS,
    maximum: int = MAX_POINTS,
) -> int:
    """`pixel_width` piksellik bir grafiğin nokta bütçesi.

    Sonuç her zaman ``[minimum, maximum]`` aralığındadır ve `pixel_width`
    büyüdükçe azalmaz (monoton).
    """
    if pixel_width <= 0:
        raise PointBudgetError(f"piksel genişliği pozitif olmalı: {pixel_width}")
    if points_per_pixel <= 0:
        raise PointBudgetError(f"piksel başına nokta pozitif olmalı: {points_per_pixel}")
    if minimum <= 0 or maximum < minimum:
        raise PointBudgetError(f"bütçe sınırları geçersiz: [{minimum}, {maximum}]")
    return min(max(pixel_width * points_per_pixel, minimum), maximum)


def fits_budget(point_count: int, pixel_width: int, **options: int) -> bool:
    """`point_count`, `pixel_width` için hesaplanan bütçeye sığıyor mu?"""
    return point_count <= points_for_width(pixel_width, **options)

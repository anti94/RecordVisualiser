"""Pencere konumlarını ekranlara sınırlama — `F4-083`.

Kullanıcı pencereyi ikinci bir monitöre taşıyıp kapattığında konum
kaydedilir. O monitör sökülmüşse kaydedilen konum artık **hiçbir ekranın
üstünde değildir** ve pencere görünmez bir yerde açılır: kullanıcı
uygulamanın açılmadığını sanır.

Bu modül o durumu düzeltir. Saf geometridir — Qt yok, ekran listesi
dışarıdan verilir, `GUI olmadan` doğrulanır.

**Kural.** Kaydedilen dikdörtgenin ekranlarla kesişen alanı, kendi
alanının `MIN_VISIBLE_FRACTION`'ından azsa (ya da mutlak eşik
`MIN_VISIBLE_PIXELS`'ten küçükse) pencere "kayıp" sayılır ve bir hedef
ekranın içine taşınır. Hedef, en çok kesişen ekrandır; hiç kesişme yoksa
**birinci** ekran (birincil monitör) seçilir.

Taşıma **boyutu korur**; hedef ekrana sığmıyorsa önce küçültülür.
Pencereyi gereksiz yere yeniden konumlandırmamak için, yeterince görünen
bir dikdörtgene hiç dokunulmaz — kullanıcının yerleşimi korunur.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

#: Pencerenin en az bu kadarı bir ekranda görünmeli.
MIN_VISIBLE_FRACTION = 0.25
#: Çok büyük pencerelerde oran yetmez; mutlak bir taban da gerekir.
MIN_VISIBLE_PIXELS = 10_000


class PlacementError(ValueError):
    """Geometri geçersiz (negatif boyut, ekransız sistem vb.)."""


@dataclass(frozen=True)
class Rect:
    """Ekran koordinatlarında bir dikdörtgen (sol üst köşe + boyut)."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise PlacementError(f"Pencere boyutu pozitif olmalı: {self.width}x{self.height}")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def intersection_area(self, other: Rect) -> int:
        """İki dikdörtgenin kesişen alanı; kesişmiyorlarsa 0."""
        overlap_x = min(self.right, other.right) - max(self.x, other.x)
        overlap_y = min(self.bottom, other.bottom) - max(self.y, other.y)
        return overlap_x * overlap_y if overlap_x > 0 and overlap_y > 0 else 0

    def moved_to(self, x: int, y: int) -> Rect:
        return Rect(x, y, self.width, self.height)

    def resized(self, width: int, height: int) -> Rect:
        return Rect(self.x, self.y, width, height)

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


def visible_area(rect: Rect, screens: Sequence[Rect]) -> int:
    """Dikdörtgenin ekranlarda görünen alanı.

    Ekranlar çakışmıyorsa (tipik çoklu monitör) bu kesişimlerin
    toplamıdır. Çakışan ekranlarda üst sınır olarak dikdörtgenin kendi
    alanı ile kırpılır — görünen alan pencereden büyük olamaz.
    """
    total = sum(rect.intersection_area(screen) for screen in screens)
    return min(total, rect.area)


def is_visible_enough(rect: Rect, screens: Sequence[Rect]) -> bool:
    """Pencere kullanıcı tarafından bulunabilecek kadar görünüyor mu."""
    shown = visible_area(rect, screens)
    if shown == 0:
        return False
    threshold = min(int(rect.area * MIN_VISIBLE_FRACTION), MIN_VISIBLE_PIXELS)
    return shown >= max(1, threshold)


def _target_screen(rect: Rect, screens: Sequence[Rect]) -> Rect:
    """En çok kesişen ekran; hiç kesişme yoksa birincil (ilk) ekran."""
    best = max(screens, key=lambda screen: rect.intersection_area(screen))
    return best if rect.intersection_area(best) > 0 else screens[0]


def clamp_to_screens(rect: Rect, screens: Sequence[Rect]) -> Rect:
    """Gerekiyorsa dikdörtgeni görünür alana taşır — `F4-083`.

    Yeterince görünen bir pencereye **dokunulmaz**; kullanıcının kendi
    yerleşimi (örneğin ekran kenarından biraz taşan bir pencere) korunur.
    """
    if not screens:
        raise PlacementError("En az bir ekran gerekli")
    if is_visible_enough(rect, screens):
        return rect

    screen = _target_screen(rect, screens)
    width = min(rect.width, screen.width)
    height = min(rect.height, screen.height)
    x = min(max(rect.x, screen.x), screen.right - width)
    y = min(max(rect.y, screen.y), screen.bottom - height)
    return Rect(x, y, width, height)


def encode_geometry(rect: Rect) -> str:
    """Ayar dosyasına yazılabilir kısa gösterim: ``"x,y,w,h"``."""
    return ",".join(str(value) for value in rect.to_tuple())


def decode_geometry(text: str) -> Rect | None:
    """`encode_geometry` çıktısını geri okur; bozuksa `None`.

    Bozuk bir kayıt uygulamayı açmayı engellememeli — konum unutulur,
    pencere varsayılan yerinde açılır.
    """
    parts = text.split(",")
    if len(parts) != 4:
        return None
    try:
        x, y, width, height = (int(part.strip()) for part in parts)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return Rect(x, y, width, height)

"""Bellek sınırlı LRU önbellek — `F4-059`.

Çizim penceresi özetleri (`ViewportSummary`, `F4-058`) pahalı üretilir ama
büyüktür. Sınırsız biriktirmek bir kayıt gezildikçe belleği şişirir; hiç
biriktirmemek her pan/zoom'da yeniden decode eder. Bu önbellek ikisinin
arasını **ölçülen bayt** üzerinden tutar:

* Girdi sayısı değil, **toplam bayt** sınırlanır. Her değerin boyutu
  `sizer` ile ölçülür (öntanımlı: değerin kendi `nbytes` alanı).
* Bütçe aşılınca **en az kullanılandan** başlayarak girdi çıkarılır.
* Bütçeden büyük tek bir değer hiç saklanmaz (`rejections` sayılır);
  böylece ``used_bytes <= max_bytes`` **her zaman** doğrudur.
* Kullanım raporlanır: `stats()` girdi sayısı, ölçülen bayt, bütçe,
  isabet/ıska, çıkarma ve ret sayılarını verir.

Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

#: Öntanımlı bütçe: 64 MiB.
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 256


class MemoryCacheError(ValueError):
    """Önbellek yapılandırması geçersiz (bütçe pozitif değil vb.)."""


@dataclass(frozen=True)
class CacheStats:
    """Önbelleğin **ölçülen** kullanımı ve sayaçları."""

    entries: int
    used_bytes: int
    max_bytes: int
    hits: int
    misses: int
    evictions: int
    rejections: int
    max_entries: int

    @property
    def free_bytes(self) -> int:
        return self.max_bytes - self.used_bytes

    @property
    def usage_ratio(self) -> float:
        """Bütçenin doluluk oranı ``[0, 1]``."""
        return self.used_bytes / self.max_bytes

    @property
    def hit_ratio(self) -> float:
        """İsabet oranı; hiç sorgu yapılmadıysa 0."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def describe(self) -> str:
        """Log/durum çubuğu için tek satırlık özet."""
        return (
            f"{self.entries} girdi, {self.used_bytes / 1024 / 1024:.1f}/"
            f"{self.max_bytes / 1024 / 1024:.1f} MiB "
            f"(%{self.usage_ratio * 100:.0f}), isabet %{self.hit_ratio * 100:.0f}, "
            f"{self.evictions} cikarma"
        )


def _checked_size(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MemoryCacheError(f"bütçe/boyut negatif olamaz ve tam sayı olmalı: {value!r}")
    return value


def _default_sizer(value: object) -> int:
    """Değerin kendi bildirdiği bayt boyutu (`nbytes`)."""
    size = getattr(value, "nbytes", None)
    if size is None:
        raise MemoryCacheError(f"{type(value).__name__} `nbytes` taşımıyor; `sizer` verin")
    return _checked_size(size)


class MemoryBoundedCache(Generic[K, V]):
    """Toplam baytı sınırlı, en az kullanılanı çıkaran önbellek."""

    def __init__(
        self,
        max_bytes: int = DEFAULT_MAX_BYTES,
        *,
        sizer: Callable[[V], int] | None = None,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._max_bytes = _checked_size(max_bytes, minimum=1)
        self._max_entries = _checked_size(max_entries, minimum=1)
        self._sizer: Callable[[V], int] = sizer or _default_sizer
        self._entries: OrderedDict[K, V] = OrderedDict()
        self._sizes: dict[K, int] = {}
        self._used = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0

    # -- sorgular ----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: K) -> bool:
        """Sayaçları **değiştirmez** — yalnız varlık sorgusu."""
        return key in self._entries

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    @property
    def used_bytes(self) -> int:
        """Saklanan değerlerin ölçülen toplam boyutu."""
        return self._used

    def keys(self) -> list[K]:
        """Anahtarlar, **en az kullanılandan en yeniye**."""
        return list(self._entries)

    def stats(self) -> CacheStats:
        return CacheStats(
            entries=len(self._entries),
            used_bytes=self._used,
            max_bytes=self._max_bytes,
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            rejections=self._rejections,
            max_entries=self._max_entries,
        )

    # -- kullanım ----------------------------------------------------------

    def get(self, key: K) -> V | None:
        """Değeri döndürür ve **en yeni** konuma taşır; yoksa `None`."""
        if key not in self._entries:
            self._misses += 1
            return None
        self._hits += 1
        self._entries.move_to_end(key)
        return self._entries[key]

    def put(self, key: K, value: V) -> bool:
        """Değeri saklar; gerekirse en eskileri çıkarır.

        Değer tek başına bütçeden büyükse **saklanmaz** ve `False` döner —
        bütçe hiçbir zaman aşılmaz.
        """
        size = _checked_size(self._sizer(value))

        self.discard(key)  # aynı anahtarın eski sürümü yerini bırakır
        if size > self._max_bytes:
            self._rejections += 1
            return False

        while self._entries and (
            self._used + size > self._max_bytes or len(self._entries) >= self._max_entries
        ):
            self._evict_oldest()

        self._entries[key] = value
        self._sizes[key] = size
        self._used += size
        return True

    def discard(self, key: K) -> bool:
        """Varsa girdiyi düşürür (çıkarma sayacına yazılmaz)."""
        if key not in self._entries:
            return False
        del self._entries[key]
        self._used -= self._sizes.pop(key)
        return True

    def clear(self) -> None:
        """Tüm girdileri düşürür; sayaçlar korunur."""
        self._entries.clear()
        self._sizes.clear()
        self._used = 0

    def reset_stats(self) -> None:
        """İsabet/ıska/çıkarma sayaçlarını sıfırlar; içerik korunur."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0

    # -- ic ----------------------------------------------------------------

    def _evict_oldest(self) -> None:
        key, _value = self._entries.popitem(last=False)
        self._used -= self._sizes.pop(key)
        self._evictions += 1

"""Bellek sınırlı LRU önbellek — `F4-059`.

Kabul: bütçe aşılınca eski girdiler çıkar; ölçülen kullanım raporlanır.

Değişmez: ``used_bytes <= max_bytes`` **her zaman** doğrudur — bütçeden
büyük tek bir değer bile saklanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sonar_analyzer.repository.memory_cache import (
    DEFAULT_MAX_BYTES,
    CacheStats,
    MemoryBoundedCache,
    MemoryCacheError,
)


@dataclass
class _Blob:
    """Kendi boyutunu bildiren bir değer (numpy dizileri gibi)."""

    nbytes: int


def _cache(max_bytes: int = 1_000) -> MemoryBoundedCache[str, _Blob]:
    return MemoryBoundedCache(max_bytes)


# --------------------------------------------------------------------------- #
# kurulum
# --------------------------------------------------------------------------- #


def test_a_new_cache_is_empty() -> None:
    cache = _cache()
    assert len(cache) == 0
    assert cache.used_bytes == 0
    assert cache.max_bytes == 1_000
    assert cache.keys() == []


def test_the_default_budget_is_documented() -> None:
    assert DEFAULT_MAX_BYTES == 64 * 1024 * 1024
    assert MemoryBoundedCache[str, _Blob]().max_bytes == DEFAULT_MAX_BYTES


@pytest.mark.parametrize("bad", [0, -1, -1_000])
def test_a_nonpositive_budget_is_rejected(bad: int) -> None:
    with pytest.raises(MemoryCacheError, match="bütçe"):
        MemoryBoundedCache(bad)


def test_a_value_without_a_size_needs_an_explicit_sizer() -> None:
    cache: MemoryBoundedCache[str, str] = MemoryBoundedCache(100)
    with pytest.raises(MemoryCacheError, match="nbytes"):
        cache.put("a", "metin")

    sized: MemoryBoundedCache[str, str] = MemoryBoundedCache(100, sizer=len)
    assert sized.put("a", "metin")
    assert sized.used_bytes == 5


# --------------------------------------------------------------------------- #
# saklama ve okuma
# --------------------------------------------------------------------------- #


def test_a_stored_value_comes_back() -> None:
    cache = _cache()
    blob = _Blob(100)
    assert cache.put("a", blob)
    assert cache.get("a") is blob
    assert len(cache) == 1
    assert cache.used_bytes == 100


def test_a_missing_key_returns_none(_unused: None = None) -> None:
    cache = _cache()
    assert cache.get("yok") is None


def test_contains_does_not_disturb_the_counters() -> None:
    cache = _cache()
    cache.put("a", _Blob(10))
    assert "a" in cache
    assert "yok" not in cache
    stats = cache.stats()
    assert stats.hits == 0
    assert stats.misses == 0


def test_replacing_a_key_replaces_its_size() -> None:
    cache = _cache()
    cache.put("a", _Blob(100))
    cache.put("a", _Blob(300))
    assert len(cache) == 1
    assert cache.used_bytes == 300


def test_discard_frees_the_bytes_without_counting_an_eviction() -> None:
    cache = _cache()
    cache.put("a", _Blob(100))
    assert cache.discard("a")
    assert not cache.discard("a")
    assert cache.used_bytes == 0
    assert cache.stats().evictions == 0


def test_clear_empties_the_cache_but_keeps_the_counters() -> None:
    cache = _cache()
    cache.put("a", _Blob(100))
    cache.get("a")
    cache.clear()
    assert len(cache) == 0
    assert cache.used_bytes == 0
    assert cache.stats().hits == 1


# --------------------------------------------------------------------------- #
# bütçe aşılınca eski girdiler çıkar
# --------------------------------------------------------------------------- #


def test_the_budget_is_never_exceeded() -> None:
    cache = _cache(1_000)
    for index in range(50):
        cache.put(f"k{index}", _Blob(300))
        assert cache.used_bytes <= cache.max_bytes


def test_the_least_recently_used_entry_is_evicted_first() -> None:
    cache = _cache(1_000)
    cache.put("a", _Blob(400))
    cache.put("b", _Blob(400))

    cache.put("c", _Blob(400))  # 1200 > 1000 -> en eski "a" cikar

    assert "a" not in cache
    assert cache.keys() == ["b", "c"]
    assert cache.used_bytes == 800
    assert cache.stats().evictions == 1


def test_reading_an_entry_makes_it_the_newest() -> None:
    cache = _cache(1_000)
    cache.put("a", _Blob(400))
    cache.put("b", _Blob(400))

    cache.get("a")  # "a" artik en yeni
    cache.put("c", _Blob(400))  # "b" cikmali

    assert "a" in cache
    assert "b" not in cache
    assert cache.keys() == ["a", "c"]


def test_several_entries_are_evicted_when_one_big_value_arrives() -> None:
    cache = _cache(1_000)
    for index in range(5):
        cache.put(f"k{index}", _Blob(200))
    assert len(cache) == 5

    cache.put("big", _Blob(900))

    assert cache.used_bytes == 900
    assert cache.keys() == ["big"]
    assert cache.stats().evictions == 5


def test_a_value_larger_than_the_budget_is_not_stored() -> None:
    cache = _cache(1_000)
    cache.put("a", _Blob(500))

    assert not cache.put("huge", _Blob(5_000))

    assert "huge" not in cache
    assert "a" in cache  # var olan icerik feda edilmedi
    assert cache.used_bytes == 500
    assert cache.stats().rejections == 1


def test_a_value_exactly_at_the_budget_fits() -> None:
    cache = _cache(1_000)
    assert cache.put("a", _Blob(1_000))
    assert cache.used_bytes == 1_000
    assert len(cache) == 1


def test_a_negative_measured_size_is_rejected() -> None:
    cache: MemoryBoundedCache[str, str] = MemoryBoundedCache(100, sizer=lambda _v: -1)
    with pytest.raises(MemoryCacheError, match="negatif"):
        cache.put("a", "x")


# --------------------------------------------------------------------------- #
# ölçülen kullanım raporlanır
# --------------------------------------------------------------------------- #


def test_stats_report_the_measured_usage() -> None:
    cache = _cache(1_000)
    cache.put("a", _Blob(250))
    cache.put("b", _Blob(150))

    stats = cache.stats()
    assert isinstance(stats, CacheStats)
    assert stats.entries == 2
    assert stats.used_bytes == 400
    assert stats.max_bytes == 1_000
    assert stats.free_bytes == 600
    assert abs(stats.usage_ratio - 0.4) < 1e-12


def test_stats_count_hits_and_misses() -> None:
    cache = _cache()
    cache.put("a", _Blob(10))

    cache.get("a")
    cache.get("a")
    cache.get("yok")

    stats = cache.stats()
    assert stats.hits == 2
    assert stats.misses == 1
    assert abs(stats.hit_ratio - 2 / 3) < 1e-12


def test_the_hit_ratio_is_zero_before_any_lookup() -> None:
    assert _cache().stats().hit_ratio == 0.0


def test_stats_count_evictions_and_rejections() -> None:
    cache = _cache(1_000)
    cache.put("a", _Blob(600))
    cache.put("b", _Blob(600))  # "a" cikar
    cache.put("huge", _Blob(2_000))  # reddedilir

    stats = cache.stats()
    assert stats.evictions == 1
    assert stats.rejections == 1


def test_describe_is_a_readable_one_liner() -> None:
    cache = MemoryBoundedCache[str, _Blob](4 * 1024 * 1024)
    cache.put("a", _Blob(1024 * 1024))
    cache.get("a")
    cache.get("yok")

    text = cache.stats().describe()
    assert "1 girdi" in text
    assert "MiB" in text
    assert "isabet" in text


def test_reset_stats_keeps_the_contents() -> None:
    cache = _cache()
    cache.put("a", _Blob(100))
    cache.get("a")

    cache.reset_stats()

    stats = cache.stats()
    assert stats.hits == 0
    assert stats.misses == 0
    assert stats.entries == 1
    assert stats.used_bytes == 100

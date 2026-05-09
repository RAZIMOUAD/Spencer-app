"""Tests for CircleCache LRU cache."""

from __future__ import annotations

import pytest

from core.cache import CircleCache


class TestCircleCacheBasic:
    def test_miss_on_empty(self):
        cache = CircleCache()
        assert cache.get(1.0, 2.0, 5.0) is None

    def test_put_and_get(self):
        cache = CircleCache()
        cache.put(1.0, 2.0, 5.0, 1.35)
        assert cache.get(1.0, 2.0, 5.0) == pytest.approx(1.35)

    def test_put_inf_and_get(self):
        cache = CircleCache()
        cache.put(0.0, 10.0, 8.0, float("inf"))
        assert cache.get(0.0, 10.0, 8.0) == float("inf")

    def test_different_keys_no_collision(self):
        cache = CircleCache()
        cache.put(1.0, 2.0, 5.0, 1.0)
        cache.put(1.0, 2.0, 6.0, 2.0)
        assert cache.get(1.0, 2.0, 5.0) == pytest.approx(1.0)
        assert cache.get(1.0, 2.0, 6.0) == pytest.approx(2.0)

    def test_rounding_key(self):
        cache = CircleCache()
        cache.put(1.0001, 2.0001, 5.0001, 1.5)
        # Rounded to 3dp: (1.0, 2.0, 5.0)
        assert cache.get(1.0, 2.0, 5.0) == pytest.approx(1.5)

    def test_rounding_collision(self):
        cache = CircleCache()
        cache.put(1.0001, 2.0, 5.0, 1.5)
        cache.put(1.0004, 2.0, 5.0, 2.5)
        # Both round to key (1.0, 2.0, 5.0) — second write wins
        assert cache.get(1.0, 2.0, 5.0) == pytest.approx(2.5)


class TestCircleCacheLRU:
    def test_evicts_oldest_when_full(self):
        cache = CircleCache(maxsize=3)
        cache.put(0.0, 0.0, 1.0, 1.0)
        cache.put(0.0, 0.0, 2.0, 2.0)
        cache.put(0.0, 0.0, 3.0, 3.0)
        # Cache is full — adding a 4th evicts the oldest (r=1.0)
        cache.put(0.0, 0.0, 4.0, 4.0)
        assert cache.get(0.0, 0.0, 1.0) is None  # evicted
        assert cache.get(0.0, 0.0, 4.0) == pytest.approx(4.0)

    def test_get_promotes_to_mru(self):
        cache = CircleCache(maxsize=3)
        cache.put(0.0, 0.0, 1.0, 1.0)
        cache.put(0.0, 0.0, 2.0, 2.0)
        cache.put(0.0, 0.0, 3.0, 3.0)
        # Access r=1.0 to promote it → it should survive the next eviction
        cache.get(0.0, 0.0, 1.0)
        cache.put(0.0, 0.0, 4.0, 4.0)  # evicts r=2.0 (now the LRU)
        assert cache.get(0.0, 0.0, 1.0) is not None  # still alive
        assert cache.get(0.0, 0.0, 2.0) is None  # evicted

    def test_len(self):
        cache = CircleCache(maxsize=10)
        assert len(cache) == 0
        cache.put(1.0, 1.0, 1.0, 1.0)
        assert len(cache) == 1


class TestCircleCacheStats:
    def test_hits_misses(self):
        cache = CircleCache()
        cache.get(1.0, 1.0, 1.0)  # miss
        cache.put(1.0, 1.0, 1.0, 1.5)
        cache.get(1.0, 1.0, 1.0)  # hit
        cache.get(2.0, 2.0, 2.0)  # miss
        assert cache.hits == 1
        assert cache.misses == 2

    def test_hit_rate_empty(self):
        cache = CircleCache()
        assert cache.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        cache = CircleCache()
        cache.put(1.0, 1.0, 1.0, 1.5)
        cache.get(1.0, 1.0, 1.0)
        assert cache.hit_rate == pytest.approx(1.0)

"""LRU cache for circle evaluation results during critical circle search."""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional


class CircleCache:
    """
    Thread-unsafe LRU cache keyed by (cx, cy, radius) rounded to 3 decimal places.

    A single cache instance is shared within one search run.  It is NOT shared
    across requests (no global state).

    Parameters
    ----------
    maxsize : int
        Maximum number of entries to keep.  Oldest entries are evicted first.
    """

    def __init__(self, maxsize: int = 10_000) -> None:
        self._cache: OrderedDict[tuple[float, float, float], float] = OrderedDict()
        self._maxsize = maxsize
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------

    @staticmethod
    def _key(cx: float, cy: float, radius: float) -> tuple[float, float, float]:
        return (round(cx, 3), round(cy, 3), round(radius, 3))

    def get(self, cx: float, cy: float, radius: float) -> Optional[float]:
        """Return cached FS or None if not present.  Moves hit entry to end (MRU)."""
        k = self._key(cx, cy, radius)
        if k in self._cache:
            self._cache.move_to_end(k)
            self.hits += 1
            return self._cache[k]
        self.misses += 1
        return None

    def put(self, cx: float, cy: float, radius: float, fs: float) -> None:
        """Store FS for a circle.  Evicts oldest entry if cache is full."""
        k = self._key(cx, cy, radius)
        if k in self._cache:
            self._cache.move_to_end(k)
        else:
            if len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
        self._cache[k] = fs

    def __len__(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

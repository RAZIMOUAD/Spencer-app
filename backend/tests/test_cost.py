"""Tests for cost estimation and mode presets."""

from __future__ import annotations

import math

import pytest

from app.schemas import CriticalSearchSettings, SpencerSettings
from app.errors import TooManyCandidatesError, PrecisionTooExpensiveError
from core.cost import (
    estimate_cost,
    fast_search,
    precise_search,
    advanced_search,
    search_for_mode,
    spencer_for_mode,
    _count_candidates,
    MAX_CANDIDATES,
    MAX_COST_SCORE,
)


# ---------------------------------------------------------------------------
# _count_candidates
# ---------------------------------------------------------------------------


class TestCountCandidates:
    def test_fast_search_small_H(self):
        n = _count_candidates(H=5.0, search=fast_search())
        assert n > 0
        assert n < MAX_CANDIDATES

    def test_precise_search_moderate_H(self):
        n = _count_candidates(H=10.0, search=precise_search())
        assert n > 0

    def test_advanced_search_large_H(self):
        n = _count_candidates(H=20.0, search=advanced_search())
        assert n > 0

    def test_more_radii_more_candidates(self):
        s1 = precise_search()
        s2 = precise_search().model_copy(update={"n_radii": s1.n_radii * 2})
        n1 = _count_candidates(10.0, s1)
        n2 = _count_candidates(10.0, s2)
        assert n2 > n1

    def test_more_n_radii_more_candidates(self):
        """n_radii appears in all three passes and always increases total count."""
        s1 = precise_search()
        s2 = precise_search().model_copy(update={"n_radii": s1.n_radii + 4})
        n1 = _count_candidates(10.0, s1)
        n2 = _count_candidates(10.0, s2)
        assert n2 > n1


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def setup_method(self):
        self.H = 10.0
        self.n_layers = 3
        self.settings = SpencerSettings()
        self.search = precise_search()

    def test_returns_cost_estimate(self):
        cost = estimate_cost(self.H, self.n_layers, self.settings, self.search)
        assert cost.n_candidates > 0
        assert cost.cost_score > 0
        assert cost.level in ("light", "moderate", "heavy", "prohibitive")
        assert cost.recommended_mode in ("fast", "precise", "advanced")

    def test_time_bounds_positive(self):
        cost = estimate_cost(self.H, self.n_layers, self.settings, self.search)
        assert cost.estimated_seconds_min > 0
        assert cost.estimated_seconds_max >= cost.estimated_seconds_min

    def test_warnings_empty_for_small_search(self):
        cost = estimate_cost(5.0, 2, SpencerSettings(), fast_search())
        # Small fast search should have no warnings
        assert isinstance(cost.warnings, list)

    def test_cost_score_formula(self):
        cost = estimate_cost(self.H, self.n_layers, self.settings, self.search)
        expected = (
            cost.n_candidates
            * self.settings.n_slices
            * math.log2(self.n_layers + 1)
            * self.settings.max_iter
        )
        assert abs(cost.cost_score - expected) < 1.0

    def test_level_light_for_fast_small(self):
        cost = estimate_cost(5.0, 1, SpencerSettings(n_slices=5, max_iter=10), fast_search())
        assert cost.level == "light"

    def test_raises_too_many_candidates(self):
        # Force too many candidates with tiny step and huge H
        tiny_step = precise_search().model_copy(update={"coarse_step": 0.01})
        with pytest.raises(TooManyCandidatesError):
            estimate_cost(100.0, 2, SpencerSettings(), tiny_step)

    def test_raises_precision_too_expensive(self):
        # Force huge cost_score with max slices/iter
        heavy = SpencerSettings(n_slices=200, max_iter=2000)
        search = precise_search().model_copy(update={"n_radii": 20})
        with pytest.raises((TooManyCandidatesError, PrecisionTooExpensiveError)):
            estimate_cost(50.0, 100, heavy, search)


# ---------------------------------------------------------------------------
# Mode presets
# ---------------------------------------------------------------------------


class TestModePresets:
    def test_fast_coarser_than_precise(self):
        assert fast_search().coarse_step > precise_search().coarse_step

    def test_advanced_finer_than_precise(self):
        assert advanced_search().coarse_step < precise_search().coarse_step

    def test_search_for_mode_fast(self):
        s = search_for_mode("fast")
        assert s.coarse_step == fast_search().coarse_step

    def test_search_for_mode_advanced(self):
        s = search_for_mode("advanced")
        assert s.coarse_step == advanced_search().coarse_step

    def test_search_for_mode_fallback(self):
        s = search_for_mode("unknown_mode")
        assert s.coarse_step == precise_search().coarse_step

    def test_spencer_for_mode_fast(self):
        s = spencer_for_mode("fast")
        assert s.n_slices == 10

    def test_spencer_for_mode_advanced(self):
        s = spencer_for_mode("advanced")
        assert s.n_slices == 50

    def test_spencer_for_mode_precise(self):
        s = spencer_for_mode("precise")
        assert s.n_slices == SpencerSettings().n_slices  # default

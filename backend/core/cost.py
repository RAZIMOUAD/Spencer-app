"""Computational cost estimation before launching a heavy analysis."""

from __future__ import annotations

import math

from app.schemas import (
    CostEstimate,
    CriticalSearchSettings,
    SpencerSettings,
)
from app.errors import TooManyCandidatesError, PrecisionTooExpensiveError

# Hard limits — raise an error, not a warning
MAX_CANDIDATES = 500_000
MAX_COST_SCORE = 5e9

# Soft limits — included as warnings
WARN_LAYERS = 50
WARN_CANDIDATES = 50_000

# Reference throughput on a typical laptop core (circles/sec)
# Empirically measured: ~300 circles/sec with 20 slices, 5 layers, tol=1e-6
_REF_CIRCLES_PER_SEC = 300.0
_REF_SLICES = 20
_REF_LOG_LAYERS = math.log2(6)  # 5 layers → log2(6) ≈ 2.58
_REF_ITERS = 200


def estimate_cost(
    H: float,
    n_layers: int,
    settings: SpencerSettings,
    search: CriticalSearchSettings,
) -> CostEstimate:
    """
    Estimate the computational cost of a critical circle search and return
    a structured CostEstimate with a recommended AnalysisMode.

    The cost metric:
        score = n_candidates × n_slices × log2(n_layers+1) × max_iter

    This is proportional to total Spencer-solver work (loops).

    Parameters
    ----------
    H : float
        Slope height in metres (drives the search grid size).
    n_layers : int
        Number of soil layers.
    settings : SpencerSettings
    search : CriticalSearchSettings

    Returns
    -------
    CostEstimate

    Raises
    ------
    TooManyCandidatesError
        n_candidates > MAX_CANDIDATES.
    PrecisionTooExpensiveError
        cost_score > MAX_COST_SCORE.
    """
    n_candidates = _count_candidates(H, search)
    n_slices = settings.n_slices
    max_iter = settings.max_iter
    log_layers = math.log2(n_layers + 1)

    cost_score = n_candidates * n_slices * log_layers * max_iter

    warnings: list[str] = []
    if n_layers > WARN_LAYERS:
        warnings.append(
            f"{n_layers} couches détectées (recommandé ≤ {WARN_LAYERS}). "
            "La recherche binaire garantit O(log n) par tranche, "
            "mais la mémoire de l'index augmente."
        )
    if n_candidates > WARN_CANDIDATES:
        warnings.append(
            f"{n_candidates:,} cercles candidats — calcul potentiellement long. "
            "Envisagez le mode 'fast' ou réduisez le pas de la grille."
        )

    # Hard guards
    if n_candidates > MAX_CANDIDATES:
        raise TooManyCandidatesError(
            f"La grille de recherche génère {n_candidates:,} cercles candidats "
            f"(maximum autorisé : {MAX_CANDIDATES:,}). "
            "Augmentez le pas ou réduisez le domaine.",
            {"n_candidates": n_candidates, "max_allowed": MAX_CANDIDATES},
        )
    if cost_score > MAX_COST_SCORE:
        raise PrecisionTooExpensiveError(
            f"Score de coût estimé {cost_score:.2e} > limite {MAX_COST_SCORE:.2e}. "
            "Réduisez n_slices, max_iter ou le pas de raffinement.",
            {"cost_score": cost_score, "limit": MAX_COST_SCORE},
        )

    # Level and mode recommendation
    level, mode = _classify(cost_score)

    # Time estimate: scale from reference throughput
    throughput_factor = (
        (_REF_SLICES / n_slices)
        * (_REF_LOG_LAYERS / max(log_layers, 0.1))
        * (_REF_ITERS / max_iter)
    )
    throughput = _REF_CIRCLES_PER_SEC * throughput_factor
    t_min = n_candidates / max(throughput * 2, 1)
    t_max = n_candidates / max(throughput * 0.3, 1)

    return CostEstimate(
        n_candidates=n_candidates,
        n_slices=n_slices,
        n_layers=n_layers,
        max_iter=max_iter,
        cost_score=cost_score,
        level=level,
        recommended_mode=mode,
        warnings=warnings,
        estimated_seconds_min=round(t_min, 1),
        estimated_seconds_max=round(t_max, 1),
    )


def _count_candidates(H: float, search: CriticalSearchSettings) -> int:
    """Approximate number of candidate circles the 3-pass search will evaluate."""
    # Pass 1: coarse grid
    cx_range = 2.0 * H      # [x_crest - 0.5H, x_crest + 1.5H]
    cy_range = 2.0 * H      # [H, H + 2H]
    step = search.coarse_step
    nx = max(1, int(cx_range / step) + 1)
    ny = max(1, int(cy_range / step) + 1)
    n_coarse = nx * ny * search.n_radii

    # Pass 2: fine neighbourhood around top_k_coarse best
    fine_range = search.coarse_step * 2
    nf = max(1, int(fine_range / search.fine_step) + 1)
    n_fine = search.top_k_coarse * nf * nf * search.n_radii

    # Pass 3: final around top_k_fine best
    final_range = search.fine_step * 2
    nfin = max(1, int(final_range / search.final_step) + 1)
    n_final = search.top_k_fine * nfin * nfin * search.n_radii

    return n_coarse + n_fine + n_final


def _classify(score: float) -> tuple[str, str]:
    """Return (level, recommended_mode) based on cost score."""
    if score < 1e6:
        return "light", "fast"
    if score < 1e7:
        return "moderate", "precise"
    if score < 1e8:
        return "heavy", "precise"
    return "prohibitive", "advanced"


# ---------------------------------------------------------------------------
# Preset search configs for each mode
# ---------------------------------------------------------------------------

def fast_search() -> CriticalSearchSettings:
    from app.schemas import CriticalSearchSettings
    return CriticalSearchSettings(
        coarse_step=2.0,
        fine_step=0.5,
        final_step=0.1,
        top_k_coarse=5,
        top_k_fine=3,
        n_radii=5,
        min_convergence_ratio=0.1,
    )


def precise_search() -> CriticalSearchSettings:
    from app.schemas import CriticalSearchSettings
    return CriticalSearchSettings()  # defaults


def advanced_search() -> CriticalSearchSettings:
    from app.schemas import CriticalSearchSettings
    return CriticalSearchSettings(
        coarse_step=0.5,
        fine_step=0.1,
        final_step=0.02,
        top_k_coarse=15,
        top_k_fine=8,
        n_radii=12,
        min_convergence_ratio=0.05,
    )


def search_for_mode(mode: str) -> CriticalSearchSettings:
    modes = {"fast": fast_search, "precise": precise_search, "advanced": advanced_search}
    return modes.get(mode, precise_search)()


def spencer_for_mode(mode: str) -> SpencerSettings:
    from app.schemas import SpencerSettings
    configs = {
        "fast":     SpencerSettings(n_slices=10, tolerance=1e-4, max_iter=100),
        "precise":  SpencerSettings(),
        "advanced": SpencerSettings(n_slices=50, tolerance=1e-8, max_iter=500),
    }
    return configs.get(mode, SpencerSettings())

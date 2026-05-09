"""Critical slip circle search — 3-pass strategy with batch, cache, early stopping."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Optional

from app import config
from app.schemas import (
    BatchProgress,
    Circle,
    CriticalCircleResult,
    CriticalSearchSettings,
    SearchStats,
    SoilLayer,
    SpencerSettings,
    TerrainPoint,
    WaterTable,
)
from app.errors import (
    AnalysisCancelledError,
    NoValidCircleError,
    SearchDomainError,
    SpencerBaseError,
)
from core.cache import CircleCache
from core.layer_index import LayerIndex
from core.slicing import auto_slice_count_for_circle, divide_into_slices
from core.spencer import solve_spencer

_EARLY_STOP_MARGIN = 0.15  # reject if estimated FS > best_fs * (1 + margin)
_BATCH_SIZE = 500           # circles per batch before emitting progress


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_critical_circle(
    terrain_pts: list[TerrainPoint],
    layers: list[SoilLayer],
    water_table: WaterTable,
    settings: SpencerSettings,
    search: CriticalSearchSettings,
    cancel_event: Optional[threading.Event] = None,
    timeout_sec: Optional[float] = None,
) -> tuple[Circle, float, SearchStats]:
    """
    Search for the slip circle with the minimum FS using a 3-pass grid strategy.

    Performance features
    --------------------
    - **LayerIndex** — built once, reused across all slices (O(log n) lookup).
    - **CircleCache** — LRU cache keyed by (cx, cy, r) rounded to 3 dp.
    - **Early stopping** — circles with estimated FS > best_fs*(1+margin) skipped.
    - **Cancellation** — cancel_event.is_set() checked before each circle.
    - **Timeout** — wall-clock deadline enforced between batches.
    - **Domain clipping** — neighbourhood searches are clipped to the original
      domain bounds so that refining near a boundary cannot escape the valid
      search space.
    - **Radius refinement** — pass 2 and 3 also vary the radius in a local
      window around the best candidate's radius, not just the global r range.

    Returns
    -------
    (critical_circle, min_fs, stats)

    Raises
    ------
    SearchDomainError        — terrain / geometry invalid.
    NoValidCircleError       — no circle converged after all passes.
    AnalysisCancelledError   — cancel_event was set.
    AnalysisTimeoutError     — wall-clock deadline exceeded.
    """
    if len(terrain_pts) < 2:
        raise SearchDomainError("Le profil du terrain doit contenir au moins 2 points.")

    H = max(pt.y for pt in terrain_pts) - min(pt.y for pt in terrain_pts)
    if H < 1e-3:
        raise SearchDomainError(f"Hauteur de talus trop faible : H = {H:.4f} m.")

    # Precompile layer index — reused across all circles in all passes
    idx = LayerIndex.build(layers, H)
    cache = CircleCache(maxsize=20_000)
    stats = SearchStats(tested=0, converged=0, rejected=0)
    deadline = time.monotonic() + timeout_sec if timeout_sec else None

    cx_min, cx_max, cy_min, cy_max, r_min, r_max = _search_domain(terrain_pts, H)

    ctx = _SearchCtx(
        terrain_pts=terrain_pts,
        water_table=water_table,
        settings=settings,
        search=search,
        idx=idx,
        cache=cache,
        stats=stats,
        cancel_event=cancel_event,
        deadline=deadline,
        cx_min=cx_min, cx_max=cx_max,
        cy_min=cy_min, cy_max=cy_max,
        r_min=r_min, r_max=r_max,
    )

    # --- Pass 1: coarse grid over full domain ---
    candidates_1 = _batch_grid_search(
        ctx, cx_min, cx_max, cy_min, cy_max, search.coarse_step, r_min, r_max
    )
    if not candidates_1:
        raise NoValidCircleError(
            "Passe grossière : aucun cercle n'a convergé. "
            "Vérifiez les paramètres mécaniques et la géométrie.",
            {"tested": stats.tested, "rejected": stats.rejected},
        )

    top_coarse = _top_k(candidates_1, search.top_k_coarse)

    # --- Pass 2: fine neighbourhood around top_k_coarse best ---
    # cx/cy half-range = coarse_step × 2; radius half-range = coarse_step
    candidates_2: list[_Candidate] = []
    for cand in top_coarse:
        candidates_2.extend(
            _batch_neighbourhood_search(
                ctx, cand.circle,
                xy_half=search.coarse_step * 2,
                r_half=search.coarse_step,
                step=search.fine_step,
            )
        )
    if not candidates_2:
        candidates_2 = top_coarse

    top_fine = _top_k(candidates_2, search.top_k_fine)

    # --- Pass 3: final refinement around top_k_fine best ---
    # cx/cy half-range = fine_step × 2; radius half-range = fine_step
    candidates_3: list[_Candidate] = []
    for cand in top_fine:
        candidates_3.extend(
            _batch_neighbourhood_search(
                ctx, cand.circle,
                xy_half=search.fine_step * 2,
                r_half=search.fine_step,
                step=search.final_step,
            )
        )
    if not candidates_3:
        candidates_3 = top_fine

    best = min(candidates_3, key=lambda c: c.fs)
    return best.circle, best.fs, stats


def iter_critical_circle(
    terrain_pts: list[TerrainPoint],
    layers: list[SoilLayer],
    water_table: WaterTable,
    settings: SpencerSettings,
    search: CriticalSearchSettings,
    cancel_event: Optional[threading.Event] = None,
    timeout_sec: Optional[float] = None,
) -> Generator[BatchProgress, None, tuple[Circle, float, SearchStats]]:
    """
    Generator version of find_critical_circle (coarse pass only, with progress).

    Yields BatchProgress after each batch of _BATCH_SIZE circles.
    StopIteration.value holds (circle, fs, stats).
    """
    t0 = time.monotonic()
    H = max(pt.y for pt in terrain_pts) - min(pt.y for pt in terrain_pts)
    idx = LayerIndex.build(layers, H)
    cache = CircleCache(maxsize=20_000)
    stats = SearchStats(tested=0, converged=0, rejected=0)
    deadline = time.monotonic() + timeout_sec if timeout_sec else None

    cx_min, cx_max, cy_min, cy_max, r_min, r_max = _search_domain(terrain_pts, H)

    ctx = _SearchCtx(
        terrain_pts=terrain_pts,
        water_table=water_table,
        settings=settings,
        search=search,
        idx=idx,
        cache=cache,
        stats=stats,
        cancel_event=cancel_event,
        deadline=deadline,
        cx_min=cx_min, cx_max=cx_max,
        cy_min=cy_min, cy_max=cy_max,
        r_min=r_min, r_max=r_max,
    )

    all_circles = _enumerate_grid(cx_min, cx_max, cy_min, cy_max, search.coarse_step, r_min, r_max, search.n_radii)
    batch: list[Circle] = []
    best_fs: Optional[float] = None
    best_circle: Optional[Circle] = None
    batch_idx = 0

    n_cx = max(1, int((cx_max - cx_min) / search.coarse_step) + 1)
    n_cy = max(1, int((cy_max - cy_min) / search.coarse_step) + 1)
    batches_total = max(1, (n_cx * n_cy * search.n_radii) // _BATCH_SIZE)

    for circle in all_circles:
        batch.append(circle)
        if len(batch) >= _BATCH_SIZE:
            for c in batch:
                fs = _try_evaluate_one(ctx, c, best_fs)
                if fs is not None:
                    if best_fs is None or fs < best_fs:
                        best_fs = fs
                        best_circle = c

            batch_idx += 1
            progress = BatchProgress(
                batch_index=batch_idx,
                batches_total=batches_total,
                tested_so_far=stats.tested,
                converged_so_far=stats.converged,
                rejected_so_far=stats.rejected,
                best_fs_so_far=best_fs,
                best_circle_so_far=best_circle,
                elapsed_seconds=round(time.monotonic() - t0, 2),
            )
            yield progress
            batch = []

    for c in batch:
        fs = _try_evaluate_one(ctx, c, best_fs)
        if fs is not None and (best_fs is None or fs < best_fs):
            best_fs = fs
            best_circle = c

    return best_circle, best_fs, stats


# ---------------------------------------------------------------------------
# Internal structures
# ---------------------------------------------------------------------------


@dataclass
class _Candidate:
    circle: Circle
    fs: float


@dataclass
class _SearchCtx:
    terrain_pts: list[TerrainPoint]
    water_table: WaterTable
    settings: SpencerSettings
    search: CriticalSearchSettings
    idx: LayerIndex
    cache: CircleCache
    stats: SearchStats
    cancel_event: Optional[threading.Event]
    deadline: Optional[float]
    # Original search domain bounds — used to clip neighbourhood searches
    cx_min: float
    cx_max: float
    cy_min: float
    cy_max: float
    r_min: float
    r_max: float
    best_fs: Optional[float] = field(default=None)


# ---------------------------------------------------------------------------
# Grid / neighbourhood helpers
# ---------------------------------------------------------------------------


def _search_domain(
    terrain_pts: list[TerrainPoint], H: float
) -> tuple[float, float, float, float, float, float]:
    x_min = terrain_pts[0].x
    x_max = terrain_pts[-1].x
    y_max = max(pt.y for pt in terrain_pts)
    y_min = min(pt.y for pt in terrain_pts)
    crest_x, toe_x = _crest_and_toe_x(terrain_pts, y_max, y_min)
    slope_width = max(toe_x - crest_x, H)

    return (
        max(x_min, crest_x - 0.60 * slope_width),  # centre near slope body
        min(x_max, toe_x + 0.60 * slope_width),
        y_max,                                      # centre above crest
        y_max + 2.0 * H,
        max(0.60 * H, 0.20 * slope_width, 1e-6),   # avoid tiny local arcs
        min(3.0 * H, 1.25 * slope_width),          # avoid excessive radii
    )


def _batch_grid_search(
    ctx: _SearchCtx,
    cx_lo: float, cx_hi: float,
    cy_lo: float, cy_hi: float,
    step: float,
    r_min: float, r_max: float,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for circle in _enumerate_grid(cx_lo, cx_hi, cy_lo, cy_hi, step, r_min, r_max, ctx.search.n_radii):
        _check_cancel_timeout(ctx)
        fs = _try_evaluate_one(ctx, circle, ctx.best_fs)
        if fs is not None:
            candidates.append(_Candidate(circle=circle, fs=fs))
            if ctx.best_fs is None or fs < ctx.best_fs:
                ctx.best_fs = fs
    return candidates


def _batch_neighbourhood_search(
    ctx: _SearchCtx,
    centre: Circle,
    xy_half: float,
    r_half: float,
    step: float,
) -> list[_Candidate]:
    """
    Search a local neighbourhood around ``centre``, clipped to the original domain.

    cx/cy are explored in ±xy_half around the centre's cx/cy.
    Radius is explored in ±r_half around the centre's radius.
    All bounds are clipped to ctx domain limits so refinement never escapes.
    """
    cx_lo = max(ctx.cx_min, centre.cx - xy_half)
    cx_hi = min(ctx.cx_max, centre.cx + xy_half)
    cy_lo = max(ctx.cy_min, centre.cy - xy_half)
    cy_hi = min(ctx.cy_max, centre.cy + xy_half)
    r_lo  = max(ctx.r_min,  centre.radius - r_half)
    r_hi  = min(ctx.r_max,  centre.radius + r_half)

    # Degenerate range guard
    if cx_lo >= cx_hi or cy_lo >= cy_hi or r_lo >= r_hi:
        return []

    candidates: list[_Candidate] = []
    for circle in _enumerate_grid(cx_lo, cx_hi, cy_lo, cy_hi, step, r_lo, r_hi, ctx.search.n_radii):
        _check_cancel_timeout(ctx)
        fs = _try_evaluate_one(ctx, circle, ctx.best_fs)
        if fs is not None:
            candidates.append(_Candidate(circle=circle, fs=fs))
            if ctx.best_fs is None or fs < ctx.best_fs:
                ctx.best_fs = fs
    return candidates


def _enumerate_grid(
    cx_lo: float, cx_hi: float,
    cy_lo: float, cy_hi: float,
    step: float,
    r_min: float, r_max: float,
    n_radii: int,
) -> Generator[Circle, None, None]:
    radii = _log_radii(r_min, r_max, n_radii)
    cx = cx_lo
    while cx <= cx_hi + 1e-9:
        cy = cy_lo
        while cy <= cy_hi + 1e-9:
            for r in radii:
                yield Circle(cx=cx, cy=cy, radius=r)
            cy += step
        cx += step


def _try_evaluate_one(
    ctx: _SearchCtx,
    circle: Circle,
    best_fs: Optional[float],
) -> Optional[float]:
    """Evaluate Spencer FS for one circle. Returns fs or None if rejected."""
    # Cache hit
    cached = ctx.cache.get(circle.cx, circle.cy, circle.radius)
    if cached is not None:
        ctx.stats.tested += 1
        if cached != float("inf"):
            ctx.stats.converged += 1
            return cached
        ctx.stats.rejected += 1
        return None

    ctx.stats.tested += 1
    try:
        if not _circle_has_realistic_terrain_intersections(circle, ctx.terrain_pts):
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
            return None

        n_slices = auto_slice_count_for_circle(circle, ctx.terrain_pts)
        circle_settings = ctx.settings.model_copy(update={"n_slices": n_slices})
        slices = divide_into_slices(
            circle=circle,
            n_slices=n_slices,
            terrain_pts=ctx.terrain_pts,
            layers=list(ctx.idx.layers),
            water_table=ctx.water_table,
            layer_index=ctx.idx,
        )

        good = sum(1 for s in slices if s.height > 0)
        min_valid_slices = max(10, int(0.65 * n_slices))
        if not slices or good < min_valid_slices:
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
            return None

        if not _slices_cover_slope_body(slices, ctx.terrain_pts):
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
            return None

        # Early stopping: rough driving-force check before full Spencer
        if best_fs is not None and _driving_ratio(slices) < 1.0 / (best_fs * (1 + _EARLY_STOP_MARGIN)):
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
            return None

        fs, _theta, converged, _it = solve_spencer(slices, circle_settings)
        if not converged or not math.isfinite(fs) or fs <= 0 or fs > config.MAX_REASONABLE_FS:
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
            return None

        # Early stopping: FS clearly worse than best
        if best_fs is not None and fs > best_fs * (1 + _EARLY_STOP_MARGIN):
            ctx.stats.rejected += 1
            ctx.cache.put(circle.cx, circle.cy, circle.radius, fs)
            return None

        ctx.stats.converged += 1
        ctx.cache.put(circle.cx, circle.cy, circle.radius, fs)
        return fs

    except SpencerBaseError:
        ctx.stats.rejected += 1
        ctx.cache.put(circle.cx, circle.cy, circle.radius, float("inf"))
        return None
    except Exception:
        ctx.stats.rejected += 1
        return None


def _circle_has_realistic_terrain_intersections(
    circle: Circle,
    terrain_pts: list[TerrainPoint],
) -> bool:
    """
    Accept only circles that enter near the upper slope and exit lower/downhill.

    This rejects shallow plateau arcs and circles that intersect the terrain
    twice but do not mobilise a plausible sliding mass.
    """
    intersections = _circle_terrain_intersections(circle, terrain_pts)
    if len(intersections) < 2:
        return False

    y_min = min(pt.y for pt in terrain_pts)
    y_max = max(pt.y for pt in terrain_pts)
    height = y_max - y_min
    if height <= 1e-9:
        return False

    crest_x, toe_x = _crest_and_toe_x(terrain_pts, y_max, y_min)
    slope_width = toe_x - crest_x
    if slope_width <= 1e-9:
        return False

    entry = intersections[0]
    exit_ = intersections[-1]
    entry_x, entry_y = entry
    exit_x, exit_y = exit_

    entry_high = entry_y >= y_min + 0.55 * height
    entry_near_crest = entry_x <= crest_x + 0.35 * slope_width
    exit_downhill = exit_y <= y_min + 0.70 * height
    exit_near_toe = exit_x >= crest_x + 0.55 * slope_width

    return entry_high and entry_near_crest and exit_downhill and exit_near_toe


def _slices_cover_slope_body(
    slices: list,
    terrain_pts: list[TerrainPoint],
) -> bool:
    """Reject local plateau arcs; require slice interval to span most of crest-toe."""
    y_min = min(pt.y for pt in terrain_pts)
    y_max = max(pt.y for pt in terrain_pts)
    height = y_max - y_min
    if height <= 1e-9:
        return False

    crest_x, toe_x = _crest_and_toe_x(terrain_pts, y_max, y_min)
    left_x = min(s.x_left for s in slices)
    right_x = max(s.x_right for s in slices)
    min_base_y = min(s.y_base for s in slices)
    area = sum(s.area for s in slices)
    span = right_x - left_x
    slope_width = toe_x - crest_x
    if slope_width <= 1e-9:
        return False

    min_span = max(0.70 * slope_width, 0.60 * height)
    min_depth = y_min + 0.20 * height
    min_area = 0.15 * slope_width * height

    return (
        span >= min_span
        and left_x < toe_x
        and right_x > crest_x
        and min_base_y <= min_depth
        and area >= min_area
    )


def _crest_and_toe_x(
    terrain_pts: list[TerrainPoint],
    y_max: float,
    y_min: float,
) -> tuple[float, float]:
    crest_x = terrain_pts[0].x
    toe_x = terrain_pts[-1].x

    for i in range(len(terrain_pts) - 1):
        a, b = terrain_pts[i], terrain_pts[i + 1]
        if abs(a.y - y_max) < 1e-6 and b.y < a.y:
            crest_x = a.x
        if a.y > b.y and abs(b.y - y_min) < 1e-6:
            toe_x = b.x

    return crest_x, toe_x


def _circle_terrain_intersections(
    circle: Circle,
    terrain_pts: list[TerrainPoint],
) -> list[tuple[float, float]]:
    """Return deduplicated circle/terrain intersections as (x, y)."""
    points: list[tuple[float, float]] = []
    cx, cy, radius = circle.cx, circle.cy, circle.radius

    for i in range(len(terrain_pts) - 1):
        x0, y0 = terrain_pts[i].x, terrain_pts[i].y
        x1, y1 = terrain_pts[i + 1].x, terrain_pts[i + 1].y
        dx, dy = x1 - x0, y1 - y0
        fx, fy = x0 - cx, y0 - cy

        a = dx * dx + dy * dy
        if a < 1e-12:
            continue
        b = 2.0 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius
        disc = b * b - 4.0 * a * c
        if disc < 0:
            continue

        sqrt_disc = math.sqrt(disc)
        for sign in (1.0, -1.0):
            t = (-b + sign * sqrt_disc) / (2.0 * a)
            if 0.0 <= t <= 1.0:
                points.append((x0 + t * dx, y0 + t * dy))

    points.sort(key=lambda item: item[0])
    deduped: list[tuple[float, float]] = []
    for x, y in points:
        if not deduped or math.hypot(x - deduped[-1][0], y - deduped[-1][1]) > 1e-4:
            deduped.append((x, y))
    return deduped


def _driving_ratio(slices) -> float:
    """Rough driving force ratio (positive driving / total weight). Used for early stop."""
    total_W = sum(s.weight for s in slices)
    driving = sum(s.weight * math.sin(math.radians(s.alpha_deg)) for s in slices)
    return driving / total_W if total_W > 1e-10 else 0.0


def _check_cancel_timeout(ctx: _SearchCtx) -> None:
    from app.errors import AnalysisTimeoutError
    if ctx.cancel_event and ctx.cancel_event.is_set():
        raise AnalysisCancelledError(
            "L'analyse a été annulée par l'utilisateur.",
            {"tested": ctx.stats.tested},
        )
    if ctx.deadline and time.monotonic() > ctx.deadline:
        raise AnalysisTimeoutError(
            "L'analyse a dépassé la durée maximale autorisée.",
            {"tested": ctx.stats.tested, "deadline_exceeded": True},
        )


def _log_radii(r_min: float, r_max: float, n: int) -> list[float]:
    if n == 1:
        return [(r_min + r_max) / 2.0]
    if r_min <= 0 or r_max <= r_min:
        return [r_min + i * (r_max - r_min) / max(n - 1, 1) for i in range(n)]
    lo, hi = math.log(r_min), math.log(r_max)
    step = (hi - lo) / (n - 1)
    return [math.exp(lo + i * step) for i in range(n)]


def _top_k(candidates: list[_Candidate], k: int) -> list[_Candidate]:
    return sorted(candidates, key=lambda c: c.fs)[:k]

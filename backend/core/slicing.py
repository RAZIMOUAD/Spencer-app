"""Slice generation for Spencer's method."""

from __future__ import annotations

import math

from app.schemas import Circle, Slice, SoilLayer, TerrainPoint, WaterTable
from app.errors import (
    CircleIntersectionError,
    EmptySliceSetError,
    LayerLookupError,
    NumericalInstabilityError,
    NonFiniteValueError,
)
from core.layer_index import LayerIndex

GAMMA_W = 9.81
COS_ALPHA_MIN = 0.05  # reject slices where |cos α| < this (α > ~87°)


def divide_into_slices(
    circle: Circle,
    n_slices: int,
    terrain_pts: list[TerrainPoint],
    layers: list[SoilLayer],
    water_table: WaterTable,
    layer_index: LayerIndex | None = None,
) -> list[Slice]:
    """
    Divide the slip mass into n_slices vertical slices.

    Layer and pore-pressure lookup
    --------------------------------
    Both use the **mid-height elevation** of the slice:

        y_mid = (y_top + y_base) / 2

    This is more representative than y_base alone when a slice straddles a
    layer boundary or crosses the water table near mid-height.

    Parameters
    ----------
    layer_index : LayerIndex | None
        Pre-built index for O(log n) layer lookup.  If None, it is built
        from ``layers`` on every call (fine for one-off use; expensive in
        batch search — build once and pass in).

    Raises
    ------
    CircleIntersectionError  — no valid overlap between circle and terrain.
    EmptySliceSetError       — no slice with h > 0 produced.
    LayerLookupError         — a base elevation outside all layer bounds.
    NumericalInstabilityError — |cos α| too small for a slice.
    NonFiniteValueError       — NaN or Inf produced.
    """
    x_left, x_right = _find_valid_x_range(circle, terrain_pts)

    if x_right - x_left < 1e-3:
        raise CircleIntersectionError(
            "La plage valide de tranches est quasi nulle. "
            "Le cercle n'intersecte le terrain qu'en un point.",
            {"cx": circle.cx, "cy": circle.cy, "r": circle.radius},
        )

    b = (x_right - x_left) / n_slices
    H_top = max(pt.y for pt in terrain_pts)
    idx: LayerIndex = layer_index or LayerIndex.build(layers, H_top)

    slices: list[Slice] = []

    for i in range(n_slices):
        x_l = x_left + i * b
        x_r = x_l + b
        x_m = 0.5 * (x_l + x_r)

        y_base = _circle_base_y(circle, x_m)
        if y_base is None:
            continue

        y_top = _terrain_y_at(x_m, terrain_pts)
        h = y_top - y_base
        if h < 1e-6:
            continue

        # Mid-height elevation — used for layer lookup and pore pressure
        y_mid = 0.5 * (y_top + y_base)

        # Base inclination: α = atan2(x_mid − cx, cy − y_base)
        # Positive α → base dips toward toe (right), driving failure.
        alpha_rad = math.atan2(x_m - circle.cx, circle.cy - y_base)
        cos_a = math.cos(alpha_rad)
        if abs(cos_a) < COS_ALPHA_MIN:
            raise NumericalInstabilityError(
                f"cos(α) = {cos_a:.4f} trop proche de zéro (tranche {i}). "
                "Réduisez le rayon ou repositionnez le cercle.",
                {"slice_index": i, "cos_alpha": cos_a},
            )

        base_len = b / abs(cos_a)  # dl = b / |cos(α)| — always positive

        # Trapezoidal area using left and right face heights
        y_top_l = _terrain_y_at(x_l, terrain_pts)
        y_base_l = _circle_base_y(circle, x_l) or y_base
        y_top_r = _terrain_y_at(x_r, terrain_pts)
        y_base_r = _circle_base_y(circle, x_r) or y_base
        area = 0.5 * b * (
            (y_top_l - y_base_l) + (y_top_r - y_base_r)
        )
        if area <= 0:
            area = h * b  # rectangular fallback; if still ≤ 0, skip
        if area <= 0:
            continue

        # Dominant layer at slice mid-height — O(log n) via LayerIndex
        try:
            layer = idx.find(y_mid)
        except LayerLookupError as exc:
            raise LayerLookupError(
                f"Tranche {i} : {exc.message}",
                {"slice_index": i, "y_mid": y_mid, **exc.details},
            ) from exc

        # Total weight W = γ · area (pore pressure handled separately)
        W = layer.gamma * area

        # Pore pressure u at slice mid-height (hydrostatic)
        hw = max(0.0, water_table.elevation - y_mid)
        u = GAMMA_W * hw
        pore_force = u * base_len

        alpha_deg = math.degrees(alpha_rad)
        driving = W * math.sin(alpha_rad)
        normal_eff = W * cos_a - pore_force

        # Finite-value guards
        for name, val in [("W", W), ("u", u), ("alpha_deg", alpha_deg)]:
            if not math.isfinite(val):
                raise NonFiniteValueError(
                    f"Tranche {i} : valeur non finie pour {name} = {val}.",
                    {"slice_index": i, "field": name, "value": val},
                )

        slices.append(
            Slice(
                index=i,
                x_left=x_l, x_right=x_r, x_mid=x_m,
                width=b,
                y_top=y_top, y_base=y_base,
                height=h, area=area,
                alpha_deg=alpha_deg,
                base_length=base_len,
                layer_id=layer.id,
                cohesion=layer.cohesion,
                phi_deg=layer.phi_deg,
                weight=W,
                pore_pressure=u,
                pore_force=pore_force,
                normal_eff=normal_eff,
                driving=driving,
                resisting=0.0,
            )
        )

    if not slices:
        raise EmptySliceSetError(
            "Aucune tranche utilisable. Le cercle est probablement trop haut "
            "ou la masse glissante est trop mince.",
            {"n_requested": n_slices},
        )

    return slices


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _find_valid_x_range(circle: Circle, terrain_pts: list[TerrainPoint]) -> tuple[float, float]:
    """
    Find the contiguous x-range where the circle base is below the terrain surface.

    Handles three cases:
    - Circle enters and exits within the terrain domain (standard).
    - Circle starts inside terrain (left boundary = terrain left boundary).
    - Circle exits outside terrain (right boundary = terrain right boundary).

    Returns (x_start, x_end).

    Raises CircleIntersectionError if no valid range exists.
    """
    x_circle_lo = circle.cx - circle.radius
    x_circle_hi = circle.cx + circle.radius
    x_terrain_lo = terrain_pts[0].x
    x_terrain_hi = terrain_pts[-1].x

    # Intersection of circle extent with terrain domain
    x_lo = max(x_circle_lo, x_terrain_lo)
    x_hi = min(x_circle_hi, x_terrain_hi)

    if x_lo >= x_hi - 1e-9:
        raise CircleIntersectionError(
            "Le cercle ne recouvre pas le domaine du terrain.",
            {"cx": circle.cx, "cy": circle.cy, "r": circle.radius,
             "x_terrain": [x_terrain_lo, x_terrain_hi]},
        )

    # All x-coordinates that could be boundaries of valid intervals
    crossings = _circle_terrain_x_intersections(circle, terrain_pts)
    candidates = sorted(set(
        [x_lo, x_hi] + [x for x in crossings if x_lo <= x <= x_hi]
    ))

    # Find sub-intervals where y_base < y_terrain (valid slice territory)
    valid: list[tuple[float, float]] = []
    for i in range(len(candidates) - 1):
        x_test = (candidates[i] + candidates[i + 1]) / 2.0
        y_b = _circle_base_y(circle, x_test)
        y_t = _terrain_y_at(x_test, terrain_pts)
        if y_b is not None and y_b < y_t - 1e-6:
            valid.append((candidates[i], candidates[i + 1]))

    if not valid:
        raise CircleIntersectionError(
            "Le cercle est entièrement au-dessus de la surface du terrain "
            "dans la zone de recouvrement.",
            {"cx": circle.cx, "cy": circle.cy, "r": circle.radius},
        )

    # Merge contiguous intervals into one span
    x_start = valid[0][0]
    x_end = valid[-1][1]
    return x_start, x_end


def _circle_base_y(circle: Circle, x: float) -> float | None:
    """Lower arc y at x, or None if x is outside the circle's horizontal extent."""
    dx = x - circle.cx
    disc = circle.radius ** 2 - dx ** 2
    if disc < 0:
        return None
    return circle.cy - math.sqrt(disc)


def _terrain_y_at(x: float, terrain_pts: list[TerrainPoint]) -> float:
    """Linearly interpolate terrain elevation at x (clamped at boundaries)."""
    if x <= terrain_pts[0].x:
        return terrain_pts[0].y
    if x >= terrain_pts[-1].x:
        return terrain_pts[-1].y
    for i in range(len(terrain_pts) - 1):
        x0, y0 = terrain_pts[i].x, terrain_pts[i].y
        x1, y1 = terrain_pts[i + 1].x, terrain_pts[i + 1].y
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return terrain_pts[-1].y


def _circle_terrain_x_intersections(
    circle: Circle,
    terrain_pts: list[TerrainPoint],
) -> list[float]:
    """
    Return sorted, deduplicated x-coordinates where the circle crosses the terrain.

    Uses the analytic formula for circle-line-segment intersection.
    Deduplicates hits within 1e-4 m tolerance (avoids double-counting at vertices).
    """
    xs: list[float] = []
    cx, cy, r = circle.cx, circle.cy, circle.radius

    for i in range(len(terrain_pts) - 1):
        x0, y0 = terrain_pts[i].x, terrain_pts[i].y
        x1, y1 = terrain_pts[i + 1].x, terrain_pts[i + 1].y

        dx, dy = x1 - x0, y1 - y0
        fx, fy = x0 - cx, y0 - cy

        a = dx * dx + dy * dy
        if a < 1e-12:
            continue
        b = 2.0 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - r * r

        disc = b * b - 4.0 * a * c
        if disc < 0:
            continue

        sqrt_disc = math.sqrt(disc)
        for sign in (1, -1):
            t = (-b + sign * sqrt_disc) / (2.0 * a)
            if 0.0 <= t <= 1.0:
                xs.append(x0 + t * dx)

    xs.sort()
    deduped: list[float] = []
    for x in xs:
        if not deduped or abs(x - deduped[-1]) > 1e-4:
            deduped.append(x)

    return deduped

"""Tests for core.slicing — real slice geometry.

Geometry
--------
Simple 3-segment terrain: [(0,10), (15,0), (30,0)]

Failure circle: cx=4, cy=12, r=13
  - y_base at x=0  ≈  −0.4  → below terrain y=10  → circle starts inside terrain domain
  - y_base at x=12 ≈   1.75 → terrain y≈1.33 → exit near x=11.8
  - Valid span: x ∈ [0, ~11.8]
  - Right slices (x > cx=4) have positive α — dominant active mass
  - Left slices (x < 4) have negative α but shorter range
  → Σ(W·sin α) > 0, FS well-defined
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pytest

from app.schemas import Circle, SoilLayer, TerrainPoint, WaterTable
from app.errors import CircleIntersectionError, EmptySliceSetError
from core.slicing import (
    divide_into_slices,
    _circle_terrain_x_intersections,
    _find_valid_x_range,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _terrain():
    """Simple 3-point terrain: slope + downstream base."""
    return [
        TerrainPoint(x=0.0,  y=10.0),
        TerrainPoint(x=15.0, y=0.0),
        TerrainPoint(x=30.0, y=0.0),
    ]


def _layers():
    return [
        SoilLayer(id=1, name="Clay", gamma=19.0, cohesion=15.0, phi_deg=25.0, thickness=None),
    ]


def _good_circle():
    """cx=4, cy=12, r=13 — enters terrain at left boundary, exits on slope face."""
    return Circle(cx=4.0, cy=12.0, radius=13.0)


def _water_table_low():
    return WaterTable(elevation=-20.0)


# ---------------------------------------------------------------------------
# _find_valid_x_range
# ---------------------------------------------------------------------------

def test_valid_range_exists():
    x_lo, x_hi = _find_valid_x_range(_good_circle(), _terrain())
    assert x_hi > x_lo


def test_valid_range_within_terrain():
    pts = _terrain()
    x_lo, x_hi = _find_valid_x_range(_good_circle(), pts)
    assert x_lo >= pts[0].x
    assert x_hi <= pts[-1].x


def test_valid_range_left_boundary_when_circle_starts_inside():
    """Circle cx=4, r=13 extends to x=-9, terrain starts at x=0 → x_lo=0."""
    pts = _terrain()
    x_lo, _ = _find_valid_x_range(_good_circle(), pts)
    assert abs(x_lo - 0.0) < 1e-6  # left boundary = terrain left


def test_no_valid_range_for_tiny_far_circle():
    pts = _terrain()
    far_circle = Circle(cx=500.0, cy=5.0, radius=1.0)
    with pytest.raises(CircleIntersectionError):
        _find_valid_x_range(far_circle, pts)


# ---------------------------------------------------------------------------
# _circle_terrain_x_intersections
# ---------------------------------------------------------------------------

def test_intersection_sorted():
    xs = _circle_terrain_x_intersections(_good_circle(), _terrain())
    assert xs == sorted(xs)


def test_intersection_deduplication_at_vertex():
    """Circle tangent at a terrain vertex must not double-count."""
    terrain = [
        TerrainPoint(x=0.0, y=5.0),
        TerrainPoint(x=5.0, y=5.0),
        TerrainPoint(x=10.0, y=0.0),
    ]
    circle = Circle(cx=5.0, cy=10.0, radius=5.0)
    xs = _circle_terrain_x_intersections(circle, terrain)
    close_to_5 = [x for x in xs if abs(x - 5.0) < 1e-3]
    assert len(close_to_5) <= 1


# ---------------------------------------------------------------------------
# divide_into_slices
# ---------------------------------------------------------------------------

def test_produces_slices():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    assert len(slices) > 0


def test_slice_count_close_to_n():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    assert 10 <= len(slices) <= 20  # some edge slivers may be dropped


def test_slice_x_boundaries_increase():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    for slc in slices:
        assert slc.x_left < slc.x_mid < slc.x_right


def test_slice_heights_positive():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    for slc in slices:
        assert slc.height > 0


def test_slice_weights_positive():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    for slc in slices:
        assert slc.weight > 0


def test_alpha_range():
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    for slc in slices:
        assert -90.0 < slc.alpha_deg < 90.0


def test_pore_pressure_zero_below_water():
    """Water table at −20 m → all slice bases above → u = 0."""
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), _water_table_low())
    assert all(s.pore_pressure == 0.0 for s in slices)


def test_pore_pressure_positive_above_water():
    """Water table at 5 m → slices with y_base < 5 have u > 0."""
    wt = WaterTable(elevation=5.0)
    slices = divide_into_slices(_good_circle(), 20, _terrain(), _layers(), wt)
    below = [s for s in slices if s.y_base < 5.0]
    if below:
        assert all(s.pore_pressure > 0 for s in below)


def test_far_circle_raises():
    tiny_far = Circle(cx=500.0, cy=5.0, radius=1.0)
    with pytest.raises(CircleIntersectionError):
        divide_into_slices(tiny_far, 20, _terrain(), _layers(), _water_table_low())


def test_high_circle_raises():
    high = Circle(cx=7.0, cy=200.0, radius=2.0)
    with pytest.raises((CircleIntersectionError, EmptySliceSetError)):
        divide_into_slices(high, 20, _terrain(), _layers(), _water_table_low())


# ---------------------------------------------------------------------------
# y_mid layer selection test
# ---------------------------------------------------------------------------

def test_ymid_changes_layer_selection():
    """
    With a 2-layer profile, the layer returned for a slice changes depending on
    whether y_mid or y_base is used for lookup.

    Setup:
      - H = 10 m, top layer C1 has thickness 6 m (z_interface = 4 m).
      - For a nearly-flat circle, we construct a slice whose:
          y_base ≈ 2 m (in C2, below interface at 4 m)
          y_top  ≈ 8 m (in C1, above interface at 4 m)
          y_mid  ≈ 5 m (in C1)
      - If lookup used y_base → C2 (gamma=25); if y_mid → C1 (gamma=19).
      - The slice weight must reflect C1 (y_mid logic).
    """
    from core.layer_index import LayerIndex

    # Two layers: C1 from z=10 to z=4 (thickness 6 m), C2 from z=4 to -∞
    c1 = SoilLayer(id=1, name="C1", gamma=19.0, cohesion=10.0, phi_deg=30.0, thickness=6.0)
    c2 = SoilLayer(id=2, name="C2", gamma=25.0, cohesion=5.0,  phi_deg=20.0, thickness=None)
    layers = [c1, c2]

    # Flat terrain at y=10, x ∈ [0, 30]
    terrain = [
        TerrainPoint(x=0.0,  y=10.0),
        TerrainPoint(x=30.0, y=10.0),
    ]

    # Circle with large radius so base is nearly flat across the terrain
    # cx=15, cy=25, r=22 → y_base at x=15 = cy - r = 3, y_top = 10 → y_mid = 6.5
    # z_interface = 4 → y_base (3) < 4 → C2 by y_base; y_mid (6.5) > 4 → C1 by y_mid
    circle = Circle(cx=15.0, cy=25.0, radius=22.0)

    idx = LayerIndex.build(layers, H_top=10.0)
    wt = WaterTable(elevation=-100.0)

    slices = divide_into_slices(circle, 10, terrain, layers, wt, layer_index=idx)
    assert len(slices) > 0

    # Find slices near the centre where y_base ≈ 3 and y_mid ≈ 6.5
    centre_slices = [s for s in slices if abs(s.x_mid - 15.0) < 3.0]
    assert centre_slices, "Expected slices near x=15"

    for slc in centre_slices:
        y_mid = 0.5 * (slc.y_top + slc.y_base)
        # y_mid should be above the interface (z=4), so layer must be C1 (id=1)
        if y_mid > 4.0:
            assert slc.layer_id == 1, (
                f"Slice at x={slc.x_mid:.2f}: y_base={slc.y_base:.2f}, y_mid={y_mid:.2f} "
                f"→ expected layer C1 (id=1), got id={slc.layer_id}"
            )
            # Weight should use C1's gamma (19.0), not C2's (25.0)
            expected_gamma = c1.gamma
            computed_gamma = slc.weight / slc.area
            assert abs(computed_gamma - expected_gamma) < 0.5, (
                f"Expected γ≈{expected_gamma}, got {computed_gamma:.2f} "
                f"(layer_id={slc.layer_id})"
            )

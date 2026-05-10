"""Geometry filters for critical slip-circle search."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas import Circle, TerrainPoint
from core.search import (
    _circle_has_realistic_terrain_intersections,
    _search_domain,
)


def _terrain():
    return [
        TerrainPoint(x=0.0, y=10.0),
        TerrainPoint(x=25.0, y=10.0),
        TerrainPoint(x=40.0, y=0.0),
        TerrainPoint(x=80.0, y=0.0),
    ]


def test_realistic_circle_intersections_accepted():
    circle = Circle(cx=40.0, cy=18.0, radius=18.0)
    assert _circle_has_realistic_terrain_intersections(circle, _terrain()) is True


def test_shallow_plateau_arc_rejected():
    circle = Circle(cx=25.0, cy=15.0, radius=6.0)
    assert _circle_has_realistic_terrain_intersections(circle, _terrain()) is False


def test_circle_with_single_terrain_intersection_rejected():
    circle = Circle(cx=82.0, cy=26.0, radius=30.0)
    assert _circle_has_realistic_terrain_intersections(circle, _terrain()) is False


def test_search_domain_allows_deeper_global_radii():
    cx_min, cx_max, cy_min, cy_max, r_min, r_max = _search_domain(_terrain(), H=10.0)
    assert cx_min >= 0.0
    assert cx_max <= 80.0
    assert cy_min == 10.0
    assert cy_max == 30.0
    assert r_min >= 5.0
    assert r_max <= 40.0
    assert r_max > 30.0

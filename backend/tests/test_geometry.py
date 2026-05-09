"""Unit tests for core.geometry."""

import math
import sys
import os

# Ensure backend/ is on the path when running from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.geometry import auto_plateaus, slope_profile, point_on_slope, layer_interfaces
from app.schemas import SoilLayer


# ---------------------------------------------------------------------------
# auto_plateaus
# ---------------------------------------------------------------------------


def test_auto_plateaus_height_dominates():
    """When H is large, H-based rule should win."""
    H, L = 20.0, 10.0
    l_amont, l_aval = auto_plateaus(H, L)
    assert l_amont == pytest.approx(max(1.5 * L, 2.5 * H))
    assert l_aval == pytest.approx(max(2.5 * L, 4.0 * H))


def test_auto_plateaus_length_dominates():
    """When L is large, L-based rule should win."""
    H, L = 5.0, 50.0
    l_amont, l_aval = auto_plateaus(H, L)
    assert l_amont == pytest.approx(1.5 * L)   # 75 > 12.5
    assert l_aval == pytest.approx(2.5 * L)    # 125 > 20


def test_auto_plateaus_are_positive():
    H, L = 8.0, 12.0
    l_amont, l_aval = auto_plateaus(H, L)
    assert l_amont > 0
    assert l_aval > 0


# ---------------------------------------------------------------------------
# slope_profile
# ---------------------------------------------------------------------------


def test_slope_profile_returns_four_points():
    pts = slope_profile(10.0, 15.0, 25.0, 40.0)
    assert len(pts) == 4


def test_slope_profile_elevations():
    H, L, l_amont, l_aval = 10.0, 20.0, 25.0, 40.0
    pts = slope_profile(H, L, l_amont, l_aval)
    assert pts[0].y == pytest.approx(H)  # upstream plateau start
    assert pts[1].y == pytest.approx(H)  # crest
    assert pts[2].y == pytest.approx(0.0)  # toe
    assert pts[3].y == pytest.approx(0.0)  # downstream end


def test_slope_profile_x_monotone():
    pts = slope_profile(10.0, 20.0, 25.0, 40.0)
    xs = [pt.x for pt in pts]
    assert xs == sorted(xs)


# ---------------------------------------------------------------------------
# point_on_slope
# ---------------------------------------------------------------------------


def test_point_on_slope_upstream():
    assert point_on_slope(5.0, 10.0, 20.0, 25.0) == pytest.approx(10.0)


def test_point_on_slope_downstream():
    assert point_on_slope(100.0, 10.0, 20.0, 25.0) == pytest.approx(0.0)


def test_point_on_slope_midslope():
    # At x = l_amont + L/2, y should be H/2
    H, L, l_amont = 10.0, 20.0, 25.0
    y = point_on_slope(l_amont + L / 2, H, L, l_amont)
    assert y == pytest.approx(H / 2, rel=1e-6)


# ---------------------------------------------------------------------------
# layer_interfaces
# ---------------------------------------------------------------------------


def test_layer_interfaces_two_layers():
    layers = [
        SoilLayer(id=1, name="C1", gamma=20.0, cohesion=10.0, phi_deg=30.0, thickness=3.0),
        SoilLayer(id=2, name="C2", gamma=22.0, cohesion=0.0, phi_deg=35.0, thickness=None),
    ]
    ifaces = layer_interfaces(10.0, layers)
    assert ifaces == pytest.approx([7.0])  # H - h1 = 10 - 3 = 7


def test_layer_interfaces_three_layers():
    layers = [
        SoilLayer(id=1, name="C1", gamma=19.0, cohesion=5.0, phi_deg=28.0, thickness=2.0),
        SoilLayer(id=2, name="C2", gamma=21.0, cohesion=8.0, phi_deg=32.0, thickness=3.0),
        SoilLayer(id=3, name="C3", gamma=23.0, cohesion=0.0, phi_deg=38.0, thickness=None),
    ]
    ifaces = layer_interfaces(10.0, layers)
    assert ifaces == pytest.approx([8.0, 5.0])  # [10-2, 10-2-3]


def test_layer_interfaces_raises_if_non_last_has_no_thickness():
    layers = [
        SoilLayer(id=1, name="C1", gamma=19.0, cohesion=5.0, phi_deg=28.0, thickness=None),
        SoilLayer(id=2, name="C2", gamma=21.0, cohesion=0.0, phi_deg=35.0, thickness=None),
    ]
    with pytest.raises(ValueError, match="not the last layer"):
        layer_interfaces(10.0, layers)

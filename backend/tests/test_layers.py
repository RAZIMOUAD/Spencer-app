"""Unit tests for core.layers."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.layers import layer_at_elevation, submerged_weight
from app.schemas import SoilLayer


# Helper to build a typical 3-layer stack
def _make_layers():
    return [
        SoilLayer(id=1, name="C1", gamma=18.0, cohesion=10.0, phi_deg=25.0, thickness=3.0),
        SoilLayer(id=2, name="C2", gamma=20.0, cohesion=5.0,  phi_deg=30.0, thickness=4.0),
        SoilLayer(id=3, name="C3", gamma=22.0, cohesion=0.0,  phi_deg=35.0, thickness=None),
    ]


# interfaces: [10-3=7, 10-3-4=3]  → [7.0, 3.0]
INTERFACES = [7.0, 3.0]


def test_layer_at_top():
    layers = _make_layers()
    layer = layer_at_elevation(9.0, INTERFACES, layers)
    assert layer.id == 1


def test_layer_in_middle():
    layers = _make_layers()
    layer = layer_at_elevation(5.0, INTERFACES, layers)
    assert layer.id == 2


def test_layer_at_substratum():
    layers = _make_layers()
    layer = layer_at_elevation(1.0, INTERFACES, layers)
    assert layer.id == 3


def test_layer_at_elevation_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        layer_at_elevation(5.0, [], [])


# ---------------------------------------------------------------------------
# submerged_weight
# ---------------------------------------------------------------------------


def test_submerged_weight_above_water_table():
    layer = SoilLayer(id=1, name="C1", gamma=20.0, cohesion=5.0, phi_deg=30.0, thickness=3.0)
    # z_mid > z_nappe → full unit weight
    w = submerged_weight(layer, z_mid=8.0, z_nappe=5.0)
    assert w == pytest.approx(20.0)


def test_submerged_weight_below_water_table():
    layer = SoilLayer(id=1, name="C1", gamma=20.0, cohesion=5.0, phi_deg=30.0, thickness=3.0)
    # z_mid < z_nappe → buoyant weight = γ - γ_w
    w = submerged_weight(layer, z_mid=3.0, z_nappe=5.0)
    assert w == pytest.approx(20.0 - 9.81)

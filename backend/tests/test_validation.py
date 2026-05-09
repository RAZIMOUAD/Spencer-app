"""Unit tests for core.validation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.validation import validate_geometry, validate_layers, validate_circle
from app.schemas import SoilLayer, Circle, TerrainPoint


# ---------------------------------------------------------------------------
# validate_geometry
# ---------------------------------------------------------------------------


def test_validate_geometry_valid():
    assert validate_geometry(10.0, 15.0) == []


def test_validate_geometry_negative_height():
    errors = validate_geometry(-1.0, 15.0)
    assert any("H" in e for e in errors)


def test_validate_geometry_zero_length():
    errors = validate_geometry(10.0, 0.0)
    assert any("L" in e for e in errors)


def test_validate_geometry_extreme_ratio():
    # H/L = 50 > 10 → should error
    errors = validate_geometry(100.0, 2.0)
    assert any("H/L" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_layers
# ---------------------------------------------------------------------------


def _valid_layers():
    return [
        SoilLayer(id=1, name="C1", gamma=19.0, cohesion=10.0, phi_deg=30.0, thickness=3.0),
        SoilLayer(id=2, name="C2", gamma=21.0, cohesion=0.0,  phi_deg=35.0, thickness=None),
    ]


def test_validate_layers_valid():
    assert validate_layers(_valid_layers(), H=10.0) == []


def test_validate_layers_thickness_sum_exceeds_H():
    layers = [
        SoilLayer(id=1, name="C1", gamma=19.0, cohesion=10.0, phi_deg=30.0, thickness=12.0),
        SoilLayer(id=2, name="C2", gamma=21.0, cohesion=0.0,  phi_deg=35.0, thickness=None),
    ]
    errors = validate_layers(layers, H=10.0)
    assert any("épaisseurs" in e for e in errors)


def test_validate_layers_invalid_phi():
    # model_construct bypasses Pydantic field validators so we can test validate_layers directly
    layers = [
        SoilLayer.model_construct(id=1, name="C1", gamma=19.0, cohesion=10.0, phi_deg=95.0, thickness=3.0),
        SoilLayer.model_construct(id=2, name="C2", gamma=21.0, cohesion=0.0,  phi_deg=35.0, thickness=None),
    ]
    errors = validate_layers(layers, H=10.0)
    assert any("φ" in e for e in errors)


def test_validate_layers_empty():
    errors = validate_layers([], H=10.0)
    assert errors  # should report at least one error


# ---------------------------------------------------------------------------
# validate_circle
# ---------------------------------------------------------------------------


def _make_terrain():
    """Realistic terrain: upstream plateau + slope + downstream base."""
    return [
        TerrainPoint(x=0.0,  y=10.0),
        TerrainPoint(x=15.0, y=10.0),  # upstream plateau
        TerrainPoint(x=30.0, y=0.0),   # slope face
        TerrainPoint(x=60.0, y=0.0),   # downstream base
    ]


def test_validate_circle_valid():
    # Circle centred above the slope, intersects upstream plateau and downstream base
    terrain = _make_terrain()
    circle = Circle(cx=22.5, cy=15.0, radius=16.0)
    errors = validate_circle(circle, terrain)
    assert errors == []


def test_validate_circle_above_terrain():
    terrain = _make_terrain()
    # Circle sits entirely above the terrain — bottom = 50 - 5 = 45 > 10
    circle = Circle(cx=7.5, cy=50.0, radius=5.0)
    errors = validate_circle(circle, terrain)
    assert any("au-dessus" in e for e in errors)


def test_validate_circle_no_intersection():
    terrain = _make_terrain()
    # Tiny circle far to the right — does not overlap the terrain domain at all
    circle = Circle(cx=100.0, cy=5.0, radius=1.0)
    errors = validate_circle(circle, terrain)
    # validate_circle delegates to _find_valid_x_range which raises
    # "Le cercle ne recouvre pas le domaine du terrain."
    assert len(errors) > 0, "Expected at least one error for a circle outside terrain domain"

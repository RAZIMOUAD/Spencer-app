"""Tests for core.spencer — Bishop Modified + Spencer force closure.

Geometry used
-------------
Simple 3-segment terrain (no large plateaus):
  [(0, 10), (15, 0), (30, 0)]

Failure circle: cx=4, cy=12, r=13
  - Enters slope near crest (left, slightly negative α)
  - Exits on slope face (right, positive α)
  - Most mass on active (positive α) side → Σ(W·sin α) > 0 → FS well-defined.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pytest

from app.schemas import Circle, SoilLayer, SpencerSettings, TerrainPoint, WaterTable
from app.errors import SpencerConvergenceError
from core.slicing import divide_into_slices
from core.spencer import solve_spencer, _bishop_iterate, _force_sweep, compute_residuals


# ---------------------------------------------------------------------------
# Fixtures — deterministic geometry
# ---------------------------------------------------------------------------

def _simple_terrain():
    """Slope from (0,10) to (15,0), then flat to (30,0). No large plateaus."""
    return [
        TerrainPoint(x=0.0,  y=10.0),
        TerrainPoint(x=15.0, y=0.0),
        TerrainPoint(x=30.0, y=0.0),
    ]


def _failure_circle():
    """
    Circle centred at (4, 12), r=13.
    Bottom at (4, -1). Intersects slope near x≈1 (y≈9.3) and x≈10.5 (y≈3).
    Active slices (α>0) dominate → Σ(W·sin α) > 0.
    """
    return Circle(cx=4.0, cy=12.0, radius=13.0)


def _homogeneous_layers():
    return [
        SoilLayer(id=1, name="Clay", gamma=19.0, cohesion=15.0, phi_deg=25.0, thickness=None),
    ]


def _dry():
    return WaterTable(elevation=-20.0)


def _make_slices(wt=None, layers=None, circle=None):
    t = _simple_terrain()
    c = circle or _failure_circle()
    l = layers or _homogeneous_layers()
    w = wt or _dry()
    return divide_into_slices(c, 20, t, l, w)


# ---------------------------------------------------------------------------
# Bishop sub-routine tests
# ---------------------------------------------------------------------------

def test_bishop_fs_positive():
    slices = _make_slices()
    fs, iters = _bishop_iterate(slices, 1e-6, 200)
    assert fs > 0.0


def test_bishop_fs_reasonable():
    """FS must be finite, positive, and physically plausible.

    The test circle (cx=4, cy=12, r=13) cuts a small shallow arc where the
    driving force is low relative to the strong soil (c'=15, φ'=25°), so FS
    is high but valid.  The test catches NaN / negative / infinite FS.
    """
    slices = _make_slices()
    fs, _ = _bishop_iterate(slices, 1e-6, 200)
    assert 0.5 < fs < 50.0


def test_bishop_converges():
    slices = _make_slices()
    _, iters = _bishop_iterate(slices, 1e-6, 200)
    assert iters < 200  # should converge well before limit


# ---------------------------------------------------------------------------
# Full Spencer solver tests
# ---------------------------------------------------------------------------

def test_solve_spencer_returns_positive_fs():
    slices = _make_slices()
    fs, theta, converged, iters = solve_spencer(slices, SpencerSettings())
    assert fs > 0.0


def test_solve_spencer_converged():
    slices = _make_slices()
    fs, theta, converged, iters = solve_spencer(slices, SpencerSettings())
    assert converged is True
    assert iters > 0


def test_solve_spencer_fs_reasonable():
    """FS must be finite, positive, and within a broad physical range."""
    slices = _make_slices()
    fs, _, _, _ = solve_spencer(slices, SpencerSettings())
    assert 0.5 < fs < 50.0


def test_solve_spencer_theta_within_settings():
    settings = SpencerSettings(theta_min=-30.0, theta_max=30.0)
    slices = _make_slices()
    _, theta, _, _ = solve_spencer(slices, settings)
    assert settings.theta_min <= theta <= settings.theta_max


def test_fs_increases_with_cohesion():
    """Higher c' → higher FS for the same circle and slope."""
    terrain = _simple_terrain()
    wt = _dry()
    circle = _failure_circle()
    fs_vals = []
    for c in [5.0, 15.0, 30.0]:
        layers = [SoilLayer(id=1, name="L", gamma=19.0, cohesion=c, phi_deg=25.0, thickness=None)]
        slices = divide_into_slices(circle, 20, terrain, layers, wt)
        fs, _, _, _ = solve_spencer(slices, SpencerSettings())
        fs_vals.append(fs)
    assert fs_vals[0] < fs_vals[1] < fs_vals[2]


def test_fs_increases_with_friction():
    """Higher φ' → higher FS for the same circle."""
    terrain = _simple_terrain()
    wt = _dry()
    circle = _failure_circle()
    fs_vals = []
    for phi in [15.0, 25.0, 35.0]:
        layers = [SoilLayer(id=1, name="L", gamma=19.0, cohesion=10.0, phi_deg=phi, thickness=None)]
        slices = divide_into_slices(circle, 20, terrain, layers, wt)
        fs, _, _, _ = solve_spencer(slices, SpencerSettings())
        fs_vals.append(fs)
    assert fs_vals[0] < fs_vals[1] < fs_vals[2]


def test_fs_decreases_with_water():
    """Higher water table → lower FS.

    With y_mid lookup, pore pressure is computed at (y_top + y_base)/2.
    For this circle, slice midpoints range from ~5 to ~8 m, so water table
    levels of -20, 6, 9 ensure dry / partial / substantial submergence.
    """
    terrain = _simple_terrain()
    circle = _failure_circle()
    layers = _homogeneous_layers()
    fs_vals = []
    for elev in [-20.0, 6.0, 9.0]:
        slices = divide_into_slices(circle, 20, terrain, layers, WaterTable(elevation=elev))
        fs, _, _, _ = solve_spencer(slices, SpencerSettings())
        fs_vals.append(fs)
    assert fs_vals[0] > fs_vals[1] > fs_vals[2]


# ---------------------------------------------------------------------------
# Residual quality tests
# ---------------------------------------------------------------------------

def test_force_sweep_relative_residual():
    """
    After convergence, the force residual relative to Σ|W| must be tight.

    Brent's method converges on |θ - θ*| < tol = 1e-6 rad.  At this
    precision, |E_n| / Σ|W| should be well below 1e-4.
    """
    slices = _make_slices()
    fs, theta, _, _ = solve_spencer(slices, SpencerSettings())
    residual = _force_sweep(slices, fs, math.radians(theta))
    sum_W = sum(abs(s.weight) for s in slices)
    assert sum_W > 0
    relative = abs(residual) / sum_W
    assert relative < 1e-4, (
        f"Force residual too large: |E_n|/Σ|W| = {relative:.2e} "
        f"(E_n={residual:.3e}, Σ|W|={sum_W:.1f})"
    )


def test_compute_residuals_moment():
    """After Bishop convergence, the moment residual must be tight."""
    slices = _make_slices()
    fs, theta, _, _ = solve_spencer(slices, SpencerSettings())
    res = compute_residuals(slices, fs, theta)
    assert res["moment_relative"] < 1e-5, (
        f"Moment residual: {res['moment_relative']:.2e}"
    )


def test_compute_residuals_force():
    """compute_residuals force_relative must agree with direct _force_sweep check."""
    slices = _make_slices()
    fs, theta, _, _ = solve_spencer(slices, SpencerSettings())
    res = compute_residuals(slices, fs, theta)
    assert res["force_relative"] < 1e-4, (
        f"Force residual: {res['force_relative']:.2e}"
    )


def test_compute_residuals_sum_W_positive():
    slices = _make_slices()
    fs, theta, _, _ = solve_spencer(slices, SpencerSettings())
    res = compute_residuals(slices, fs, theta)
    assert res["sum_W"] > 0


def test_bishop_equals_spencer_fs_circular():
    """
    For a circular slip surface, Bishop FS and Spencer FS must agree to
    within 0.1%.  This is a theorem (interslice forces cancel about the
    circle centre), not an approximation.
    """
    slices = _make_slices()
    fs_bishop, _ = _bishop_iterate(slices, 1e-6, 200)
    fs_spencer, _, _, _ = solve_spencer(slices, SpencerSettings())
    relative_diff = abs(fs_spencer - fs_bishop) / fs_bishop
    assert relative_diff < 1e-3, (
        f"Spencer FS = {fs_spencer:.6f}, Bishop FS = {fs_bishop:.6f}, "
        f"relative diff = {relative_diff:.2e} (expected < 0.1%)"
    )

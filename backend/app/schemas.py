"""Pydantic v2 schemas for Spencer slope stability analysis."""

from __future__ import annotations

import math
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app import config


class TerrainPoint(BaseModel):
    x: float
    y: float


class SoilLayer(BaseModel):
    id: int
    name: str
    gamma: float = Field(..., description="Unit weight kN/m³", gt=0)
    cohesion: float = Field(..., description="Effective cohesion c' kPa", ge=0)
    phi_deg: float = Field(..., description="Effective friction angle φ' degrees", gt=0, lt=90)
    thickness: Optional[float] = Field(
        default=None,
        description="Layer thickness in metres; None for substratum (bottom layer)",
    )

    @field_validator("thickness")
    @classmethod
    def thickness_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("thickness must be positive")
        return v

    @property
    def phi_rad(self) -> float:
        return math.radians(self.phi_deg)


class WaterTable(BaseModel):
    elevation: Optional[float] = Field(
        default=None,
        description="Piezometric elevation in metres; None means no water table",
    )


class Circle(BaseModel):
    cx: float = Field(..., description="X coordinate of slip circle centre")
    cy: float = Field(..., description="Y coordinate of slip circle centre")
    radius: float = Field(..., description="Radius in metres", gt=0)


class Slice(BaseModel):
    index: int
    # Geometry
    x_left: float = Field(..., description="Left boundary x of slice (m)")
    x_right: float = Field(..., description="Right boundary x of slice (m)")
    x_mid: float = Field(..., description="Mid-point x of slice (m)")
    width: float = Field(..., description="Slice width b in metres", gt=0)
    y_top: float = Field(..., description="Surface elevation at x_mid (m)")
    y_base: float = Field(..., description="Circle base elevation at x_mid (m)")
    height: float = Field(..., description="Slice height h = y_top - y_base (m)", ge=0)
    area: float = Field(..., description="Trapezoidal slice area (m²)", ge=0)
    # Base geometry
    alpha_deg: float = Field(..., description="Base inclination angle α in degrees (positive = dip toward toe)")
    base_length: float = Field(..., description="Chord length of slice base dl = b/cos(α) in metres", gt=0)
    # Soil identity
    layer_id: int = Field(..., description="ID of the dominant layer at this slice base")
    cohesion: float = Field(..., description="Effective cohesion c' at base (kPa)", ge=0)
    phi_deg: float = Field(..., description="Effective friction angle φ' at base (degrees)", gt=0, lt=90)
    # Forces (per unit out-of-plane length, kN/m)
    weight: float = Field(..., description="Slice weight W = γ·area (kN/m)", ge=0)
    pore_pressure: float = Field(..., description="Pore pressure at slice base u (kPa)", ge=0)
    pore_force: float = Field(..., description="Pore force U = u·base_length (kN/m)", ge=0)
    # Spencer per-slice results (populated after solve)
    normal_eff: float = Field(default=0.0, description="Effective normal force N' at base (kN/m)")
    driving: float = Field(default=0.0, description="Driving component W·sin(α) (kN/m)")
    resisting: float = Field(default=0.0, description="Available shear strength S (kN/m)")


class SpencerSettings(BaseModel):
    n_slices: int = Field(default=20, ge=5, le=200, description="Number of vertical slices")
    tolerance: float = Field(default=config.TOL_SPENCER, gt=0, description="Convergence tolerance for FS")
    max_iter: int = Field(default=config.MAX_ITER, ge=10, le=2000, description="Maximum solver iterations")
    theta_min: float = Field(default=config.THETA_MIN, description="Min interslice force angle (degrees)")
    theta_max: float = Field(default=config.THETA_MAX, description="Max interslice force angle (degrees)")


class CriticalSearchSettings(BaseModel):
    """Grid search parameters for finding the critical slip circle."""
    coarse_step: float = Field(default=config.STEP_COARSE, gt=0, description="Coarse grid spacing in metres")
    fine_step: float = Field(default=config.STEP_FINE, gt=0, description="Fine grid spacing in metres")
    final_step: float = Field(default=config.STEP_FINAL, gt=0, description="Final refinement step in metres")
    top_k_coarse: int = Field(default=config.TOP_K_COARSE, ge=1, description="Best circles kept from coarse pass")
    top_k_fine: int = Field(default=config.TOP_K_FINE, ge=1, description="Best circles kept from fine pass")
    n_radii: int = Field(default=config.N_RADII, ge=2, description="Number of radii tested per centre")
    min_convergence_ratio: float = Field(
        default=config.MIN_CONVERGENCE_RATIO, ge=0, le=1,
        description="Min fraction of slices with positive height to accept a circle",
    )


class AnalysisRequest(BaseModel):
    layers: list[SoilLayer] = Field(..., min_length=1)
    water_table: WaterTable
    circle: Circle
    settings: SpencerSettings = Field(default_factory=SpencerSettings)
    slope_height: float = Field(..., description="Total slope height H in metres", gt=0)
    slope_length: float = Field(..., description="Horizontal slope projection L in metres", gt=0)


class CriticalCircleRequest(BaseModel):
    layers: list[SoilLayer] = Field(..., min_length=1)
    water_table: WaterTable
    settings: SpencerSettings = Field(default_factory=SpencerSettings)
    search: CriticalSearchSettings = Field(default_factory=CriticalSearchSettings)
    slope_height: float = Field(..., description="Total slope height H in metres", gt=0)
    slope_length: float = Field(..., description="Horizontal slope projection L in metres", gt=0)


class SearchStats(BaseModel):
    tested: int = Field(..., description="Total circles evaluated")
    converged: int = Field(..., description="Circles where Spencer converged")
    rejected: int = Field(..., description="Circles rejected (geometry or convergence)")


class AnalysisResult(BaseModel):
    fs: float = Field(..., description="Factor of Safety", ge=0)
    stability_status: str = Field(..., description="unstable | limit | stable")
    theta: float = Field(..., description="Interslice force inclination angle (degrees)")
    slices: list[Slice]
    converged: bool
    iterations: int = Field(..., ge=0)
    elapsed_seconds: float = Field(default=0.0, ge=0, description="Wall-clock calculation time in seconds")
    circle: Circle


class CriticalCircleResult(BaseModel):
    critical_circle: Circle
    fs: float = Field(..., description="Minimum Factor of Safety found", ge=0)
    result: AnalysisResult
    stats: SearchStats


# ---------------------------------------------------------------------------
# Cost estimation & analysis modes
# ---------------------------------------------------------------------------

class AnalysisMode(str):
    FAST = "fast"         # coarse grid only, 10 slices, tol=1e-4
    PRECISE = "precise"   # 3-pass grid, 20 slices, tol=1e-6 (default)
    ADVANCED = "advanced" # very fine grid, 50 slices, tol=1e-8


class CostEstimate(BaseModel):
    """Estimated computational cost returned before a heavy analysis."""
    n_candidates: int = Field(..., description="Total circles that will be evaluated")
    n_slices: int = Field(..., description="Slices per circle")
    n_layers: int = Field(..., description="Soil layers")
    max_iter: int = Field(..., description="Max Spencer iterations per circle")
    cost_score: float = Field(
        ...,
        description="Dimensionless cost: n_candidates × n_slices × log2(n_layers+1) × max_iter",
    )
    level: str = Field(..., description="One of: 'light', 'moderate', 'heavy', 'prohibitive'")
    recommended_mode: str = Field(..., description="Suggested AnalysisMode")
    warnings: list[str] = Field(default_factory=list)
    estimated_seconds_min: float
    estimated_seconds_max: float


# ---------------------------------------------------------------------------
# Batch progress
# ---------------------------------------------------------------------------

class BatchProgress(BaseModel):
    """Emitted after each batch during a long search."""
    batch_index: int
    batches_total: int
    tested_so_far: int
    converged_so_far: int
    rejected_so_far: int
    best_fs_so_far: Optional[float] = None
    best_circle_so_far: Optional[Circle] = None
    elapsed_seconds: float
    cancelled: bool = False


# ---------------------------------------------------------------------------
# Job system
# ---------------------------------------------------------------------------

class JobState(str):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(BaseModel):
    """Persisted state of an async analysis job."""
    job_id: str
    state: str = Field(..., description="pending | running | done | failed | cancelled")
    created_at: float = Field(..., description="Unix timestamp of creation")
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    progress: Optional[BatchProgress] = None
    result: Optional[CriticalCircleResult] = None
    error: Optional[dict] = None
    request_summary: dict = Field(
        default_factory=dict,
        description="Serialised subset of the original request for display",
    )


class JobCreateResponse(BaseModel):
    job_id: str
    state: str
    cost_estimate: CostEstimate

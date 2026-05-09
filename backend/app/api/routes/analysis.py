"""Analysis API routes — Spencer method."""

from __future__ import annotations

import math

from fastapi import APIRouter
from pydantic import ValidationError as PydanticValidationError

from app.schemas import (
    AnalysisRequest,
    AnalysisResult,
    Circle,
    CriticalCircleRequest,
    CriticalCircleResult,
    JobCreateResponse,
    JobStatus,
    SearchStats,
    Slice,
)
from app.errors import ValidationError, GeometryError
from core.geometry import slope_profile, auto_plateaus
from core.validation import validate_layers, validate_geometry, validate_circle
from core.slicing import divide_into_slices
from core.spencer import solve_spencer
from core.search import find_critical_circle

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_result(
    slices: list[Slice],
    fs: float,
    theta: float,
    converged: bool,
    iterations: int,
    circle: Circle,
) -> AnalysisResult:
    """Populate resisting field on each slice, then return an AnalysisResult."""
    enriched: list[Slice] = []
    for slc in slices:
        alpha = math.radians(slc.alpha_deg)
        phi = math.radians(slc.phi_deg)
        cos_a = math.cos(alpha)
        resisting = (
            slc.cohesion * slc.base_length
            + (slc.weight * cos_a - slc.pore_force) * math.tan(phi)
        ) / fs
        enriched.append(slc.model_copy(update={"resisting": resisting}))

    return AnalysisResult(
        fs=fs,
        theta=theta,
        slices=enriched,
        converged=converged,
        iterations=iterations,
        circle=circle,
    )


# ---------------------------------------------------------------------------
# Synchronous endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/evaluate-circle",
    response_model=AnalysisResult,
    summary="Évaluer un cercle de glissement donné",
)
async def evaluate_circle(req: AnalysisRequest) -> AnalysisResult:
    """
    Run Spencer's method for a single user-specified slip circle.

    Returns the Factor of Safety, the interslice force angle θ, and
    the computed slices with geometric and force details.
    """
    geom_errors = validate_geometry(req.slope_height, req.slope_length)
    if geom_errors:
        raise ValidationError("Géométrie invalide", {"errors": geom_errors})

    layer_errors = validate_layers(req.layers, req.slope_height)
    if layer_errors:
        raise ValidationError("Paramètres de couches invalides", {"errors": layer_errors})

    l_amont, l_aval = auto_plateaus(req.slope_height, req.slope_length)
    terrain_pts = slope_profile(req.slope_height, req.slope_length, l_amont, l_aval)

    circle_errors = validate_circle(req.circle, terrain_pts)
    if circle_errors:
        raise GeometryError("Cercle de glissement invalide", {"errors": circle_errors})

    slices = divide_into_slices(
        circle=req.circle,
        n_slices=req.settings.n_slices,
        terrain_pts=terrain_pts,
        layers=req.layers,
        water_table=req.water_table,
    )

    fs, theta, converged, iterations = solve_spencer(slices, req.settings)

    return _build_result(slices, fs, theta, converged, iterations, req.circle)


@router.post(
    "/critical-circle",
    response_model=CriticalCircleResult,
    summary="Chercher le cercle critique (FS minimum) — synchrone",
)
async def critical_circle(req: CriticalCircleRequest) -> CriticalCircleResult:
    """
    Run the 3-pass grid search to find the slip circle with the minimum FS.

    Returns the critical circle, the minimum FS, the full Spencer result for
    that circle, and search statistics (tested / converged / rejected counts).

    For heavy searches, prefer the async job endpoints (/jobs).
    """
    geom_errors = validate_geometry(req.slope_height, req.slope_length)
    if geom_errors:
        raise ValidationError("Géométrie invalide", {"errors": geom_errors})

    layer_errors = validate_layers(req.layers, req.slope_height)
    if layer_errors:
        raise ValidationError("Paramètres de couches invalides", {"errors": layer_errors})

    l_amont, l_aval = auto_plateaus(req.slope_height, req.slope_length)
    terrain_pts = slope_profile(req.slope_height, req.slope_length, l_amont, l_aval)

    best_circle, min_fs, stats = find_critical_circle(
        terrain_pts=terrain_pts,
        layers=req.layers,
        water_table=req.water_table,
        settings=req.settings,
        search=req.search,
    )

    slices = divide_into_slices(
        circle=best_circle,
        n_slices=req.settings.n_slices,
        terrain_pts=terrain_pts,
        layers=req.layers,
        water_table=req.water_table,
    )
    fs, theta, converged, iterations = solve_spencer(slices, req.settings)
    result = _build_result(slices, fs, theta, converged, iterations, best_circle)

    return CriticalCircleResult(
        critical_circle=best_circle,
        fs=min_fs,
        result=result,
        stats=stats,
    )


@router.post(
    "/validate",
    response_model=dict,
    summary="Valider la géométrie sans lancer le calcul",
)
async def validate_only(payload: dict) -> dict:
    """Return ``{"ok": true, "errors": []}`` on success, or a list of errors."""
    errors: list[str] = []
    try:
        req = AnalysisRequest.model_validate(payload)
    except PydanticValidationError as exc:
        return {
            "ok": False,
            "errors": [
                " / ".join(str(part) for part in err.get("loc", ())) + f" : {err.get('msg')}"
                for err in exc.errors()
            ],
        }

    errors.extend(validate_geometry(req.slope_height, req.slope_length))
    errors.extend(validate_layers(req.layers, req.slope_height))

    if not errors:
        l_amont, l_aval = auto_plateaus(req.slope_height, req.slope_length)
        terrain_pts = slope_profile(req.slope_height, req.slope_length, l_amont, l_aval)
        errors.extend(validate_circle(req.circle, terrain_pts))

    return {"ok": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# Async job endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=202,
    summary="Créer un job de recherche asynchrone",
)
async def create_job(req: CriticalCircleRequest) -> JobCreateResponse:
    """
    Estimate cost, validate input, and enqueue a background critical-circle search.

    Returns 202 with ``job_id`` and ``cost_estimate``.
    Raises 422 if the search domain would be too expensive.

    Poll ``GET /api/analysis/jobs/{job_id}`` for status and progress.
    """
    from app import jobs as job_store

    geom_errors = validate_geometry(req.slope_height, req.slope_length)
    if geom_errors:
        raise ValidationError("Géométrie invalide", {"errors": geom_errors})

    layer_errors = validate_layers(req.layers, req.slope_height)
    if layer_errors:
        raise ValidationError("Paramètres de couches invalides", {"errors": layer_errors})

    # create_job raises TooManyCandidatesError / PrecisionTooExpensiveError if over limits
    response = job_store.create_job(req)

    # Launch immediately in the background
    await job_store.start_job(response.job_id, req)

    return response


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatus,
    summary="Statut d'un job asynchrone",
)
async def get_job(job_id: str) -> JobStatus:
    """
    Poll the state of a background search job.

    State machine: ``pending → running → done | failed | cancelled``

    The ``progress`` field is populated while running, giving live
    best_fs_so_far, tested/converged/rejected counts, and elapsed seconds.
    """
    from app import jobs as job_store
    return job_store.get_job(job_id)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobStatus,
    summary="Annuler un job asynchrone",
)
async def cancel_job(job_id: str) -> JobStatus:
    """
    Request cancellation of a running or pending job.

    Sets a threading.Event that the search loop checks between batches.
    Returns the job's current status (may still show ``running`` briefly).
    """
    from app import jobs as job_store
    return job_store.cancel_job(job_id)


@router.get(
    "/jobs",
    response_model=list[JobStatus],
    summary="Lister tous les jobs",
)
async def list_jobs() -> list[JobStatus]:
    """Return all jobs in the in-memory store (most recent session only)."""
    from app import jobs as job_store
    return job_store.list_jobs()


# Keep old /run endpoint as an alias for backward compatibility
router.add_api_route(
    "/run",
    evaluate_circle,
    methods=["POST"],
    response_model=AnalysisResult,
    summary="[Alias] Évaluer un cercle — voir /evaluate-circle",
    include_in_schema=False,
)

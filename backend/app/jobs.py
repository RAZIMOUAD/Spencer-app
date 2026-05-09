"""Async job store for long-running critical circle searches."""

from __future__ import annotations

import asyncio
import math
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app import config
from app.schemas import (
    BatchProgress,
    CriticalCircleRequest,
    CriticalCircleResult,
    CriticalSearchSettings,
    JobCreateResponse,
    JobStatus,
    Slice,
    SpencerSettings,
)
from app.errors import AnalysisCancelledError, SpencerBaseError
from core.cost import estimate_cost
from core.geometry import auto_plateaus, slope_profile
from core.search import find_critical_circle
from core.slicing import divide_into_slices
from core.spencer import solve_spencer

# ---------------------------------------------------------------------------
# Global job store — in-process, non-persistent
# ---------------------------------------------------------------------------

_jobs: dict[str, JobStatus] = {}
_cancel_events: dict[str, threading.Event] = {}
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="spencer-job")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_job(req: CriticalCircleRequest) -> JobCreateResponse:
    """
    Estimate cost, reject if over limits, and register a new job.

    Returns JobCreateResponse with job_id + cost_estimate.
    Does NOT start the job — call start_job() to launch it.
    """
    H = req.slope_height
    n_layers = len(req.layers)

    # Raises TooManyCandidatesError / PrecisionTooExpensiveError if over limits
    settings = _internal_settings(max(req.slope_height, req.slope_length))
    search = _internal_search()
    cost = estimate_cost(H, n_layers, settings, search)

    job_id = str(uuid.uuid4())
    now = time.time()
    _jobs[job_id] = JobStatus(
        job_id=job_id,
        state="pending",
        created_at=now,
        request_summary={
            "slope_height": req.slope_height,
            "slope_length": req.slope_length,
            "n_layers": n_layers,
            "mode_hint": cost.recommended_mode,
        },
    )
    _cancel_events[job_id] = threading.Event()

    return JobCreateResponse(
        job_id=job_id,
        state="pending",
        cost_estimate=cost,
    )


async def start_job(job_id: str, req: CriticalCircleRequest) -> None:
    """
    Launch the Spencer search in the thread-pool executor.

    Updates job state to running immediately; sets done/failed on completion.
    """
    job = _get_or_raise(job_id)
    if job.state != "pending":
        return

    _update_job(job_id, state="running", started_at=time.time())

    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_job_sync,
        job_id,
        req,
        _cancel_events[job_id],
    )


def get_job(job_id: str) -> JobStatus:
    return _get_or_raise(job_id)


def cancel_job(job_id: str) -> JobStatus:
    job = _get_or_raise(job_id)
    if job.state in ("done", "failed", "cancelled"):
        return job
    event = _cancel_events.get(job_id)
    if event:
        event.set()
    if job.state == "pending":
        _update_job(job_id, state="cancelled", finished_at=time.time())
    return _jobs[job_id]


def list_jobs() -> list[JobStatus]:
    return list(_jobs.values())


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _get_or_raise(job_id: str) -> JobStatus:
    from app.errors import JobNotFoundError
    job = _jobs.get(job_id)
    if job is None:
        raise JobNotFoundError(
            f"Job introuvable : {job_id}",
            {"job_id": job_id},
        )
    return job


def _update_job(job_id: str, **kwargs) -> None:
    _jobs[job_id] = _jobs[job_id].model_copy(update=kwargs)


def _run_job_sync(
    job_id: str,
    req: CriticalCircleRequest,
    cancel_event: threading.Event,
) -> None:
    """Executed in a background thread. Updates job store directly."""
    try:
        l_amont, l_aval = auto_plateaus(req.slope_height, req.slope_length)
        terrain_pts = slope_profile(req.slope_height, req.slope_length, l_amont, l_aval)

        settings = _internal_settings(max(req.slope_height, req.slope_length))
        search = _internal_search()
        best_circle, min_fs, stats = find_critical_circle(
            terrain_pts=terrain_pts,
            layers=req.layers,
            water_table=req.water_table,
            settings=settings,
            search=search,
            cancel_event=cancel_event,
        )

        # Full Spencer result for the critical circle
        final_settings = _internal_settings(best_circle.radius)
        slices = divide_into_slices(
            circle=best_circle,
            n_slices=final_settings.n_slices,
            terrain_pts=terrain_pts,
            layers=req.layers,
            water_table=req.water_table,
        )
        fs, theta, converged, iterations = solve_spencer(slices, final_settings)
        enriched = _enrich_slices(slices, fs)

        from app.schemas import AnalysisResult
        analysis = AnalysisResult(
            fs=fs,
            stability_status=config.classify_factor_of_safety(fs),
            theta=theta,
            slices=enriched,
            converged=converged,
            iterations=iterations,
            circle=best_circle,
        )
        result = CriticalCircleResult(
            critical_circle=best_circle,
            fs=min_fs,
            result=analysis,
            stats=stats,
        )
        _update_job(
            job_id,
            state="done",
            finished_at=time.time(),
            result=result,
        )

    except AnalysisCancelledError:
        _update_job(job_id, state="cancelled", finished_at=time.time())

    except SpencerBaseError as exc:
        _update_job(
            job_id,
            state="failed",
            finished_at=time.time(),
            error={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    except Exception as exc:
        _update_job(
            job_id,
            state="failed",
            finished_at=time.time(),
            error={"code": "INTERNAL_ERROR", "message": str(exc), "details": {}},
        )


def _enrich_slices(slices: list[Slice], fs: float) -> list[Slice]:
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
    return enriched


def _internal_settings(radius: float) -> SpencerSettings:
    return SpencerSettings(
        n_slices=config.auto_slice_count(radius),
        tolerance=config.TOL_SPENCER,
        max_iter=config.MAX_ITER,
        theta_min=config.THETA_MIN,
        theta_max=config.THETA_MAX,
    )


def _internal_search() -> CriticalSearchSettings:
    return CriticalSearchSettings(
        coarse_step=config.STEP_COARSE,
        fine_step=config.STEP_FINE,
        final_step=config.STEP_FINAL,
        top_k_coarse=config.TOP_K_COARSE,
        top_k_fine=config.TOP_K_FINE,
        n_radii=config.N_RADII,
        min_convergence_ratio=config.MIN_CONVERGENCE_RATIO,
    )

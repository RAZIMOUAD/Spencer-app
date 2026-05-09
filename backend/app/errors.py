"""Error types and FastAPI exception handlers for the Spencer application."""

from __future__ import annotations

from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Domain exception hierarchy
# ---------------------------------------------------------------------------


class SpencerBaseError(Exception):
    """Base class for all application errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# --- Input / geometry errors (HTTP 422) ------------------------------------

class ValidationError(SpencerBaseError):
    """Input data failed domain validation (layers, geometry, water table)."""
    code = "VALIDATION_ERROR"
    http_status = 422


class InvalidTerrainError(SpencerBaseError):
    """Terrain points are non-monotone, self-crossing, or contain vertical segments."""
    code = "INVALID_TERRAIN"
    http_status = 422


class CircleIntersectionError(SpencerBaseError):
    """Circle does not intersect the terrain at two distinct points."""
    code = "CIRCLE_INTERSECTION_ERROR"
    http_status = 422


class GeometryError(SpencerBaseError):
    """Generic slip circle or terrain geometry error."""
    code = "GEOMETRY_ERROR"
    http_status = 422


class WaterTableError(SpencerBaseError):
    """Water table elevation is inconsistent with the slope geometry."""
    code = "WATER_TABLE_ERROR"
    http_status = 422


class SearchDomainError(SpencerBaseError):
    """Critical circle search domain is empty or has inconsistent bounds."""
    code = "SEARCH_DOMAIN_ERROR"
    http_status = 422


# --- Slice / computation errors (HTTP 422) ---------------------------------

class EmptySliceSetError(SpencerBaseError):
    """A geometrically valid circle produced zero usable slices."""
    code = "EMPTY_SLICE_SET"
    http_status = 422


class InvalidSliceError(SpencerBaseError):
    """A slice has a negative height, zero area, or its base is outside the circle."""
    code = "INVALID_SLICE"
    http_status = 422


class LayerLookupError(SpencerBaseError):
    """A slice base elevation does not fall within any defined soil layer."""
    code = "LAYER_LOOKUP_ERROR"
    http_status = 422


# --- Numerical / solver errors (HTTP 422) ----------------------------------

class NumericalInstabilityError(SpencerBaseError):
    """cos(α) near zero, division by tiny number, or negative radicand detected."""
    code = "NUMERICAL_INSTABILITY"
    http_status = 422


class NonFiniteValueError(SpencerBaseError):
    """NaN or Inf encountered during computation."""
    code = "NON_FINITE_VALUE"
    http_status = 422


class SpencerConvergenceError(SpencerBaseError):
    """Spencer iterative solver did not converge within max_iter iterations."""
    code = "CONVERGENCE_ERROR"
    http_status = 422


class SpencerBracketError(SpencerBaseError):
    """Cannot bracket a root for FS or λ; residuals do not change sign."""
    code = "BRACKET_ERROR"
    http_status = 422


class NoValidCircleError(SpencerBaseError):
    """Global search found no circle where Spencer converged."""
    code = "NO_VALID_CIRCLE"
    http_status = 422


# --- Job / resource guard errors -------------------------------------------

class AnalysisTimeoutError(SpencerBaseError):
    """Analysis job exceeded the allowed wall-clock time."""
    code = "ANALYSIS_TIMEOUT"
    http_status = 408


class AnalysisCancelledError(SpencerBaseError):
    """Analysis job was cancelled by the user."""
    code = "ANALYSIS_CANCELLED"
    http_status = 409


class TooManyCandidatesError(SpencerBaseError):
    """The search grid would generate more candidate circles than allowed."""
    code = "TOO_MANY_CANDIDATES"
    http_status = 422


class MemoryBudgetExceededError(SpencerBaseError):
    """Estimated memory footprint exceeds the server limit."""
    code = "MEMORY_BUDGET_EXCEEDED"
    http_status = 422


class PrecisionTooExpensiveError(SpencerBaseError):
    """The requested precision/step combination is computationally prohibitive."""
    code = "PRECISION_TOO_EXPENSIVE"
    http_status = 422


class JobNotFoundError(SpencerBaseError):
    """No job exists with the given ID."""
    code = "JOB_NOT_FOUND"
    http_status = 404


# --- Warnings (non-fatal, returned as metadata) ----------------------------

class TooManyLayersWarning(SpencerBaseError):
    """More than the recommended number of soil layers — performance may degrade."""
    code = "TOO_MANY_LAYERS_WARNING"
    http_status = 200  # not an error, embedded in the response


# Keep old name as alias
ConvergenceError = SpencerConvergenceError


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class AppError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: AppError


# ---------------------------------------------------------------------------
# FastAPI exception handlers
# ---------------------------------------------------------------------------


def _make_error_response(code: str, message: str, details: Optional[dict] = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""

    @app.exception_handler(SpencerBaseError)
    async def spencer_error_handler(request: Request, exc: SpencerBaseError) -> JSONResponse:
        # TooManyLayersWarning is non-fatal — callers embed it in the response body;
        # if it somehow surfaces here, treat as 400 so the client sees it.
        status = exc.http_status if exc.http_status != 200 else 400
        return JSONResponse(
            status_code=status,
            content=_make_error_response(exc.code, exc.message, exc.details),
        )

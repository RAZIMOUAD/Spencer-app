"""Internal numerical configuration for the Spencer-Slope API."""

from __future__ import annotations

TOL_SPENCER = 1e-4
TOL_GLOBAL = 0.01
MAX_ITER = 100

STEP_COARSE = 2.0
STEP_FINE = 0.1
STEP_FINAL = 0.01

EPSILON = 1e-6
FS_LIMIT_TOLERANCE = 0.01

THETA_MIN = -30.0
THETA_MAX = 30.0

TOP_K_COARSE = 5
TOP_K_FINE = 3
N_RADII = 5
MIN_CONVERGENCE_RATIO = 0.05
MAX_REASONABLE_FS = 10.0


def auto_slice_count(slip_width: float) -> int:
    """Choose a stable slice count from the real slip-mass width."""
    return max(20, min(40, int(slip_width / 1.0)))


def classify_factor_of_safety(fs: float) -> str:
    """Classify stability using the project convention around FS = 1."""
    if abs(fs - 1.0) <= FS_LIMIT_TOLERANCE:
        return "limit"
    if fs > 1.0:
        return "stable"
    return "unstable"

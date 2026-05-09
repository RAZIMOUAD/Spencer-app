"""End-to-end API tests — /evaluate-circle and /critical-circle.

Uses FastAPI's TestClient (httpx-backed, no server needed).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_LAYER_SIMPLE = {
    "id": 1,
    "name": "Clay",
    "gamma": 19.0,
    "cohesion": 15.0,
    "phi_deg": 25.0,
    "thickness": None,
}

_LAYER_TOP = {
    "id": 1,
    "name": "Top",
    "gamma": 18.0,
    "cohesion": 10.0,
    "phi_deg": 28.0,
    "thickness": 4.0,
}

_LAYER_SUB = {
    "id": 2,
    "name": "Sub",
    "gamma": 21.0,
    "cohesion": 20.0,
    "phi_deg": 32.0,
    "thickness": None,
}

_WATER_TABLE_DRY = {"elevation": -50.0}

# A circle known to work with the slope H=10, L=15 (auto plateaus added)
# cx=4, cy=12, r=13 — used in unit tests, circle enters from outside terrain domain
_CIRCLE = {"cx": 4.0, "cy": 12.0, "radius": 13.0}


def _evaluate_payload(circle=None, layers=None, wt=None):
    return {
        "layers": layers or [_LAYER_SIMPLE],
        "water_table": wt or _WATER_TABLE_DRY,
        "circle": circle or _CIRCLE,
        "settings": {"n_slices": 20, "tolerance": 1e-6, "max_iter": 200,
                     "theta_min": -30.0, "theta_max": 30.0},
        "slope_height": 10.0,
        "slope_length": 15.0,
    }


def _critical_payload(layers=None, wt=None):
    return {
        "layers": layers or [_LAYER_SIMPLE],
        "water_table": wt or _WATER_TABLE_DRY,
        "settings": {"n_slices": 10, "tolerance": 1e-4, "max_iter": 100,
                     "theta_min": -30.0, "theta_max": 30.0},
        "search": {
            "coarse_step": 3.0,   # coarse for speed in tests
            "fine_step": 1.0,
            "final_step": 0.5,
            "top_k_coarse": 3,
            "top_k_fine": 2,
            "n_radii": 3,
            "min_convergence_ratio": 0.05,
        },
        "slope_height": 10.0,
        "slope_length": 15.0,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /evaluate-circle
# ---------------------------------------------------------------------------

class TestEvaluateCircle:
    def test_returns_200(self):
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        assert r.status_code == 200, r.text

    def test_response_has_fs(self):
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        body = r.json()
        assert "fs" in body
        assert body["fs"] > 0.0

    def test_response_has_slices(self):
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        body = r.json()
        assert "slices" in body
        assert len(body["slices"]) > 0

    def test_response_converged(self):
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        body = r.json()
        assert body["converged"] is True

    def test_fs_decreases_with_water(self):
        """Higher water table → lower FS — verifies the full API pipeline."""
        dry = client.post("/api/analysis/evaluate-circle",
                          json=_evaluate_payload(wt={"elevation": -50.0}))
        wet = client.post("/api/analysis/evaluate-circle",
                          json=_evaluate_payload(wt={"elevation": 5.0}))
        assert dry.status_code == 200 and wet.status_code == 200
        assert dry.json()["fs"] > wet.json()["fs"]

    def test_invalid_geometry_returns_error(self):
        payload = _evaluate_payload()
        payload["slope_height"] = -1.0  # invalid
        r = client.post("/api/analysis/evaluate-circle", json=payload)
        assert r.status_code >= 400

    def test_circle_entering_from_outside_domain_accepted(self):
        """Circle cx=4, r=13 extends to x=-9; terrain starts at x≈0.
        validate_circle() must now accept this (matches slicing logic)."""
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        assert r.status_code == 200, (
            "Circle entering from outside terrain domain should be accepted. "
            f"Got {r.status_code}: {r.text}"
        )

    def test_slice_weights_positive(self):
        r = client.post("/api/analysis/evaluate-circle", json=_evaluate_payload())
        slices = r.json()["slices"]
        assert all(s["weight"] > 0 for s in slices)

    def test_multilayer_response(self):
        """Two-layer slope still converges and returns a valid FS."""
        payload = _evaluate_payload(layers=[_LAYER_TOP, _LAYER_SUB])
        r = client.post("/api/analysis/evaluate-circle", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["fs"] > 0


# ---------------------------------------------------------------------------
# /critical-circle
# ---------------------------------------------------------------------------

class TestCriticalCircle:
    def test_returns_200(self):
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        assert r.status_code == 200, r.text

    def test_response_has_critical_circle(self):
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        body = r.json()
        assert "critical_circle" in body
        c = body["critical_circle"]
        assert c["radius"] > 0

    def test_response_has_fs(self):
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        body = r.json()
        assert body["fs"] > 0.0

    def test_response_has_stats(self):
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        body = r.json()
        assert "stats" in body
        assert body["stats"]["tested"] > 0
        assert body["stats"]["converged"] > 0

    def test_critical_circle_within_domain(self):
        """Critical circle cy must be >= H (domain lower bound = H = 10)."""
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        body = r.json()
        H = 10.0
        cy = body["critical_circle"]["cy"]
        assert cy >= H - 1e-6, (
            f"cy={cy:.3f} is below domain lower bound cy_min={H}"
        )

    def test_critical_fs_is_positive_and_finite(self):
        """The critical circle search must return a physically valid FS."""
        r = client.post("/api/analysis/critical-circle", json=_critical_payload())
        assert r.status_code == 200, r.text
        fs = r.json()["fs"]
        assert 0 < fs < 1000, f"FS={fs} is not in a physically plausible range"

    def test_multilayer_critical_circle(self):
        """Two-layer slope with critical search returns valid result."""
        payload = _critical_payload(layers=[_LAYER_TOP, _LAYER_SUB])
        r = client.post("/api/analysis/critical-circle", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["fs"] > 0


# ---------------------------------------------------------------------------
# /validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_valid_request_returns_ok(self):
        r = client.post("/api/analysis/validate", json=_evaluate_payload())
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["errors"] == []

    def test_invalid_geometry_flagged(self):
        # Use an extreme H/L ratio that passes Pydantic (both > 0) but fails
        # validate_geometry (ratio < 0.05 or > 10).
        payload = _evaluate_payload()
        payload["slope_height"] = 0.1   # H=0.1, L=15 → ratio = 0.0067 < 0.05
        r = client.post("/api/analysis/validate", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is False
        assert len(body["errors"]) > 0

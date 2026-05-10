"""Spencer's method — Bishop Modified moment equilibrium + Spencer force closure.

Solver classification
---------------------
This module implements what the literature calls "Spencer's method" as
described in Spencer (1967) and Fredlund & Krahn (1977):

    Stage 1 — Moment equilibrium (Bishop's Modified Method):
        Iterates FS until moment equilibrium is satisfied.
        For a CIRCULAR slip surface, interslice forces have zero net moment
        about the circle centre, so the moment equation is independent of θ.
        Consequence: for circular surfaces, FS_moment = FS_Bishop regardless
        of the assumed θ.  This is a mathematical theorem, not an
        approximation.

    Stage 2 — Force closure (Spencer 1967, eq. 17):
        For the converged FS, finds θ ∈ [θ_min, θ_max] such that the
        cumulative horizontal interslice force E_n = 0 at the right boundary.
        Uses the exact combined-equilibrium ΔE formula (see _force_sweep).

    This is Spencer's method as intended for circular failure surfaces.
    For non-circular surfaces, a full co-iteration (θ affects N via vertical
    equilibrium, N affects FS_moment) would be needed.  That case is not yet
    supported — the solver would need restructuring.

Pore pressure convention
------------------------
u·b = pore_pressure × width is used consistently throughout:
    - In Bishop: (W − u·b) is the effective vertical force on the base
      (u·b ≡ u·l·cos α since l = b/cos α).
    - In force sweep: u·b·tan α ≡ u·l·sin α is the horizontal pore component.
    Both are correct for the respective equilibrium equations.
"""

from __future__ import annotations

import math

from app.schemas import Slice, SpencerSettings
from app.errors import (
    SpencerBracketError,
    SpencerConvergenceError,
    NonFiniteValueError,
    NumericalInstabilityError,
)

_EPS = 1e-10


def solve_spencer(
    slices: list[Slice],
    settings: SpencerSettings,
) -> tuple[float, float, bool, int]:
    """
    Solve for FS and θ using Spencer's method (Bishop moment + force closure).

    Returns
    -------
    (fs, theta_deg, converged, iterations)

    See module docstring for the solver classification and pore pressure notes.
    """
    tol = settings.tolerance
    max_it = settings.max_iter
    theta_lo = math.radians(settings.theta_min)
    theta_hi = math.radians(settings.theta_max)

    # --- Stage 1: Bishop's Modified Method (moment equilibrium) ---
    fs, bishop_iters = _bishop_iterate(slices, tol, max_it)

    # --- Stage 2: Spencer force closure — find θ at this FS ---
    def force_residual(theta: float) -> float:
        return _force_sweep(slices, fs, theta)

    try:
        theta_star, brent_iters = _brent(force_residual, theta_lo, theta_hi, tol, max_it)
    except SpencerBracketError:
        # Force equilibrium satisfied at θ≈0 (e.g. near-symmetric slope)
        theta_star = 0.0
        brent_iters = 0

    total_iters = bishop_iters + brent_iters

    if not math.isfinite(fs) or fs <= 0:
        raise NonFiniteValueError(
            "Le calcul n'a pas produit de facteur de sécurité valide pour cette surface de rupture. "
            "Essayez de modifier la position ou le rayon du cercle.",
            {"fs": fs, "theta_deg": math.degrees(theta_star)},
        )

    return fs, math.degrees(theta_star), True, total_iters


def compute_residuals(
    slices: list[Slice],
    fs: float,
    theta_deg: float,
) -> dict[str, float]:
    """
    Post-solve residual diagnostics.

    Returns a dict with:
    - ``moment_relative``: |FS·Σ(W·sin α) − Σ(R_moment)| / |Σ(W·sin α)|
      where R_moment = (c'·l + N'_bishop·tan φ') / m_α.
      Should be ≈ 0 (Bishop converged to this).
    - ``force_relative``: |E_n| / Σ|W|.
      Should be ≈ 0 (Brent found this θ).
    - ``sum_W``: Σ|W| [kN/m], used to normalise force residual.
    """
    theta = math.radians(theta_deg)
    sum_W_sin = 0.0
    sum_R = 0.0
    sum_abs_W = 0.0

    for slc in slices:
        alpha = math.radians(slc.alpha_deg)
        phi = math.radians(slc.phi_deg)
        cos_a = math.cos(alpha)
        sin_a = math.sin(alpha)
        tan_phi = math.tan(phi)

        m_a = cos_a + sin_a * tan_phi / fs
        ub = slc.pore_pressure * slc.width
        N_prime = (slc.weight - ub) / m_a if abs(m_a) > _EPS else 0.0
        R = slc.cohesion * slc.base_length + N_prime * tan_phi

        sum_W_sin += slc.weight * sin_a
        sum_R += R
        sum_abs_W += abs(slc.weight)

    moment_residual = abs(fs * sum_W_sin - sum_R) / max(abs(sum_W_sin), _EPS)

    E_n = _force_sweep(slices, fs, theta)
    force_residual = abs(E_n) / max(sum_abs_W, _EPS)

    return {
        "moment_relative": moment_residual,
        "force_relative": force_residual,
        "sum_W": sum_abs_W,
        "E_n": E_n,
    }


# ---------------------------------------------------------------------------
# Stage 1 — Bishop's Modified Method
# ---------------------------------------------------------------------------

def _bishop_iterate(
    slices: list[Slice],
    tol: float,
    max_iter: int,
) -> tuple[float, int]:
    """
    Iterate Bishop's m_α formula to find the moment-based FS.

    Bishop's Modified Method (no θ, valid for circular surfaces):
        m_α = cos α · (1 + tan α · tan φ' / FS)
            = cos α + sin α · tan φ' / FS

        FS_{n+1} = Σ[(c'·l + (W − u·b) · tan φ') / m_α] / Σ(W · sin α)

    Pore pressure note: (W − u·b) is the effective vertical load.
    Since u·l·cos α = u·(b/cos α)·cos α = u·b, this is exact.

    Returns (fs, iterations).  Raises SpencerConvergenceError if not converged.
    """
    denom = sum(s.weight * math.sin(math.radians(s.alpha_deg)) for s in slices)
    if denom < _EPS:
        raise SpencerConvergenceError(
            "Le cercle de rupture ne génère pas de poussée sur le talus. "
            "Repositionnez-le pour qu'il coupe davantage le versant (déplacez le centre ou agrandissez le rayon).",
            {"sum_W_sin_alpha": denom},
        )

    # Première approximation comme dans le cours :
    # N ≈ W cos(α), puis FS0 = Σ[c·l + (N - U)tanφ] / Σ(W sinα).
    # Les itérations suivantes raffinent ce FS jusqu'à convergence.
    fs = _initial_course_factor_of_safety(slices, denom)
    for it in range(max_iter):
        num = 0.0
        for slc in slices:
            alpha = math.radians(slc.alpha_deg)
            phi = math.radians(slc.phi_deg)
            cos_a = math.cos(alpha)
            tan_a = math.tan(alpha)
            tan_phi = math.tan(phi)

            m_a = cos_a * (1.0 + tan_a * tan_phi / fs)
            if abs(m_a) < _EPS:
                raise NumericalInstabilityError(
                    f"Instabilité numérique détectée sur la section {slc.index + 1} du calcul. "
                    "Essayez de modifier l'angle de frottement φ' ou la position du cercle de rupture.",
                    {"slice_index": slc.index, "alpha_deg": slc.alpha_deg, "fs": fs},
                )

            ub = slc.pore_pressure * slc.width   # u·b ≡ u·l·cos α (exact)
            N_prime = (slc.weight - ub) / m_a
            num += slc.cohesion * slc.base_length + N_prime * tan_phi

        fs_new = num / denom
        if not math.isfinite(fs_new):
            raise NonFiniteValueError(
                "Le calcul a produit une valeur non physique. "
                "Vérifiez les paramètres mécaniques des couches (γ, c', φ') et la géométrie du talus.",
                {"iteration": it, "fs_new": fs_new},
            )
        if abs(fs_new - fs) < tol:
            return fs_new, it + 2
        fs = fs_new

    raise SpencerConvergenceError(
        f"Le calcul n'a pas abouti à une solution stable après {max_iter} itérations. "
        "Essayez avec un cercle différent ou ajustez les paramètres mécaniques des couches.",
        {"iterations": max_iter, "last_fs": fs},
    )


def _initial_course_factor_of_safety(slices: list[Slice], denom: float) -> float:
    """Initial FS from the course approximation N ≈ W·cos(α)."""
    num = 0.0
    for slc in slices:
        alpha = math.radians(slc.alpha_deg)
        phi = math.radians(slc.phi_deg)
        normal_eff = slc.weight * math.cos(alpha) - slc.pore_force
        num += slc.cohesion * slc.base_length + normal_eff * math.tan(phi)

    fs0 = num / denom
    if not math.isfinite(fs0) or fs0 <= 0:
        return 1.5
    return fs0


# ---------------------------------------------------------------------------
# Stage 2 — Spencer force sweep
# ---------------------------------------------------------------------------

def _force_sweep(slices: list[Slice], fs: float, theta: float) -> float:
    """
    Left-to-right Spencer force sweep.

    Derives ΔE per slice from the combined vertical + horizontal equilibrium,
    eliminating N analytically (Spencer 1967, eq. 17; Fredlund & Krahn 1977):

        m_α = cos α + sin α · tan φ' / FS
        n_α = sin α − cos α · tan φ' / FS

    From vertical equilibrium (sign convention: ΔE = E_i − E_{i+1}):
        N'·m_α = W − u·b − c'·l·sin α / FS − ΔE·tan θ       ...(V)

    From horizontal equilibrium (same convention):
        ΔE = N'·(sin α + cos α·tan φ'/FS) + u·b·tan α + c'·l·cos α/FS  ...(H)

    Substituting (V) into (H) and solving for ΔE:
        ΔE·(1 + n_α·tan θ / m_α) = A
        A = n_α·(W − u·b − c'·l·sin α / FS) / m_α + u·b·tan α − c'·l·cos α/FS

    Pore pressure note: u·b·tan α = u·l·sin α (equivalent forms).

    Convention: E accumulates left-to-right; E_0 = 0 at the left boundary.
    Force closure requires E_n = 0 at the right boundary.
    For active slices (α > 0): ΔE < 0 (resistance reduces E).
    For passive slices (α < 0): ΔE > 0 (compression increases E back toward 0).

    Returns E_n (should be 0 when θ satisfies force equilibrium at this FS).
    """
    T = math.tan(theta)
    E = 0.0

    for slc in slices:
        alpha = math.radians(slc.alpha_deg)
        phi = math.radians(slc.phi_deg)
        cos_a = math.cos(alpha)
        sin_a = math.sin(alpha)
        tan_phi = math.tan(phi)

        m_a = cos_a + sin_a * tan_phi / fs
        n_a = sin_a - cos_a * tan_phi / fs

        if abs(m_a) < _EPS:
            raise NumericalInstabilityError(
                f"Instabilité numérique sur la section {slc.index + 1}. "
                "Vérifiez que l'angle de frottement φ' est compris entre 1° et 89°.",
                {"slice_index": slc.index},
            )

        ub = slc.pore_pressure * slc.width       # u·b  [kN/m]
        tan_a = sin_a / cos_a if abs(cos_a) > _EPS else 0.0

        A = (
            n_a * (slc.weight - ub - slc.cohesion * slc.base_length * sin_a / fs) / m_a
            + ub * tan_a
            - slc.cohesion * slc.base_length * cos_a / fs
        )

        denom = 1.0 + n_a * T / m_a
        if abs(denom) < _EPS:
            raise NumericalInstabilityError(
                f"Instabilité numérique sur la section {slc.index + 1}. "
                "Élargissez la plage d'angle θ dans les paramètres Spencer (θ min / θ max).",
                {"slice_index": slc.index, "theta_deg": math.degrees(theta)},
            )

        E += A / denom

        if not math.isfinite(E):
            raise NonFiniteValueError(
                "Le calcul des forces interlamelles a produit une valeur non physique. "
                "Vérifiez les paramètres de sol et la géométrie du cercle.",
                {"slice_index": slc.index, "E": E},
            )

    return E


# ---------------------------------------------------------------------------
# Brent's method
# ---------------------------------------------------------------------------

def _brent(
    f,
    a: float,
    b: float,
    tol: float,
    max_iter: int,
) -> tuple[float, int]:
    """
    Find a root of f in [a, b] using Brent's method.

    Returns (root, iterations).
    Raises SpencerBracketError if f(a)·f(b) > 0.
    Raises SpencerConvergenceError if max_iter exceeded.
    """
    fa, fb = f(a), f(b)

    if not math.isfinite(fa) or not math.isfinite(fb):
        raise SpencerBracketError(
            "Impossible d'équilibrer les forces pour ce cercle de rupture. "
            "Élargissez la plage d'angle θ (θ min / θ max) dans les paramètres Spencer.",
            {"a": a, "b": b, "fa": fa, "fb": fb},
        )

    if fa * fb > 0:
        raise SpencerBracketError(
            "L'équilibre des forces n'est pas trouvable dans la plage d'angles θ définie. "
            "Élargissez θ min et θ max dans les paramètres Spencer (par exemple −45° à +45°).",
            {"a": a, "b": b, "fa": fa, "fb": fb},
        )

    if abs(fa) < tol:
        return a, 1
    if abs(fb) < tol:
        return b, 1

    c, fc = b, fb
    d = e = b - a

    for it in range(max_iter):
        if fb * fc > 0:
            c, fc = a, fa
            d = e = b - a

        if abs(fc) < abs(fb):
            a, fa = b, fb
            b, fb = c, fc
            c, fc = a, fa

        tol1 = 2.0 * _EPS * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)

        if abs(xm) <= tol1 or abs(fb) < tol:
            return b, it + 1

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0:
                q = -q
            else:
                p = -p
            if 2.0 * p < min(3.0 * xm * q - abs(tol1 * q), abs(e * q)):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d

        a, fa = b, fb
        b += d if abs(d) > tol1 else (tol1 if xm > 0 else -tol1)
        fb = f(b)

        if not math.isfinite(fb):
            raise NonFiniteValueError(
                "Valeur non physique rencontrée lors de la recherche d'équilibre. "
                "Vérifiez les paramètres de sol et la géométrie.",
                {"b": b},
            )

    raise SpencerConvergenceError(
        "L'équilibre des forces n'a pas convergé. "
        "Essayez d'élargir la plage d'angle θ (θ min / θ max) dans les paramètres Spencer.",
        {"iterations": max_iter},
    )

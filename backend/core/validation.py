"""Domain validation functions for geometry, layers, and slip circles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import Circle, SoilLayer, TerrainPoint


def validate_geometry(H: float, L: float) -> list[str]:
    """
    Validate basic slope geometry.

    Parameters
    ----------
    H : float
        Slope height in metres.
    L : float
        Horizontal projection in metres.

    Returns
    -------
    list[str]
        Empty list if valid; otherwise a list of human-readable error messages.
    """
    errors: list[str] = []

    if H <= 0:
        errors.append(f"La hauteur du talus H doit être > 0 (valeur fournie : {H})")
    if L <= 0:
        errors.append(f"La longueur horizontale L doit être > 0 (valeur fournie : {L})")

    if H > 0 and L > 0:
        ratio = H / L
        if ratio > 10.0:
            errors.append(
                f"Rapport H/L = {ratio:.2f} trop élevé (max 10). "
                "Vérifiez les dimensions du talus."
            )
        if ratio < 0.05:
            errors.append(
                f"Rapport H/L = {ratio:.2f} trop faible (min 0.05). "
                "Le talus est quasi-horizontal."
            )

    return errors


def validate_layers(layers: list["SoilLayer"], H: float) -> list[str]:
    """
    Validate soil layer parameters.

    Checks:
      - At least one layer present.
      - All layers except the last must have positive thickness.
      - Last layer (substratum) must have thickness = None.
      - Sum of layer thicknesses must be < H.
      - γ > 0 for each layer.
      - c' >= 0 for each layer.
      - 0 < φ' < 90 for each layer.

    Parameters
    ----------
    layers : list[SoilLayer]
        Ordered list of soil layers top-to-bottom.
    H : float
        Total slope height in metres.

    Returns
    -------
    list[str]
        Human-readable error messages (empty if valid).
    """
    errors: list[str] = []

    if not layers:
        errors.append("La liste des couches est vide.")
        return errors

    thickness_sum = 0.0
    for i, layer in enumerate(layers):
        prefix = f"Couche {layer.name!r} (id={layer.id})"
        is_last = i == len(layers) - 1

        # Thickness rules
        if is_last:
            if layer.thickness is not None:
                errors.append(
                    f"{prefix} : le substratum (dernière couche) ne doit pas "
                    "avoir d'épaisseur (thickness doit être null)."
                )
        else:
            if layer.thickness is None:
                errors.append(
                    f"{prefix} : thickness est null mais ce n'est pas la dernière couche."
                )
            elif layer.thickness <= 0:
                errors.append(f"{prefix} : l'épaisseur doit être > 0 ({layer.thickness} fourni).")
            else:
                thickness_sum += layer.thickness

        # Mechanical parameters
        if layer.gamma <= 0:
            errors.append(f"{prefix} : le poids volumique γ doit être > 0 ({layer.gamma} fourni).")
        if layer.cohesion < 0:
            errors.append(f"{prefix} : la cohésion c' doit être >= 0 ({layer.cohesion} fourni).")
        if not (0 < layer.phi_deg < 90):
            errors.append(
                f"{prefix} : l'angle φ' doit être dans ]0°, 90°[ ({layer.phi_deg}° fourni)."
            )

    # Sum of thicknesses check (only if H > 0 to avoid division-by-zero)
    if H > 0 and thickness_sum >= H:
        errors.append(
            f"La somme des épaisseurs ({thickness_sum:.3f} m) doit être inférieure à "
            f"la hauteur du talus H ({H:.3f} m)."
        )

    return errors


def validate_circle(circle: "Circle", terrain_pts: list["TerrainPoint"]) -> list[str]:
    """
    Validate that the slip circle is geometrically consistent with the terrain.

    Uses the same logic as ``_find_valid_x_range`` in slicing.py so that any
    circle accepted here will also be accepted by ``divide_into_slices``.
    In particular, circles that enter from outside the terrain domain (typical
    for failure circles whose centre is upstream) are accepted as long as the
    circle base dips below the terrain surface over a meaningful x-range.

    Parameters
    ----------
    circle : Circle
        Candidate slip circle.
    terrain_pts : list[TerrainPoint]
        Piecewise-linear terrain surface (at least 2 points).

    Returns
    -------
    list[str]
        Human-readable error messages (empty if valid).
    """
    errors: list[str] = []

    if circle.radius <= 0:
        errors.append(f"Le rayon du cercle doit être > 0 ({circle.radius} fourni).")
        return errors

    if len(terrain_pts) < 2:
        errors.append("Le profil du terrain doit contenir au moins 2 points.")
        return errors

    # Delegate to the same range-finder used by slicing — keeps both in sync
    from core.slicing import _find_valid_x_range
    from app.errors import CircleIntersectionError

    try:
        x_left, x_right = _find_valid_x_range(circle, terrain_pts)
        if x_right - x_left < 1e-3:
            errors.append(
                "La plage valide de tranches est quasi nulle "
                "(cercle tangent au terrain en un seul point)."
            )
    except CircleIntersectionError as exc:
        errors.append(exc.message)

    return errors

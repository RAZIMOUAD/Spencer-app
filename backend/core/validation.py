"""Domain validation functions for geometry, layers, and slip circles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import Circle, SoilLayer, TerrainPoint


def validate_geometry(H: float, L: float) -> list[str]:
    errors: list[str] = []

    if H <= 0:
        errors.append(f"La hauteur du talus doit être supérieure à 0 m (valeur saisie : {H} m).")
    if L <= 0:
        errors.append(f"La projection horizontale doit être supérieure à 0 m (valeur saisie : {L} m).")

    if H > 0 and L > 0:
        ratio = H / L
        if ratio > 10.0:
            errors.append(
                f"Le talus est trop abrupt pour cette méthode (H/L = {ratio:.1f}, maximum admis : 10). "
                "Vérifiez la hauteur H et la projection L."
            )
        if ratio < 0.05:
            errors.append(
                f"Le talus est pratiquement horizontal (H/L = {ratio:.2f}). "
                "La méthode de Spencer nécessite une pente minimale."
            )

    return errors


def validate_layers(layers: list["SoilLayer"], H: float) -> list[str]:
    errors: list[str] = []

    if not layers:
        errors.append("Aucune couche de sol n'est définie. Ajoutez au moins une couche.")
        return errors

    thickness_sum = 0.0
    for i, layer in enumerate(layers):
        prefix = f"Couche « {layer.name} »"
        is_last = i == len(layers) - 1

        # Thickness rules
        if is_last:
            if layer.thickness is not None:
                errors.append(
                    f"{prefix} est la couche de fond (substratum) et ne doit pas avoir d'épaisseur définie. "
                    "Laissez ce champ vide pour la dernière couche."
                )
        else:
            if layer.thickness is None:
                errors.append(
                    f"{prefix} : l'épaisseur n'est pas renseignée. "
                    "Saisissez une valeur positive (en mètres)."
                )
            elif layer.thickness <= 0:
                errors.append(
                    f"{prefix} : l'épaisseur doit être positive ({layer.thickness} m saisi)."
                )
            else:
                thickness_sum += layer.thickness

        # Mechanical parameters
        if layer.gamma <= 0:
            errors.append(
                f"{prefix} : le poids volumique γ doit être positif ({layer.gamma} kN/m³ saisi)."
            )
        if layer.cohesion < 0:
            errors.append(
                f"{prefix} : la cohésion c' ne peut pas être négative ({layer.cohesion} kPa saisi)."
            )
        if not (0 < layer.phi_deg < 90):
            errors.append(
                f"{prefix} : l'angle de frottement φ' doit être compris entre 0° et 90° "
                f"(valeur saisie : {layer.phi_deg}°)."
            )

    # Sum of thicknesses check
    if H > 0 and thickness_sum >= H:
        errors.append(
            f"La somme des épaisseurs des couches ({thickness_sum:.2f} m) dépasse la hauteur "
            f"du talus ({H:.2f} m). Réduisez une ou plusieurs épaisseurs."
        )

    return errors


def validate_circle(circle: "Circle", terrain_pts: list["TerrainPoint"]) -> list[str]:
    errors: list[str] = []

    if circle.radius <= 0:
        errors.append(f"Le rayon du cercle de rupture doit être positif ({circle.radius} m saisi).")
        return errors

    if len(terrain_pts) < 2:
        errors.append("Le profil du talus est invalide. Vérifiez les dimensions saisies.")
        return errors

    from core.slicing import _find_valid_x_range
    from app.errors import CircleIntersectionError

    try:
        x_left, x_right = _find_valid_x_range(circle, terrain_pts)
        if x_right - x_left < 1e-3:
            errors.append(
                "Le cercle de rupture n'intersecte pas suffisamment le talus. "
                "Augmentez le rayon ou déplacez le centre du cercle."
            )
    except CircleIntersectionError as exc:
        errors.append(exc.message)

    return errors

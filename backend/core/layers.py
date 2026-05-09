"""Layer lookup and effective weight utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import SoilLayer


def layer_at_elevation(
    z: float,
    interfaces: list[float],
    layers: list["SoilLayer"],
) -> "SoilLayer":
    """
    Return the SoilLayer that contains elevation z.

    Parameters
    ----------
    z : float
        Elevation to query (metres).
    interfaces : list[float]
        Interface elevations sorted descending [z_12, z_23, ...].
        Produced by ``core.geometry.layer_interfaces``.
    layers : list[SoilLayer]
        Ordered list of layers top-to-bottom (same order used to build interfaces).

    Returns
    -------
    SoilLayer
        The layer whose vertical extent includes z.

    Raises
    ------
    ValueError
        If z is above the top of the first layer or below the substratum (should not
        happen in a well-formed model).
    """
    if not layers:
        raise ValueError("layers list is empty")

    # Iterate through interfaces; each interface separates layer[i] from layer[i+1]
    for i, z_iface in enumerate(interfaces):
        if z > z_iface:
            return layers[i]

    # Below all interfaces → substratum (last layer)
    return layers[-1]


def submerged_weight(layer: "SoilLayer", z_mid: float, z_nappe: float) -> float:
    """
    Compute the effective (buoyancy-corrected) unit weight of a layer at a given
    elevation, accounting for the water table.

    Above the water table the full unit weight γ is used.
    Below the water table the buoyant unit weight γ' = γ - γ_w is used.

    Parameters
    ----------
    layer : SoilLayer
        The soil layer in question.
    z_mid : float
        Mid-point elevation of the element being weighted (metres).
    z_nappe : float
        Water table elevation (metres).

    Returns
    -------
    float
        Effective unit weight in kN/m³.
    """
    gamma_w = 9.81  # kN/m³
    if z_mid <= z_nappe:
        return layer.gamma - gamma_w
    return layer.gamma

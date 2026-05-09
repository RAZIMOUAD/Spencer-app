"""Pure geometry functions for slope profile and layer interfaces."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import SoilLayer, TerrainPoint


def auto_plateaus(H: float, L: float) -> tuple[float, float]:
    """
    Compute upstream and downstream plateau lengths from slope dimensions.

    Rules (same as the existing notebook):
      l_amont = max(1.5*L, 2.5*H)
      l_aval  = max(2.5*L, 4.0*H)

    Parameters
    ----------
    H : float
        Total slope height in metres.
    L : float
        Horizontal projection of the slope in metres.

    Returns
    -------
    tuple[float, float]
        (l_amont, l_aval) in metres.
    """
    l_amont = max(1.5 * L, 2.5 * H)
    l_aval = max(2.5 * L, 4.0 * H)
    return l_amont, l_aval


def slope_profile(
    H: float,
    L: float,
    l_amont: float,
    l_aval: float,
) -> list["TerrainPoint"]:
    """
    Build the piecewise-linear terrain surface as an ordered list of points.

    The profile has three segments:
      1. Upstream plateau: y = H, from x=0 to x=l_amont
      2. Slope face:       y decreases from H to 0, from x=l_amont to x=l_amont+L
      3. Downstream base:  y = 0, from x=l_amont+L to x=l_amont+L+l_aval

    Parameters
    ----------
    H, L, l_amont, l_aval : float
        Slope height, horizontal projection, and plateau lengths (metres).

    Returns
    -------
    list[TerrainPoint]
        Four corner points defining the terrain surface.
    """
    # Import here to avoid circular imports at module load time
    from app.schemas import TerrainPoint

    x_toe = l_amont + L  # start of downstream plateau
    return [
        TerrainPoint(x=0.0, y=H),
        TerrainPoint(x=l_amont, y=H),
        TerrainPoint(x=x_toe, y=0.0),
        TerrainPoint(x=x_toe + l_aval, y=0.0),
    ]


def point_on_slope(x: float, H: float, L: float, l_amont: float) -> float:
    """
    Return the terrain surface elevation y at horizontal coordinate x.

    Parameters
    ----------
    x : float
        Horizontal position in metres.
    H : float
        Total slope height in metres.
    L : float
        Horizontal projection of slope face in metres.
    l_amont : float
        Upstream plateau length in metres.

    Returns
    -------
    float
        Surface elevation (y) at position x, clamped to [0, H].
    """
    x_crest = l_amont
    x_toe = l_amont + L

    if x <= x_crest:
        return H
    if x >= x_toe:
        return 0.0
    # Linear interpolation along slope face
    t = (x - x_crest) / (x_toe - x_crest)
    return H * (1.0 - t)


def layer_interfaces(H: float, layers: list["SoilLayer"]) -> list[float]:
    """
    Compute interface elevations between soil layers, sorted descending.

    The first layer is at the top. Interfaces are accumulated downward from H.
    The last (substratum) layer has no thickness and no interface below it.

    Parameters
    ----------
    H : float
        Total slope height in metres (top of profile = elevation H).
    layers : list[SoilLayer]
        Ordered list of SoilLayer objects from top to bottom.

    Returns
    -------
    list[float]
        Elevations of interfaces [z_12, z_23, ...] in descending order.
        The list has len(layers) - 1 entries (no interface below substratum).
    """
    interfaces: list[float] = []
    z = H
    for layer in layers[:-1]:  # skip substratum (no thickness)
        if layer.thickness is None:
            raise ValueError(
                f"Layer '{layer.name}' (id={layer.id}) is not the last layer "
                "but has thickness=None."
            )
        z -= layer.thickness
        interfaces.append(z)
    return interfaces


def slope_angle_deg(H: float, L: float) -> float:
    """Return the slope angle α in degrees (arctan H/L)."""
    return math.degrees(math.atan2(H, L))

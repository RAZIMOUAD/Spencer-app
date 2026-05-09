"""Precompiled layer lookup — O(log n) instead of O(n) per query."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from app.schemas import SoilLayer
from app.errors import LayerLookupError


@dataclass(frozen=True)
class LayerIndex:
    """
    Immutable precompiled index for fast layer lookup by elevation.

    Build once per analysis request, reuse across all slices and all circles.

    Attributes
    ----------
    layers : tuple[SoilLayer, ...]
        Layers ordered top-to-bottom.
    interfaces : tuple[float, ...]
        Interface elevations sorted **descending** [z_12, z_23, ...].
        Length = len(layers) - 1 (no interface below substratum).
    H_top : float
        Top of profile elevation (= max terrain y).
    """

    layers: tuple[SoilLayer, ...]
    interfaces: tuple[float, ...]
    H_top: float

    # Ascending copy for bisect (bisect works on ascending sequences)
    _interfaces_asc: tuple[float, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # Store ascending copy; bypass frozen=True via object.__setattr__
        object.__setattr__(
            self,
            "_interfaces_asc",
            tuple(reversed(self.interfaces)),
        )

    # ------------------------------------------------------------------

    def find(self, z: float) -> SoilLayer:
        """
        Return the SoilLayer that contains elevation z.

        Uses bisect_right on the ascending interface list for O(log n) lookup.

        Parameters
        ----------
        z : float
            Elevation to query (metres).

        Returns
        -------
        SoilLayer

        Raises
        ------
        LayerLookupError
            z is outside the defined profile (should not happen in practice).
        """
        if not self.layers:
            raise LayerLookupError(
                "L'index de couches est vide.",
                {"z": z},
            )

        # _interfaces_asc: ascending thresholds that separate layers bottom-to-top.
        # Example: 3 layers with interfaces [8.0, 4.0] (desc) →
        #          _interfaces_asc = [4.0, 8.0]
        # bisect_right(asc, z) gives the number of interfaces below z.
        # layer index from bottom = bisect_right(asc, z)
        # layer index from top    = n_layers - 1 - bisect_right(asc, z)
        n = len(self.layers)
        pos = bisect.bisect_right(self._interfaces_asc, z)
        # pos = 0 → below all interfaces → substratum (last layer)
        # pos = n-1 → above all interfaces → top layer (first)
        layer_idx_from_bottom = pos
        layer_idx_from_top = n - 1 - layer_idx_from_bottom

        if not (0 <= layer_idx_from_top < n):
            raise LayerLookupError(
                f"Élévation z={z:.3f} m hors des limites du profil "
                f"[−∞, {self.H_top:.3f}].",
                {"z": z, "H_top": self.H_top, "n_layers": n},
            )

        return self.layers[layer_idx_from_top]

    # ------------------------------------------------------------------

    @classmethod
    def build(cls, layers: list[SoilLayer], H_top: float) -> "LayerIndex":
        """
        Build a LayerIndex from a layer list and the terrain top elevation.

        Parameters
        ----------
        layers : list[SoilLayer]
            Ordered top-to-bottom. Last layer is the substratum (no thickness).
        H_top : float
            Elevation of the top of the profile (max terrain y).

        Returns
        -------
        LayerIndex
        """
        from core.geometry import layer_interfaces  # avoid circular import at module level

        interfaces = layer_interfaces(H_top, layers)
        return cls(
            layers=tuple(layers),
            interfaces=tuple(interfaces),
            H_top=H_top,
        )

    # ------------------------------------------------------------------

    @property
    def n_layers(self) -> int:
        return len(self.layers)

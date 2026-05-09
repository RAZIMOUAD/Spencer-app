"""Tests for LayerIndex binary search."""

from __future__ import annotations

import pytest

from app.schemas import SoilLayer
from app.errors import LayerLookupError
from core.layer_index import LayerIndex


def _layer(id: int, thickness=None) -> SoilLayer:
    return SoilLayer(id=id, name=f"C{id}", gamma=20.0, cohesion=10.0, phi_deg=30.0, thickness=thickness)


def _build(H=10.0, thicknesses=(2.0, 3.0)) -> LayerIndex:
    """Build a 3-layer index: C1 (2m), C2 (3m), C3 (substratum)."""
    layers = [_layer(1, thicknesses[0]), _layer(2, thicknesses[1]), _layer(3, None)]
    return LayerIndex.build(layers, H)


class TestLayerIndexBuild:
    def test_interfaces_count(self):
        idx = _build(H=10.0, thicknesses=(2.0, 3.0))
        # 2 interfaces: z=8 (C1/C2 boundary), z=5 (C2/C3 boundary)
        assert len(idx.interfaces) == 2

    def test_interfaces_descending(self):
        idx = _build(H=10.0, thicknesses=(2.0, 3.0))
        assert idx.interfaces[0] > idx.interfaces[1]

    def test_interface_values(self):
        idx = _build(H=10.0, thicknesses=(2.0, 3.0))
        # Top layer C1 has thickness 2m → interface at H - 2 = 8
        # C2 has thickness 3m → interface at 8 - 3 = 5
        assert abs(idx.interfaces[0] - 8.0) < 1e-9
        assert abs(idx.interfaces[1] - 5.0) < 1e-9

    def test_single_layer(self):
        layer = _layer(1, None)
        idx = LayerIndex.build([layer], H_top=10.0)
        assert len(idx.interfaces) == 0


class TestLayerIndexFind:
    def setup_method(self):
        self.idx = _build(H=10.0, thicknesses=(2.0, 3.0))

    def test_find_top_layer(self):
        # z=9 is inside C1 (between 8 and 10)
        layer = self.idx.find(9.0)
        assert layer.id == 1

    def test_find_middle_layer(self):
        # z=6 is inside C2 (between 5 and 8)
        layer = self.idx.find(6.0)
        assert layer.id == 2

    def test_find_bottom_layer(self):
        # z=2 is inside C3 (below 5)
        layer = self.idx.find(2.0)
        assert layer.id == 3

    def test_find_exactly_at_interface(self):
        # z=8 is at the C1/C2 boundary — should fall to C2 or C1 (consistently one)
        layer = self.idx.find(8.0)
        assert layer.id in (1, 2)  # either is acceptable at boundary

    def test_find_below_all_interfaces(self):
        # z=0 → substratum C3
        layer = self.idx.find(0.0)
        assert layer.id == 3

    def test_find_negative_z(self):
        # z=-5 deep below substratum → still C3 (extends downward)
        layer = self.idx.find(-5.0)
        assert layer.id == 3

    def test_find_single_layer(self):
        layer = _layer(1, None)
        idx = LayerIndex.build([layer], H_top=10.0)
        assert idx.find(5.0).id == 1
        assert idx.find(-100.0).id == 1

    def test_find_is_fast(self):
        """O(log n) — just check it doesn't raise with many layers."""
        layers = [_layer(i, 1.0) for i in range(1, 16)] + [_layer(16, None)]
        idx = LayerIndex.build(layers, H_top=15.0)
        for z in range(-5, 16):
            idx.find(float(z))

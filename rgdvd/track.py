"""Procedural closed-circuit road, kerbs, barriers, and trackside scenery."""
from __future__ import annotations

import math
import random

from panda3d.core import Material, NodePath, PNMImage, Texture, Vec4

from .geometry import box, cylinder_z, mesh


class RacingCircuit:
    CENTER_RX = 100.0
    CENTER_RY = 146.0
    OUTER_RX = 121.0
    OUTER_RY = 167.0
    INNER_RX = 79.0
    INNER_RY = 125.0
    SEGMENTS = 256

    def __init__(self, parent: NodePath, quality: str = "medium") -> None:
        self.quality = quality if quality in ("low", "medium", "high") else "medium"
        self.root = parent.attachNewNode("coastal-grand-prix-circuit")
        self._build_ground()
        self._build_asphalt()
        self._build_kerbs()
        self._build_road_markings()
        self._build_barriers()
        self._build_infield()
        self._build_environment()

    def contains(self, x: float, y: float) -> bool:
        radial = math.sqrt((x / self.CENTER_RX) ** 2 +
                           (y / self.CENTER_RY) ** 2)
        return 0.825 <= radial <= 1.175

    def _ellipse(self, rx: float, ry: float, angle: float,
                 z: float) -> tuple[float, float, float]:
        return rx * math.cos(angle), ry * math.sin(angle), z

    def _build_ground(self) -> None:
        ground = box(self.root, "terrain-base", (0, 0, -0.9),
                     (1100, 1200, 1.8), (0.12, 0.24, 0.105, 1))
        ground.setColorScale(0.95, 1.0, 0.94, 1)

    def _asphalt_texture(self) -> Texture:
        # Tileable, deterministic fine-grain asphalt. No external asset required.
        size = 256
        image = PNMImage(size, size, 3)
        rng = random.Random(2026)
        for y in range(size):
            for x in range(size):
                grain = rng.uniform(-0.035, 0.035)
                broad = 0.012 * math.sin(x * 0.17) * math.sin(y * 0.13)
                value = max(0.075, min(0.22, 0.135 + grain + broad))
                image.setXel(x, y, value * 0.94, value * 0.98, value * 1.04)
        texture = Texture("procedural-asphalt")
        texture.load(image)
        texture.setWrapU(Texture.WMRepeat)
        texture.setWrapV(Texture.WMRepeat)
        texture.setMinfilter(Texture.FTLinearMipmapLinear)
        texture.setMagfilter(Texture.FTLinear)
        return texture

    def _build_asphalt(self) -> None:
        vertices, uvs, normals, triangles = [], [], [], []
        n = self.SEGMENTS
        for i in range(n):
            angle = 2 * math.pi * i / n
            vertices.append(self._ellipse(self.OUTER_RX, self.OUTER_RY, angle, 0.035))
            vertices.append(self._ellipse(self.INNER_RX, self.INNER_RY, angle, 0.035))
            uvs.extend(((i / n * 8.0, 0.0), (i / n * 8.0, 4.0)))
            normals.extend(((0, 0, 1), (0, 0, 1)))
        for i in range(n):
            j = (i + 1) % n
            a, b = i*2, i*2+1
            c, d = j*2, j*2+1
            triangles.extend(((a, c, b), (b, c, d)))
        road = mesh(self.root, "continuous-asphalt-surface", vertices,
                    triangles, (0.84, 0.86, 0.89, 1), uvs=uvs, normals=normals)
        road.setTexture(self._asphalt_texture(), 1)
        # UVs are already repeated in the mesh; no additional texture scale is needed.
        material = Material("aged-asphalt")
        material.setShininess(8)
        material.setSpecular(Vec4(0.08, 0.08, 0.09, 1))
        road.setMaterial(material, 1)

        self._ring_strip(self.OUTER_RX+3.8, self.OUTER_RY+3.8,
                         self.OUTER_RX+0.8, self.OUTER_RY+0.8,
                         0.02, (0.34, 0.31, 0.25, 1), "outer-gravel")
        self._ring_strip(self.INNER_RX-0.8, self.INNER_RY-0.8,
                         self.INNER_RX-3.4, self.INNER_RY-3.4,
                         0.02, (0.31, 0.29, 0.25, 1), "inner-gravel")

    def _ring_strip(self, outer_rx: float, outer_ry: float,
                    inner_rx: float, inner_ry: float, z: float,
                    color: tuple[float, float, float, float], name: str) -> None:
        vertices, normals, triangles = [], [], []
        n = self.SEGMENTS
        for i in range(n):
            a = 2 * math.pi * i / n
            vertices.extend((self._ellipse(outer_rx, outer_ry, a, z),
                             self._ellipse(inner_rx, inner_ry, a, z)))
            normals.extend(((0, 0, 1), (0, 0, 1)))
        for i in range(n):
            j = (i + 1) % n
            a, b, c, d = 2*i, 2*i+1, 2*j, 2*j+1
            triangles.extend(((a, c, b), (b, c, d)))
        mesh(self.root, name, vertices, triangles, color, normals=normals)

    def _build_kerbs(self) -> None:
        # Red/white kerb blocks along both road edges.
        for inner in (False, True):
            for segment in range(0, self.SEGMENTS, 2):
                a0 = 2 * math.pi * segment / self.SEGMENTS
                a1 = 2 * math.pi * (segment + 2) / self.SEGMENTS
                if inner:
                    outer = (self.INNER_RX+2.9, self.INNER_RY+2.9)
                    inner_edge = (self.INNER_RX-0.1, self.INNER_RY-0.1)
                else:
                    outer = (self.OUTER_RX+0.1, self.OUTER_RY+0.1)
                    inner_edge = (self.OUTER_RX-2.9, self.OUTER_RY-2.9)
                vertices = [
                    self._ellipse(*outer, a0, 0.08),
                    self._ellipse(*inner_edge, a0, 0.08),
                    self._ellipse(*outer, a1, 0.08),
                    self._ellipse(*inner_edge, a1, 0.08),
                ]
                color = (0.78, 0.035, 0.025, 1) if (segment // 2) % 2 == 0 else (0.88, 0.88, 0.84, 1)
                mesh(self.root, "painted-rumble-kerb", vertices,
                     [(0, 2, 1), (1, 2, 3)], color)

    def _build_road_markings(self) -> None:
        for i in range(0, self.SEGMENTS, 9):
            angle = 2 * math.pi * (i + 2) / self.SEGMENTS
            x, y, _ = self._ellipse(self.CENTER_RX, self.CENTER_RY, angle, -0.34)
            tangent_x = -self.CENTER_RX * math.sin(angle)
            tangent_y = self.CENTER_RY * math.cos(angle)
            heading = math.degrees(math.atan2(-tangent_x, tangent_y))
            dash = box(self.root, "broken-center-line", (x, y, 0.09),
                       (0.20, 5.2, 0.025), (0.72, 0.72, 0.68, 1))
            dash.setH(heading)

        for i in range(20):
            x = -19.0 + i * 2.0
            for row in range(2):
                color = (0.88, 0.89, 0.88, 1) if (i + row) % 2 == 0 else (0.035, 0.04, 0.045, 1)
                box(self.root, "start-finish-checker", (x, -146.0 + row*1.5, 0.09),
                    (2.0, 1.5, 0.035), color)

        for y in (-124.0, -119.5):
            box(self.root, "pit-lane-line", (0, y, 0.09),
                (24.0, 0.12, 0.03), (0.87, 0.83, 0.68, 1))

    def _build_barriers(self) -> None:
        for i in range(96):
            angle = 2 * math.pi * i / 96
            x, y, _ = self._ellipse(self.OUTER_RX+6.0, self.OUTER_RY+6.0,
                                    angle, 0.0)
            tangent_x = -(self.OUTER_RX+6.0) * math.sin(angle)
            tangent_y = (self.OUTER_RY+6.0) * math.cos(angle)
            heading = math.degrees(math.atan2(-tangent_x, tangent_y))
            wall = box(self.root, "concrete-safety-barrier", (x, y, 0.95),
                       (1.25, 8.0, 1.9), (0.52, 0.54, 0.55, 1))
            wall.setH(heading)
            if i % 3 == 0:
                panel = box(self.root, "barrier-colour-panel", (x, y, 1.08),
                            (1.28, 3.6, 0.58),
                            (0.72, 0.035, 0.025, 1) if (i//3) % 2 == 0 else (0.86, 0.86, 0.82, 1))
                panel.setH(heading)

        for side in (-1, 1):
            for j in range(8):
                stack = cylinder_z(self.root, "stacked-tyres", 0.64, 0.47,
                                   (0.025, 0.028, 0.03, 1), 20)
                stack.setPos(side*126.0, -18.0 + j*1.4, 0.23)
                top = cylinder_z(self.root, "stacked-tyres-top", 0.64, 0.47,
                                 (0.025, 0.028, 0.03, 1), 20)
                top.setPos(side*126.0, -18.0 + j*1.4, 0.68)

    def _build_infield(self) -> None:
        box(self.root, "pit-building", (0, -92, 3.0), (58, 12, 6),
            (0.60, 0.63, 0.65, 1))
        box(self.root, "pit-roof", (0, -92, 6.2), (60, 13, 0.55),
            (0.12, 0.14, 0.17, 1))
        for i in range(8):
            x = -24.0 + i*6.8
            box(self.root, "garage-opening", (x, -85.8, 2.0),
                (4.3, 0.12, 3.2), (0.035, 0.045, 0.055, 1))
            box(self.root, "garage-header", (x, -85.65, 3.8),
                (4.3, 0.16, 0.18), (0.84, 0.84, 0.81, 1))
        box(self.root, "pit-wall", (0, -81, 1.1), (58, 1.0, 2.2),
            (0.72, 0.73, 0.72, 1))

        box(self.root, "grandstand-base", (0, 111, 2.0), (46, 15, 4),
            (0.35, 0.37, 0.39, 1))
        for row in range(5):
            box(self.root, "grandstand-seat-row", (0, 105 + row*2.7, 4.1 + row*0.85),
                (48, 2.0, 0.34), (0.18, 0.22, 0.25, 1))
        box(self.root, "grandstand-roof", (0, 112, 9.2), (52, 18, 0.65),
            (0.095, 0.12, 0.15, 1))
        for x in range(-20, 21, 4):
            box(self.root, "grandstand-support", (x, 113, 5.8),
                (0.35, 0.45, 6.3), (0.20, 0.23, 0.25, 1))

        for x in (-115, 115):
            for y in (-90, -10, 75):
                mast = cylinder_z(self.root, "floodlight-mast", 0.18, 17,
                                  (0.23, 0.25, 0.27, 1), 10)
                mast.setPos(x, y, 8.5)
                box(self.root, "floodlight-arm", (x, y, 17.2),
                    (5.0, 0.22, 0.22), (0.22, 0.24, 0.26, 1))
                for offset in (-1.8, 0, 1.8):
                    lamp = box(self.root, "floodlight", (x+offset, y, 17.0),
                               (0.75, 0.55, 0.28), (0.95, 0.91, 0.72, 1))
                    lamp.setLightOff(1)

    def _build_environment(self) -> None:
        rng = random.Random(42)
        tree_count = {"low": 40, "medium": 90, "high": 140}[self.quality]
        hill_count = {"low": 10, "medium": 18, "high": 24}[self.quality]
        for i in range(tree_count):
            angle = 2 * math.pi * i / tree_count
            radius_x = rng.uniform(185, 300)
            radius_y = radius_x * 1.36
            x = radius_x * math.cos(angle) + rng.uniform(-10, 10)
            y = radius_y * math.sin(angle) + rng.uniform(-12, 12)
            trunk_height = rng.uniform(4.5, 7.5)
            trunk = cylinder_z(self.root, "tree-trunk", 0.48, trunk_height,
                               (0.20, 0.12, 0.07, 1), 7)
            trunk.setPos(x, y, trunk_height/2)
            foliage = cylinder_z(self.root, "tree-canopy", rng.uniform(2.8, 4.6),
                                 rng.uniform(7.0, 10.0),
                                 (rng.uniform(0.045, 0.09), rng.uniform(0.18, 0.29),
                                  rng.uniform(0.055, 0.11), 1), 7)
            foliage.setPos(x, y, trunk_height + 2.5)

        for i in range(hill_count):
            angle = 2 * math.pi * i / hill_count
            x = 430 * math.cos(angle)
            y = 510 * math.sin(angle)
            hill = cylinder_z(self.root, "distant-hill", rng.uniform(22, 44),
                              rng.uniform(40, 85), (0.16, 0.25, 0.15, 1), 7)
            hill.setPos(x, y, 18)

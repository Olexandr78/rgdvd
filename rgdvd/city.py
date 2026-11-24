"""Open-world street-racing city built from modular urban geometry.

The city is a free-roam environment, not a closed circuit. Roads form a
connected street grid with intersections, sidewalks, crosswalks, blocks,
mixed-height buildings, shopfronts, rooftop details and street lighting.
"""
from __future__ import annotations

import math
import random

from panda3d.core import NodePath, PNMImage, Texture, Vec4

from .geometry import box, cylinder_z, mesh


class UrbanCity:
    GRID = 120.0
    HALF_ROAD = 13.0
    EXTENT = 960.0

    def __init__(self, parent: NodePath, quality: str = "medium") -> None:
        self.quality = quality if quality in ("low", "medium", "high") else "medium"
        self.root = parent.attachNewNode("RGDVD-open-city")
        self.rng = random.Random(2406)
        self._build_ground()
        self._build_street_grid()
        self._build_blocks()
        self._build_street_furniture()
        self._build_district_landmarks()

    def contains(self, x: float, y: float) -> bool:
        """True on paved streets or the broad junction aprons."""
        if abs(x) > self.EXTENT or abs(y) > self.EXTENT:
            return False
        gx = abs((x + self.GRID / 2) % self.GRID - self.GRID / 2)
        gy = abs((y + self.GRID / 2) % self.GRID - self.GRID / 2)
        return gx <= self.HALF_ROAD or gy <= self.HALF_ROAD

    def _build_ground(self) -> None:
        box(self.root, "city-terrain", (0, 0, -1.2),
            (self.EXTENT * 2 + 300, self.EXTENT * 2 + 300, 2.4),
            (0.105, 0.125, 0.115, 1))
        # A distant, low skyline closes the horizon without a racetrack bowl.
        for i in range(48):
            angle = 2 * math.pi * i / 48
            x, y = 1110 * math.cos(angle), 1110 * math.sin(angle)
            h = self.rng.uniform(35, 115)
            tower = box(self.root, "far-city-silhouette", (x, y, h / 2),
                        (self.rng.uniform(24, 55), self.rng.uniform(24, 55), h),
                        (0.13, 0.16, 0.17, 1))
            tower.setColorScale(0.72, 0.78, 0.82, 1)

    def _build_street_grid(self) -> None:
        extent = self.EXTENT
        # Continuous asphalt ribbons make a connected 1.9 x 1.9 km street grid.
        lane_v, lane_t = [], []
        cross_v, cross_t = [], []
        stop_v, stop_t = [], []

        def add_rect(vertices, triangles, x, y, width, depth, z=0.105):
            base = len(vertices)
            vertices.extend(((x-width/2, y-depth/2, z),
                             (x+width/2, y-depth/2, z),
                             (x+width/2, y+depth/2, z),
                             (x-width/2, y+depth/2, z)))
            triangles.extend(((base, base+1, base+2), (base, base+2, base+3)))

        for index in range(-8, 9):
            p = index * self.GRID
            box(self.root, "north-south-asphalt", (p, 0, 0.015),
                (self.HALF_ROAD * 2, extent * 2, 0.12),
                (0.105, 0.112, 0.12, 1))
            box(self.root, "east-west-asphalt", (0, p, 0.018),
                (extent * 2, self.HALF_ROAD * 2, 0.12),
                (0.105, 0.112, 0.12, 1))
            # Concrete sidewalks on both sides of each road.
            for side in (-1, 1):
                sx = p + side * (self.HALF_ROAD + 3.0)
                sy = p + side * (self.HALF_ROAD + 3.0)
                box(self.root, "avenue-sidewalk", (sx, 0, 0.12),
                    (5.5, extent * 2, 0.24), (0.34, 0.35, 0.34, 1))
                box(self.root, "boulevard-sidewalk", (0, sy, 0.12),
                    (extent * 2, 5.5, 0.24), (0.34, 0.35, 0.34, 1))

            # Broken lane dividers, painted as individual short dashes.
            for d in range(-15, 16):
                along = d * 48.0
                for offset in (-3.0, 3.0):
                    add_rect(lane_v, lane_t, p + offset, along, 0.16, 8.0)
                    add_rect(lane_v, lane_t, along, p + offset, 8.0, 0.16)

        # Crosswalk bars at the grid intersections.
        for ix in range(-8, 9):
            for iy in range(-8, 9):
                cx, cy = ix * self.GRID, iy * self.GRID
                for n in range(6):
                    offset = -7.5 + n * 3.0
                    add_rect(cross_v, cross_t, cx + offset, cy + 17.0, 1.7, 5.0)
                    add_rect(cross_v, cross_t, cx + 17.0, cy + offset, 5.0, 1.7)
                # Stop lines before each intersection.
                for side in (-1, 1):
                    add_rect(stop_v, stop_t, cx + side * 9.5, cy - 19.0, 0.22, 8.0)

    def _building_windows(self, x: float, y: float, width: float,
                          depth: float, floors: int, floor_height: float,
                          facade_color: tuple[float, float, float, float]) -> None:
        """Batch window quads into one mesh per building, not hundreds of nodes."""
        vertices, triangles = [], []
        cols = max(2, int(width // 5.2))
        rows = max(2, floors - 1)
        for face in (0, 1):
            for row in range(rows):
                z = 2.4 + row * floor_height
                for col in range(cols):
                    u = (col + 0.5) / cols
                    wx = x - width * 0.5 + u * width
                    ww = min(1.45, width / cols * 0.42)
                    wh = min(1.65, floor_height * 0.48)
                    if face == 0:
                        yy = y - depth * 0.5 - 0.035
                        points = [(wx-ww, yy, z), (wx+ww, yy, z),
                                  (wx+ww, yy, z+wh), (wx-ww, yy, z+wh)]
                    else:
                        yy = y + depth * 0.5 + 0.035
                        points = [(wx+ww, yy, z), (wx-ww, yy, z),
                                  (wx-ww, yy, z+wh), (wx+ww, yy, z+wh)]
                    base = len(vertices)
                    vertices.extend(points)
                    triangles.extend(((base, base+1, base+2),
                                      (base, base+2, base+3)))
        # Side-facing windows are a second batched facade strip.
        side_cols = max(2, int(depth // 5.2))
        for side in (-1, 1):
            xx = x + side * (width * 0.5 + 0.035)
            for row in range(rows):
                z = 2.4 + row * floor_height
                for col in range(side_cols):
                    wy = y - depth * 0.5 + (col + 0.5) / side_cols * depth
                    ww = min(1.35, depth / side_cols * 0.42)
                    wh = min(1.65, floor_height * 0.48)
                    points = ([(xx, wy-ww, z), (xx, wy+ww, z),
                               (xx, wy+ww, z+wh), (xx, wy-ww, z+wh)]
                              if side > 0 else
                              [(xx, wy+ww, z), (xx, wy-ww, z),
                               (xx, wy-ww, z+wh), (xx, wy+ww, z+wh)])
                    base = len(vertices)
                    vertices.extend(points)
                    triangles.extend(((base, base+1, base+2),
                                      (base, base+2, base+3)))
        if vertices:
            lit = self.rng.random() < 0.38
            glass = ((0.72, 0.66, 0.43, 1) if lit else
                     (0.10, 0.19, 0.24, 1))
            node = mesh(self.root, "repeated-window-facade", vertices,
                        triangles, glass)
            node.setLightOff(1)

    def _make_building(self, x: float, y: float, width: float,
                       depth: float, height: float, kind: str) -> None:
        floors = max(2, int(height / 3.6))
        floor_height = height / floors
        palettes = {
            "office": [(0.34, 0.39, 0.42, 1), (0.48, 0.47, 0.42, 1),
                       (0.25, 0.31, 0.34, 1)],
            "residential": [(0.53, 0.48, 0.40, 1), (0.43, 0.45, 0.43, 1),
                            (0.61, 0.56, 0.48, 1)],
            "industrial": [(0.34, 0.38, 0.37, 1), (0.46, 0.43, 0.36, 1)],
            "shop": [(0.47, 0.43, 0.37, 1), (0.38, 0.43, 0.44, 1)],
        }
        facade = self.rng.choice(palettes[kind])
        box(self.root, f"{kind}-building-shell", (x, y, height * 0.5 + 0.25),
            (width, depth, height), facade)
        self._building_windows(x, y, width, depth, floors, floor_height, facade)
        # Flat roof lip, parapet and rooftop mechanical equipment.
        box(self.root, "roof-parapet", (x, y, height + 0.45),
            (width + 0.7, depth + 0.7, 0.9), (0.23, 0.26, 0.27, 1))
        for _ in range(2 if height > 24 else 1):
            rx = x + self.rng.uniform(-width * 0.25, width * 0.25)
            ry = y + self.rng.uniform(-depth * 0.25, depth * 0.25)
            box(self.root, "rooftop-HVAC", (rx, ry, height + 1.5),
                (self.rng.uniform(2, 4), self.rng.uniform(2, 4), 1.4),
                (0.24, 0.27, 0.28, 1))
        if kind == "shop":
            # Dark glass shopfront with a bright sign band.
            box(self.root, "shopfront-glass", (x, y - depth * 0.5 - 0.045, 2.0),
                (width * 0.72, 0.07, 2.8), (0.055, 0.12, 0.15, 1))
            sign = box(self.root, "shop-sign", (x, y - depth * 0.5 - 0.09, 3.65),
                       (width * 0.76, 0.12, 0.42),
                       self.rng.choice(((0.72, 0.10, 0.045, 1),
                                        (0.08, 0.35, 0.48, 1),
                                        (0.74, 0.53, 0.12, 1))))
            sign.setLightOff(1)

    def _build_blocks(self) -> None:
        # Build distinct downtown, residential and industrial districts.
        block_count = 0
        for ix in range(-7, 8):
            for iy in range(-7, 8):
                cx, cy = ix * self.GRID + 60, iy * self.GRID + 60
                if abs(cx) > self.EXTENT - 70 or abs(cy) > self.EXTENT - 70:
                    continue
                block_count += 1
                if abs(ix) <= 2 and abs(iy) <= 2:
                    district = "downtown"
                elif ix >= 4 or iy <= -4:
                    district = "industrial"
                else:
                    district = "residential"
                # Leave a service lane / courtyard through each block.
                if self.quality == "low":
                    count = 1
                elif self.quality == "medium":
                    count = 2 if district == "downtown" else 1
                else:
                    count = 3 if district == "downtown" else 2
                for building_index in range(count):
                    if count == 1:
                        bx, by = cx, cy
                    else:
                        bx = cx + (-23 if building_index % 2 == 0 else 23)
                        by = cy + (-18 if building_index < 2 else 18)
                    if district == "downtown":
                        kind = "office"
                        height = self.rng.uniform(42, 125 if self.quality == "high" else 88)
                        width, depth = self.rng.uniform(27, 39), self.rng.uniform(27, 38)
                    elif district == "industrial":
                        kind = "industrial"
                        height = self.rng.uniform(8, 19)
                        width, depth = self.rng.uniform(32, 46), self.rng.uniform(27, 40)
                    else:
                        kind = "shop" if building_index == 0 and self.rng.random() < 0.32 else "residential"
                        height = self.rng.uniform(12, 42)
                        width, depth = self.rng.uniform(25, 38), self.rng.uniform(24, 36)
                    self._make_building(bx, by, width, depth, height, kind)

    def _build_street_furniture(self) -> None:
        # Streetlights, traffic signals, poles, bins and occasional trees.
        for axis in ("x", "y"):
            for road_index in range(-8, 9):
                for step in range(-4, 5):
                    along = step * 120.0 + 36.0
                    across = road_index * self.GRID + (10.0 if (step + road_index) % 2 else -10.0)
                    x, y = (across, along) if axis == "x" else (along, across)
                    pole = cylinder_z(self.root, "streetlight-pole", 0.14, 8.5,
                                      (0.18, 0.20, 0.21, 1), 10)
                    pole.setPos(x, y, 4.25)
                    arm = box(self.root, "streetlight-arm", (x + 1.0, y, 8.3),
                              (2.2, 0.16, 0.16), (0.20, 0.22, 0.23, 1))
                    lamp = box(self.root, "LED-streetlamp", (x + 2.0, y, 8.15),
                               (0.85, 0.45, 0.18), (0.95, 0.83, 0.58, 1))
                    lamp.setLightOff(1)
        for ix in range(-7, 8):
            for iy in range(-7, 8):
                if (ix + iy) % 3 == 0:
                    x, y = ix * self.GRID + 22, iy * self.GRID + 22
                    trunk = cylinder_z(self.root, "urban-tree-trunk", 0.28, 3.4,
                                       (0.24, 0.16, 0.10, 1), 9)
                    trunk.setPos(x, y, 1.7)
                    crown = cylinder_z(self.root, "urban-tree-crown", 2.1, 4.6,
                                       (0.10, 0.22, 0.13, 1), 10)
                    crown.setPos(x, y, 5.0)

    def _build_district_landmarks(self) -> None:
        # Rail/warehouse yard in the industrial quarter.
        for i in range(7):
            x = 600 + i * 24
            box(self.root, "warehouse-loading-bay", (x, -620, 5.5),
                (20, 52, 11), (0.31, 0.34, 0.34, 1))
            box(self.root, "warehouse-roof", (x, -620, 11.3),
                (21, 53, 0.7), (0.17, 0.20, 0.21, 1))
        # Large central plaza with a fountain and low surrounding walls.
        box(self.root, "central-plaza-paving", (0, 0, 0.10),
            (66, 66, 0.18), (0.39, 0.40, 0.38, 1))
        cylinder_z(self.root, "plaza-fountain-basin", 9.0, 0.8,
                   (0.42, 0.45, 0.45, 1), 32).setPos(0, 0, 0.55)
        cylinder_z(self.root, "plaza-fountain-core", 1.2, 3.2,
                   (0.56, 0.61, 0.62, 1), 20).setPos(0, 0, 2.3)

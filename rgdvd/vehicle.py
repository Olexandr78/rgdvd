"""Procedural vehicle models for RGDVD."""
from __future__ import annotations

from panda3d.core import Material, NodePath, TransparencyAttrib, Vec4

from .geometry import box, cylinder_x, make_car_body, make_glass


class SportsCar:
    def __init__(self, parent: NodePath,
                 paint: tuple[float, float, float, float] = (0.64, 0.018, 0.012, 1.0)) -> None:
        self.paint_color = paint
        self.root = parent.attachNewNode("player-car")
        self.wheels: list[NodePath] = []
        self.front_wheel_pivots: list[NodePath] = []
        self._build_body()
        self._build_wheels()
        self._build_lights_and_details()

    def _paint(self, node: NodePath, name: str, roughness: float = 0.24) -> None:
        material = Material(name)
        material.setShininess((1.0 - roughness) * 110.0)
        material.setSpecular(Vec4(0.72, 0.72, 0.76, 1.0))
        node.setMaterial(material, 1)

    def _build_body(self) -> None:
        body = make_car_body(self.root, "sculpted-body", self.paint_color)
        self._paint(body, "metallic-clearcoat", 0.15)
        for side in (-1, 1):
            box(self.root, "side-skirt", (side*0.91, -0.05, 0.48),
                (0.15, 2.55, 0.22), (0.055, 0.06, 0.07, 1))
            box(self.root, "front-air-intake", (side*0.48, 2.12, 0.72),
                (0.60, 0.12, 0.22), (0.025, 0.03, 0.035, 1))
            box(self.root, "side-vent", (side*0.985, 0.95, 0.98),
                (0.025, 0.55, 0.13), (0.025, 0.028, 0.032, 1))
        cabin = box(self.root, "cabin-underframe", (0, -0.02, 1.57),
                    (1.38, 2.02, 0.64), (0.045, 0.055, 0.065, 1))
        cabin.setColorScale(0.72, 0.75, 0.8, 1)
        roof = box(self.root, "roof-panel", (0, -0.10, 2.08),
                   (1.18, 1.22, 0.12), self.paint_color)
        self._paint(roof, "roof-paint", 0.18)
        glass_color = (0.11, 0.20, 0.25, 0.88)
        glass_parts = [
            make_glass(self.root, "front-windshield", [
                (-0.58, 0.86, 1.48), (0.58, 0.86, 1.48),
                (0.50, 0.48, 2.00), (-0.50, 0.48, 2.00)], glass_color),
            make_glass(self.root, "rear-glass", [
                (-0.50, -0.72, 2.00), (0.50, -0.72, 2.00),
                (0.61, -1.12, 1.48), (-0.61, -1.12, 1.48)], glass_color),
        ]
        for glass in glass_parts:
            glass.setTransparency(TransparencyAttrib.MAlpha)
            glass.setDepthWrite(False)
        for side in (-1, 1):
            side_glass = make_glass(self.root, "side-window", [
                (side*0.70, -0.88, 1.56), (side*0.70, 0.69, 1.56),
                (side*0.56, 0.43, 1.98), (side*0.56, -0.67, 1.98)],
                (0.10, 0.17, 0.21, 0.82))
            side_glass.setTransparency(TransparencyAttrib.MAlpha)
            side_glass.setDepthWrite(False)
            box(self.root, "door-handle", (side*0.985, -0.28, 1.02),
                (0.035, 0.28, 0.055), (0.50, 0.52, 0.55, 1))
        box(self.root, "front-grille", (0, 2.13, 0.82),
            (1.28, 0.08, 0.24), (0.018, 0.022, 0.026, 1))
        box(self.root, "front-splitter", (0, 2.24, 0.43),
            (1.92, 0.40, 0.08), (0.025, 0.028, 0.032, 1))
        box(self.root, "rear-diffuser", (0, -2.17, 0.48),
            (1.72, 0.30, 0.18), (0.025, 0.028, 0.032, 1))
        for side in (-1, 1):
            cylinder_x(self.root, "exhaust-tip", 0.075, 0.11,
                       (0.42, 0.44, 0.46, 1), 16).setPos(side*0.57, -2.20, 0.56)
            box(self.root, "wing-support", (side*0.55, -1.88, 1.45),
                (0.07, 0.10, 0.72), (0.045, 0.05, 0.055, 1))
        spoiler = box(self.root, "rear-wing", (0, -1.91, 1.84),
                      (2.08, 0.48, 0.09), (0.035, 0.04, 0.045, 1))
        self._paint(spoiler, "carbon-wing", 0.35)
        for side in (-1, 1):
            box(self.root, "mirror-arm", (side*0.82, 0.70, 1.53),
                (0.28, 0.07, 0.06), (0.06, 0.06, 0.07, 1))
            mirror = box(self.root, "mirror-housing", (side*0.96, 0.71, 1.57),
                         (0.24, 0.28, 0.18), self.paint_color)
            self._paint(mirror, "mirror-paint", 0.18)

    def _build_wheels(self) -> None:
        for x in (-1.00, 1.00):
            for y in (-1.43, 1.43):
                pivot = self.root.attachNewNode("front-wheel-steer" if y > 0 else "rear-wheel")
                pivot.setPos(x, y, 0.52)
                if y > 0:
                    self.front_wheel_pivots.append(pivot)
                cylinder_x(pivot, "performance-road-tyre", 0.455, 0.34,
                           (0.018, 0.020, 0.022, 1), 32)
                cylinder_x(pivot, "tyre-sidewall", 0.365, 0.355,
                           (0.035, 0.037, 0.039, 1), 32)
                rim = cylinder_x(pivot, "alloy-rim", 0.315, 0.365,
                                 (0.42, 0.45, 0.49, 1), 32)
                self._paint(rim, "machined-alloy", 0.25)
                cylinder_x(pivot, "wheel-hub", 0.105, 0.39,
                           (0.12, 0.13, 0.15, 1), 24)
                for face in (-1, 1):
                    for spoke_index in range(6):
                        spoke = box(pivot, "alloy-spoke", (face*0.19, 0, 0),
                                    (0.035, 0.275, 0.055),
                                    (0.63, 0.66, 0.70, 1))
                        spoke.setP(spoke_index * 60)
                rotor = cylinder_x(pivot, "brake-disc", 0.255, 0.045,
                                   (0.20, 0.21, 0.22, 1), 32)
                rotor.setPos(-0.08 if x > 0 else 0.08, 0, 0)
                box(pivot, "brake-caliper", (0.10 if x > 0 else -0.10,
                    0.19, 0.035), (0.13, 0.22, 0.28), (0.68, 0.045, 0.025, 1))
                self.wheels.append(pivot)

    def _build_lights_and_details(self) -> None:
        for side in (-1, 1):
            headlight = box(self.root, "LED-headlight", (side*0.57, 2.08, 1.06),
                            (0.54, 0.11, 0.19), (0.84, 0.91, 1.0, 1))
            headlight.setLightOff(1)
            headlight.setColorScale(1.25, 1.25, 1.35, 1)
            tail = box(self.root, "LED-tail-light", (side*0.61, -2.12, 1.02),
                       (0.54, 0.12, 0.16), (0.80, 0.012, 0.008, 1))
            tail.setLightOff(1)
            tail.setColorScale(1.3, 0.45, 0.4, 1)
            signal = box(self.root, "side-marker", (side*0.94, 1.35, 0.91),
                         (0.035, 0.20, 0.075), (0.95, 0.38, 0.02, 1))
            signal.setLightOff(1)
        box(self.root, "number-plate", (0, 2.245, 0.66),
            (0.56, 0.035, 0.13), (0.80, 0.82, 0.77, 1))

    def update(self, x: float, y: float, heading: float, speed_mps: float,
               steer_angle: float, dt: float) -> None:
        self.root.setPos(x, y, 0.03)
        self.root.setH(heading * 57.2957795131)
        spin = -speed_mps * dt / 0.455 * 57.2957795131
        for wheel in self.wheels:
            wheel.setP(wheel.getP() + spin)
        for wheel in self.front_wheel_pivots:
            wheel.setH(steer_angle * 57.2957795131)

    def reset_pose(self, x: float = 0.0, y: float = -120.0,
                   heading: float = 0.0) -> None:
        self.root.setPos(x, y, 0.03)
        self.root.setH(heading * 57.2957795131)
        for wheel in self.wheels:
            wheel.setP(0)
            wheel.setH(0)


class VolgaCar(SportsCar):
    """A boxy, period-correct Volga GAZ-24-10 silhouette made from primitives."""

    def _build_body(self) -> None:
        body_color = self.paint_color
        body = box(self.root, "Volga-four-door-sedan-body", (0, 0, 0.93),
                   (1.86, 4.62, 0.62), body_color)
        self._paint(body, "Volga-enamel", 0.22)
        hood = box(self.root, "Volga-long-bonnet", (0, 1.48, 1.20),
                   (1.78, 1.40, 0.22), body_color)
        trunk = box(self.root, "Volga-trunk", (0, -1.62, 1.20),
                    (1.78, 1.02, 0.22), body_color)
        self._paint(hood, "Volga-bonnet-paint", 0.22)
        self._paint(trunk, "Volga-trunk-paint", 0.22)
        # Open cabin glazing: do not place an opaque cuboid behind the windows.
        # The roof is supported by separate A/B/C pillars, like a real sedan.
        roof = box(self.root, "Volga-flat-roof", (0, -0.02, 2.12),
                   (1.55, 1.62, 0.12), body_color)
        self._paint(roof, "Volga-roof-paint", 0.2)
        glass_color = (0.045, 0.095, 0.12, 0.94)
        windows = [
            make_glass(self.root, "Volga-windscreen", [
                (-0.70, 0.80, 1.60), (0.70, 0.80, 1.60),
                (0.68, 0.48, 2.05), (-0.68, 0.48, 2.05)], glass_color),
            make_glass(self.root, "Volga-rear-window", [
                (-0.68, -0.48, 2.05), (0.68, -0.48, 2.05),
                (0.70, -0.83, 1.60), (-0.70, -0.83, 1.60)], glass_color),
        ]
        # Slim painted pillars frame the glass instead of hiding it.
        for side in (-1, 1):
            for y, z0, z1 in ((0.49, 1.58, 2.08), (-0.02, 1.58, 2.08),
                              (-0.82, 1.58, 2.08)):
                pillar = box(self.root, "Volga-window-pillar",
                             (side * (0.73 if z1 > 2 else 0.78), y,
                              (z0 + z1) / 2),
                             (0.085, 0.09, z1 - z0), body_color)
                self._paint(pillar, "Volga-pillar-paint", 0.22)
        for glass in windows:
            glass.setTransparency(TransparencyAttrib.MAlpha)
            glass.setDepthWrite(False)
        for side in (-1, 1):
            for y in (-0.55, 0.48):
                pane = make_glass(self.root, "Volga-side-window", [
                    (side*0.82, y-0.44, 1.70), (side*0.82, y+0.44, 1.70),
                    (side*0.82, y+0.34, 2.04), (side*0.82, y-0.34, 2.04)],
                    glass_color)
                pane.setTransparency(TransparencyAttrib.MAlpha)
                pane.setDepthWrite(False)
            for y in (-0.95, 0.05):
                box(self.root, "Volga-door-handle", (side*0.94, y, 1.20),
                    (0.035, 0.25, 0.06), (0.72, 0.72, 0.68, 1))
            box(self.root, "Volga-chrome-side-trim", (side*0.94, 0, 0.94),
                (0.035, 3.55, 0.045), (0.68, 0.69, 0.66, 1))
            box(self.root, "Volga-side-mirror", (side*0.92, 0.78, 1.55),
                (0.16, 0.25, 0.18), (0.65, 0.66, 0.64, 1))
        box(self.root, "Volga-front-grille", (0, 2.32, 1.03),
            (0.90, 0.06, 0.32), (0.72, 0.73, 0.70, 1))
        for side in (-1, 1):
            lamp = box(self.root, "Volga-round-headlamp", (side*0.62, 2.33, 1.16),
                       (0.34, 0.07, 0.34), (0.91, 0.94, 0.96, 1))
            lamp.setLightOff(1)
            box(self.root, "Volga-front-indicator", (side*0.84, 2.30, 0.96),
                (0.12, 0.07, 0.12), (1.0, 0.48, 0.04, 1))
            box(self.root, "Volga-tail-lamp", (side*0.69, -2.34, 1.15),
                (0.30, 0.07, 0.35), (0.72, 0.025, 0.015, 1))
        for y in (-2.35, 2.36):
            bumper = box(self.root, "Volga-chrome-bumper", (0, y, 0.76),
                         (2.00, 0.18, 0.16), (0.70, 0.72, 0.72, 1))
            self._paint(bumper, "Volga-chrome", 0.12)
        box(self.root, "Volga-number-plate", (0, 2.405, 0.88),
            (0.48, 0.025, 0.12), (0.86, 0.87, 0.83, 1))

    def _build_wheels(self) -> None:
        for x in (-0.98, 0.98):
            for y in (-1.48, 1.48):
                pivot = self.root.attachNewNode("Volga-wheel")
                pivot.setPos(x, y, 0.52)
                if y > 0:
                    self.front_wheel_pivots.append(pivot)
                cylinder_x(pivot, "Volga-black-tyre", 0.43, 0.27,
                           (0.025, 0.027, 0.029, 1), 28)
                cylinder_x(pivot, "Volga-steel-wheel", 0.29, 0.29,
                           (0.56, 0.58, 0.57, 1), 24)
                cylinder_x(pivot, "Volga-hubcap", 0.13, 0.31,
                           (0.78, 0.79, 0.76, 1), 20)
                self.wheels.append(pivot)

    def _build_lights_and_details(self) -> None:
        # The Volga's round headlamps and chrome bumpers are built in its body.
        return

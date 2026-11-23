"""Lightweight racing-line AI for the first circuit test."""
from __future__ import annotations

import math

from panda3d.core import NodePath

from .physics import Controls, VehiclePhysics
from .track import RacingCircuit
from .vehicle import SportsCar


class AIDriver:
    """A simple closed-loop driver that follows the circuit centre line."""
    def __init__(self, parent: NodePath, track: RacingCircuit, start_angle: float,
                 paint: tuple[float, float, float, float], label: str) -> None:
        self.track = track
        rx, ry = track.CENTER_RX, track.CENTER_RY
        x = rx * math.cos(start_angle)
        y = ry * math.sin(start_angle)
        tangent_x = -rx * math.sin(start_angle)
        tangent_y = ry * math.cos(start_angle)
        heading = math.atan2(-tangent_x, tangent_y)
        self.physics = VehiclePhysics(x=x, y=y, heading=heading)
        self.car = SportsCar(parent, paint=paint)
        self.label = label
        self.car.update(x, y, heading, 0.0, 0.0, 0.0)

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    def update(self, dt: float) -> None:
        p = self.physics
        rx, ry = self.track.CENTER_RX, self.track.CENTER_RY
        theta = math.atan2(p.y / ry, p.x / rx)
        lookahead = 0.16 + min(0.16, abs(p.speed) * 0.004)
        target_theta = theta + lookahead
        target_x = rx * math.cos(target_theta)
        target_y = ry * math.sin(target_theta)

        dx, dy = target_x - p.x, target_y - p.y
        desired_heading = math.atan2(-dx, dy)
        heading_error = self._wrap_angle(desired_heading - p.heading)
        steer = max(-1.0, min(1.0, heading_error * 2.6))

        sin_t, cos_t = math.sin(theta), math.cos(theta)
        denominator = (rx*rx*sin_t*sin_t + ry*ry*cos_t*cos_t) ** 1.5
        curvature = (rx * ry) / max(1.0, denominator)
        target_speed = min(39.0, math.sqrt(7.2 / max(curvature, 0.0001)))
        if abs(heading_error) > 0.55:
            target_speed *= 0.72
        error_speed = target_speed - abs(p.speed)
        throttle = 1.0 if error_speed > 2.0 else (0.35 if error_speed > 0 else 0.0)
        brake = 0.75 if error_speed < -4.0 else 0.0

        p.on_track = self.track.contains(p.x, p.y)
        p.update(Controls(throttle=throttle, brake=brake, steer=steer), dt)
        self.car.update(p.x, p.y, p.heading, p.speed, p.steer_angle, dt)

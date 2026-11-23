"""Deterministic, dependency-free vehicle dynamics for RGDVD.

This is a tunable single-car model, not a full tyre/engine simulation. It uses
engine torque and gearing for longitudinal force and a bicycle model for yaw.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class Controls:
    throttle: float = 0.0       # 0..1
    brake: float = 0.0          # 0..1
    steer: float = 0.0          # -1..1 (negative = right, positive = left)
    handbrake: bool = False


class VehiclePhysics:
    MASS_KG = 1480.0
    WHEEL_RADIUS_M = 0.337
    WHEELBASE_M = 2.72
    FINAL_DRIVE = 3.42
    GEAR_RATIOS = (3.15, 2.18, 1.62, 1.27, 1.00, 0.82)
    IDLE_RPM = 850.0
    REDLINE_RPM = 7600.0
    MAX_FORWARD_MPS = 78.0
    MAX_REVERSE_MPS = 11.0

    def __init__(self, x: float = 0.0, y: float = -148.0,
                 heading: float = -math.pi / 2,
                 car_id: str = "street_gt") -> None:
        from .cars import get_car_spec
        spec = get_car_spec(car_id)
        self.car_id = car_id if car_id in __import__("rgdvd.cars", fromlist=["CAR_SPECS"]).CAR_SPECS else "street_gt"
        self.MASS_KG = float(spec["mass_kg"])
        self.MAX_FORWARD_MPS = float(spec["max_speed_mps"])
        self.TORQUE_MULTIPLIER = float(spec["torque_multiplier"])
        self.GRIP_MULTIPLIER = float(spec["grip_multiplier"])
        self.x = x
        self.y = y
        self.heading = heading
        self.speed = 0.0
        self.lateral_speed = 0.0
        self.yaw_rate = 0.0
        self.steer_angle = 0.0
        self.gear = 1
        self.rpm = self.IDLE_RPM
        self.throttle = 0.0
        self.brake = 0.0
        self.handbrake = False
        self.on_track = True
        self.distance_m = 0.0

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _lerp(current: float, target: float, amount: float) -> float:
        return current + (target - current) * min(1.0, max(0.0, amount))

    def _torque_nm(self, rpm: float) -> float:
        """Approximate naturally aspirated performance-engine torque curve."""
        points = ((850, 250), (1800, 335), (3200, 390),
                  (4800, 410), (6100, 385), (7600, 315))
        if rpm <= points[0][0]:
            return points[0][1] * self.TORQUE_MULTIPLIER
        for (r0, t0), (r1, t1) in zip(points, points[1:]):
            if rpm <= r1:
                torque = t0 + (t1 - t0) * ((rpm - r0) / (r1 - r0))
                return torque * self.TORQUE_MULTIPLIER
        return points[-1][1] * self.TORQUE_MULTIPLIER

    def _calculate_rpm(self) -> float:
        if abs(self.speed) < 1.0:
            return self.IDLE_RPM + self.throttle * 1100.0
        ratio = self.GEAR_RATIOS[self.gear - 1] * self.FINAL_DRIVE
        wheel_rpm = abs(self.speed) / (2.0 * math.pi * self.WHEEL_RADIUS_M) * 60.0
        return self._clamp(wheel_rpm * ratio, self.IDLE_RPM, self.REDLINE_RPM)

    def _shift_if_needed(self) -> None:
        self.rpm = self._calculate_rpm()
        if self.rpm > 7100.0 and self.gear < len(self.GEAR_RATIOS):
            self.gear += 1
            self.rpm = self._calculate_rpm()
        elif self.rpm < 2450.0 and self.gear > 1 and self.speed > 9.0:
            self.gear -= 1
            self.rpm = self._calculate_rpm()

    def update(self, controls: Controls, dt: float) -> None:
        dt = self._clamp(dt, 0.0, 1.0 / 30.0)
        if dt <= 0.0:
            return

        throttle = self._clamp(controls.throttle, 0.0, 1.0)
        brake = self._clamp(controls.brake, 0.0, 1.0)
        steer = self._clamp(controls.steer, -1.0, 1.0)
        handbrake = bool(controls.handbrake)
        self.throttle, self.brake, self.handbrake = throttle, brake, handbrake

        self._shift_if_needed()
        if throttle > 0.01:
            if self.speed < -0.5:
                self.speed = min(0.0, self.speed + 13.0 * dt)
            else:
                gear_ratio = self.GEAR_RATIOS[self.gear - 1] * self.FINAL_DRIVE
                torque = self._torque_nm(self.rpm)
                drive_force = torque * gear_ratio * 0.88 / self.WHEEL_RADIUS_M
                engine_accel = drive_force / self.MASS_KG * throttle
                if not self.on_track:
                    engine_accel *= 0.58
                self.speed += engine_accel * dt

        if brake > 0.0:
            if self.speed > 0.65:
                brake_deceleration = 13.5 * brake
                if handbrake:
                    brake_deceleration += 7.0 * brake
                self.speed = max(0.0, self.speed - brake_deceleration * dt)
            else:
                self.speed = max(-self.MAX_REVERSE_MPS,
                                 self.speed - 4.5 * brake * dt)

        drag = 0.20 + 0.00034 * self.speed * self.speed
        if not self.on_track:
            drag += 2.4
        if abs(self.speed) > 0.0:
            self.speed -= math.copysign(drag * dt, self.speed)
        self.speed = self._clamp(self.speed, -self.MAX_REVERSE_MPS,
                                 self.MAX_FORWARD_MPS)

        speed_abs = abs(self.speed)
        max_steer = math.radians(34.0 - 21.0 * min(1.0, speed_abs / 58.0))
        target_steer = steer * max_steer
        self.steer_angle = self._lerp(self.steer_angle, target_steer,
                                      dt * (8.0 if not handbrake else 12.0))

        grip = (0.92 if self.on_track else 0.47) * self.GRIP_MULTIPLIER
        if handbrake:
            grip *= 0.46
        self.yaw_rate = (self.speed / self.WHEELBASE_M) * math.tan(self.steer_angle)
        self.yaw_rate *= grip
        self.heading += self.yaw_rate * dt

        rightward_target = -steer * speed_abs * (0.24 if handbrake else 0.025)
        if not self.on_track:
            rightward_target *= 0.55
        side_response = 2.0 if handbrake else 7.0
        self.lateral_speed = self._lerp(self.lateral_speed, rightward_target,
                                        dt * side_response)
        if abs(steer) < 0.02 and not handbrake:
            self.lateral_speed = self._lerp(self.lateral_speed, 0.0, dt * 5.0)

        forward_x = -math.sin(self.heading)
        forward_y = math.cos(self.heading)
        right_x = math.cos(self.heading)
        right_y = math.sin(self.heading)
        dx = (forward_x * self.speed + right_x * self.lateral_speed) * dt
        dy = (forward_y * self.speed + right_y * self.lateral_speed) * dt
        self.x += dx
        self.y += dy
        self.distance_m += math.hypot(dx, dy)
        self._shift_if_needed()

    def reset(self, x: float = 0.0, y: float = -148.0,
              heading: float = -math.pi / 2) -> None:
        self.__init__(x=x, y=y, heading=heading, car_id=self.car_id)

    @property
    def speed_kmh(self) -> float:
        return abs(self.speed) * 3.6

    @property
    def steering_wheel_degrees(self) -> float:
        return math.degrees(self.steer_angle) * 14.0

    def snapshot(self) -> dict[str, float | int | bool]:
        return {
            "x": self.x, "y": self.y, "heading": self.heading,
            "speed": self.speed, "speed_kmh": self.speed_kmh,
            "gear": self.gear, "rpm": self.rpm,
            "on_track": self.on_track,
        }

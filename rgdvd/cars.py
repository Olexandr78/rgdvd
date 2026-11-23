"""Original fictional vehicle presets. No real-world brand assets included."""
from __future__ import annotations

CAR_SPECS = {
    "street_gt": {
        "name": "Street GT",
        "mass_kg": 1480.0,
        "torque_multiplier": 1.0,
        "max_speed_mps": 78.0,
        "grip_multiplier": 1.0,
        "paint": (0.64, 0.018, 0.012, 1.0),
        "required_wins": 0,
    },
    "touring_v8": {
        "name": "Touring V8",
        "mass_kg": 1560.0,
        "torque_multiplier": 1.19,
        "max_speed_mps": 84.0,
        "grip_multiplier": 0.98,
        "paint": (0.025, 0.17, 0.66, 1.0),
        "required_wins": 5,
    },
    "track_special": {
        "name": "Track Special",
        "mass_kg": 1310.0,
        "torque_multiplier": 1.08,
        "max_speed_mps": 82.0,
        "grip_multiplier": 1.13,
        "paint": (0.88, 0.55, 0.025, 1.0),
        "required_wins": 12,
    },
    "prototype_x": {
        "name": "Prototype X",
        "mass_kg": 990.0,
        "torque_multiplier": 1.34,
        "max_speed_mps": 96.0,
        "grip_multiplier": 1.08,
        "paint": (0.72, 0.75, 0.78, 1.0),
        "required_wins": 25,
    },
}


def get_car_spec(car_id: str) -> dict:
    return CAR_SPECS.get(car_id, CAR_SPECS["street_gt"])


def unlocked_cars(unlocked: list[str]) -> list[str]:
    return [car_id for car_id in CAR_SPECS if car_id in unlocked]

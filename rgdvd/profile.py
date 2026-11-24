"""Offline career progression stored locally as JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import APP_DIR


class CareerProfile:
    STARTING_CREDITS = 2500
    DEFAULT_CARS = ["street_gt", "volga_2410"]
    CAR_UNLOCKS = {
        "touring_v8": 5,
        "track_special": 12,
        "prototype_x": 25,
    }

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (APP_DIR / "career.json")
        self.data: dict[str, Any] = {
            "credits": self.STARTING_CREDITS,
            "races": 0,
            "wins": 0,
            "total_distance_km": 0.0,
            "best_lap_seconds": None,
            "unlocked_cars": self.DEFAULT_CARS.copy(),
            "history": [],
        }
        self.load()

    def load(self) -> None:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                self.data.update(stored)
        except (OSError, ValueError, TypeError):
            pass
        self._validate()

    def _validate(self) -> None:
        self.data["credits"] = max(0, int(self.data.get("credits", 0)))
        self.data["races"] = max(0, int(self.data.get("races", 0)))
        self.data["wins"] = max(0, int(self.data.get("wins", 0)))
        self.data["total_distance_km"] = max(
            0.0, float(self.data.get("total_distance_km", 0.0)))
        unlocked = self.data.get("unlocked_cars", self.DEFAULT_CARS)
        if not isinstance(unlocked, list):
            unlocked = self.DEFAULT_CARS.copy()
        self.data["unlocked_cars"] = sorted(set(self.DEFAULT_CARS + [
            str(item) for item in unlocked
        ]))
        history = self.data.get("history", [])
        self.data["history"] = history[-50:] if isinstance(history, list) else []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2),
                             encoding="utf-8")
        temporary.replace(self.path)

    @property
    def credits(self) -> int:
        return int(self.data["credits"])

    def is_unlocked(self, car_id: str) -> bool:
        return car_id in self.data["unlocked_cars"]

    def record_race(self, duration_seconds: float, distance_km: float,
                    position: int, best_lap_seconds: float | None = None) -> dict[str, Any]:
        duration_seconds = max(0.0, float(duration_seconds))
        distance_km = max(0.0, float(distance_km))
        position = max(1, int(position))
        payout = {1: 1800, 2: 1200, 3: 800}.get(position, 350)
        payout += min(500, int(distance_km * 3))
        self.data["credits"] += payout
        self.data["races"] += 1
        if position == 1:
            self.data["wins"] += 1
        self.data["total_distance_km"] += distance_km
        old_best = self.data.get("best_lap_seconds")
        if best_lap_seconds and best_lap_seconds > 0:
            if old_best is None or best_lap_seconds < float(old_best):
                self.data["best_lap_seconds"] = float(best_lap_seconds)

        unlocked_now = []
        for car_id, required_wins in self.CAR_UNLOCKS.items():
            if self.data["wins"] >= required_wins and not self.is_unlocked(car_id):
                self.data["unlocked_cars"].append(car_id)
                unlocked_now.append(car_id)
        entry = {
            "duration_seconds": round(duration_seconds, 2),
            "distance_km": round(distance_km, 3),
            "position": position,
            "payout": payout,
            "wins_total": self.data["wins"],
        }
        self.data["history"].append(entry)
        self.data["history"] = self.data["history"][-50:]
        self.save()
        return {"payout": payout, "unlocked": unlocked_now, "entry": entry}

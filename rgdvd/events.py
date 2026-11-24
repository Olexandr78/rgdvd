"""Original city event catalogue and deterministic routes for RGDVD.

The catalogue contains 24 circuit events and 29 point-to-point sprints (53 total).
Routes use the existing city's 120-unit road grid; the city itself is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class RaceEvent:
    event_id: str
    name: str
    event_type: str
    route: tuple[tuple[float, float], ...]
    laps: int = 1

    @property
    def start(self) -> tuple[float, float]:
        return self.route[0]


_DISTRICTS = ("DOWNTOWN", "RIVERSIDE", "OLD QUARTER", "INDUSTRIAL",
              "NORTH AVENUE", "SOUTH LOOP")


def _circuit(index: int) -> RaceEvent:
    column = index % 6
    row = index // 6
    x0 = -600.0 + column * 120.0
    y0 = -480.0 + row * 240.0
    width = (2 + index % 3) * 120.0
    height = (2 + (index // 2) % 3) * 120.0
    x1 = min(840.0, x0 + width)
    y1 = min(840.0, y0 + height)
    if x1 <= x0:
        x0, x1 = x1 - 240.0, x1
    if y1 <= y0:
        y0, y1 = y1 - 240.0, y1
    route = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    return RaceEvent(
        f"CIR-{index + 1:02d}",
        f"{_DISTRICTS[index % len(_DISTRICTS)]} CIRCUIT {index + 1:02d}",
        "CIRCUIT", route, 2,
    )


def _sprint(index: int) -> RaceEvent:
    rng = random.Random(7300 + index)
    x = float(((index * 5) % 13 - 6) * 120)
    y = float(((index * 7) % 13 - 6) * 120)
    route = [(x, y)]
    directions = ((120.0, 0.0), (-120.0, 0.0),
                  (0.0, 120.0), (0.0, -120.0))
    previous = None
    for _ in range(6 + index % 3):
        options = []
        for direction in directions:
            if previous and direction == (-previous[0], -previous[1]):
                continue
            nx, ny = x + direction[0], y + direction[1]
            if abs(nx) <= 840 and abs(ny) <= 840:
                options.append(direction)
        if not options:
            options = list(directions)
        direction = rng.choice(options)
        x += direction[0]
        y += direction[1]
        previous = direction
        route.append((x, y))
    return RaceEvent(
        f"SPR-{index + 1:02d}",
        f"{_DISTRICTS[index % len(_DISTRICTS)]} SPRINT {index + 1:02d}",
        "SPRINT", tuple(route), 1,
    )


EVENTS: tuple[RaceEvent, ...] = tuple(
    [_circuit(i) for i in range(24)] +
    [_sprint(i) for i in range(29)]
)
EVENT_BY_ID = {event.event_id: event for event in EVENTS}

"""RGDVD room server for Render or any ASGI host.

This small relay server forwards player states. It is not an authoritative
anti-cheat physics server; competitive ranked play will need server simulation.
Rooms are in-memory and are reset when the service restarts.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse


app = FastAPI(title="RGDVD Online", version="0.1.0")
MAX_PLAYERS = int(os.getenv("RGDVD_MAX_PLAYERS", "16"))
ROOMS: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
LOCKS: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "RGDVD Online", "status": "ok", "protocol": "rgdvd-ws-1"}


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "rooms": len(ROOMS)})


def _room_snapshot(room: str) -> list[dict[str, Any]]:
    result = []
    for player_id, player in ROOMS[room].items():
        result.append({
            "id": player_id,
            "name": player["name"],
            "state": player["state"],
        })
    return result


async def _broadcast(room: str, packet: dict[str, Any]) -> None:
    dead = []
    for player_id, player in list(ROOMS[room].items()):
        ws = player["socket"]
        try:
            await ws.send_json(packet)
        except Exception:
            dead.append(player_id)
    for player_id in dead:
        ROOMS[room].pop(player_id, None)


@app.websocket("/ws/{room}")
async def multiplayer_room(websocket: WebSocket, room: str) -> None:
    room = "".join(ch for ch in room.upper() if ch.isalnum() or ch in "-_")[:32]
    room = room or "OPEN-LOBBY"
    name = (websocket.query_params.get("name") or "Driver")[:20]
    player_id = uuid.uuid4().hex[:12]

    async with LOCKS[room]:
        if len(ROOMS[room]) >= MAX_PLAYERS:
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": "Room is full"})
            await websocket.close(code=1013)
            return
        await websocket.accept()
        ROOMS[room][player_id] = {
            "socket": websocket,
            "name": name,
            "state": {"x": 0.0, "y": -148.0, "heading": -1.5708, "speed": 0.0},
            "last_seen": time.monotonic(),
        }
        await websocket.send_json({
            "type": "welcome", "id": player_id,
            "room": room, "max_players": MAX_PLAYERS,
        })
        await _broadcast(room, {"type": "players", "players": _room_snapshot(room)})

    try:
        while True:
            packet = await websocket.receive_json()
            if not isinstance(packet, dict):
                continue
            if packet.get("type") == "state":
                state = packet.get("state", {})
                if not isinstance(state, dict):
                    continue
                clean = {}
                for key in ("x", "y", "heading", "speed"):
                    try:
                        value = float(state.get(key, 0.0))
                    except (TypeError, ValueError):
                        value = 0.0
                    if not (-100000.0 < value < 100000.0):
                        value = 0.0
                    clean[key] = value
                async with LOCKS[room]:
                    player = ROOMS[room].get(player_id)
                    if player:
                        player["state"] = clean
                        player["last_seen"] = time.monotonic()
                        await _broadcast(room, {
                            "type": "state", "players": _room_snapshot(room),
                        })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with LOCKS[room]:
            ROOMS[room].pop(player_id, None)
            await _broadcast(room, {"type": "players", "players": _room_snapshot(room)})
            if not ROOMS[room]:
                ROOMS.pop(room, None)
                LOCKS.pop(room, None)

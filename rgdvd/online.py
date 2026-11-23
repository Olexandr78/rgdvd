"""Optional online multiplayer transport for the Render WebSocket service."""
from __future__ import annotations

import json
import threading
from typing import Any
from urllib.parse import quote

try:
    import websocket
except ImportError:  # offline-only install remains usable
    websocket = None


class OnlineSession:
    def __init__(self, base_url: str, room: str, nickname: str) -> None:
        if websocket is None:
            raise RuntimeError(
                "Online mode needs websocket-client. Run: "
                "python -m pip install websocket-client"
            )
        self.base_url = base_url.strip().rstrip("/")
        if self.base_url.startswith("https://"):
            self.ws_url = "wss://" + self.base_url[8:]
        elif self.base_url.startswith("http://"):
            self.ws_url = "ws://" + self.base_url[7:]
        elif self.base_url.startswith(("ws://", "wss://")):
            self.ws_url = self.base_url
        else:
            self.ws_url = "wss://" + self.base_url
        self.room = quote(room.strip()[:32] or "OPEN-LOBBY", safe="")
        self.nickname = quote(nickname.strip()[:20] or "Driver", safe="")
        self.connected = False
        self.closed = False
        self.error: str | None = None
        self.players: dict[str, dict[str, Any]] = {}
        self.player_id: str | None = None
        self._lock = threading.Lock()
        self._ws = websocket.WebSocketApp(
            f"{self.ws_url}/ws/{self.room}?name={self.nickname}",
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={"ping_interval": 20, "ping_timeout": 8},
            daemon=True, name="RGDVD-Online",
        )
        self._thread.start()

    def _on_open(self, ws: Any) -> None:
        self.connected = True

    def _on_message(self, ws: Any, message: str) -> None:
        try:
            packet = json.loads(message)
        except (ValueError, TypeError):
            return
        if packet.get("type") == "welcome":
            self.player_id = str(packet.get("id", ""))
        elif packet.get("type") == "error":
            self.error = str(packet.get("message", "Online server rejected the connection"))
            self.connected = False
        elif packet.get("type") in ("players", "state"):
            players = packet.get("players", [])
            if isinstance(players, list):
                with self._lock:
                    self.players = {
                        str(player["id"]): player for player in players
                        if isinstance(player, dict) and "id" in player
                    }

    def _on_error(self, ws: Any, error: Any) -> None:
        self.error = str(error)
        self.connected = False

    def _on_close(self, ws: Any, status: Any, message: Any) -> None:
        self.connected = False
        self.closed = True

    def send_state(self, state: dict[str, float]) -> None:
        if not self.connected or self.closed:
            return
        packet = {
            "type": "state",
            "state": {key: float(state.get(key, 0.0))
                      for key in ("x", "y", "heading", "speed")},
        }
        try:
            self._ws.send(json.dumps(packet, separators=(",", ":")))
        except Exception as exc:
            self.error = str(exc)

    def poll(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for key, value in self.players.items()
                    if key != self.player_id]

    def close(self) -> None:
        self.closed = True
        try:
            self._ws.close()
        except Exception:
            pass

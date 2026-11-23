"""LAN multiplayer transport using UDP discovery and state snapshots."""
from __future__ import annotations
import json
import socket
import threading
import time
import uuid
from typing import Any

DISCOVERY_PORT = 39770
PROTOCOL = "rgdvd-lan-1"
MAX_PACKET = 8192


def _encode(packet: dict[str, Any]) -> bytes:
    return json.dumps(packet, separators=(",", ":")).encode("utf-8")


def _decode(data: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
        if isinstance(value, dict) and value.get("protocol") == PROTOCOL:
            return value
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return None


class LanSession:
    def __init__(self, sock: socket.socket, role: str, nickname: str,
                 room: str, peer: tuple[str, int] | None = None) -> None:
        self.socket, self.role = sock, role
        self.nickname, self.room, self.peer = nickname[:20], room[:20], peer
        self.player_id = uuid.uuid4().hex[:10]
        self.connected = role == "host"
        self.closed = False
        self.error: str | None = None
        self.local_state = {"x": 0.0, "y": -148.0, "heading": -1.5708, "speed": 0.0}
        self.players: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._last_snapshot = self._last_send = 0.0
        self._thread = threading.Thread(target=self._worker, name="RGDVD-LAN", daemon=True)
        self._thread.start()

    @classmethod
    def host(cls, nickname: str, room: str = "RGDVD") -> "LanSession":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(0.05)
        session = cls(sock, "host", nickname, room)
        session.players[session.player_id] = {
            "id": session.player_id, "name": session.nickname,
            "state": session.local_state, "host": True,
        }
        return session

    @staticmethod
    def discover(timeout: float = 1.1) -> list[dict[str, Any]]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.12)
        found: dict[str, dict[str, Any]] = {}
        try:
            sock.bind(("", 0))
            sock.sendto(_encode({"protocol": PROTOCOL, "kind": "discover"}),
                        ("255.255.255.255", DISCOVERY_PORT))
            deadline = time.monotonic() + max(0.2, timeout)
            while time.monotonic() < deadline:
                try:
                    data, address = sock.recvfrom(MAX_PACKET)
                except socket.timeout:
                    continue
                packet = _decode(data)
                if packet and packet.get("kind") == "offer":
                    found[address[0]] = {
                        "host": str(packet.get("host", "LAN host")),
                        "room": str(packet.get("room", "RGDVD")),
                        "players": int(packet.get("players", 1)),
                        "address": address[0],
                    }
        finally:
            sock.close()
        return list(found.values())

    @classmethod
    def join(cls, address: str, nickname: str, timeout: float = 2.0) -> "LanSession":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.05)
        session = cls(sock, "client", nickname, "RGDVD", (address, DISCOVERY_PORT))
        sock.sendto(_encode({
            "protocol": PROTOCOL, "kind": "join",
            "id": session.player_id, "name": session.nickname,
        }), session.peer)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not session.connected:
            time.sleep(0.03)
        if not session.connected:
            session.close()
            raise TimeoutError(f"LAN host {address} did not answer")
        return session

    def send_state(self, state: dict[str, float]) -> None:
        current = {key: float(state.get(key, 0.0))
                   for key in ("x", "y", "heading", "speed")}
        with self._lock:
            self.local_state = current
            if self.role == "host" and self.player_id in self.players:
                self.players[self.player_id]["state"] = current
        now = time.monotonic()
        if self.role == "client" and self.peer and now - self._last_send >= 1/15:
            self._last_send = now
            try:
                self.socket.sendto(_encode({
                    "protocol": PROTOCOL, "kind": "state",
                    "id": self.player_id, "name": self.nickname, "state": current,
                }), self.peer)
            except OSError as exc:
                self.error = str(exc)

    def poll(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for key, value in self.players.items()
                    if key != self.player_id]

    def _worker(self) -> None:
        while not self.closed:
            now = time.monotonic()
            if self.role == "host" and now - self._last_snapshot >= 1/15:
                self._last_snapshot = now
                self._broadcast_snapshot()
            try:
                data, address = self.socket.recvfrom(MAX_PACKET)
            except socket.timeout:
                self._expire_players(now)
                continue
            except OSError:
                break
            packet = _decode(data)
            if not packet:
                continue
            kind = packet.get("kind")
            if self.role == "host":
                self._handle_host_packet(kind, packet, address, now)
            elif kind == "welcome":
                self.connected = True
                self.room = str(packet.get("room", self.room))
                self.peer = address
            elif kind == "snapshot":
                incoming = packet.get("players", [])
                if isinstance(incoming, list):
                    with self._lock:
                        self.players = {
                            str(item["id"]): item for item in incoming
                            if isinstance(item, dict) and "id" in item
                        }

    def _handle_host_packet(self, kind: Any, packet: dict[str, Any],
                            address: tuple[str, int], now: float) -> None:
        if kind == "discover":
            self.socket.sendto(_encode({
                "protocol": PROTOCOL, "kind": "offer",
                "host": self.nickname, "room": self.room, "players": len(self.players),
            }), address)
        elif kind == "join":
            player_id = str(packet.get("id", ""))[:20]
            if not player_id:
                return
            with self._lock:
                self.players[player_id] = {
                    "id": player_id, "name": str(packet.get("name", "Driver"))[:20],
                    "state": {"x": 0.0, "y": -148.0, "heading": -1.5708, "speed": 0.0},
                    "last_seen": now, "address": address,
                }
            self.socket.sendto(_encode({
                "protocol": PROTOCOL, "kind": "welcome", "room": self.room,
            }), address)
        elif kind == "state":
            player_id, state = str(packet.get("id", ""))[:20], packet.get("state", {})
            if not isinstance(state, dict):
                return
            with self._lock:
                player = self.players.get(player_id)
                if player and player.get("address") == address:
                    player["name"] = str(packet.get("name", player["name"]))[:20]
                    player["state"] = {
                        key: float(state.get(key, 0.0))
                        for key in ("x", "y", "heading", "speed")
                    }
                    player["last_seen"] = now

    def _broadcast_snapshot(self) -> None:
        with self._lock:
            snapshot = [
                {"id": pid, "name": p["name"], "state": p["state"]}
                for pid, p in self.players.items()
            ]
            addresses = [p["address"] for p in self.players.values() if p.get("address")]
        packet = _encode({"protocol": PROTOCOL, "kind": "snapshot", "players": snapshot})
        for address in addresses:
            try:
                self.socket.sendto(packet, address)
            except OSError:
                pass

    def _expire_players(self, now: float) -> None:
        if self.role != "host":
            return
        with self._lock:
            stale = [pid for pid, p in self.players.items()
                     if pid != self.player_id and now - p.get("last_seen", now) > 8.0]
            for pid in stale:
                self.players.pop(pid, None)

    def close(self) -> None:
        self.closed = True
        try:
            self.socket.close()
        except OSError:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=0.3)

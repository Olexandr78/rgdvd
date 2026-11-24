"""Local configuration storage. No telemetry and no cloud dependency."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "RGDVD"
CONFIG_PATH = APP_DIR / "settings.json"
DEFAULT_SERVER_URL = "https://rgdvd.onrender.com"
OLD_SERVER_URLS = {
    "wss://rgdvd-online.onrender.com",
    "https://rgdvd-online.onrender.com",
}

DEFAULTS: dict[str, Any] = {
    "nickname": "Driver",
    "room": "OPEN-LOBBY",
    "server_url": DEFAULT_SERVER_URL,
    "quality": "medium",
    "car_id": "street_gt",
    "controller_preset": "auto",
    "wheel_deadzone": 0.04,
    "wheel_invert_steering": False,
    "wheel_invert_pedals": False,
    "wheel_handbrake_button": 11,
    "shadows": True,
    "vsync": True,
    "width": 1366,
    "height": 768,
}


def load_config() -> dict[str, Any]:
    config = DEFAULTS.copy()
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config.update({key: value for key, value in loaded.items()
                           if key in DEFAULTS})
    except (OSError, ValueError, TypeError):
        pass

    # Migrate installations that still contain the previous placeholder URL.
    if str(config.get("server_url", "")).strip().rstrip("/") in OLD_SERVER_URLS:
        config["server_url"] = DEFAULT_SERVER_URL
    return config


def save_config(config: dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = DEFAULTS.copy()
    cleaned.update({key: value for key, value in config.items()
                    if key in DEFAULTS})
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    temporary.replace(CONFIG_PATH)

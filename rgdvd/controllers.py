"""Steering wheel and gamepad input profiles for RGDVD."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from panda3d.core import InputDevice


PRESETS = ("auto", "esperanza_nitro_egw102", "generic")
PRESET_LABELS = {
    "auto": "AUTO DETECT",
    "esperanza_nitro_egw102": "ESPERANZA NITRO EGW102",
    "generic": "GENERIC WHEEL",
}
AXES = {
    "x": InputDevice.Axis.x,
    "y": InputDevice.Axis.y,
    "wheel": InputDevice.Axis.wheel,
    "left_x": InputDevice.Axis.left_x,
    "left_trigger": InputDevice.Axis.left_trigger,
    "right_trigger": InputDevice.Axis.right_trigger,
    "accelerator": InputDevice.Axis.accelerator,
    "brake": InputDevice.Axis.brake,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def apply_deadzone(value: float, deadzone: float = 0.04) -> float:
    value = clamp(float(value), -1.0, 1.0)
    if abs(value) <= deadzone:
        return 0.0
    return (1.0 if value > 0 else -1.0) * (
        (abs(value) - deadzone) / (1.0 - deadzone)
    )


def detect_preset(device_name: str, requested: str = "auto") -> str:
    if requested in PRESETS and requested != "auto":
        return requested
    name = device_name.lower()
    if any(token in name for token in ("esperanza", "nitro", "egw102")):
        return "esperanza_nitro_egw102"
    return "generic"


@dataclass(slots=True)
class WheelControls:
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    handbrake: bool = False
    device_name: str = ""
    preset: str = "auto"
    connected: bool = False


class WheelInput:
    """Polls Panda3D input devices; keyboard controls remain available."""

    def __init__(self, base: Any, config: dict[str, Any] | None = None) -> None:
        self.base = base
        self.config = config if config is not None else {}
        requested = str(self.config.get("controller_preset", "auto"))
        self.requested_preset = requested if requested in PRESETS else "auto"
        self._attached: set[int] = set()
        self._device: Any | None = None
        self._device_name = ""

    def set_preset(self, preset: str) -> None:
        if preset not in PRESETS:
            raise ValueError(f"Unknown controller preset: {preset}")
        self.requested_preset = preset
        self.config["controller_preset"] = preset
        self._device = None

    @staticmethod
    def _name(device: Any) -> str:
        for attr in ("getName", "get_name"):
            method = getattr(device, attr, None)
            if callable(method):
                try:
                    return str(method())
                except Exception:
                    pass
        return str(getattr(device, "name", "Unknown controller"))

    def _devices(self) -> list[Any]:
        manager = getattr(self.base, "devices", None)
        if manager is None:
            return []
        try:
            return list(manager.getDevices())
        except Exception:
            return []

    def _select_device(self) -> Any | None:
        devices = self._devices()
        if not devices:
            self._device = None
            self._device_name = ""
            return None
        if self._device in devices:
            return self._device

        named = [(device, self._name(device)) for device in devices]
        if self.requested_preset == "esperanza_nitro_egw102":
            preferred = [item for item in named
                         if any(token in item[1].lower()
                                for token in ("esperanza", "nitro", "egw102"))]
            selected = preferred[0] if preferred else named[0]
        elif self.requested_preset == "generic":
            selected = named[0]
        else:
            preferred = [item for item in named
                         if any(token in item[1].lower()
                                for token in ("esperanza", "nitro", "egw102"))]
            selected = preferred[0] if preferred else named[0]

        self._device, self._device_name = selected
        identity = id(self._device)
        if identity not in self._attached:
            try:
                self.base.attachInputDevice(
                    self._device, prefix=f"rgdvd-controller-{len(self._attached)}")
            except Exception:
                # Polling works even when the device manager does not expose
                # event attachment on a particular Panda3D backend.
                pass
            self._attached.add(identity)
        return self._device

    @staticmethod
    def _axis(device: Any, name: str) -> float | None:
        axis_type = AXES.get(name)
        if axis_type is None:
            return None
        try:
            axis = device.findAxis(axis_type)
            if not axis:
                return None
            return float(axis.value)
        except Exception:
            return None

    def _first_axis(self, device: Any, names: tuple[str, ...]) -> float | None:
        for name in names:
            value = self._axis(device, name)
            if value is not None:
                return value
        return None

    def read(self) -> WheelControls:
        device = self._select_device()
        if device is None:
            return WheelControls()
        preset = detect_preset(self._device_name, self.requested_preset)

        if preset == "esperanza_nitro_egw102":
            steering_axes = ("x", "left_x", "wheel")
        else:
            steering_axes = ("wheel", "x", "left_x")
        raw_steer = self._first_axis(device, steering_axes)
        if raw_steer is None:
            raw_steer = 0.0
        if bool(self.config.get("wheel_invert_steering", False)):
            raw_steer = -raw_steer
        steer = -apply_deadzone(raw_steer, float(
            self.config.get("wheel_deadzone", 0.04)))

        # EGW102 DirectInput mode reports the two pedals on opposite halves
        # of Y; XInput mode exposes them as separate LT/RT triggers.
        left_trigger = self._axis(device, "left_trigger")
        right_trigger = self._axis(device, "right_trigger")
        if left_trigger is not None or right_trigger is not None:
            brake = clamp((left_trigger or 0.0), 0.0, 1.0)
            throttle = clamp((right_trigger or 0.0), 0.0, 1.0)
        else:
            accelerator = self._axis(device, "accelerator")
            brake_axis = self._axis(device, "brake")
            combined_y = self._axis(device, "y")
            if accelerator is not None or brake_axis is not None:
                throttle = clamp(accelerator or 0.0, 0.0, 1.0)
                brake = clamp(brake_axis or 0.0, 0.0, 1.0)
            elif combined_y is not None:
                if bool(self.config.get("wheel_invert_pedals", False)):
                    combined_y = -combined_y
                throttle = clamp(combined_y, 0.0, 1.0)
                brake = clamp(-combined_y, 0.0, 1.0)
            else:
                throttle = brake = 0.0

        handbrake_button = int(self.config.get("wheel_handbrake_button", 11))
        try:
            handbrake = bool(device.is_button_pressed(handbrake_button))
        except Exception:
            handbrake = False

        return WheelControls(
            throttle=throttle, brake=brake, steer=steer,
            handbrake=handbrake, device_name=self._device_name,
            preset=preset, connected=True,
        )

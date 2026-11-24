"""RGDVD - offline career, quick race, LAN and online racing client."""
from __future__ import annotations

import math
import time
from typing import Any

from direct.gui.DirectGui import DirectButton, DirectEntry, DirectFrame, DirectLabel
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, AntialiasAttrib, DirectionalLight, Fog,
    LineSegs, TextNode, Vec4, WindowProperties, loadPrcFileData,
)

from rgdvd import __version__
from rgdvd.cars import CAR_SPECS, get_car_spec, unlocked_cars
from rgdvd.config import APP_DIR, DEFAULT_SERVER_URL, load_config, save_config
from rgdvd.network import LanSession
from rgdvd.online import OnlineSession
from rgdvd.physics import Controls, VehiclePhysics
from rgdvd.profile import CareerProfile
from rgdvd.city import UrbanCity
from rgdvd.vehicle import SportsCar, VolgaCar
from rgdvd.audio import VehicleAudio
from rgdvd.events import EVENT_BY_ID
from rgdvd.map_screen import WorldMapScreen
from rgdvd.geometry import box
from rgdvd.controllers import WheelInput, PRESETS, PRESET_LABELS


loadPrcFileData("", "win-size 1366 768")
loadPrcFileData("", "sync-video true")
loadPrcFileData("", "show-frame-rate-meter false")
loadPrcFileData("", "framebuffer-srgb true")
loadPrcFileData("", "textures-power-2 none")


class RGDVDGame(ShowBase):
    def __init__(self) -> None:
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.44, 0.61, 0.75, 1)
        self.game_config = load_config()
        self.profile = CareerProfile()
        self.audio: VehicleAudio | None = None
        try:
            self.audio = VehicleAudio(self.loader, APP_DIR)
            self.audio.stop()
        except Exception:
            self.audio = None
        self.car_id = str(self.game_config.get("car_id", "street_gt"))
        if not self.profile.is_unlocked(self.car_id):
            self.car_id = "street_gt"
        props = WindowProperties()
        props.setTitle(f"RGDVD {__version__} | Racing")
        props.setCursorHidden(False)
        props.setSize(int(self.game_config.get("width", 1366)),
                      int(self.game_config.get("height", 768)))
        self.win.requestProperties(props)
        self.camLens.setNearFar(0.1, 1800.0)
        self.camLens.setFov(72)
        self.render.setAntialias(AntialiasAttrib.MAuto)

        self.state = "MENU"
        self.mode = "QUICK"
        self.scene_root = None
        self.light_nodes = []
        self.car: SportsCar | None = None
        self.track: UrbanCity | None = None
        self.physics: VehiclePhysics | None = None
        self.ai_drivers = []
        self.remote_cars: dict[str, SportsCar] = {}
        self.network_session: LanSession | OnlineSession | None = None
        self.network_error: str | None = None
        self.last_network_send = 0.0
        self.race_time = 0.0
        self.lap = 1
        self.last_x = 0.0
        self.last_lap_time = 0.0
        self.best_lap: float | None = None
        self.current_event = None
        self.event_targets: list[tuple[float, float]] = []
        self.event_target_index = 0
        self.event_lap = 1
        self.event_laps = 1
        self.animated_arrows = []
        self.route_barriers: list[tuple[float, float, float]] = []
        self.map_origin = "MENU"
        self.map_screen: WorldMapScreen | None = None
        self.controls = {key: False for key in (
            "w", "s", "a", "d", "arrow_up", "arrow_down",
            "arrow_left", "arrow_right", "space", "q", "e",
        )}
        self.wheel_input = WheelInput(self, self.game_config)
        self._wheel_shift_up_was_pressed = False
        self._wheel_shift_down_was_pressed = False
        self._setup_menu()
        self.map_screen = WorldMapScreen(
            self.aspect2d, self.start_selected_event, self.close_world_map)
        self._bind_events()
        self.taskMgr.add(self._game_update, "rgdvd-game-update")
        self.taskMgr.add(self._camera_update, "rgdvd-camera-update")

    def _setup_menu(self) -> None:
        # Carbon-fibre inspired motorsport front end with a clear action hierarchy.
        self.menu = DirectFrame(
            frameColor=(0.012, 0.018, 0.027, 1),
            frameSize=(-1.78, 1.78, -1.0, 1.0), pos=(0, 0, 0),
        )
        DirectFrame(
            parent=self.menu, frameColor=(0.025, 0.037, 0.052, 1),
            frameSize=(-1.68, 1.68, -0.91, 0.91), pos=(0, 0, 0),
        )
        # Header strip.
        DirectFrame(parent=self.menu, frameColor=(0.86, 0.075, 0.045, 1),
                    frameSize=(-1.68, 1.68, -0.012, 0.012), pos=(0, 0, 0.79))
        DirectLabel(
            parent=self.menu, text="RGDVD", text_scale=0.092,
            text_fg=(0.97, 0.98, 1, 1), text_shadow=(0, 0, 0, 0.7),
            frameColor=(0, 0, 0, 0), pos=(-1.48, 0, 0.84),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text="STREET RACING  /  OPEN CITY",
            text_scale=0.025, text_fg=(0.60, 0.70, 0.79, 1),
            frameColor=(0, 0, 0, 0), pos=(-0.78, 0, 0.855),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text=f"BUILD {__version__}   •   PC",
            text_scale=0.023, text_fg=(0.68, 0.76, 0.83, 1),
            frameColor=(0, 0, 0, 0), pos=(1.46, 0, 0.855),
            text_align=TextNode.ARight,
        )

        # Left hero / garage panel.
        DirectFrame(
            parent=self.menu, frameColor=(0.045, 0.063, 0.082, 1),
            frameSize=(-0.76, 0.76, -0.58, 0.58), pos=(-0.83, 0, 0.055),
        )
        DirectFrame(
            parent=self.menu, frameColor=(0.86, 0.075, 0.045, 1),
            frameSize=(-0.76, 0.025, -0.58, 0.58), pos=(-0.83, 0, 0.055),
        )
        DirectLabel(
            parent=self.menu, text="YOUR CITY. YOUR RULES.",
            text_scale=0.027, text_fg=(0.98, 0.30, 0.18, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.43, 0, 0.48),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text="RGDVD",
            text_scale=0.19, text_fg=(0.96, 0.98, 1, 1),
            text_shadow=(0.02, 0.02, 0.02, 0.9),
            frameColor=(0, 0, 0, 0), pos=(-1.43, 0, 0.20),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text="NIGHT STREET SERIES",
            text_scale=0.040, text_fg=(0.63, 0.75, 0.85, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.41, 0, 0.08),
            text_align=TextNode.ALeft,
        )
        DirectFrame(
            parent=self.menu, frameColor=(0.86, 0.075, 0.045, 1),
            frameSize=(-0.56, 0.56, -0.006, 0.006), pos=(-0.83, 0, -0.08),
        )
        DirectLabel(
            parent=self.menu,
            text="53 EVENTS   /   6 DISTRICTS   /   OPEN-WORLD DRIVING",
            text_scale=0.021, text_fg=(0.75, 0.82, 0.88, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.40, 0, -0.20),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text="CAREER PROGRESS",
            text_scale=0.021, text_fg=(0.52, 0.64, 0.74, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.40, 0, -0.36),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text=self._menu_summary(),
            text_scale=0.019, text_fg=(0.86, 0.90, 0.94, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.40, 0, -0.47),
            text_align=TextNode.ALeft, text_wordwrap=42,
        )

        # Main action deck.
        DirectFrame(
            parent=self.menu, frameColor=(0.035, 0.050, 0.067, 1),
            frameSize=(-0.75, 0.75, -0.58, 0.58), pos=(0.83, 0, 0.055),
        )
        DirectLabel(
            parent=self.menu, text="RACE CONTROL",
            text_scale=0.043, text_fg=(0.95, 0.97, 0.99, 1),
            frameColor=(0, 0, 0, 0), pos=(0.22, 0, 0.49),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.menu, text="Choose how you want to drive",
            text_scale=0.022, text_fg=(0.56, 0.67, 0.76, 1),
            frameColor=(0, 0, 0, 0), pos=(0.22, 0, 0.40),
            text_align=TextNode.ALeft,
        )
        self._menu_button("01   FREE ROAM", 0.83, 0.245, self.start_career,
                          width=0.61, accent=True)
        self._menu_button("02   WORLD MAP / EVENTS", 0.83, 0.055,
                          self.start_quick_race, width=0.61)
        self._menu_button("03   HOST LAN GAME", 0.83, -0.135,
                          self.host_lan, width=0.61)
        self._menu_button("04   FIND LAN GAME", 0.83, -0.325,
                          self.join_lan, width=0.61)
        self._menu_button("05   ONLINE ROOM", 0.83, -0.515,
                          self.join_online, width=0.61)

        # Driver identity and online connection details.
        DirectFrame(
            parent=self.menu, frameColor=(0.030, 0.043, 0.058, 1),
            frameSize=(-1.60, 1.60, -0.115, 0.115), pos=(0, 0, -0.72),
        )
        DirectLabel(
            parent=self.menu, text="DRIVER",
            text_scale=0.018, text_fg=(0.55, 0.67, 0.77, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.48, 0, -0.655),
            text_align=TextNode.ALeft,
        )
        self.nickname_entry = DirectEntry(
            parent=self.menu, initialText=str(self.game_config.get("nickname", "Driver")),
            numLines=1, width=12, scale=0.032, pos=(-1.48, 0, -0.79),
            frameColor=(0.10, 0.14, 0.18, 1),
            text_fg=(0.96, 0.98, 1, 1), cursorKeys=1,
        )
        DirectLabel(
            parent=self.menu, text="ROOM",
            text_scale=0.018, text_fg=(0.55, 0.67, 0.77, 1),
            frameColor=(0, 0, 0, 0), pos=(-0.58, 0, -0.655),
            text_align=TextNode.ALeft,
        )
        self.room_entry = DirectEntry(
            parent=self.menu, initialText=str(self.game_config.get("room", "OPEN-LOBBY")),
            numLines=1, width=13, scale=0.032, pos=(-0.58, 0, -0.79),
            frameColor=(0.10, 0.14, 0.18, 1),
            text_fg=(0.96, 0.98, 1, 1), cursorKeys=1,
        )
        DirectLabel(
            parent=self.menu, text="ONLINE SERVER",
            text_scale=0.018, text_fg=(0.55, 0.67, 0.77, 1),
            frameColor=(0, 0, 0, 0), pos=(0.38, 0, -0.655),
            text_align=TextNode.ALeft,
        )
        self.server_entry = DirectEntry(
            parent=self.menu,
            initialText=str(self.game_config.get("server_url", DEFAULT_SERVER_URL)),
            numLines=1, width=35, scale=0.029, pos=(0.38, 0, -0.79),
            frameColor=(0.10, 0.14, 0.18, 1),
            text_fg=(0.86, 0.91, 0.95, 1), cursorKeys=1,
        )

        self.menu_status = DirectLabel(
            parent=self.menu, text=self._menu_summary(),
            text_scale=0.017, text_fg=(0.62, 0.72, 0.80, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, -0.90),
        )
        self._menu_button("GARAGE", -1.31, -0.965, self.next_car,
                          width=0.22, compact=True)
        self._menu_button("WHEEL", -0.66, -0.965, self.cycle_controller_preset,
                          width=0.22, compact=True)
        self._menu_button("GEARBOX", 0.0, -0.965, self.cycle_transmission,
                          width=0.25, compact=True)
        self._menu_button("GRAPHICS", 0.66, -0.965, self.cycle_quality,
                          width=0.22, compact=True)
        self._menu_button("EXIT", 1.31, -0.965, self.userExit,
                          width=0.18, compact=True, danger=True)

        self.pause_menu = DirectFrame(
            frameColor=(0.015, 0.022, 0.032, 0.94),
            frameSize=(-1.78, 1.78, -1.0, 1.0), pos=(0, 0, 0),
        )
        DirectLabel(parent=self.pause_menu, text="PAUSED",
                    text_scale=0.13, text_fg=(0.96, 0.97, 0.98, 1),
                    frameColor=(0, 0, 0, 0), pos=(0, 0, 0.31))
        DirectButton(parent=self.pause_menu, text="RESUME",
                     text_scale=0.05, scale=1.0, pos=(0, 0, 0.06),
                     frameSize=(-0.55, 0.55, -0.09, 0.09),
                     frameColor=(0.72, 0.08, 0.045, 1),
                     command=self.resume_race)
        DirectButton(parent=self.pause_menu, text="RESTART RACE",
                     text_scale=0.043, scale=1.0, pos=(0, 0, -0.16),
                     frameSize=(-0.55, 0.55, -0.09, 0.09),
                     frameColor=(0.10, 0.14, 0.18, 1),
                     command=self.restart_race)
        DirectButton(parent=self.pause_menu, text="RETURN TO MENU",
                     text_scale=0.040, scale=1.0, pos=(0, 0, -0.38),
                     frameSize=(-0.55, 0.55, -0.09, 0.09),
                     frameColor=(0.10, 0.14, 0.18, 1),
                     command=self.return_to_menu)
        self.pause_menu.hide()

        self.result_menu = DirectFrame(
            frameColor=(0.015, 0.022, 0.032, 0.94),
            frameSize=(-1.78, 1.78, -1.0, 1.0), pos=(0, 0, 0),
        )
        self.result_label = DirectLabel(
            parent=self.result_menu, text="RACE COMPLETE",
            text_scale=0.10, text_fg=(0.96, 0.97, 0.98, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.29),
        )
        self.result_details = DirectLabel(
            parent=self.result_menu, text="", text_scale=0.038,
            text_fg=(0.76, 0.83, 0.87, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.03),
        )
        DirectButton(parent=self.result_menu, text="BACK TO MENU",
                     text_scale=0.045, scale=1.0, pos=(0, 0, -0.28),
                     frameSize=(-0.58, 0.58, -0.09, 0.09),
                     frameColor=(0.72, 0.08, 0.045, 1),
                     command=self.return_to_menu)
        self.result_menu.hide()

        self.hud_text = OnscreenText(
            text="", pos=(-1.70, 0.91), scale=0.043,
            fg=(0.95, 0.97, 0.98, 1), align=TextNode.ALeft,
            shadow=(0, 0, 0, 0.8), mayChange=True,
        )
        self.hud_text.hide()
        self.hud_bottom = OnscreenText(
            text="", pos=(0, -0.94), scale=0.027,
            fg=(0.90, 0.93, 0.94, 1), shadow=(0, 0, 0, 0.8),
            mayChange=True,
        )
        self.hud_bottom.hide()
        self.gauge_root = self.aspect2d.attachNewNode("dashboard-gauges")
        self.gauge_needles = {}
        self.gauge_readouts = {}
        self._build_dashboard_gauges()
        self.gauge_root.hide()

    def _build_dashboard_gauges(self) -> None:
        """Create analog-style speedometer (left) and tachometer (right)."""
        specs = (
            ("speed", -0.82, "SPEED", "km/h", 300.0, (0.20, 0.78, 1.0, 1.0)),
            ("rpm", 0.82, "TACHOMETER", "x1000 rpm", 9000.0, (1.0, 0.25, 0.12, 1.0)),
        )
        self.gauge_centers = {}
        for key, cx, title, unit, maximum, color in specs:
            cz, radius = -0.53, 0.34
            self.gauge_centers[key] = (cx, cz, radius, maximum)
            lines = LineSegs(f"{key}-gauge-face")
            lines.setThickness(2.2)
            lines.setColor(0.72, 0.79, 0.84, 0.88)
            steps = 60
            for index in range(steps + 1):
                angle = math.radians(-135.0 + 270.0 * index / steps)
                x = cx + radius * math.sin(angle)
                z = cz + radius * math.cos(angle)
                if index == 0:
                    lines.moveTo(x, 0, z)
                else:
                    lines.drawTo(x, 0, z)
            for tick in range(11):
                angle = math.radians(-135.0 + 27.0 * tick)
                outer = radius * 0.96
                inner = radius * (0.78 if tick % 2 == 0 else 0.86)
                lines.moveTo(cx + outer * math.sin(angle), 0,
                             cz + outer * math.cos(angle))
                lines.drawTo(cx + inner * math.sin(angle), 0,
                             cz + inner * math.cos(angle))
            face = self.gauge_root.attachNewNode(lines.create())
            face.setTransparency(True)

            needle_lines = LineSegs(f"{key}-needle")
            needle_lines.setThickness(3.0)
            needle_lines.setColor(*color)
            needle_lines.moveTo(0, 0, 0)
            needle_lines.drawTo(0, 0, radius * 0.72)
            needle = self.gauge_root.attachNewNode(needle_lines.create())
            needle.setPos(cx, -0.012, cz)
            self.gauge_needles[key] = needle

            OnscreenText(text=title, parent=self.gauge_root,
                         pos=(cx, cz + 0.43), scale=0.035,
                         fg=(0.91, 0.94, 0.97, 0.96),
                         align=TextNode.ACenter)
            self.gauge_readouts[key] = OnscreenText(
                text="0", parent=self.gauge_root, pos=(cx, cz - 0.015),
                scale=0.055, fg=(0.98, 0.99, 1.0, 1),
                align=TextNode.ACenter, mayChange=True)
            OnscreenText(text=unit, parent=self.gauge_root,
                         pos=(cx, cz - 0.095), scale=0.020,
                         fg=(0.65, 0.73, 0.80, 0.95),
                         align=TextNode.ACenter)
            for tick in range(0, 11, 2):
                angle = math.radians(-135.0 + 27.0 * tick)
                label_radius = radius * 0.66
                label_value = int(maximum * tick / 10 / (1000 if key == "rpm" else 1))
                OnscreenText(
                    text=str(label_value), parent=self.gauge_root,
                    pos=(cx + label_radius * math.sin(angle),
                         cz + label_radius * math.cos(angle)),
                    scale=0.019, fg=(0.76, 0.82, 0.87, 0.95),
                    align=TextNode.ACenter)
            if key == "rpm":
                self.gauge_gear = OnscreenText(
                    text="GEAR  N", parent=self.gauge_root,
                    pos=(cx, cz - 0.205), scale=0.032,
                    fg=(1.0, 0.82, 0.28, 1),
                    align=TextNode.ACenter, mayChange=True)

    def _update_dashboard_gauges(self) -> None:
        if self.physics is None:
            return
        values = {
            "speed": max(0.0, self.physics.speed_kmh),
            "rpm": max(0.0, self.physics.rpm),
        }
        for key, value in values.items():
            _, _, _, maximum = self.gauge_centers[key]
            fraction = max(0.0, min(1.0, value / maximum))
            self.gauge_needles[key].setR(-135.0 + 270.0 * fraction)
            shown = int(round(value))
            self.gauge_readouts[key].setText(
                f"{shown:03d}" if key == "speed" else f"{shown:04d}")
        gear = self.physics.gear
        gear_text = "R" if gear < 0 else ("N" if gear == 0 else str(gear))
        self.gauge_gear.setText(f"GEAR  {gear_text}")

    def _menu_button(self, text: str, x: float, z: float, command: Any,
                     width: float = 0.59, accent: bool = False,
                     compact: bool = False, danger: bool = False) -> None:
        if danger:
            color = (0.34, 0.075, 0.065, 1)
        elif accent:
            color = (0.75, 0.075, 0.045, 1)
        elif compact:
            color = (0.105, 0.14, 0.18, 1)
        else:
            color = (0.12, 0.17, 0.21, 1)
        height = 0.060 if compact else 0.085
        text_size = 0.032 if compact else 0.047
        DirectButton(
            parent=self.menu, text=text, text_scale=text_size,
            text_fg=(0.96, 0.97, 0.98, 1),
            frameColor=color, relief=1, borderWidth=(0.008, 0.008),
            frameSize=(-width, width, -height, height),
            scale=1.0, pos=(x, 0, z),
            command=command,
        )


    def _menu_summary(self) -> str:
        wins = self.profile.data.get("wins", 0)
        races = self.profile.data.get("races", 0)
        car_name = get_car_spec(self.car_id)["name"]
        quality = str(self.game_config.get("quality", "medium")).upper()
        unlocked_count = len(unlocked_cars(self.profile.data.get("unlocked_cars", [])))
        preset = PRESET_LABELS.get(self.wheel_input.requested_preset, "AUTO DETECT")
        transmission = str(self.game_config.get("transmission", "automatic")).upper()
        return (f"CAREER  {races} RACES / {wins} WINS     "
                f"CREDITS  {self.profile.credits:,}     "
                f"CAR  {car_name} ({unlocked_count}/{len(CAR_SPECS)})     "
                f"GRAPHICS  {quality}     WHEEL  {preset}     GEARBOX  {transmission}")

    def _refresh_menu(self, message: str | None = None) -> None:
        self.menu_status["text"] = message or self._menu_summary()

    def _nickname(self) -> str:
        value = self.nickname_entry.get().strip()[:20]
        return value or "Driver"

    def _room(self) -> str:
        value = self.room_entry.get().strip()[:32]
        return value or "OPEN-LOBBY"

    def _save_menu_settings(self) -> None:
        self.game_config["nickname"] = self._nickname()
        self.game_config["room"] = self._room()
        self.game_config["server_url"] = self.server_entry.get().strip() or DEFAULT_SERVER_URL
        self.game_config["car_id"] = self.car_id
        save_config(self.game_config)

    def _bind_events(self) -> None:
        for key in self.controls:
            self.accept(key, self._set_control, [key, True])
            self.accept(key + "-up", self._set_control, [key, False])
        self.accept("escape", self.toggle_pause)
        self.accept("r", self.restart_race)
        self.accept("m", self.toggle_world_map)
        self.accept("f6", self.cycle_controller_preset)
        self.accept("f7", self.cycle_transmission)

    def _set_control(self, key: str, value: bool) -> None:
        self.controls[key] = value

    def next_car(self) -> None:
        owned = unlocked_cars(self.profile.data.get("unlocked_cars", []))
        if not owned:
            owned = ["street_gt"]
        current_index = owned.index(self.car_id) if self.car_id in owned else 0
        if len(owned) == 1:
            locked = [car_id for car_id in CAR_SPECS if car_id not in owned]
            if locked:
                next_spec = get_car_spec(locked[0])
                self._refresh_menu(
                    f"{next_spec['name']} unlocks after {next_spec['required_wins']} career wins."
                )
                return
        self.car_id = owned[(current_index + 1) % len(owned)]
        self._save_menu_settings()
        self._refresh_menu()

    def cycle_controller_preset(self) -> None:
        current = self.wheel_input.requested_preset
        index = PRESETS.index(current) if current in PRESETS else 0
        preset = PRESETS[(index + 1) % len(PRESETS)]
        self.wheel_input.set_preset(preset)
        save_config(self.game_config)
        label = PRESET_LABELS[preset]
        self._refresh_menu(f"CONTROL PROFILE: {label}  |  Reconnect the wheel if needed.")

    def cycle_transmission(self) -> None:
        current = str(self.game_config.get("transmission", "automatic")).lower()
        mode = "manual" if current != "manual" else "automatic"
        self.game_config["transmission"] = mode
        if self.physics is not None:
            self.physics.set_transmission_mode(mode)
        save_config(self.game_config)
        label = "MANUAL" if mode == "manual" else "AUTOMATIC"
        self._refresh_menu(f"TRANSMISSION: {label}  |  F7 toggles in game; Q/E shift.")

    def cycle_quality(self) -> None:
        qualities = ("low", "medium", "high")
        current = str(self.game_config.get("quality", "medium")).lower()
        self.game_config["quality"] = qualities[(qualities.index(current) + 1)
                                           % len(qualities)] if current in qualities else "medium"
        save_config(self.game_config)
        self._refresh_menu()

    def _close_network(self) -> None:
        if self.network_session is not None:
            self.network_session.close()
            self.network_session = None
        for car in self.remote_cars.values():
            car.root.removeNode()
        self.remote_cars.clear()

    def start_career(self) -> None:
        self._save_menu_settings()
        self._close_network()
        self.start_race("CAREER")

    def start_quick_race(self) -> None:
        self.open_world_map()

    def open_world_map(self) -> None:
        if self.state not in ("MENU", "RACING") or self.map_screen is None:
            return
        self.map_origin = self.state
        if self.map_origin == "MENU":
            self.menu.hide()
            x, y = 0.0, -120.0
        else:
            x = self.physics.x if self.physics else 0.0
            y = self.physics.y if self.physics else -120.0
            self.hud_text.hide()
            self.hud_bottom.hide()
            self.gauge_root.hide()
            if self.audio:
                self.audio.stop()
        self.state = "MAP"
        self.map_screen.show(x, y)

    def close_world_map(self) -> None:
        if self.map_screen is not None:
            self.map_screen.hide()
        if self.map_origin == "MENU":
            self.state = "MENU"
            self.menu.show()
        elif self.map_origin == "RACING":
            self.state = "RACING"
            self.hud_text.show()
            self.hud_bottom.show()
            self.gauge_root.show()
            if self.audio:
                self.audio.start()

    def toggle_world_map(self) -> None:
        if self.state == "MAP":
            self.close_world_map()
        elif self.state in ("MENU", "RACING"):
            self.open_world_map()

    def start_selected_event(self, event_id: str) -> None:
        if event_id not in EVENT_BY_ID:
            return
        self._save_menu_settings()
        self._close_network()
        if self.map_screen is not None:
            self.map_screen.hide()
        self.menu.hide()
        self.start_race("EVENT", event_id)

    def host_lan(self) -> None:
        self._save_menu_settings()
        self._close_network()
        try:
            self.network_session = LanSession.host(self._nickname(), self._room())
            self.start_race("LAN HOST")
            self._refresh_hud_status("LAN HOST - share your local IP with friends")
        except OSError as exc:
            self._refresh_menu(f"Could not host LAN game: {exc}")

    def join_lan(self) -> None:
        self._save_menu_settings()
        self._close_network()
        self._refresh_menu("Searching for LAN hosts...")
        try:
            hosts = LanSession.discover(timeout=1.2)
            if not hosts:
                self._refresh_menu("No LAN hosts found. Check Wi-Fi and firewall.")
                return
            host = hosts[0]
            self.network_session = LanSession.join(host["address"], self._nickname())
            self.start_race("LAN CLIENT")
            self._refresh_hud_status(f"JOINED {host['host']} / {host['address']}")
        except (OSError, TimeoutError) as exc:
            self._refresh_menu(f"LAN connection failed: {exc}")

    def join_online(self) -> None:
        self._save_menu_settings()
        self._close_network()
        try:
            base_url = str(self.game_config.get("server_url", DEFAULT_SERVER_URL)).strip()
            self.network_session = OnlineSession(base_url, self._room(), self._nickname())
            self.start_race("ONLINE")
            self._refresh_hud_status("CONNECTING TO ONLINE ROOM...")
        except (RuntimeError, ValueError) as exc:
            self._refresh_menu(str(exc))

    def _clear_lighting(self) -> None:
        for light_node in self.light_nodes:
            self.render.clearLight(light_node)
            light_node.removeNode()
        self.light_nodes.clear()
        self.render.clearFog()

    def _setup_lighting(self) -> None:
        self._clear_lighting()
        ambient = AmbientLight("soft-sky-ambient")
        quality = str(self.game_config.get("quality", "medium")).lower()
        ambient.setColor(Vec4(0.52 if quality == "low" else 0.43,
                              0.55 if quality == "low" else 0.47,
                              0.60 if quality == "low" else 0.53, 1))
        ambient_node = self.scene_root.attachNewNode(ambient)
        self.render.setLight(ambient_node)
        self.light_nodes.append(ambient_node)

        sun = DirectionalLight("late-afternoon-sun")
        sun.setColor(Vec4(1.0, 0.91, 0.77, 1))
        if self.game_config.get("shadows", True) and quality != "low":
            sun.setShadowCaster(True, 1024 if quality == "medium" else 2048,
                                1024 if quality == "medium" else 2048)
        sun_np = self.scene_root.attachNewNode(sun)
        sun_np.setHpr(-32, -48, 0)
        self.render.setLight(sun_np)
        self.light_nodes.append(sun_np)
        self.render.setShaderAuto()

        fog = Fog("distance-haze")
        fog.setColor(0.44, 0.61, 0.75)
        fog.setExpDensity(0.00095 if quality == "low" else 0.00082)
        self.render.setFog(fog)

    def _build_scene(self) -> None:
        if self.scene_root is not None:
            self._clear_lighting()
            self.scene_root.removeNode()
        self.scene_root = self.render.attachNewNode("race-scene")
        self._setup_lighting()
        self.track = UrbanCity(self.scene_root, quality=str(self.game_config.get("quality", "medium")).lower())
        self.physics = VehiclePhysics(x=0.0, y=-120.0, heading=0.0, car_id=self.car_id)
        self.physics.set_transmission_mode(str(self.game_config.get("transmission", "automatic")))
        paint = get_car_spec(self.car_id)["paint"]
        vehicle_class = VolgaCar if self.car_id == "volga_2410" else SportsCar
        self.car = vehicle_class(self.scene_root, paint=paint)
        self.car.reset_pose(self.physics.x, self.physics.y, self.physics.heading)
        self.animated_arrows = []
        # Open-world street driving: no circuit racing line or lap AI.
        self.ai_drivers = []
        self.remote_cars = {}
        self.camera.setPos(0, -136, 9)
        self.camera.lookAt(0, -120, 1.2)

    def start_race(self, mode: str = "QUICK",
                   event_id: str | None = None) -> None:
        self.mode = mode
        self.current_event = EVENT_BY_ID.get(event_id) if event_id else None
        self._build_scene()
        if self.current_event is not None:
            self._setup_event_route(self.current_event)
        if self.audio:
            self.audio.start()
        self.menu.hide()
        self.pause_menu.hide()
        self.result_menu.hide()
        self.hud_text.show()
        self.hud_bottom.show()
        self.gauge_root.show()
        self.state = "RACING"
        self.network_error = None
        self.race_time = 0.0
        self.lap = 1
        self.last_lap_time = 0.0
        self.best_lap = None
        self.last_x = 0.0
        self.last_network_send = 0.0

    def restart_race(self) -> None:
        if self.physics is None or self.car is None:
            return
        if self.current_event is not None:
            self._build_scene()
            self._setup_event_route(self.current_event)
        else:
            self.physics.reset(x=0.0, y=-120.0, heading=0.0)
            self.car.reset_pose(self.physics.x, self.physics.y, self.physics.heading)
        for driver in self.ai_drivers:
            driver.reset()
        self.race_time = 0.0
        self.lap = 1
        self.last_lap_time = 0.0
        self.last_x = 0.0
        self.best_lap = None
        self.state = "RACING"
        self.pause_menu.hide()
        self.result_menu.hide()
        self.hud_text.show()
        self.hud_bottom.show()
        self.gauge_root.show()

    def toggle_pause(self) -> None:
        if self.state == "MAP":
            self.close_world_map()
        elif self.state == "RACING":
            self.state = "PAUSED"
            self.pause_menu.show()
        elif self.state == "PAUSED":
            self.resume_race()

    def resume_race(self) -> None:
        self.state = "RACING"
        self.pause_menu.hide()

    def return_to_menu(self) -> None:
        """Close the 3D runtime; the CustomTkinter launcher becomes visible again."""
        self.userExit()

    def _game_update(self, task):
        dt = min(globalClock.getDt(), 1.0 / 30.0)
        if self.state == "RACING" and self.physics and self.car and self.track:
            wheel = self.wheel_input.read()
            keyboard_throttle = float(self.controls["w"] or self.controls["arrow_up"])
            keyboard_brake = float(self.controls["s"] or self.controls["arrow_down"])
            keyboard_steer = float(self.controls["a"] or self.controls["arrow_left"]) - float(
                self.controls["d"] or self.controls["arrow_right"])
            throttle = max(keyboard_throttle, wheel.throttle)
            brake = max(keyboard_brake, wheel.brake)
            steer = wheel.steer if wheel.connected else keyboard_steer
            handbrake = bool(self.controls["space"] or wheel.handbrake)
            if self.physics.transmission_mode == "manual":
                if self.controls["e"] or (wheel.shift_up and not self._wheel_shift_up_was_pressed):
                    self.physics.shift_up()
                if self.controls["q"] or (wheel.shift_down and not self._wheel_shift_down_was_pressed):
                    self.physics.shift_down()
            self._wheel_shift_up_was_pressed = wheel.shift_up
            self._wheel_shift_down_was_pressed = wheel.shift_down
            self.physics.on_track = self.track.contains(self.physics.x, self.physics.y)
            previous_x, previous_y = self.physics.x, self.physics.y
            self.physics.update(Controls(
                throttle=throttle, brake=brake, steer=steer,
                handbrake=handbrake), dt)
            self._resolve_route_barriers(previous_x, previous_y)
            self.car.update(self.physics.x, self.physics.y, self.physics.heading,
                            self.physics.speed, self.physics.steer_angle, dt)
            if self.audio:
                self.audio.update(self.physics.rpm, throttle,
                                  self.physics.lateral_speed,
                                  handbrake, self.physics.gear)
            self._animate_route_arrows()
            if self.current_event is not None:
                self._update_event_progress()

            self._update_network(dt)
            self.race_time += dt
            self._update_hud()
        return task.cont

    def _setup_event_route(self, event) -> None:
        route = list(event.route)
        if len(route) < 2 or self.physics is None or self.car is None:
            return
        self.event_targets = route[1:] + ([route[0]] if event.event_type == "CIRCUIT" else [])
        self.event_target_index = 0
        self.event_lap = 1
        self.event_laps = event.laps
        self.animated_arrows = []
        self.route_barriers = []
        for index, point in enumerate(self.event_targets):
            if event.event_type == "CIRCUIT":
                following = route[(index + 2) % len(route)]
            elif index + 2 < len(route):
                following = route[index + 2]
            else:
                previous = route[index]
                following = (point[0] + point[0] - previous[0],
                             point[1] + point[1] - previous[1])
            self._make_route_gate(point, following[0], following[1])
        dx = route[1][0] - route[0][0]
        dy = route[1][1] - route[0][1]
        length = math.hypot(dx, dy) or 1.0
        start_x = route[0][0] - dx / length * 20.0
        start_y = route[0][1] - dy / length * 20.0
        heading = math.atan2(-dx, dy)
        self.physics.reset(start_x, start_y, heading)
        self.car.reset_pose(start_x, start_y, heading)
        self.camera.setPos(start_x, start_y - 18, 9)
        self.camera.lookAt(start_x, start_y, 1.2)

    def _make_route_gate(self, point, next_x: float, next_y: float) -> None:
        if self.scene_root is None:
            return
        gate = self.scene_root.attachNewNode("physical-checkpoint-barrier")
        gate.setPos(point[0], point[1], 0)
        heading = math.degrees(math.atan2(-(next_x - point[0]),
                                          next_y - point[1]))
        gate.setH(heading)
        self.route_barriers.append((float(point[0]), float(point[1]), heading))

        # A broad, unmistakable barrier wall on both sides of a clear central
        # driving lane. The panels are not just decoration: collision is
        # resolved against these exact wall sections in _resolve_route_barriers.
        concrete = (0.075, 0.095, 0.12, 1)
        for side in (-1, 1):
            panel = box(gate, "solid-checkpoint-wall",
                        (side * 6.85, 0.0, 0.82),
                        (6.45, 0.72, 1.64), concrete)
            panel.setLightOff(1)
            panel.setColorScale(0.82, 0.90, 1.0, 1)
            # Red/white hazard plates make the wall readable at speed.
            for stripe in range(5):
                stripe_x = side * (4.45 + stripe * 1.08)
                plate = box(gate, "wall-hazard-stripe",
                            (stripe_x, -0.375, 0.84),
                            (0.34, 0.035, 1.38),
                            (0.92, 0.22, 0.075, 1) if stripe % 2 == 0
                            else (0.78, 0.83, 0.86, 1))
                plate.setLightOff(1)

        blue = (0.015, 0.36, 0.95, 1)
        for side in (-10.25, 10.25):
            post = box(gate, "blue-checkpoint-post", (side, 0, 1.35),
                       (0.58, 0.72, 2.7), blue)
            post.setLightOff(1)
            post.setColorScale(0.75, 0.88, 1.25, 1)
        beam = box(gate, "blue-checkpoint-beam", (0, 0, 2.85),
                   (20.9, 0.55, 0.48), blue)
        beam.setLightOff(1)
        beam.setColorScale(0.65, 0.84, 1.35, 1)
        for base_x in (-1.1, 0.0, 1.1):
            arrow = gate.attachNewNode("animated-chevron")
            arrow.setPos(base_x, -0.31, 2.86)
            for angle in (-42, 42):
                segment = box(arrow, "arrow-segment", (0, 0, 0),
                              (0.13, 0.12, 0.54), (0.18, 0.72, 1.0, 1))
                segment.setR(angle)
                segment.setLightOff(1)
                segment.setColorScale(0.55, 0.85, 1.45, 1)
            self.animated_arrows.append((arrow, base_x))

    def _resolve_route_barriers(self, previous_x: float, previous_y: float) -> None:
        """Stop the car against checkpoint wall panels while leaving a wide lane."""
        if self.physics is None or not self.route_barriers:
            return
        for wall_x, wall_y, heading_deg in self.route_barriers:
            dx = self.physics.x - wall_x
            dy = self.physics.y - wall_y
            angle = math.radians(heading_deg)
            # Gate-local X runs across the road; local Y follows the route.
            local_x = dx * math.cos(angle) + dy * math.sin(angle)
            local_y = -dx * math.sin(angle) + dy * math.cos(angle)
            # The middle 6.8 m stays open. Both wall wings occupy the shoulders.
            if 2.55 < abs(local_x) < 11.65 and abs(local_y) < 2.75:
                self.physics.x = previous_x
                self.physics.y = previous_y
                self.physics.speed = 0.0
                self.physics.lateral_speed = 0.0
                self.physics.yaw_rate = 0.0
                break

    def _animate_route_arrows(self) -> None:
        for index, (arrow, base_x) in enumerate(self.animated_arrows):
            pulse = 0.5 + 0.5 * math.sin(self.race_time * 5.0 + index * 0.8)
            arrow.setX(base_x + math.sin(self.race_time * 2.4 + index) * 0.10)
            arrow.setColorScale(0.7 + pulse * 0.3, 0.85 + pulse * 0.15, 1.2, 1)

    def _update_event_progress(self) -> None:
        if not self.current_event or not self.physics or not self.event_targets:
            return
        target = self.event_targets[self.event_target_index]
        distance = math.hypot(self.physics.x - target[0],
                              self.physics.y - target[1])
        if distance <= 15.0:
            self.event_target_index += 1
            if self.event_target_index >= len(self.event_targets):
                if self.event_lap < self.event_laps:
                    self.event_lap += 1
                    self.event_target_index = 0
                else:
                    self._finish_race()

    def _update_network(self, dt: float) -> None:
        if self.network_session is None or self.physics is None:
            return
        now = time.monotonic()
        if now - self.last_network_send >= 1/15:
            self.last_network_send = now
            self.network_session.send_state(self.physics.snapshot())
        seen_players: set[str] = set()
        for player in self.network_session.poll():
            player_id = str(player.get("id", ""))
            state = player.get("state", {})
            if not player_id or not isinstance(state, dict):
                continue
            seen_players.add(player_id)
            if player_id not in self.remote_cars and self.scene_root is not None:
                self.remote_cars[player_id] = SportsCar(
                    self.scene_root, paint=(0.03, 0.30, 0.74, 1.0))
            car = self.remote_cars.get(player_id)
            if car is not None:
                try:
                    car.update(float(state.get("x", 0)),
                               float(state.get("y", -120)),
                               float(state.get("heading", 0.0)),
                               float(state.get("speed", 0)), 0.0, dt)
                except (TypeError, ValueError):
                    pass
        for player_id in set(self.remote_cars) - seen_players:
            self.remote_cars.pop(player_id).root.removeNode()
        if getattr(self.network_session, "error", None):
            self.network_error = self.network_session.error

    def _update_laps(self) -> None:
        assert self.physics is not None
        x, y = self.physics.x, self.physics.y
        crossed = self.last_x < 0.0 <= x and y < -137.0 and self.physics.speed > 3.0
        if crossed and self.race_time > 8.0:
            lap_time = self.race_time - self.last_lap_time
            self.last_lap_time = self.race_time
            if self.best_lap is None or lap_time < self.best_lap:
                self.best_lap = lap_time
            self.lap += 1
            if self.lap > 3:
                self._finish_race()
        self.last_x = x

    def _finish_race(self) -> None:
        self.state = "RESULTS"
        if self.audio:
            self.audio.stop()
        payout_text = "Free drive complete."
        if self.mode in ("CAREER", "EVENT") and self.physics is not None:
            result = self.profile.record_race(
                self.race_time, self.physics.distance_m / 1000.0, 1,
                self.best_lap,
            )
            unlocked = (", unlocked: " + ", ".join(result["unlocked"])
                        if result["unlocked"] else "")
            payout_text = (f"Event reward: +{result['payout']:,} credits"
                           f"{unlocked}\nWallet: {self.profile.credits:,}")
        self.result_label["text"] = "RACE COMPLETE"
        best = self._format_time(self.best_lap) if self.best_lap else "--:--.--"
        self.result_details["text"] = (
            f"Event: {self.current_event.name if self.current_event else self.mode}\n"
            f"Time: {self._format_time(self.race_time)}\n"
            f"Best lap: {best}\n{payout_text}"
        )
        self.pause_menu.hide()
        self.hud_text.hide()
        self.hud_bottom.hide()
        self.gauge_root.hide()
        self.result_menu.show()

    def _refresh_hud_status(self, message: str) -> None:
        self.network_error = message

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds // 60)
        remainder = seconds - minutes * 60
        return f"{minutes:02d}:{remainder:05.2f}"

    def _update_hud(self) -> None:
        assert self.physics is not None
        p = self.physics
        offroad = "  |  OFF ROAD" if not p.on_track else ""
        remote_count = len(self.remote_cars)
        network_line = ""
        if self.mode.startswith("LAN"):
            network_line = f"\nLAN PLAYERS  {remote_count + 1}"
        elif self.mode == "ONLINE":
            network_line = f"\nONLINE PLAYERS  {remote_count + 1}"
            if isinstance(self.network_session, OnlineSession) and not self.network_session.connected:
                network_line = "\nONLINE CONNECTING..."
        if self.network_error:
            network_line += f"\n{self.network_error[:48]}"
        if self.current_event is not None:
            event_line = (f"{self.current_event.name}\n"
                          f"CHECKPOINT  {self.event_target_index + 1}/"
                          f"{len(self.event_targets)}   LAP {self.event_lap}/"
                          f"{self.event_laps}")
        else:
            event_line = f"FREE ROAM  /  {self._format_time(self.race_time)}"
        self.hud_text.setText(
            f"RGDVD  /  {self.mode}\n"
            f"DIST  {p.distance_m / 1000.0:07.2f} km\n"
            f"{event_line}{network_line}{offroad}"
        )
        self._update_dashboard_gauges()
        self.hud_bottom.setText(
            "W/↑ GAS   S/↓ BRAKE   A/D STEER   SPACE HANDBRAKE   Q/E SHIFT   F7 GEARBOX   R RESET"
        )

    def _camera_update(self, task):
        if self.state == "RACING" and self.physics is not None:
            dt = min(globalClock.getDt(), 1.0 / 20.0)
            p = self.physics
            fx, fy = -math.sin(p.heading), math.cos(p.heading)
            speed_factor = min(1.0, abs(p.speed) / 55.0)
            distance = 13.5 + speed_factor * 2.5
            desired_x = p.x - fx * distance
            desired_y = p.y - fy * distance
            desired_z = 6.0 + speed_factor * 1.8
            current = self.camera.getPos()
            blend = min(1.0, dt * 3.6)
            self.camera.setPos(
                current.x + (desired_x-current.x)*blend,
                current.y + (desired_y-current.y)*blend,
                current.z + (desired_z-current.z)*blend)
            self.camera.lookAt(p.x, p.y, 1.15)
            self.camLens.setFov(70.0 + speed_factor * 8.0)
        return task.cont

    def userExit(self) -> None:
        self._close_network()
        if self.audio:
            self.audio.stop()
        save_config(self.game_config)
        super().userExit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RGDVD 3D racing runtime")
    parser.add_argument("--mode", choices=("free", "event", "host-lan", "join-lan", "online"), default="menu")
    parser.add_argument("--event-id", default="")
    parser.add_argument("--nickname", default="Driver")
    parser.add_argument("--room", default="OPEN-LOBBY")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL)
    args = parser.parse_args()

    game = RGDVDGame()
    game.nickname_entry.enterText(args.nickname)
    game.room_entry.enterText(args.room)
    game.server_entry.enterText(args.server)
    if args.mode == "free":
        game.start_career()
    elif args.mode == "event":
        game.start_selected_event(args.event_id)
    elif args.mode == "host-lan":
        game.host_lan()
    elif args.mode == "join-lan":
        game.join_lan()
    elif args.mode == "online":
        game.join_online()
    game.run()

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
    TextNode, Vec4, WindowProperties, loadPrcFileData,
)

from rgdvd import __version__
from rgdvd.ai import AIDriver
from rgdvd.config import load_config, save_config
from rgdvd.network import LanSession
from rgdvd.online import OnlineSession
from rgdvd.physics import Controls, VehiclePhysics
from rgdvd.profile import CareerProfile
from rgdvd.track import RacingCircuit
from rgdvd.vehicle import SportsCar


loadPrcFileData("", "win-size 1366 768")
loadPrcFileData("", "sync-video true")
loadPrcFileData("", "show-frame-rate-meter false")
loadPrcFileData("", "framebuffer-srgb true")
loadPrcFileData("", "textures-power-2 none")


class RGDVDGame(ShowBase):
    PAINTS = [
        ("GT Red", (0.64, 0.018, 0.012, 1.0)),
        ("Electric Blue", (0.025, 0.17, 0.66, 1.0)),
        ("Competition Yellow", (0.88, 0.55, 0.025, 1.0)),
        ("Graphite", (0.13, 0.15, 0.17, 1.0)),
        ("Pearl White", (0.78, 0.80, 0.82, 1.0)),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.44, 0.61, 0.75, 1)
        self.config = load_config()
        self.profile = CareerProfile()
        props = WindowProperties()
        props.setTitle(f"RGDVD {__version__} | Racing")
        props.setCursorHidden(False)
        props.setSize(int(self.config.get("width", 1366)),
                      int(self.config.get("height", 768)))
        self.win.requestProperties(props)
        self.camLens.setNearFar(0.1, 1800.0)
        self.camLens.setFov(72)
        self.render.setAntialias(AntialiasAttrib.MAuto)

        self.state = "MENU"
        self.mode = "QUICK"
        self.scene_root = None
        self.car: SportsCar | None = None
        self.track: RacingCircuit | None = None
        self.physics: VehiclePhysics | None = None
        self.ai_drivers: list[AIDriver] = []
        self.remote_cars: dict[str, SportsCar] = {}
        self.network_session: LanSession | OnlineSession | None = None
        self.network_error: str | None = None
        self.last_network_send = 0.0
        self.race_time = 0.0
        self.lap = 1
        self.last_x = 0.0
        self.last_lap_time = 0.0
        self.best_lap: float | None = None
        self.paint_index = max(0, min(
            len(self.PAINTS)-1, int(self.config.get("paint_index", 0))))
        self.controls = {key: False for key in (
            "w", "s", "a", "d", "arrow_up", "arrow_down",
            "arrow_left", "arrow_right", "space",
        )}
        self._setup_menu()
        self._bind_events()
        self.taskMgr.add(self._game_update, "rgdvd-game-update")
        self.taskMgr.add(self._camera_update, "rgdvd-camera-update")

    def _setup_menu(self) -> None:
        self.menu = DirectFrame(
            frameColor=(0.018, 0.027, 0.040, 0.96),
            frameSize=(-1.333, 1.333, -1.0, 1.0), pos=(0, 0, 0),
        )
        DirectLabel(
            parent=self.menu, text="RGDVD", text_scale=0.16,
            text_fg=(0.94, 0.96, 0.97, 1), text_shadow=(0, 0, 0, 0.7),
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.88),
        )
        DirectLabel(
            parent=self.menu, text="REAL DRIVING. ONE DISC. THREE WAYS TO RACE.",
            text_scale=0.029, text_fg=(0.56, 0.68, 0.75, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.73),
        )
        DirectLabel(
            parent=self.menu, text="DRIVER NAME",
            text_scale=0.025, text_fg=(0.69, 0.75, 0.79, 1),
            frameColor=(0, 0, 0, 0), pos=(-0.56, 0, 0.57),
        )
        self.nickname_entry = DirectEntry(
            parent=self.menu, initialText=str(self.config.get("nickname", "Driver")),
            numLines=1, width=14, scale=0.043, pos=(-0.82, 0, 0.49),
            frameColor=(0.11, 0.15, 0.19, 1),
            text_fg=(0.96, 0.97, 0.98, 1), cursorKeys=1,
        )
        DirectLabel(
            parent=self.menu, text="ROOM CODE",
            text_scale=0.025, text_fg=(0.69, 0.75, 0.79, 1),
            frameColor=(0, 0, 0, 0), pos=(0.56, 0, 0.57),
        )
        self.room_entry = DirectEntry(
            parent=self.menu, initialText=str(self.config.get("room", "OPEN-LOBBY")),
            numLines=1, width=14, scale=0.043, pos=(0.23, 0, 0.49),
            frameColor=(0.11, 0.15, 0.19, 1),
            text_fg=(0.96, 0.97, 0.98, 1), cursorKeys=1,
        )

        self._menu_button("CAREER", -0.52, 0.22, self.start_career)
        self._menu_button("QUICK RACE", 0.52, 0.22, self.start_quick_race)
        self._menu_button("HOST LAN", -0.52, 0.02, self.host_lan)
        self._menu_button("FIND LAN GAME", 0.52, 0.02, self.join_lan)
        self._menu_button("ONLINE ROOM", -0.52, -0.18, self.join_online)
        self._menu_button("CHANGE CAR COLOUR", 0.52, -0.18, self.change_paint)
        self._menu_button("GRAPHICS SETTINGS", -0.52, -0.38, self.cycle_quality)
        self._menu_button("EXIT", 0.52, -0.38, self.userExit)

        self.menu_status = DirectLabel(
            parent=self.menu, text=self._menu_summary(),
            text_scale=0.025, text_fg=(0.62, 0.76, 0.81, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, -0.63),
        )
        DirectLabel(
            parent=self.menu,
            text="W/↑ GAS     S/↓ BRAKE     A/D STEER     SPACE HANDBRAKE     R RESET     ESC PAUSE",
            text_scale=0.023, text_fg=(0.58, 0.64, 0.69, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, -0.84),
        )

        self.pause_menu = DirectFrame(
            frameColor=(0.015, 0.022, 0.032, 0.90),
            frameSize=(-1.333, 1.333, -1.0, 1.0), pos=(0, 0, 0),
        )
        DirectLabel(parent=self.pause_menu, text="PAUSED",
                    text_scale=0.13, text_fg=(0.96, 0.97, 0.98, 1),
                    frameColor=(0, 0, 0, 0), pos=(0, 0, 0.31))
        DirectButton(parent=self.pause_menu, text="RESUME",
                     text_scale=0.05, scale=1.0, pos=(0, 0, 0.06),
                     frameColor=(0.70, 0.055, 0.035, 1),
                     command=self.resume_race)
        DirectButton(parent=self.pause_menu, text="RESTART RACE",
                     text_scale=0.045, scale=0.9, pos=(0, 0, -0.14),
                     frameColor=(0.10, 0.13, 0.16, 1),
                     command=self.restart_race)
        DirectButton(parent=self.pause_menu, text="RETURN TO MENU",
                     text_scale=0.04, scale=0.85, pos=(0, 0, -0.34),
                     frameColor=(0.10, 0.13, 0.16, 1),
                     command=self.return_to_menu)
        self.pause_menu.hide()

        self.result_menu = DirectFrame(
            frameColor=(0.015, 0.022, 0.032, 0.92),
            frameSize=(-1.333, 1.333, -1.0, 1.0), pos=(0, 0, 0),
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
                     text_scale=0.045, scale=0.9, pos=(0, 0, -0.28),
                     frameColor=(0.70, 0.055, 0.035, 1),
                     command=self.return_to_menu)
        self.result_menu.hide()

        self.hud_text = OnscreenText(
            text="", pos=(-1.28, 0.91), scale=0.043,
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

    def _menu_button(self, text: str, x: float, z: float, command: Any) -> None:
        DirectButton(
            parent=self.menu, text=text, text_scale=0.038,
            text_fg=(0.95, 0.96, 0.97, 1), frameColor=(0.12, 0.17, 0.21, 1),
            relief=1, borderWidth=(0.008, 0.008),
            scale=0.78, pos=(x, 0, z), command=command,
        )

    def _menu_summary(self) -> str:
        wins = self.profile.data.get("wins", 0)
        races = self.profile.data.get("races", 0)
        paint_name = self.PAINTS[self.paint_index][0]
        quality = str(self.config.get("quality", "medium")).upper()
        return (f"CAREER  {races} RACES / {wins} WINS     "
                f"CREDITS  {self.profile.credits:,}     "
                f"CAR  {paint_name}     GRAPHICS  {quality}")

    def _refresh_menu(self, message: str | None = None) -> None:
        self.menu_status["text"] = message or self._menu_summary()

    def _nickname(self) -> str:
        value = self.nickname_entry.get().strip()[:20]
        return value or "Driver"

    def _room(self) -> str:
        value = self.room_entry.get().strip()[:32]
        return value or "OPEN-LOBBY"

    def _save_menu_settings(self) -> None:
        self.config["nickname"] = self._nickname()
        self.config["room"] = self._room()
        self.config["paint_index"] = self.paint_index
        save_config(self.config)

    def _bind_events(self) -> None:
        for key in self.controls:
            self.accept(key, self._set_control, [key, True])
            self.accept(key + "-up", self._set_control, [key, False])
        self.accept("escape", self.toggle_pause)
        self.accept("r", self.restart_race)

    def _set_control(self, key: str, value: bool) -> None:
        self.controls[key] = value

    def change_paint(self) -> None:
        self.paint_index = (self.paint_index + 1) % len(self.PAINTS)
        self._save_menu_settings()
        self._refresh_menu()

    def cycle_quality(self) -> None:
        qualities = ("low", "medium", "high")
        current = str(self.config.get("quality", "medium")).lower()
        self.config["quality"] = qualities[(qualities.index(current) + 1)
                                           % len(qualities)] if current in qualities else "medium"
        save_config(self.config)
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
        self._save_menu_settings()
        self._close_network()
        self.start_race("QUICK")

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
            base_url = str(self.config.get("server_url", "")).strip()
            self.network_session = OnlineSession(base_url, self._room(), self._nickname())
            self.start_race("ONLINE")
            self._refresh_hud_status("CONNECTING TO ONLINE ROOM...")
        except (RuntimeError, ValueError) as exc:
            self._refresh_menu(str(exc))

    def _setup_lighting(self) -> None:
        ambient = AmbientLight("soft-sky-ambient")
        quality = str(self.config.get("quality", "medium")).lower()
        ambient.setColor(Vec4(0.52 if quality == "low" else 0.43,
                              0.55 if quality == "low" else 0.47,
                              0.60 if quality == "low" else 0.53, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("late-afternoon-sun")
        sun.setColor(Vec4(1.0, 0.91, 0.77, 1))
        if self.config.get("shadows", True) and quality != "low":
            sun.setShadowCaster(True, 1024 if quality == "medium" else 2048,
                                1024 if quality == "medium" else 2048)
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-32, -48, 0)
        self.render.setLight(sun_np)
        self.render.setShaderAuto()

        fog = Fog("distance-haze")
        fog.setColor(0.44, 0.61, 0.75)
        fog.setExpDensity(0.00095 if quality == "low" else 0.00082)
        self.render.setFog(fog)

    def _build_scene(self) -> None:
        if self.scene_root is not None:
            self.scene_root.removeNode()
        self.scene_root = self.render.attachNewNode("race-scene")
        self._setup_lighting()
        self.track = RacingCircuit(self.scene_root)
        self.physics = VehiclePhysics()
        paint = self.PAINTS[self.paint_index][1]
        self.car = SportsCar(self.scene_root, paint=paint)
        self.ai_drivers = []
        self.remote_cars = {}
        if self.mode in ("CAREER", "QUICK"):
            opponent_paints = (
                (0.025, 0.17, 0.66, 1.0),
                (0.88, 0.55, 0.025, 1.0),
                (0.62, 0.66, 0.68, 1.0),
            )
            for index, opponent_paint in enumerate(opponent_paints, start=1):
                self.ai_drivers.append(AIDriver(
                    self.scene_root, self.track,
                    -math.pi / 2 + index * 0.72, opponent_paint, f"AI-{index}"
                ))
        self.camera.setPos(0, -163, 8)
        self.camera.lookAt(0, -148, 1)

    def start_race(self, mode: str = "QUICK") -> None:
        self.mode = mode
        self._build_scene()
        self.menu.hide()
        self.pause_menu.hide()
        self.result_menu.hide()
        self.hud_text.show()
        self.hud_bottom.show()
        self.state = "RACING"
        self.race_time = 0.0
        self.lap = 1
        self.last_lap_time = 0.0
        self.best_lap = None
        self.last_x = 0.0
        self.last_network_send = 0.0

    def restart_race(self) -> None:
        if self.physics is None or self.car is None:
            return
        self.physics.reset()
        self.car.reset_pose()
        for driver in self.ai_drivers:
            driver.physics.reset(driver.physics.x, driver.physics.y, driver.physics.heading)
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

    def toggle_pause(self) -> None:
        if self.state == "RACING":
            self.state = "PAUSED"
            self.pause_menu.show()
        elif self.state == "PAUSED":
            self.resume_race()

    def resume_race(self) -> None:
        self.state = "RACING"
        self.pause_menu.hide()

    def return_to_menu(self) -> None:
        self.state = "MENU"
        self._close_network()
        if self.scene_root is not None:
            self.scene_root.removeNode()
            self.scene_root = None
        self.pause_menu.hide()
        self.result_menu.hide()
        self.hud_text.hide()
        self.hud_bottom.hide()
        self.menu.show()
        self._refresh_menu()

    def _game_update(self, task):
        dt = min(globalClock.getDt(), 1.0 / 30.0)
        if self.state == "RACING" and self.physics and self.car and self.track:
            throttle = float(self.controls["w"] or self.controls["arrow_up"])
            brake = float(self.controls["s"] or self.controls["arrow_down"])
            steer = float(self.controls["a"] or self.controls["arrow_left"]) - float(
                self.controls["d"] or self.controls["arrow_right"])
            self.physics.on_track = self.track.contains(self.physics.x, self.physics.y)
            self.physics.update(Controls(
                throttle=throttle, brake=brake, steer=steer,
                handbrake=self.controls["space"]), dt)
            self.car.update(self.physics.x, self.physics.y, self.physics.heading,
                            self.physics.speed, self.physics.steer_angle, dt)

            for driver in self.ai_drivers:
                driver.physics.on_track = self.track.contains(
                    driver.physics.x, driver.physics.y)
                driver.update(dt)

            self._update_network(dt)
            self._update_laps()
            self.race_time += dt
            self._update_hud()
        return task.cont

    def _update_network(self, dt: float) -> None:
        if self.network_session is None or self.physics is None:
            return
        now = time.monotonic()
        if now - self.last_network_send >= 1/15:
            self.last_network_send = now
            self.network_session.send_state(self.physics.snapshot())
        for player in self.network_session.poll():
            player_id = str(player.get("id", ""))
            state = player.get("state", {})
            if not player_id or not isinstance(state, dict):
                continue
            if player_id not in self.remote_cars and self.scene_root is not None:
                self.remote_cars[player_id] = SportsCar(
                    self.scene_root, paint=(0.03, 0.30, 0.74, 1.0))
            car = self.remote_cars.get(player_id)
            if car is not None:
                try:
                    car.update(float(state.get("x", 0)),
                               float(state.get("y", -148)),
                               float(state.get("heading", -1.5708)),
                               float(state.get("speed", 0)), 0.0, dt)
                except (TypeError, ValueError):
                    pass
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
        payout_text = "Online/LAN result - career rewards not applied."
        if self.mode == "CAREER" and self.physics is not None:
            result = self.profile.record_race(
                self.race_time, self.physics.distance_m / 1000.0, 1,
                self.best_lap,
            )
            unlocked = (", unlocked: " + ", ".join(result["unlocked"])
                        if result["unlocked"] else "")
            payout_text = (f"Career reward: +{result['payout']:,} credits"
                           f"{unlocked}\nWallet: {self.profile.credits:,}")
        self.result_label["text"] = "RACE COMPLETE"
        best = self._format_time(self.best_lap) if self.best_lap else "--:--.--"
        self.result_details["text"] = (
            f"Mode: {self.mode}\n"
            f"Time: {self._format_time(self.race_time)}\n"
            f"Best lap: {best}\n{payout_text}"
        )
        self.pause_menu.hide()
        self.hud_text.hide()
        self.hud_bottom.hide()
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
        offroad = "  |  OFF TRACK" if not p.on_track else ""
        best = self._format_time(self.best_lap) if self.best_lap is not None else "--:--.--"
        remote_count = len(self.remote_cars)
        network_line = ""
        if self.mode.startswith("LAN"):
            network_line = f"\nLAN PLAYERS  {remote_count + 1}"
        elif self.mode == "ONLINE":
            network_line = f"\nONLINE PLAYERS  {remote_count + 1}"
            if isinstance(self.network_session, OnlineSession) and not self.network_session.connected:
                network_line = "\nONLINE CONNECTING..."
        self.hud_text.setText(
            f"RGDVD  /  {self.mode}\n"
            f"{p.speed_kmh:06.1f} km/h\n"
            f"GEAR  {p.gear}     RPM  {int(p.rpm):04d}\n"
            f"LAP   {min(self.lap, 3):02d} / 03\n"
            f"TIME  {self._format_time(self.race_time)}\n"
            f"BEST  {best}{network_line}{offroad}"
        )
        self.hud_bottom.setText(
            "W/↑ THROTTLE   S/↓ BRAKE   A/D STEER   SPACE HANDBRAKE   R RESET   ESC PAUSE"
        )

    def _camera_update(self, task):
        if self.state == "RACING" and self.physics is not None:
            dt = min(globalClock.getDt(), 1.0 / 20.0)
            p = self.physics
            fx, fy = -math.sin(p.heading), math.cos(p.heading)
            speed_factor = min(1.0, abs(p.speed) / 55.0)
            distance = 10.5 + speed_factor * 2.0
            desired_x = p.x - fx * distance
            desired_y = p.y - fy * distance
            desired_z = 4.1 + speed_factor * 1.7
            current = self.camera.getPos()
            blend = min(1.0, dt * 4.5)
            self.camera.setPos(
                current.x + (desired_x-current.x)*blend,
                current.y + (desired_y-current.y)*blend,
                current.z + (desired_z-current.z)*blend)
            self.camera.lookAt(p.x, p.y, 1.15)
            self.camLens.setFov(70.0 + speed_factor * 8.0)
        return task.cont

    def userExit(self) -> None:
        self._close_network()
        save_config(self.config)
        super().userExit()


if __name__ == "__main__":
    RGDVDGame().run()

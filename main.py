"""RGDVD - Python 3D racing game prototype.

Install and run:
    python -m pip install -r requirements.txt
    python main.py
"""
from __future__ import annotations

import math

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    AmbientLight, AntialiasAttrib, DirectionalLight, Fog,
    TextNode, Vec4, WindowProperties, loadPrcFileData,
)

from rgdvd import __version__
from rgdvd.ai import AIDriver
from rgdvd.physics import Controls, VehiclePhysics
from rgdvd.track import RacingCircuit
from rgdvd.vehicle import SportsCar


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
        props = WindowProperties()
        props.setTitle(f"RGDVD {__version__} | Racing prototype")
        props.setCursorHidden(False)
        self.win.requestProperties(props)
        self.camLens.setNearFar(0.1, 1800.0)
        self.camLens.setFov(72)
        self.render.setAntialias(AntialiasAttrib.MAuto)

        self.state = "MENU"
        self.scene_root = None
        self.car: SportsCar | None = None
        self.track: RacingCircuit | None = None
        self.physics: VehiclePhysics | None = None
        self.ai_drivers: list[AIDriver] = []
        self.race_time = 0.0
        self.lap = 1
        self.last_x = 0.0
        self.last_lap_time = 0.0
        self.best_lap: float | None = None
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
            frameColor=(0.018, 0.027, 0.040, 0.94),
            frameSize=(-1.333, 1.333, -1.0, 1.0),
            pos=(0, 0, 0),
        )
        DirectLabel(
            parent=self.menu, text="RGDVD", text_scale=0.19,
            text_fg=(0.94, 0.96, 0.97, 1),
            text_shadow=(0, 0, 0, 0.7), frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.42),
        )
        DirectLabel(
            parent=self.menu, text="REALISTIC DRIVING / PYTHON 3D PROJECT",
            text_scale=0.034, text_fg=(0.56, 0.68, 0.75, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, 0.28),
        )
        self.start_button = DirectButton(
            parent=self.menu, text="START RACE", text_scale=0.055,
            text_fg=(1, 1, 1, 1), frameColor=(0.70, 0.055, 0.035, 1),
            relief=1, borderWidth=(0.01, 0.01),
            scale=1.0, pos=(0, 0, -0.02),
            command=self.start_race,
        )
        self.exit_button = DirectButton(
            parent=self.menu, text="EXIT", text_scale=0.045,
            text_fg=(0.82, 0.86, 0.88, 1), frameColor=(0.10, 0.13, 0.16, 1),
            relief=1, borderWidth=(0.01, 0.01),
            scale=0.9, pos=(0, 0, -0.20), command=self.userExit,
        )
        DirectLabel(
            parent=self.menu,
            text="W / S  throttle & brake     A / D  steering     SPACE  handbrake     ESC  pause",
            text_scale=0.028, text_fg=(0.67, 0.72, 0.76, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, -0.60),
        )
        DirectLabel(
            parent=self.menu, text="EARLY PLAYABLE BUILD  |  OFFLINE MODE",
            text_scale=0.024, text_fg=(0.40, 0.50, 0.57, 1),
            frameColor=(0, 0, 0, 0), pos=(0, 0, -0.83),
        )

        self.pause_menu = DirectFrame(
            frameColor=(0.015, 0.022, 0.032, 0.88),
            frameSize=(-1.333, 1.333, -1.0, 1.0),
            pos=(0, 0, 0),
        )
        DirectLabel(
            parent=self.pause_menu, text="PAUSED", text_scale=0.13,
            text_fg=(0.96, 0.97, 0.98, 1), frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.26),
        )
        DirectButton(
            parent=self.pause_menu, text="RESUME", text_scale=0.05,
            text_fg=(1, 1, 1, 1), frameColor=(0.70, 0.055, 0.035, 1),
            scale=1.0, pos=(0, 0, -0.02), command=self.resume_race,
        )
        DirectButton(
            parent=self.pause_menu, text="RESTART", text_scale=0.045,
            text_fg=(0.9, 0.92, 0.94, 1), frameColor=(0.10, 0.13, 0.16, 1),
            scale=0.9, pos=(0, 0, -0.20), command=self.restart_race,
        )
        self.pause_menu.hide()

        self.hud_text = OnscreenText(
            text="", pos=(-1.28, 0.91), scale=0.047,
            fg=(0.95, 0.97, 0.98, 1), align=TextNode.ALeft,
            shadow=(0, 0, 0, 0.8), mayChange=True,
        )
        self.hud_text.hide()
        self.hud_bottom = OnscreenText(
            text="", pos=(0, -0.92), scale=0.032,
            fg=(0.90, 0.93, 0.94, 1), shadow=(0, 0, 0, 0.8),
            mayChange=True,
        )
        self.hud_bottom.hide()

    def _bind_events(self) -> None:
        for key in self.controls:
            self.accept(key, self._set_control, [key, True])
            self.accept(key + "-up", self._set_control, [key, False])
        self.accept("escape", self.toggle_pause)
        self.accept("r", self.restart_race)

    def _set_control(self, key: str, value: bool) -> None:
        self.controls[key] = value

    def _setup_lighting(self) -> None:
        ambient = AmbientLight("soft-sky-ambient")
        ambient.setColor(Vec4(0.43, 0.47, 0.53, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("late-afternoon-sun")
        sun.setColor(Vec4(1.0, 0.91, 0.77, 1))
        # 1024 shadow map keeps the first build friendlier to integrated GPUs.
        sun.setShadowCaster(True, 1024, 1024)
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-32, -48, 0)
        self.render.setLight(sun_np)
        self.render.setShaderAuto()

        fog = Fog("distance-haze")
        fog.setColor(0.44, 0.61, 0.75)
        fog.setExpDensity(0.00082)
        self.render.setFog(fog)

    def _build_scene(self) -> None:
        if self.scene_root is not None:
            self.scene_root.removeNode()
        self.scene_root = self.render.attachNewNode("race-scene")
        self._setup_lighting()
        self.track = RacingCircuit(self.scene_root)
        self.physics = VehiclePhysics()
        self.car = SportsCar(self.scene_root)
        self.ai_drivers = []
        opponent_paints = (
            (0.025, 0.17, 0.66, 1.0),
            (0.88, 0.55, 0.025, 1.0),
            (0.62, 0.66, 0.68, 1.0),
        )
        for index, paint in enumerate(opponent_paints, start=1):
            start_angle = -math.pi / 2 + index * 0.72
            self.ai_drivers.append(AIDriver(
                self.scene_root, self.track, start_angle, paint, f"AI-{index}"
            ))
        self.camera.setPos(0, -163, 8)
        self.camera.lookAt(0, -148, 1)

    def start_race(self) -> None:
        self._build_scene()
        self.menu.hide()
        self.pause_menu.hide()
        self.hud_text.show()
        self.hud_bottom.show()
        self.state = "RACING"
        self.race_time = 0.0
        self.lap = 1
        self.last_lap_time = 0.0
        self.best_lap = None
        self.last_x = 0.0

    def restart_race(self) -> None:
        if self.physics is None or self.car is None:
            self.start_race()
            return
        self.physics.reset()
        self.car.reset_pose()
        self.race_time = 0.0
        self.lap = 1
        self.last_lap_time = 0.0
        self.last_x = 0.0
        self.best_lap = None
        self.state = "RACING"
        self.pause_menu.hide()
        self.menu.hide()
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

    def _game_update(self, task):
        dt = min(globalClock.getDt(), 1.0 / 30.0)
        if self.state == "RACING" and self.physics and self.car and self.track:
            throttle = float(self.controls["w"] or self.controls["arrow_up"])
            brake = float(self.controls["s"] or self.controls["arrow_down"])
            steer = float(self.controls["a"] or self.controls["arrow_left"]) - float(
                self.controls["d"] or self.controls["arrow_right"]
            )
            self.physics.on_track = self.track.contains(self.physics.x, self.physics.y)
            self.physics.update(Controls(
                throttle=throttle, brake=brake, steer=steer,
                handbrake=self.controls["space"],
            ), dt)
            self.car.update(self.physics.x, self.physics.y, self.physics.heading,
                            self.physics.speed, self.physics.steer_angle, dt)
            for driver in self.ai_drivers:
                driver.update(dt)
            self._update_laps()
            self.race_time += dt
            self._update_hud()
        return task.cont

    def _update_laps(self) -> None:
        assert self.physics is not None
        x, y = self.physics.x, self.physics.y
        if self.last_x < 0.0 <= x and y < -137.0 and self.physics.speed > 3.0:
            if self.race_time > 8.0:
                lap_time = self.race_time - self.last_lap_time
                self.last_lap_time = self.race_time
                self.lap += 1
                if self.best_lap is None or lap_time < self.best_lap:
                    self.best_lap = lap_time
        self.last_x = x

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
        self.hud_text.setText(
            f"RGDVD  /  CIRCUIT TEST\n"
            f"{p.speed_kmh:06.1f} km/h\n"
            f"GEAR  {p.gear}     RPM  {int(p.rpm):04d}\n"
            f"LAP   {self.lap:02d}\n"
            f"TIME  {self._format_time(self.race_time)}\n"
            f"BEST  {best}    RIVALS  {len(self.ai_drivers):02d}{offroad}"
        )
        self.hud_bottom.setText(
            "W / ↑  THROTTLE     S / ↓  BRAKE     A / D  STEER     SPACE  HANDBRAKE     R  RESET     ESC  PAUSE"
        )

    def _camera_update(self, task):
        if self.state == "RACING" and self.physics is not None:
            dt = min(globalClock.getDt(), 1.0 / 20.0)
            p = self.physics
            forward_x = -math.sin(p.heading)
            forward_y = math.cos(p.heading)
            speed_factor = min(1.0, abs(p.speed) / 55.0)
            distance = 10.5 + speed_factor * 2.0
            desired_x = p.x - forward_x * distance
            desired_y = p.y - forward_y * distance
            desired_z = 4.1 + speed_factor * 1.7
            current = self.camera.getPos()
            blend = min(1.0, dt * 4.5)
            self.camera.setPos(
                current.x + (desired_x-current.x)*blend,
                current.y + (desired_y-current.y)*blend,
                current.z + (desired_z-current.z)*blend,
            )
            self.camera.lookAt(p.x, p.y, 1.15)
            self.camLens.setFov(70.0 + speed_factor * 8.0)
        return task.cont


if __name__ == "__main__":
    RGDVDGame().run()

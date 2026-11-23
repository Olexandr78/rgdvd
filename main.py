"""RGDVD - first playable 3D racing prototype.

Run:
    python -m pip install -r requirements.txt
    python main.py

Controls:
    W / Up       accelerate
    S / Down     brake / reverse
    A,D / arrows steer
    Space        handbrake
    R            reset car
    Esc          quit

This is an early arcade-physics prototype. Detailed vehicle simulation,
multiplayer, and production art are planned for later milestones.
"""
import math

from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    AmbientLight, DirectionalLight, Vec3, Vec4,
    Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, WindowProperties,
    TextNode, Fog
)


def make_mesh(parent, name, vertices, triangles, color):
    """Create a simple vertex-colored triangle mesh."""
    data = GeomVertexData(name, GeomVertexFormat.getV3(), Geom.UHStatic)
    writer = GeomVertexWriter(data, "vertex")
    for vertex in vertices:
        writer.addData3(*vertex)

    prim = GeomTriangles(Geom.UHStatic)
    for a, b, c in triangles:
        prim.addVertices(a, b, c)
        prim.closePrimitive()

    geom = Geom(data)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    path = parent.attachNewNode(node)
    path.setColor(*color)
    path.setTwoSided(True)
    return path


def make_box(parent, name, center, size, color):
    cx, cy, cz = center
    sx, sy, sz = (v / 2 for v in size)
    vertices = [
        (cx-sx, cy-sy, cz-sz), (cx+sx, cy-sy, cz-sz),
        (cx+sx, cy+sy, cz-sz), (cx-sx, cy+sy, cz-sz),
        (cx-sx, cy-sy, cz+sz), (cx+sx, cy-sy, cz+sz),
        (cx+sx, cy+sy, cz+sz), (cx-sx, cy+sy, cz+sz),
    ]
    triangles = [
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    ]
    return make_mesh(parent, name, vertices, triangles, color)


def make_cylinder(parent, name, radius, depth, color, segments=16):
    vertices = []
    triangles = []
    for z in (-depth / 2, depth / 2):
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            vertices.append((radius * math.cos(angle),
                             radius * math.sin(angle), z))
    bottom_center = len(vertices)
    vertices.append((0, 0, -depth / 2))
    top_center = len(vertices)
    vertices.append((0, 0, depth / 2))
    for i in range(segments):
        j = (i + 1) % segments
        triangles.extend([
            (i, j, segments + j), (i, segments + j, segments + i),
            (bottom_center, j, i),
            (top_center, segments + i, segments + j),
        ])
    return make_mesh(parent, name, vertices, triangles, color)


class RGDVD(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.48, 0.68, 0.88, 1)
        props = WindowProperties()
        props.setTitle("RGDVD - Racing Game Prototype")
        props.setSize(1280, 720)
        self.win.requestProperties(props)

        self.speed = 0.0
        self.heading = -90.0
        self.max_speed = 72.0
        self.acceleration = 30.0
        self.braking = 52.0
        self.steer_rate = 78.0
        self.keys = {key: False for key in
                     ("w", "s", "a", "d", "space", "arrow_up",
                      "arrow_down", "arrow_left", "arrow_right")}

        self.build_world()
        self.build_car()
        self.build_ui()
        self.accept_keys()
        self.taskMgr.add(self.update, "game-update")
        self.taskMgr.add(self.update_camera, "camera-update")

    def build_world(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.48, 0.50, 0.55, 1))
        self.render.setLight(self.render.attachNewNode(ambient))
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(1.0, 0.94, 0.82, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-35, -55, 0)
        self.render.setLight(sun_np)

        fog = Fog("distance-fog")
        fog.setColor(0.48, 0.68, 0.88)
        fog.setExpDensity(0.0018)
        self.render.setFog(fog)

        make_box(self.render, "grass-field", (0, 0, -1.2),
                 (700, 900, 1), (0.16, 0.34, 0.13, 1))
        self.build_track()
        self.build_trackside()

    def build_track(self):
        # A wide closed oval circuit, built from a ring mesh.
        outer_x, outer_y = 105.0, 155.0
        inner_x, inner_y = 68.0, 118.0
        count = 240
        vertices = []
        triangles = []
        for i in range(count):
            angle = 2 * math.pi * i / count
            c, s = math.cos(angle), math.sin(angle)
            vertices.extend([
                (outer_x * c, outer_y * s, -0.55),
                (inner_x * c, inner_y * s, -0.54),
            ])
        for i in range(count):
            j = (i + 1) % count
            a, b = 2*i, 2*i+1
            c, d = 2*j, 2*j+1
            triangles.extend([(a, c, b), (b, c, d)])
        make_mesh(self.render, "asphalt-circuit", vertices, triangles,
                  (0.105, 0.11, 0.12, 1))

        # Dashed center line around the circuit.
        for i in range(0, count, 5):
            angle = 2 * math.pi * (i + 2) / count
            x = 86.5 * math.cos(angle)
            y = 136.5 * math.sin(angle)
            dash = make_box(self.render, "center-line-dash",
                            (x, y, -0.48), (0.65, 4.0, 0.08),
                            (0.88, 0.86, 0.72, 1))
            dash.setH(-math.degrees(angle))

        # Start/finish stripe across the track at the bottom.
        for i in range(12):
            x = -17.0 + i * 2.9
            color = (0.92, 0.92, 0.92, 1) if i % 2 == 0 else (0.08, 0.08, 0.08, 1)
            make_box(self.render, "start-finish", (x, -132.0, -0.43),
                     (2.9, 3.0, 0.08), color)

    def build_trackside(self):
        # Simple low-cost scenery; this is placeholder art, not final assets.
        for i in range(48):
            angle = 2 * math.pi * i / 48
            x = 125 * math.cos(angle)
            y = 178 * math.sin(angle)
            trunk = make_cylinder(self.render, "tree-trunk", 0.8, 7,
                                  (0.25, 0.13, 0.06, 1), 8)
            trunk.setPos(x, y, 2.0)
            crown = make_cylinder(self.render, "tree-crown", 3.2, 8,
                                  (0.08, 0.25, 0.09, 1), 8)
            crown.setPos(x, y, 7.0)

    def build_car(self):
        self.car = self.render.attachNewNode("player-car")
        # Body, cabin, bumpers and lights form a temporary procedural model.
        make_box(self.car, "body", (0, 0, 0.95), (2.05, 4.5, 0.85),
                 (0.72, 0.035, 0.025, 1))
        make_box(self.car, "hood", (0, 1.48, 1.39), (1.92, 1.45, 0.16),
                 (0.82, 0.045, 0.025, 1))
        make_box(self.car, "cabin", (0, -0.25, 1.65), (1.65, 2.0, 0.9),
                 (0.10, 0.17, 0.20, 1))
        make_box(self.car, "roof", (0, -0.2, 2.12), (1.58, 1.5, 0.12),
                 (0.68, 0.04, 0.025, 1))
        make_box(self.car, "front-bumper", (0, 2.28, 0.72),
                 (2.08, 0.18, 0.28), (0.12, 0.12, 0.13, 1))
        make_box(self.car, "rear-bumper", (0, -2.28, 0.72),
                 (2.08, 0.18, 0.28), (0.12, 0.12, 0.13, 1))
        for x in (-0.72, 0.72):
            make_box(self.car, "headlight", (x, 2.05, 1.12),
                     (0.42, 0.12, 0.2), (0.95, 0.9, 0.65, 1))
            make_box(self.car, "taillight", (x, -2.05, 1.1),
                     (0.42, 0.12, 0.2), (0.8, 0.015, 0.01, 1))
        self.wheels = []
        for x in (-1.05, 1.05):
            for y in (-1.45, 1.45):
                wheel = make_cylinder(self.car, "tire", 0.48, 0.28,
                                      (0.025, 0.025, 0.028, 1), 20)
                wheel.setPos(x, y, 0.55)
                wheel.setP(90)
                self.wheels.append(wheel)

        self.reset_car()

    def build_ui(self):
        self.hud = OnscreenText(
            text="", pos=(-1.28, 0.88), scale=0.052,
            fg=(1, 1, 1, 1), align=TextNode.ALeft,
            mayChange=True, shadow=(0, 0, 0, 0.8)
        )
        OnscreenText(
            text="W/↑ accelerate   S/↓ brake   A,D/←,→ steer   SPACE handbrake   R reset",
            pos=(0, -0.94), scale=0.038, fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.8)
        )

    def accept_keys(self):
        for key in self.keys:
            self.accept(key, self.set_key, [key, True])
            self.accept(key + "-up", self.set_key, [key, False])
        self.accept("r", self.reset_car)
        self.accept("escape", self.userExit)

    def set_key(self, key, value):
        self.keys[key] = value

    def reset_car(self):
        self.speed = 0.0
        self.heading = -90.0
        self.car.setPos(0, -132, 0)
        self.car.setH(self.heading)

    def update(self, task):
        dt = min(globalClock.getDt(), 0.05)
        accelerating = self.keys["w"] or self.keys["arrow_up"]
        braking = self.keys["s"] or self.keys["arrow_down"]
        left = self.keys["a"] or self.keys["arrow_left"]
        right = self.keys["d"] or self.keys["arrow_right"]
        handbrake = self.keys["space"]

        if accelerating:
            self.speed += self.acceleration * dt
        elif braking:
            self.speed -= self.braking * dt
        else:
            drag = 9.0 if not handbrake else 34.0
            if self.speed > 0:
                self.speed = max(0, self.speed - drag * dt)
            elif self.speed < 0:
                self.speed = min(0, self.speed + drag * dt)

        self.speed = max(-18, min(self.max_speed, self.speed))
        steer = (1 if left else 0) - (1 if right else 0)
        speed_factor = min(1.0, abs(self.speed) / 12.0)
        if handbrake:
            speed_factor = max(speed_factor, 0.8)
        self.heading += steer * self.steer_rate * speed_factor * dt * (
            1 if self.speed >= 0 else -1
        )
        self.car.setH(self.heading)

        radians = math.radians(self.heading)
        forward = Vec3(-math.sin(radians), math.cos(radians), 0)
        self.car.setPos(self.car.getPos() + forward * self.speed * dt)

        # Small visual wheel spin.
        for wheel in self.wheels:
            wheel.setR(wheel.getR() - self.speed * dt * 45)

        kmh = abs(self.speed) * 3.6
        self.hud.setText(
            f"RGDVD  |  {kmh:05.1f} km/h  |  "
            f"{'REVERSE' if self.speed < -0.5 else 'DRIVE'}"
        )
        return task.cont

    def update_camera(self, task):
        dt = min(globalClock.getDt(), 0.05)
        desired = self.car.getPos() + self.car.getQuat().xform(Vec3(0, -15, 6))
        current = self.camera.getPos()
        blend = min(1.0, dt * 5.0)
        self.camera.setPos(current + (desired - current) * blend)
        self.camera.lookAt(self.car.getPos() + Vec3(0, 0, 1.4))
        return task.cont


if __name__ == "__main__":
    RGDVD().run()

"""Interactive overhead city map for choosing RGDVD street events."""
from __future__ import annotations

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import LineSegs, NodePath, TextNode, Vec4

from .events import EVENTS, EVENT_BY_ID, RaceEvent


class WorldMapScreen:
    def __init__(self, aspect2d: NodePath, on_start, on_back) -> None:
        self.aspect2d = aspect2d
        self.on_start = on_start
        self.on_back = on_back
        self.selected_id = EVENTS[0].event_id
        self.root = DirectFrame(
            frameColor=(0.008, 0.015, 0.026, 0.98),
            frameSize=(-1.78, 1.78, -1.0, 1.0),
            pos=(0, 0, 0),
        )
        DirectLabel(
            parent=self.root, text="CITY MAP",
            text_scale=0.085, text_fg=(0.92, 0.96, 1, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.42, 0, 0.84),
            text_align=TextNode.ALeft,
        )
        DirectLabel(
            parent=self.root, text="RGDVD  /  STREET EVENT SELECT",
            text_scale=0.024, text_fg=(0.25, 0.68, 0.92, 1),
            frameColor=(0, 0, 0, 0), pos=(-1.40, 0, 0.75),
            text_align=TextNode.ALeft,
        )
        DirectFrame(
            parent=self.root, frameColor=(0.025, 0.043, 0.060, 1),
            frameSize=(-1.52, 0.47, -0.83, 0.68), pos=(0, 0, -0.04),
        )
        DirectFrame(
            parent=self.root, frameColor=(0.025, 0.043, 0.060, 1),
            frameSize=(0.57, 1.64, -0.83, 0.68), pos=(0, 0, -0.04),
        )
        self._draw_roads()
        self.markers: dict[str, DirectButton] = {}
        for event in EVENTS:
            x, y = self._map_point(*event.start)
            button = DirectButton(
                parent=self.root, text="◆", text_scale=0.030,
                text_fg=(0.20, 0.78, 1.0, 1),
                frameColor=(0, 0, 0, 0), relief=DGG.FLAT,
                frameSize=(-0.025, 0.025, -0.025, 0.025),
                pos=(x, 0, y), command=self.select_event,
                extraArgs=[event.event_id],
                rolloverSound=None, clickSound=None,
            )
            self.markers[event.event_id] = button

        self.player_marker = DirectLabel(
            parent=self.root, text="▲", text_scale=0.060,
            text_fg=(1.0, 0.76, 0.16, 1),
            frameColor=(0, 0, 0, 0), pos=(-0.52, 0, -0.04),
        )
        for label, x, z in (
            ("DOWNTOWN", -0.52, 0.48),
            ("RESIDENTIAL", -1.22, -0.55),
            ("INDUSTRIAL", 0.10, -0.57),
        ):
            DirectLabel(
                parent=self.root, text=label, text_scale=0.018,
                text_fg=(0.48, 0.58, 0.65, 0.8),
                frameColor=(0, 0, 0, 0), pos=(x, 0, z),
            )

        self.event_title = DirectLabel(
            parent=self.root, text="", text_scale=0.033,
            text_fg=(0.94, 0.97, 1, 1),
            frameColor=(0, 0, 0, 0), pos=(1.10, 0, 0.48),
            text_align=TextNode.ACenter, text_wordwrap=22,
        )
        self.event_type = DirectLabel(
            parent=self.root, text="", text_scale=0.024,
            text_fg=(0.22, 0.72, 0.96, 1),
            frameColor=(0, 0, 0, 0), pos=(1.10, 0, 0.34),
        )
        self.event_info = DirectLabel(
            parent=self.root, text="", text_scale=0.020,
            text_fg=(0.67, 0.76, 0.83, 1),
            frameColor=(0, 0, 0, 0), pos=(1.10, 0, 0.16),
            text_wordwrap=23,
        )
        DirectLabel(
            parent=self.root, text="53 EVENTS  /  24 CIRCUITS  /  29 SPRINTS",
            text_scale=0.018, text_fg=(0.48, 0.62, 0.71, 1),
            frameColor=(0, 0, 0, 0), pos=(1.10, 0, -0.17),
        )
        self.start_button = DirectButton(
            parent=self.root, text="START EVENT",
            text_scale=0.035, text_fg=(0.98, 1, 1, 1),
            frameColor=(0.02, 0.34, 0.50, 1),
            frameSize=(-0.43, 0.43, -0.075, 0.075),
            pos=(1.10, 0, -0.40), command=self._start,
        )
        DirectButton(
            parent=self.root, text="BACK",
            text_scale=0.030, text_fg=(0.85, 0.91, 0.95, 1),
            frameColor=(0.12, 0.16, 0.20, 1),
            frameSize=(-0.30, 0.30, -0.065, 0.065),
            pos=(1.10, 0, -0.61), command=self.on_back,
        )
        DirectLabel(
            parent=self.root, text="CYAN DIAMOND: EVENT     YELLOW TRIANGLE: YOU",
            text_scale=0.017, text_fg=(0.57, 0.68, 0.76, 1),
            frameColor=(0, 0, 0, 0), pos=(-0.52, 0, -0.86),
        )
        self.select_event(self.selected_id)
        self.root.hide()

    @staticmethod
    def _map_point(x: float, y: float) -> tuple[float, float]:
        return (-1.45 + (x + 960.0) / 1920.0 * 1.84,
                -0.79 + (y + 960.0) / 1920.0 * 1.55)

    def _draw_roads(self) -> None:
        lines = LineSegs("map-city-grid")
        lines.setThickness(3.0)
        lines.setColor(0.16, 0.24, 0.30, 1)
        for road in range(-8, 9):
            value = road * 120.0
            x0, z0 = self._map_point(value, -960)
            x1, z1 = self._map_point(value, 960)
            lines.moveTo(x0, 0, z0)
            lines.drawTo(x1, 0, z1)
            x0, z0 = self._map_point(-960, value)
            x1, z1 = self._map_point(960, value)
            lines.moveTo(x0, 0, z0)
            lines.drawTo(x1, 0, z1)
        path = self.root.attachNewNode(lines.create())
        path.setDepthTest(False)
        path.setDepthWrite(False)

    def select_event(self, event_id: str) -> None:
        event = EVENT_BY_ID.get(event_id)
        if event is None:
            return
        self.selected_id = event_id
        for key, marker in self.markers.items():
            marker["text_fg"] = ((1.0, 0.75, 0.16, 1) if key == event_id
                                 else (0.20, 0.78, 1.0, 1))
            marker["text_scale"] = 0.040 if key == event_id else 0.030
        self.event_title["text"] = event.name
        self.event_type["text"] = event.event_type
        length = sum(
            ((event.route[i][0] - event.route[i - 1][0]) ** 2 +
             (event.route[i][1] - event.route[i - 1][1]) ** 2) ** 0.5
            for i in range(1, len(event.route))
        )
        if event.event_type == "CIRCUIT":
            length += ((event.route[0][0] - event.route[-1][0]) ** 2 +
                       (event.route[0][1] - event.route[-1][1]) ** 2) ** 0.5
        self.event_info["text"] = (
            f"Route length: {length / 1000:.2f} km\n"
            f"Laps: {event.laps}\n"
            f"Checkpoints: {len(event.route)}"
        )

    def update_player(self, x: float, y: float) -> None:
        px, pz = self._map_point(x, y)
        self.player_marker.setPos(px, 0, pz)

    def show(self, x: float, y: float) -> None:
        self.update_player(x, y)
        self.root.show()

    def hide(self) -> None:
        self.root.hide()

    def _start(self) -> None:
        self.on_start(self.selected_id)

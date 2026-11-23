# RGDVD

**RGDVD** is a Python 3D racing-game project. The current playable build is an offline circuit-driving prototype with AI rivals; it is the foundation for later LAN and internet multiplayer.

## Current build — 0.2.0

This build replaces the first box-only placeholder with a more substantial prototype:

- Procedural GT-style sports car with body panels, cabin glass, alloy wheels, brake discs, lights, wing and exhausts.
- Closed oval circuit with textured asphalt, painted kerbs, road markings, concrete barriers, a pit building, grandstand, lighting masts and surrounding scenery.
- Three AI rivals that follow the circuit racing line.
- Chase camera with speed-sensitive distance and field of view.
- A dependency-free vehicle model with torque curve, automatic gears, braking/reverse, speed-sensitive steering, handbrake slip, drag and off-track penalties.
- Menu, pause/restart controls, speed/RPM/gear display, lap timer and best-lap tracking.
- Procedural environment materials: no large external art packs are required for this prototype.

**Important:** the car and circuit are procedural prototype assets, not scanned or photorealistic production assets. The handling is a tunable approximation, not a tyre-by-tyre simulator. This is a playable foundation, not a finished AAA game.

## Requirements

- Windows 10/11 or Linux
- Python 3.10 or newer
- Panda3D 1.10.x
- A GPU with working OpenGL drivers

## Run

\`\`\`powershell
python -m pip install -r requirements.txt
python main.py
\`\`\`

## Controls

| Key | Action |
|---|---|
| \`W\` / \`↑\` | Throttle |
| \`S\` / \`↓\` | Brake; reverse after stopping |
| \`A\` / \`←\` | Steer left |
| \`D\` / \`→\` | Steer right |
| \`Space\` | Handbrake |
| \`R\` | Restart race |
| \`Esc\` | Pause / resume |

## Repository layout

\`\`\`text
main.py                 Panda3D application, menu, HUD and camera
rgdvd/physics.py        Standalone vehicle dynamics model
rgdvd/geometry.py       Procedural mesh helpers and car body mesh
rgdvd/vehicle.py        Procedural sports-car assembly
rgdvd/track.py          Circuit, pit lane, barriers and scenery
rgdvd/ai.py             Racing-line AI opponent
tests/test_physics.py   Dependency-free physics tests
\`\`\`

## Development roadmap

1. Improve the car model, track surfaces, lighting and driving feel.
2. Add collision geometry, suspension and tire/grip tuning.
3. Add AI race rules, multiple cars and race classification.
4. Add LAN discovery and authoritative LAN race sessions.
5. Add online matchmaking/server support (Render is a candidate host, not a requirement for offline/LAN play).
6. Build and measure a complete offline DVD image; target a 4.7 GB DVD-R and a 4 GB RAM budget.

Offline play must remain usable without an internet connection. LAN multiplayer must not require the online service. The DVD build will need to contain all files required for offline play.

# RGDVD

**RGDVD** is a Python 3D racing game project using Panda3D. It is designed around three ways to play: offline, local network (LAN), and online rooms.

## Current build — 0.3.0

### Driving and race content
- Procedural GT-style sports car with a multi-section body, glazing, alloy wheels, brake discs, lights, wing, mirrors and exhausts.
- Closed circuit with procedural tiled asphalt, painted kerbs, road markings, barriers, pit building, grandstand, floodlight masts, trees and distant terrain.
- Three AI opponents for career and quick races.
- Chase camera, speedometer, tachometer, automatic six-speed gearbox, lap counter, timer and best lap.
- Vehicle model with an engine torque curve, gears, braking, reverse, speed-dependent steering, lateral slip, handbrake, drag and off-track penalties.
- Main menu, pause, restart, three-lap event, career rewards, local save profile, credits and four garage vehicles with unlockable handling presets.
- Selectable paint colours and low/medium/high graphics presets.

### Offline
Career and quick races run without an internet connection. Career data is saved locally under the user's application-data folder. Offline mode does not require the Render server.

### LAN multiplayer
- Host a race from the main menu.
- Find hosts using UDP broadcast discovery on port **39770**.
- Host relays player state snapshots to connected clients.
- LAN play does not use the Render service or require internet access.

Windows Firewall may ask permission for private-network UDP traffic. Allow RGDVD on the trusted local network to use host discovery.

### Online multiplayer
- The client connects to a room using WebSockets.
- Room codes let friends join the same session.
- The included FastAPI server relays player states and is designed for deployment to Render using render.yaml.
- The default client address is https://rgdvd.onrender.com. The default URL is https://rgdvd.onrender.com; the client automatically upgrades it to WSS for online rooms.

**Online server deployment:** sign in to Render, create a new Blueprint from this GitHub repository, and deploy render.yaml. The server currently keeps rooms in memory; rooms disappear when the service restarts. It relays client positions and is not yet an authoritative anti-cheat physics server. Do not use it for ranked competition or trust client-reported race results.

## Requirements and launch

- Windows 10/11 or Linux
- Python 3.10+
- Panda3D 1.10.x
- Online play additionally uses websocket-client

Install and launch:

~~~powershell
python -m pip install -r requirements.txt
python main.py
~~~

On Windows, run_windows.bat checks and installs dependencies before launch.

## Controls

| Key | Action |
|---|---|
| W / Up | Throttle |
| S / Down | Brake; reverse after stopping |
| A / Left | Steer left |
| D / Right | Steer right |
| Space | Handbrake |
| R | Restart race |
| Esc | Pause / resume |

## DVD / offline Windows build

build_dvd.bat builds a self-contained Windows folder using PyInstaller, checks the payload against a conservative single-layer DVD-R limit, and creates RGDVD.iso when Microsoft's oscdimg (from Windows ADK Deployment Tools) is installed.

Run the build on Windows:

~~~bat
build_dvd.bat
~~~

The game folder is bundled with its Python runtime; the target PC does not need Python installed. This produces a compact offline build, but the final folder/ISO size must be checked after the build. The current procedural art is small; high-resolution photoreal car and environment asset packs have not been included.

## Memory and performance target

The design target is **up to 4 GB system RAM**, using small procedural textures and a low/medium/high quality setting. This is a target, not a verified measurement yet. The build has not yet been profiled on the user's machine. Start with the Low preset on integrated graphics.

## Project layout

~~~text
main.py                  Panda3D client, menus, race loop, HUD and camera
rgdvd/physics.py         Vehicle dynamics
rgdvd/geometry.py        Procedural mesh builders
rgdvd/vehicle.py         Procedural sports-car assembly
rgdvd/track.py           Circuit and scenery
rgdvd/ai.py              Racing-line AI
rgdvd/profile.py         Offline career save and unlock progression
rgdvd/config.py          Local settings
rgdvd/network.py         UDP LAN discovery and state relay
rgdvd/online.py          WebSocket online client
server/app.py            FastAPI room relay for Render
render.yaml              Render Blueprint
build_dvd.bat            Self-contained Windows/DVD build
tests/                   Physics, networking and profile tests
~~~

## Honest limitations of this build

This is a connected playable prototype foundation, not a finished photorealistic AAA racing game. The car and environment are procedural meshes rather than high-detail artist-made models or scanned materials. Suspension, tyre contact patches, deformable damage, weather, sound design, traffic, multiple tracks, authoritative online simulation, player accounts, persistent online leaderboards, collision synchronization, and final DVD size/performance validation remain incomplete.

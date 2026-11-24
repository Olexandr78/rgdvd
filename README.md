# RGDVD

**RGDVD** is a Python 3D racing game project using Panda3D. It is designed around three ways to play: offline, local network (LAN), and online rooms.

## Current build — 0.3.0

### Driving and race content
- Procedural GT-style sports car with a multi-section body, glazing, alloy wheels, brake discs, lights, wing, mirrors and exhausts.
- Large open city (approximately 1.9 × 1.9 km playable grid) with connected avenues, intersections, lane markings, crosswalks, sidewalks, mixed-use blocks, office towers, apartments, industrial warehouses, shopfronts, rooftop equipment, streetlights, trees and a distant skyline.
- Interactive overhead city map with player position and 53 selectable event routes: 24 two-lap circuits and 29 point-to-point sprints.
- Blue illuminated checkpoint gates with animated chevrons, event timer, checkpoint progression and career rewards.
- Free-roam street driving with no closed-circuit lap loop; press M to open the city map while driving.
- Six-speed automatic or manual gearbox selectable from the main menu; Q/E shift gears, F7 switches modes while driving, and configurable wheel buttons can act as shift paddles.
- Chase camera, speedometer, tachometer, race timer and event progress HUD.
- Vehicle model with an engine torque curve, gears, braking, reverse, speed-dependent steering, lateral slip, handbrake, drag and off-track penalties.
- Night-racing themed main menu, pause, restart, local save profile, credits and five garage vehicles, including a drivable procedural Volga GAZ-24-10.
- Runtime-generated engine, tyre-slip and gear-change audio; no external sound packs are required.
- Selectable paint colours and low/medium/high graphics presets.

### Offline
City free roam and street driving run without an internet connection. Local settings and garage progress are saved under the user's application-data folder. Offline mode does not require the Render server.

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
| M | Open / close city map |
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
main.py                  Panda3D client, menus, free-roam loop, HUD and camera
rgdvd/city.py            Open-world urban environment
rgdvd/events.py          53 original circuit and sprint routes
rgdvd/map_screen.py      Overhead map and event selection
rgdvd/audio.py           Synthesized engine, tyre and shift sounds
rgdvd/physics.py         Vehicle dynamics
rgdvd/geometry.py        Procedural mesh builders
rgdvd/vehicle.py         Sports cars and procedural Volga GAZ-24-10
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

This is a connected playable prototype foundation, not a finished photorealistic AAA racing game. The car and city are currently procedural geometry, not photogrammetry or licensed high-detail artist-made assets; this is a larger street-city prototype, not photorealism. The 53 selectable events currently run as solo checkpoint/time-trial routes: rival AI racers, police pursuits, drift scoring, traffic, collision-aware barrier physics, and fully simulated race opponents are not implemented yet. Engine and tyre sounds are synthesized at runtime rather than recorded from real cars. Steering wheel support depends on Windows exposing the device through its DirectInput/XInput driver; exact button numbering can vary by driver and can be changed with wheel_handbrake_button in settings.json. Manual shifting is sequential six-speed; wheel shift-up/down buttons default to 5/4 and can be changed in settings.json. The Volga is an original low-poly procedural interpretation, not a scanned model. Suspension, tyre contact patches, deformable damage, weather, authoritative online simulation, player accounts, persistent online leaderboards, collision synchronization, and final DVD size/performance validation remain incomplete.

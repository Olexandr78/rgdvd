# RGDVD

A Python 3D racing game designed for offline play, LAN multiplayer, and online racing.

## Current build: first playable prototype

The repository now contains a small procedural 3D driving prototype:
- A closed oval circuit with asphalt, center markings, and scenery.
- A player car with a chase camera.
- Acceleration, braking, reverse, steering, and handbrake.
- A speedometer HUD.
- No internet connection required.

The car and scenery are temporary procedural models. They are not the final realistic vehicle assets.

## Run it

Requires Python 3.10+.

```bash
python -m pip install -r requirements.txt
python main.py
```

### Controls

| Key | Action |
|---|---|
| W / Up | Accelerate |
| S / Down | Brake / reverse |
| A,D / Left,Right | Steer |
| Space | Handbrake |
| R | Reset car |
| Esc | Quit |

## Project goals

- Realistic vehicle models, materials, lighting, and environments.
- Offline single-player mode with AI opponents.
- LAN multiplayer without internet access.
- Online multiplayer through a dedicated server (Render is the initial hosting target).
- A complete offline installer designed to fit on one 4.7 GB DVD-R.
- Target memory budget: up to 4 GB RAM.

## Planned technology

- Python 3 and Panda3D for the game runtime and 3D rendering.
- Bullet Physics for more advanced vehicle and collision simulation.
- UDP for low-latency LAN gameplay.
- A server-side networking layer for online sessions.

## Development status

This is an early playable prototype, not a finished racing game. Vehicle physics, proper 3D art, AI, multiplayer, menus, and the DVD build pipeline remain to be implemented and tested.

## Design principles

1. Offline play must never depend on the online service.
2. LAN multiplayer must work without internet access.
3. Online services must not be required to launch the game.
4. Large environments should stream assets as needed to control memory use.
5. The DVD build must include everything required for offline play.

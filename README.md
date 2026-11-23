# RGDVD

A realistic 3D racing game built with Python.

## Project goals

- Realistic driving, vehicle handling, and detailed 3D environments.
- Offline single-player mode with AI opponents.
- LAN multiplayer without an internet connection.
- Online multiplayer through a dedicated server hosted separately (initial target: Render).
- A complete offline installer designed to fit on a single 4.7 GB DVD-R.
- Target memory budget: up to 4 GB RAM.

## Planned technology

- Python 3
- Panda3D for 3D rendering and game runtime
- Bullet Physics for vehicle and collision simulation
- UDP for low-latency LAN gameplay
- A server-side networking layer for online sessions

## Development status

Early planning stage. The engine, networking protocol, asset pipeline, and DVD build process still need to be implemented and tested.

## Design principles

1. Offline play must never depend on the online service.
2. LAN multiplayer must work without internet access.
3. Online services must not be required to launch the game.
4. Large environments should stream assets as needed to control memory use.
5. The DVD build must include everything required for offline play.

"""Procedurally synthesized vehicle audio; no external copyrighted samples."""
from __future__ import annotations

import math
import random
import wave
from pathlib import Path


class VehicleAudio:
    SAMPLE_RATE = 22050

    def __init__(self, loader, cache_dir: Path) -> None:
        self.loader = loader
        self.cache_dir = Path(cache_dir) / "audio"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._write_engine()
        self._write_tyre()
        self._write_shift()
        self.engine = loader.loadSfx(str(self.cache_dir / "engine_loop.wav"))
        self.tyres = loader.loadSfx(str(self.cache_dir / "tyre_loop.wav"))
        self.shift = loader.loadSfx(str(self.cache_dir / "gear_shift.wav"))
        self.engine.setLoop(True)
        self.tyres.setLoop(True)
        self.engine.setVolume(0.18)
        self.tyres.setVolume(0.0)
        self.engine.play()
        self.tyres.play()
        self.last_gear = 1

    def _write_samples(self, name: str, samples: list[float]) -> None:
        path = self.cache_dir / name
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self.SAMPLE_RATE)
            pcm = bytearray()
            for sample in samples:
                value = int(max(-1.0, min(1.0, sample)) * 32767)
                pcm.extend(value.to_bytes(2, "little", signed=True))
            output.writeframes(pcm)

    def _write_engine(self) -> None:
        rate = self.SAMPLE_RATE
        samples = []
        duration = 2.0
        for i in range(int(rate * duration)):
            t = i / rate
            phase = 2.0 * math.pi * 92.0 * t
            tone = (0.48 * math.sin(phase) +
                    0.24 * math.sin(phase * 2.01) +
                    0.13 * math.sin(phase * 3.03) +
                    0.07 * math.sin(phase * 4.07))
            pulse = 0.78 + 0.22 * math.sin(2.0 * math.pi * 5.5 * t)
            samples.append(tone * pulse * 0.48)
        self._write_samples("engine_loop.wav", samples)

    def _write_tyre(self) -> None:
        rng = random.Random(2410)
        rate = self.SAMPLE_RATE
        samples = []
        previous = 0.0
        for i in range(int(rate * 1.5)):
            noise = rng.uniform(-1.0, 1.0)
            previous = previous * 0.72 + noise * 0.28
            samples.append(previous * 0.22)
        self._write_samples("tyre_loop.wav", samples)

    def _write_shift(self) -> None:
        rate = self.SAMPLE_RATE
        samples = []
        for i in range(int(rate * 0.20)):
            t = i / rate
            envelope = max(0.0, 1.0 - t / 0.20)
            tone = math.sin(2 * math.pi * (420 - 180 * t) * t)
            samples.append(tone * envelope * 0.30)
        self._write_samples("gear_shift.wav", samples)

    def update(self, rpm: float, throttle: float, lateral_speed: float,
               handbrake: bool, gear: int) -> None:
        play_rate = max(0.65, min(3.2, float(rpm) / 2300.0))
        self.engine.setPlayRate(play_rate)
        self.engine.setVolume(0.10 + max(0.0, min(1.0, throttle)) * 0.20)
        slip = min(1.0, abs(lateral_speed) / 9.0)
        tyre_volume = max(slip, 0.75 if handbrake else 0.0) * 0.34
        self.tyres.setVolume(tyre_volume)
        if int(gear) != self.last_gear:
            self.shift.stop()
            self.shift.play()
            self.last_gear = int(gear)

    def start(self) -> None:
        self.engine.play()
        self.tyres.play()

    def stop(self) -> None:
        for sound in (self.engine, self.tyres, self.shift):
            try:
                sound.stop()
            except Exception:
                pass

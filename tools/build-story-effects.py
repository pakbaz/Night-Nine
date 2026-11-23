#!/usr/bin/env python3
"""Build the story-moment sound effects from their generated masters.

Masters, prompts and loudness targets: assets/audio/story-effects/story-effects.json.
Each master is trimmed of leading silence, mixed to mono, faded at both ends and set to its
loudness target, then written to game/assets/audio/effects/<name>.wav and registered in the
soundscape manifest so lines can play it as a `cue`.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/audio/story-effects"
PROVENANCE = "assets/audio/story-effects/story-effects.json"
OUT = ROOT / "game/assets/audio/effects"


def shaped(samples, rate, lufs):
    level = np.sqrt(np.convolve(samples ** 2, np.ones(240) / 240, mode="same"))
    start = max(0, int(np.argmax(level > level.max() * 0.05)) - int(0.02 * rate))
    samples = samples[start:].copy()
    fade_in, fade_out = int(0.01 * rate), int(0.12 * rate)
    samples[:fade_in] *= np.linspace(0, 1, fade_in)
    samples[-fade_out:] *= np.linspace(1, 0, fade_out) ** 2
    meter = pyloudnorm.Meter(rate, block_size=min(0.4, len(samples) / rate * 0.8))
    samples = samples * 10 ** ((lufs - meter.integrated_loudness(samples)) / 20)
    peak = np.abs(samples).max()
    return samples * (0.89 / peak) if peak > 0.89 else samples


def build():
    effects = json.loads((ROOT / PROVENANCE).read_text())["effects"]
    manifest = {}
    for name, spec in effects.items():
        master = SOURCE / f"{name}-master.wav"
        assert hashlib.sha256(master.read_bytes()).hexdigest() == spec["sha256"], name
        samples, rate = sf.read(master, always_2d=True)
        path = OUT / f"{name}.wav"
        sf.write(path, shaped(samples.mean(axis=1), rate, spec["lufs"]), rate, subtype="PCM_16")
        info = sf.info(path)
        manifest[name] = {"file": f"res://assets/audio/effects/{name}.wav",
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "seconds": round(info.frames / info.samplerate, 4),
                          "provenance": PROVENANCE}
    return manifest


if __name__ == "__main__":
    built = build()
    path = ROOT / "game/assets/audio/soundscape-manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(built)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({name: entry["seconds"] for name, entry in built.items()}))

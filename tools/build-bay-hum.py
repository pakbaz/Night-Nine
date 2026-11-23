#!/usr/bin/env python3
"""Build the ninth-night hum from the generated choir and solo-voice masters.

The hum is many voices holding one note (A3, 220 Hz): the Choir under the bay. Frank's
first reel caught one voice on that note; by his last reel it was a choir. The radio copy
is band-limited like an AM receiver; the reels carry seeded tape hiss underneath.
Masters and their provenance: assets/audio/bay-hum/.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
MASTERS = ROOT / "assets/audio/bay-hum"
OUT = ROOT / "game/assets/audio/effects"
RATE = 24000
NOTE = 220.0
PROVENANCE = "assets/audio/bay-hum/bay-hum.json"


def master(name):
    samples, rate = sf.read(MASTERS / name, always_2d=True)
    assert rate == RATE, (name, rate)
    return samples.mean(axis=1)


def retune(samples, measured, wanted):
    """Resample so the measured pitch lands on the wanted pitch."""
    up = int(round(measured / wanted * 1000))
    return signal.resample_poly(samples, up, 1000)


def band(samples, low, high):
    sos = signal.butter(4, [low, high], btype="band", fs=RATE, output="sos")
    return signal.sosfiltfilt(sos, samples)


def loudness(samples, lufs):
    meter = pyloudnorm.Meter(RATE)
    return samples * 10 ** ((lufs - meter.integrated_loudness(samples)) / 20)


def fades(samples, fade_in, fade_out):
    out = samples.copy()
    a, b = int(fade_in * RATE), int(fade_out * RATE)
    out[:a] *= np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    out[-b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return out


def seamless(samples, overlap):
    """Fold the tail over the head with an equal-power crossfade so the clip loops without a seam."""
    n = int(overlap * RATE)
    t = np.linspace(0, np.pi / 2, n)
    head = samples[:n] * np.sin(t) + samples[-n:] * np.cos(t)
    return np.concatenate([head, samples[n:-n]])


def tape_hiss(seconds, seed, lufs):
    noise = np.random.default_rng(seed).standard_normal(int(seconds * RATE))
    return loudness(band(noise, 300, 5200), lufs)


def write(name, samples):
    path = OUT / (name + ".wav")
    peak = np.abs(samples).max()
    if peak > 0.89:
        samples = samples * 0.89 / peak
    sf.write(path, samples, RATE, subtype="PCM_16")
    return {"file": "res://assets/audio/effects/" + path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "seconds": round(len(samples) / RATE, 4),
            "provenance": PROVENANCE}


def build():
    provenance = json.loads((ROOT / PROVENANCE).read_text())["masters"]
    choir = retune(master("choir-master.wav"), provenance["choir-master.wav"]["measured_pitch_hz"], NOTE)
    voice = retune(master("voice-master.wav"), provenance["voice-master.wav"]["measured_pitch_hz"], NOTE / 2)
    manifest = {}
    # The cue heard on the beach and under Saren's broadcast, and Dad's Reel 07: one held note.
    manifest["ninth_night"] = write("ninth_night", loudness(fades(choir[: 5 * RATE], 0.4, 1.0), -18.0))
    # Frank's receiver at 815 kHz: the same choir, looping, through an AM radio's bandwidth.
    radio = seamless(band(choir, 170, 3600), 1.0)
    manifest["ninth_night_loop"] = write("ninth_night_loop", loudness(radio, -18.0))
    # Frank's reels: one voice in March, a choir the day before the boat, both under tape hiss.
    hiss = tape_hiss(4.0, 511, -44.0)
    # Equally loud, so the difference a player hears is one voice against many, not volume.
    first = loudness(band(voice[RATE // 2: RATE // 2 + 4 * RATE], 150, 3800), -24.0)
    last = loudness(band(choir[: 4 * RATE], 150, 3800), -24.0)
    manifest["hum_first_reel"] = write("hum_first_reel", fades(first + hiss, 0.15, 0.25))
    manifest["hum_last_reel"] = write("hum_last_reel", fades(last + hiss, 0.15, 0.25))
    return manifest


if __name__ == "__main__":
    built = build()
    path = ROOT / "game/assets/audio/soundscape-manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(built)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({name: entry["seconds"] for name, entry in built.items()}))

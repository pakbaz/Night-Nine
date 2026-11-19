#!/usr/bin/env python3
"""Synthesize the small interface sounds: a solved lead, a wrong try, a hint.

Run with .tools/local-media-env/bin/python3. Everything is generated here, so
there is no third-party audio to license. 48 kHz mono 16-bit WAV.
"""
from pathlib import Path
import numpy as np, soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "game/assets/audio/effects"
RATE = 48000

def bell(freq, seconds, decay, partials=((1, 1.0), (2.0, .28), (3.01, .09), (4.2, .04))):
    t = np.arange(int(seconds * RATE)) / RATE
    tone = sum(a * np.sin(2 * np.pi * freq * k * t) * np.exp(-t / (decay / k ** .5)) for k, a in partials)
    attack = np.minimum(1.0, t / .006)
    return tone * attack

def place(mix, sound, at):
    start = int(at * RATE)
    mix[start:start + len(sound)] += sound[:len(mix) - start]

def finish(mix, peak_db):
    mix = mix / (np.abs(mix).max() + 1e-9) * 10 ** (peak_db / 20)
    fade = int(.02 * RATE)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix.astype(np.float32)

def solved():
    mix = np.zeros(int(1.2 * RATE))
    rng = np.random.default_rng(9)
    click = rng.normal(0, 1, int(.012 * RATE)) * np.exp(-np.arange(int(.012 * RATE)) / (.002 * RATE))
    click = np.convolve(click, np.ones(6) / 6, "same")
    place(mix, click * .35, 0.0)
    place(mix, bell(659.25, 1.0, .5), .02)
    place(mix, bell(987.77, 1.0, .55) * .8, .13)
    return finish(mix, -9)

def wrong():
    t = np.arange(int(.45 * RATE)) / RATE
    sweep = 146.8 * (1 - .12 * np.minimum(1, t / .25))
    knock = np.sin(2 * np.pi * np.cumsum(sweep) / RATE) * np.exp(-t / .09)
    under = np.sin(2 * np.pi * 110 * t) * np.exp(-np.maximum(0, t - .07) / .1) * (t > .07) * .6
    return finish(knock + under, -12)

def hint():
    mix = np.zeros(int(.7 * RATE))
    place(mix, bell(783.99, .7, .28, ((1, 1.0), (2.0, .2), (3.0, .05))), 0.0)
    return finish(mix, -14)

if __name__ == "__main__":
    for name, sound in [("ui_solved", solved()), ("ui_wrong", wrong()), ("ui_hint", hint())]:
        sf.write(OUT / (name + ".wav"), sound, RATE, "PCM_16")
        print(name, round(len(sound) / RATE, 2), "s")

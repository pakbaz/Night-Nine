#!/usr/bin/env python3
"""The bay's hum is a choir: many voices holding one note, audible through a small radio speaker."""
import json
import unittest
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "game/assets/audio/soundscape-manifest.json").read_text())


def load(cue):
    path = ROOT / "game" / MANIFEST[cue]["file"].removeprefix("res://")
    samples, rate = sf.read(path, always_2d=True)
    return samples.mean(axis=1), rate


def spectrum(samples, rate):
    power = np.abs(np.fft.rfft(samples * np.hanning(len(samples)))) ** 2
    return np.fft.rfftfreq(len(samples), 1 / rate), power


def share(freqs, power, low, high):
    return power[(freqs >= low) & (freqs < high)].sum() / power.sum()


def strongest(freqs, power, low, high):
    band = (freqs >= low) & (freqs < high)
    return freqs[band][np.argmax(power[band])]


def beating(samples, rate, f0):
    """How much the note's level wavers (50 ms frames): one steady voice holds level,
    many slightly detuned voices beat against each other."""
    sos = signal.butter(4, [f0 * 0.9, f0 * 1.1], btype="band", fs=rate, output="sos")
    envelope = np.abs(signal.hilbert(signal.sosfiltfilt(sos, samples)))
    frame = int(0.05 * rate)
    envelope = envelope[: len(envelope) // frame * frame].reshape(-1, frame).mean(axis=1)
    return np.std(envelope) / np.mean(envelope)


def harmonic_spread(freqs, power, f0, harmonic):
    """Width (Hz) of a harmonic where it stays within 12 dB of its peak: one sine is a hairline,
    a crowd of slightly detuned voices is a band."""
    band = (freqs > f0 * harmonic - 25) & (freqs < f0 * harmonic + 25)
    peak = power[band].max()
    wide = freqs[band][power[band] > peak * 10 ** (-12 / 10)]
    return wide.max() - wide.min()


class BayHumTests(unittest.TestCase):
    def test_hum_is_many_voices_on_one_note(self):
        samples, rate = load("ninth_night")
        freqs, power = spectrum(samples, rate)
        self.assertAlmostEqual(strongest(freqs, power, 180, 260), 220, delta=4, msg="the ninth-night note is A3")
        self.assertGreater(harmonic_spread(freqs, power, 220, 2), 2.5, "a crowd of voices, not one pure tone")
        self.assertGreater(share(freqs, power, 300, 3400), 0.45, "most of the choir passes a small radio speaker")

    def test_hum_holds_its_note(self):
        samples, rate = load("ninth_night")
        second = rate
        pitches = [strongest(*spectrum(samples[i:i + second], rate), 180, 260)
                   for i in range(0, len(samples) - second, second // 2)]
        self.assertLess(max(pitches) - min(pitches), 8, "the choir holds one note the whole time")

    def test_receiver_hum_loops_without_a_click(self):
        samples, rate = load("ninth_night_loop")
        freqs, power = spectrum(samples, rate)
        self.assertAlmostEqual(strongest(freqs, power, 180, 260), 220, delta=4, msg="the radio plays the same note")
        step = np.abs(np.diff(samples)).max()
        self.assertLess(abs(samples[-1] - samples[0]), step * 1.5, "the loop point is no bigger than a normal step")

    def test_frank_reels_go_from_one_voice_to_a_choir(self):
        first, rate = load("hum_first_reel")
        last, _ = load("hum_last_reel")
        for samples in (first, last):
            freqs, power = spectrum(samples, rate)
            note = share(freqs, power, 150, 3400)
            hiss = share(freqs, power, 3400, rate / 2)
            self.assertGreater(note, hiss * 3, "the hum carries over the tape hiss, not the other way round")
        self.assertGreater(beating(last, rate, 220), beating(first, rate, 220) * 2,
                           "the last reel is many voices beating together; the first is one steady voice")
        meter = pyloudnorm.Meter(rate)
        self.assertLess(abs(meter.integrated_loudness(last) - meter.integrated_loudness(first)), 1.0,
                        "the reels are equally loud, so 'just louder' is not the answer")


if __name__ == "__main__":
    unittest.main()

"""Synthesize short, original heel and sole contacts for the painted walking surfaces."""
from pathlib import Path
import wave

import numpy as np

RATE = 24000
OUTPUT = Path(__file__).resolve().parents[1] / "game/assets/audio/steps"


def pulse(time, start, attack, decay):
    t = np.maximum(time - start, 0)
    return (1 - np.exp(-t / attack)) * np.exp(-t / decay)


def render(material, side, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(int(RATE * .38)) / RATE
    noise = rng.normal(size=len(t))
    mid = np.convolve(noise, np.ones(7) / 7, mode="same")
    grit = noise - np.convolve(noise, np.ones(3) / 3, mode="same")
    pitch = 1 + side * .055
    def ring(frequency, decay, start=0):
        return np.sin(2 * np.pi * frequency * pitch * (t - start)) * pulse(t, start, .0025, decay)
    sole = pulse(t, .064 + side * .009, .007, .033)
    tread = ring(81, .036) + .86 * mid * pulse(t, 0, .002, .025)
    if material == "timber":
        voice = tread + .48 * ring(194, .043) + .24 * ring(347, .022) + .83 * mid * sole
    elif material == "tile":
        voice = tread + .31 * ring(586, .016) + .36 * grit * pulse(t, .003, .001, .009) + mid * sole
        voice[895:] += .12 * voice[:-895]
    elif material == "shore":
        grit_env = pulse(t, .005, .012, .033) + .88 * pulse(t, .057, .011, .053)
        voice = .28 * tread + .92 * mid * grit_env + .20 * grit * grit_env
    else:
        voice = .70 * tread + .43 * ring(242, .047) + .20 * ring(605, .044, .014) + .66 * mid * sole
    voice *= np.minimum(1, (.38 - t) / .04)
    samples = np.rint(voice * (.64 * 32767 / np.max(np.abs(voice)))).astype("<i2")
    with wave.open(str(OUTPUT / f"{material}-{side}.wav"), "wb") as stream:
        stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(samples.tobytes())


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for index, surface in enumerate(("timber", "tile", "shore", "glass")):
        for foot in range(2):
            render(surface, foot, 112 + 11 * index + foot)

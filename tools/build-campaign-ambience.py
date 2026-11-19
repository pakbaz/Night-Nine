"""Render the Night Nine location beds as 48 kHz stereo masters and loopable Godot files."""
import argparse
import hashlib
import importlib.util
import json
import math
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sound", ROOT / "tools/build-prologue-ambience.py")
sound = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sound)
RATE = sound.RATE
SOURCE = ROOT / "assets/audio/ambience-campaign"
RUNTIME = ROOT / "game/assets/audio/ambience-campaign"
# Bed, two spatial details, and the room's acoustic character.
ROOMS = {
    "c1_flat": ("home", "pipes", "traffic", "close"),
    "c1_pier": ("coast", "rigging", "pilings", "open"),
    "c1_dinner": ("kitchen", "ceramic", "cloth", "warm"),
    "c1_escape": ("street", "traffic", "wind", "open"),
    "c2_aquarium": ("waterworks", "glass", "drip", "tile"),
    "c2_ship": ("vessel", "bulkhead", "servo", "metal"),
    "c3_house": ("home", "timber", "pages", "warm"),
    "c3_archive": ("archive", "pages", "pipes", "shelves"),
    "i1_archive": ("choir", "resonance", "glass", "deep"),
    "c4_safe": ("home", "duct", "pipes", "close"),
    "c4_escape": ("basement", "latch", "duct", "tile"),
    "c5_shack": ("radio", "paper", "wind", "close"),
    "c5_station": ("radio", "reel", "keys", "studio"),
    "c6_iris": ("street", "traffic", "cloth", "open"),
    "c6_jail": ("basement", "latch", "duct", "metal"),
    "i2_nora": ("gallery", "crystal", "servo", "deep"),
    "c7_gate": ("upland", "fence", "wind", "open"),
    "c7_swap": ("upland", "servo", "fence", "open"),
    "c8_lab": ("lab", "blower", "glass", "tile"),
    "c8_beach": ("coast", "sand", "wind", "open"),
    "c8_rig": ("lab", "keys", "reel", "studio"),
    "c9_gallery": ("gallery", "glass", "crystal", "deep"),
    "c9_wake": ("gallery", "servo", "breath", "metal"),
    "c9_choir": ("choir", "crystal", "breath", "deep"),
    "c10_station": ("radio", "reel", "paper", "studio"),
    "c10_town": ("coast", "pilings", "rigging", "open"),
    "c10_live": ("radio", "keys", "breath", "studio"),
    "c10_report": ("choir", "resonance", "cloth", "deep"),
    "epilogue": ("street", "cloth", "traffic", "warm"),
    "one_year": ("radio", "ceramic", "paper", "studio"),
    "postcredits": ("upland", "wind", "resonance", "open"),
}
BEDS = {
    "home": (70, 485, 60., .26), "coast": (70, 1390, 0, .60),
    "kitchen": (108, 1770, 119.5, .33), "street": (56, 860, 0, .56),
    "waterworks": (65, 1270, 88., .34), "vessel": (52, 680, 47.5, .41),
    "archive": (109, 710, 60., .18), "choir": (95, 1420, 0, .37),
    "basement": (62, 760, 119.7, .28), "radio": (87, 725, 59.8, .18),
    "gallery": (104, 1220, 83.4, .27), "upland": (85, 1260, 0, .54),
    "lab": (92, 1220, 120.3, .26),
}
REVERB = {"close": (.021, .14), "warm": (.037, .20), "tile": (.082, .28),
          "metal": (.115, .25), "shelves": (.027, .12), "studio": (.013, .07),
          "deep": (.304, .37), "open": (.146, .09)}
FREQ = {"pipes": 168, "rigging": 611, "ceramic": 1185, "glass": 1430,
        "bulkhead": 87, "latch": 375, "keys": 720, "fence": 295, "crystal": 600, "resonance": 210}


def detail(kind, rng):
    if kind in ("paper", "pages", "cloth"):
        return sound.pen(rng) * (0.45 if kind == "cloth" else .78)
    if kind in ("pilings", "timber", "reel", "servo"):
        return sound.wood(rng, rng.uniform(.32, .91), 39 if kind == "reel" else 27,
                          rng.uniform(105, 142) if kind in ("timber", "pilings") else rng.uniform(242, 375))
    if kind in ("sand", "drip"):
        return sound.lap(rng, rng.uniform(.46, 1.48)) * (1 if kind == "sand" else .4)
    if kind in FREQ:
        f = FREQ[kind] * rng.uniform(.92, 1.10)
        decay = 1.4 if kind in ("crystal", "resonance") else rng.uniform(5, 22)
        t = np.arange(round(RATE * min(3.8, 9/decay))) / RATE
        return sound.impulse_voice(t, f, rng, decay) * (1 - np.exp(-t/.009))
    length = rng.uniform(1.8, 4.1)
    t = np.arange(round(RATE*length))/RATE
    lo, hi = {"traffic": (54, 691), "wind": (132, 1950), "breath": (170, 1100),
              "blower": (172, 890), "duct": (95, 590)}[kind]
    return sound.colored(rng, len(t), lo, hi) * .32 * np.sin(math.pi*t/length)**2


def render(room, recipe):
    family, detail1, detail2, space = recipe
    seed = int.from_bytes(hashlib.sha256(room.encode()).digest()[:4], "little")
    rng = np.random.default_rng(seed)
    seconds = 34 + seed % 12
    n = seconds * RATE
    cross = 2 * RATE
    t = np.arange(n + cross)/RATE
    low, high, motor, motion = BEDS[family]
    rng_mod = sound.drift(rng, t, 2.8, .72-motion*.4, 1+motion*.5)
    air = sound.colored(rng, len(t), low, high) * .064 * rng_mod
    if motor:
        phase = 2*np.pi*np.cumsum(motor*(1+sound.drift(rng,t,3.,-.0016,.0016)))/RATE
        air += (.017*np.sin(phase)+.006*np.sin(2*phase+.6)) * rng_mod
    m = sound.diffuse(air, [(0, -.22, .79), (.017, .45, .37)])
    for side in (-.81, .78):
        far = sound.colored(rng, len(t), low*1.45, high*1.56) * .032 * sound.drift(rng,t,3.2,.56,1.5)
        sound.place(m, far, 0, side)
    if family in ("coast", "waterworks"):
        at = .1
        while at < seconds+2:
            a = sound.lap(rng, rng.uniform(1.3,2.8))
            sound.place(m,a,at,rng.uniform(-.85,.86),.14 if family=="waterworks" else .38)
            at += rng.uniform(2.6,4.2)
    if family in ("choir","gallery"):
        pitches = (144.8,217.4) if family=="choir" else (120.4,180.6)
        m += sound.diffuse(sound.tower(rng,t,pitches),[(0,-.63,.048),(.150,.83,.033)])
    delay, reflect = REVERB[space]
    for side, kind in ((-.69, detail1), (.72, detail2)):
        at = rng.uniform(1.8, 6.1)
        while at < seconds + 1:
            a = detail(kind,rng)
            pan = side + rng.uniform(-.14,.14)
            gain = rng.uniform(.045,.130)
            sound.place(m,a,at,pan,gain)
            sound.place(m,a,at+delay,-pan,reflect*gain)
            at += rng.uniform(6.3,12.1)
    angle = np.arange(cross)/(cross-1)*np.pi/2
    m[:cross] = m[n:] * np.cos(angle[:,None])**2 + m[:cross] * np.sin(angle[:,None])**2
    m = m[:n] - np.mean(m[:n],axis=0)
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name,m,RATE,subtype="FLOAT")
        measured,_ = sound.loudness(Path(f.name))
    target = -23.5 if space=="open" else -25.
    m *= min(10**((target-measured)/20), .84/np.max(abs(m)))
    master = SOURCE / (room+".flac")
    output = RUNTIME / (room+".ogg")
    sf.write(master,m,RATE,subtype="PCM_24")
    with sf.SoundFile(output,"w",RATE,2,format="OGG",subtype="VORBIS",compression_level=.51) as stream:
        for start in range(0, n, 4096):
            stream.write(m[start:start + 4096])
    decoded, rate = sf.read(output,dtype="float32")
    delta = abs(decoded[0] - decoded[-1])
    if rate != RATE or decoded.shape != (n,2) or np.any(delta > np.quantile(abs(np.diff(decoded,axis=0)),.999,axis=0)):
        raise ValueError("Check the decoded loop boundary for " + room)
    lu, peak = sound.loudness(output)
    return dict(recipe=recipe,seed=seed,seconds=seconds,rate=RATE,channels=2,integrated_lufs=lu,true_peak_dbtp=peak,
                wrap_delta_dbfs=[round(sound.db(x),1) for x in delta],master_sha256=sound.digest(master),
                runtime_sha256=sound.digest(output),runtime_bytes=output.stat().st_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rooms",nargs="*")
    args = parser.parse_args()
    SOURCE.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    index = SOURCE / "ambience.json"
    report = json.loads(index.read_text()) if index.exists() else {}
    for room in args.rooms or ROOMS:
        report[room] = render(room, ROOMS[room])
        index.write_text(json.dumps(report,indent=2)+"\n")
        print(room, report[room]["integrated_lufs"], flush=True)

"""Derive the delegates' facial patches from the final Sentinel Point room painting."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ROOM = ROOT / "assets/environments/sentinel-point/room.png"
RUNTIME = ROOT / "game/assets/illustrated/cast"
spec = importlib.util.spec_from_file_location("expression", Path(__file__).with_name("prepare-archivist-sprite.py"))
expression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(expression)

# Source-pixel landmarks follow the angle of each face in the room painting.
DELEGATES = {
    "general_us": {
        "upper_lids": [[(219,395),(223,390),(229,386),(236,381),(239,380)],
                       [(257,376),(259,375),(262,373),(264,373)]],
        "lower_lids": [[(219,395),(224,392),(231,390),(236,384),(239,380)],
                       [(257,376),(259,378),(262,377),(264,373)]],
        "eye_box": (214,367,55,34),
        "mouth": [(238,443.5),(243,440.5),(251,437.3),(258,434.7),(264,432.5),(267.4,430.9)],
        "mouth_box": (231,425,44,29),
    },
    "general_cn": {
        "upper_lids": [[(1411,390),(1414,389.6),(1416.5,390.5),(1418.8,393),(1421,396)],
                       [(1439.4,397.3),(1441.5,396.7),(1444,397.6),(1448,400),(1453.8,403)]],
        "lower_lids": [[(1411,390),(1414,392),(1416.5,394.5),(1418.8,395.3),(1421,396)],
                       [(1439.4,397.3),(1441.5,399.8),(1444,401.5),(1448,402.5),(1453.8,403)]],
        "eye_box": (1404,382,57,30),
        "mouth": [(1411.6,448),(1415,448.6),(1420,449.2),(1425,451.1),(1431,453.3),(1437,454.5)],
        "mouth_box": (1405,440,39,25),
    },
}
MOUTHS = {
    "mouth_parted": (2.3,0,0), "mouth_open": (5.2,0,.01),
    "mouth_round": (5.4,.7,-.03), "mouth_wide": (3.1,0,.06)
}
CUES = {"X":None,"A":None,"B":"mouth_parted","C":"mouth_wide","D":"mouth_open",
        "E":"mouth_round","F":"mouth_round","G":"mouth_parted","H":"mouth_parted"}


def prepare(actor_id, landmarks, pixels):
    eyes = landmarks["eye_box"]
    lips = landmarks["mouth_box"]
    frames = {}
    pieces = []
    for name, weight in (("blink_half",.52),("blink_closed",1.0)):
        piece = expression.blink(pixels,weight,landmarks["upper_lids"],landmarks["lower_lids"],eyes)
        pieces.append((name,piece,eyes))
    for name, (height,rounding,spread) in MOUTHS.items():
        piece = expression.lips(pixels,height,rounding,spread,landmarks["mouth"],lips)
        pieces.append((name,piece,lips))
    width = max(piece.width for _,piece,_ in pieces)
    height = sum(piece.height for _,piece,_ in pieces)
    atlas = Image.new("RGBA",(width,height))
    top = 0
    for name,piece,box in pieces:
        atlas.paste(piece,(0,top))
        frames[name] = {"source_origin":list(box[:2]),"atlas_region":[0,top,*piece.size]}
        top += piece.height
    out = ROOT / "assets/environments/sentinel-point/delegates" / actor_id
    out.mkdir(parents=True,exist_ok=True)
    filename = actor_id+"-face-atlas.png"
    atlas.save(out/filename,optimize=True)
    manifest = {
        "reference": str(ROOM.relative_to(ROOT)), "reference_sha256":hashlib.sha256(ROOM.read_bytes()).hexdigest(),
        "atlas":filename, "frames":frames, "cue_frames":CUES,
    }
    (out/"sprite.json").write_text(json.dumps(manifest,indent=2)+"\n")
    runtime = RUNTIME/actor_id
    runtime.mkdir(parents=True,exist_ok=True)
    for f in (filename,"sprite.json"):
        shutil.copyfile(out/f,runtime/f)


if __name__ == "__main__":
    rgb = np.asarray(Image.open(ROOM).convert("RGB"),dtype=float)
    for who,marks in DELEGATES.items():
        prepare(who,marks,rgb)

"""Prepare matching GPT Image keyframes and bidirectional displacement for the Godot chapter shots."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/cinematics/campaign"
RUNTIME = ROOT / "game/assets/illustrated/campaign/inserts"
WORK = (800, 450)
REPORT = SOURCE / "animation.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(name):
    src = SOURCE / "masters" / (name + ".png")
    im = Image.open(src).convert("RGB")
    # Keep the framing registered across the pair even when GPT supplies
    # slightly different pixel dimensions for the edit.
    fit = ImageOps.fit(im, (1600, 900), method=Image.Resampling.LANCZOS)
    out = RUNTIME / (name + ".webp")
    fit.save(out, quality=95, method=6)
    return np.asarray(fit.resize(WORK, Image.Resampling.LANCZOS)), {
        "source": src.name, "size": list(im.size), "sha256": digest(src),
        "runtime": out.name, "runtime_sha256": digest(out)}


def pack_flow(flow, reverse, first, other, x, y):
    h, w = flow.shape[:2]
    dx = x + flow[:, :, 0]
    dy = y + flow[:, :, 1]
    registered = cv2.remap(other, dx, dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    reverse_at_match = cv2.remap(reverse, dx, dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mismatch = np.linalg.norm(flow + reverse_at_match, axis=2)
    photometric = np.abs(first.astype(np.float32) - registered.astype(np.float32))
    confidence = np.exp(-mismatch / (1.6 + np.linalg.norm(flow,axis=2)*.08)) * np.exp(-photometric / 55.)
    confidence = cv2.GaussianBlur(confidence, (0,0), 1.2)
    # Separate arrays for both directions occupy the two halves of an RGB PNG.
    # 128 is true zero so uniform surfaces stay stationary after texture import.
    encoded = np.rint(np.clip(flow / [w,h] / .12, -1,1) * 127 + 128).astype(np.uint8)
    data = np.dstack((encoded, np.rint(confidence * 255).astype(np.uint8)))
    return data, float(np.mean(photometric))


def prepare(room):
    a, ai = frame(room)
    b, bi = frame(room+"-motion")
    ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
    motion = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    motion.setFinestScale(0)
    forward = motion.calc(ga, gb, None)
    backward = motion.calc(gb, ga, None)
    x, y = np.meshgrid(np.arange(WORK[0],dtype=np.float32), np.arange(WORK[1],dtype=np.float32))
    f, residual = pack_flow(forward,backward,ga,gb,x,y)
    r, reverse_residual = pack_flow(backward,forward,gb,ga,x,y)
    out = RUNTIME / (room+"-flow.png")
    Image.fromarray(np.concatenate([f,r],axis=1)).save(out,optimize=True)
    diff = float(np.mean(np.abs(ga.astype(np.float32)-gb.astype(np.float32))))
    result = {"first":ai,"last":bi,"motion_map":out.name,"map_sha256":digest(out),"working_size":list(WORK),
              "mean_unregistered_difference":round(diff,3),"mean_warped_difference":round(residual,3),
              "reverse_mean_warped_difference":round(reverse_residual,3),
              "motion_pixel_95th_percentile":round(float(np.percentile(np.linalg.norm(forward,axis=2),95)),3)}
    print(room, diff, residual, flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rooms",nargs="*")
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True,exist_ok=True)
    records = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    rooms = args.rooms or list(json.loads((SOURCE/"shots.json").read_text())["chapter_keyframes"])
    for room in rooms:
        records[room] = prepare(room)
        REPORT.write_text(json.dumps(records,indent=2)+"\n")

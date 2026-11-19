"""Prepare Godot cutouts and speech patches from the archived GPT Image portraits and Vision landmarks."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/characters/campaign"
RUNTIME = ROOT / "game/assets/illustrated/cast"
ART_SPEC = importlib.util.spec_from_file_location("painted_face", ROOT / "tools/prepare-archivist-sprite.py")
art = importlib.util.module_from_spec(ART_SPEC)
ART_SPEC.loader.exec_module(art)
art.SCALE = 4
SHAPES = {"X": None, "A": None, "B": "mouth_parted", "C": "mouth_wide", "D": "mouth_open",
          "E": "mouth_round", "F": "mouth_round", "G": "mouth_parted", "H": "mouth_parted"}


def split_ring(points):
    """Follow the two outlines from the outer corner to the inner corner."""
    ring = np.roll(points, -np.argmin(points[:, 0]), axis=0)
    right = np.argmax(ring[:, 0])
    arcs = [ring[:right + 1], np.concatenate((ring[:1], ring[:right - 1:-1]))]
    ordered = []
    for arc in arcs:
        arc = arc[np.argsort(arc[:, 0])]
        x, idx = np.unique(arc[:, 0], return_index=True)
        ordered.append(np.column_stack((x, arc[idx, 1])))
    return sorted(ordered, key=lambda a: np.mean(a[1:-1, 1]))


def padded_box(points, padding, size):
    lo = np.maximum(0, np.floor(points.min(axis=0) - padding)).astype(int)
    hi = np.minimum(size, np.ceil(points.max(axis=0) + padding)).astype(int)
    return (*lo.tolist(), *(hi - lo).tolist())


def face_frames(base, landmarks):
    size = np.array(base.size)
    p = {k: np.array(v) * size for k, v in landmarks["points"].items()}
    eye_rings = [p["leftEye"], p["rightEye"]]
    corners = [split_ring(r) for r in eye_rings]
    upper, lower = zip(*corners)
    eye_box = padded_box(np.vstack(eye_rings), 8, size)
    outer, inner = p["outerLips"], p["innerLips"]
    left, right = outer[np.argmin(outer[:, 0])], outer[np.argmax(outer[:, 0])]
    lips_top, lips_bottom = split_ring(inner)
    xx = np.linspace(inner[:, 0].min() + .1, inner[:, 0].max() - .1, 7)
    mid_y = (np.interp(xx, *lips_top.T) + np.interp(xx, *lips_bottom.T)) * .5
    edge = np.vstack((left, np.column_stack((xx, mid_y)), right))
    radius = right[0] - left[0]
    mouth_box = padded_box(outer, [radius * .16 + 3, radius * .30 + 3], size)
    rgb = np.asarray(base.convert("RGB"), dtype=np.float32)
    patches = {}
    for key, weight in (("blink_half", .52), ("blink_closed", 1)):
        patches[key] = (eye_box, art.blink(rgb, weight, upper, lower, eye_box, human_lids=True))
    face_light = np.percentile(rgb[eye_box[1]:eye_box[1]+eye_box[3], eye_box[0]:eye_box[0]+eye_box[2]], 82, axis=(0, 1))
    for key, opening, rounding, spread in (("mouth_parted", .060, 0, 0), ("mouth_open", .145, 0, .008),
                                              ("mouth_round", .16, 1.1, -.07), ("mouth_wide", .081, 0, .044)):
        patches[key] = (mouth_box, art.lips(rgb, radius * opening, rounding, spread, edge, mouth_box, face_light))
    centers = [np.rint(eye.mean(axis=0)).astype(int).tolist() for eye in eye_rings]
    return patches, centers, np.rint(edge[len(edge)//2]).astype(int).tolist()


def prepare(name, review):
    original = SOURCE / "masters" / (name + ".png")
    base = Image.open(original).convert("RGBA")
    base.thumbnail((1240, 1080), Image.Resampling.LANCZOS)
    folder = RUNTIME / name
    folder.mkdir(parents=True, exist_ok=True)
    image_path = folder / (name + ".webp")
    base.save(image_path, quality=94, method=6, exact=True)
    manifest = {"base": image_path.name, "source": str(original.relative_to(ROOT)), "source_sha256": art.sha(original),
                "size": list(base.size), "origin": "top_left", "foot_anchor": [base.width // 2, base.height],
                "frames": {}, "cue_frames": {}, "sha256": {image_path.name: art.sha(image_path)}}
    if name not in ("wick", "biscuit", "admiral"):
        landmarks = json.loads((SOURCE / "landmarks" / (name + ".json")).read_text())
        patches, centers, mouth = face_frames(base, landmarks)
        atlas = Image.new("RGBA", (max(b[2] for b, _ in patches.values()) + 2,
                                   sum(b[3] + 2 for b, _ in patches.values())))
        y = 0
        for key, (box, piece) in patches.items():
            x0, y0, w, h = box
            alpha = base.getchannel("A").crop((x0, y0, x0+w, y0+h))
            piece.putalpha(Image.fromarray(np.minimum(np.asarray(alpha), np.asarray(piece.getchannel("A")))))
            atlas.paste(piece, (0, y))
            manifest["frames"][key] = {"atlas_region": [0, y, w, h], "source_origin": [x0, y0]}
            y += h + 2
        atlas_path = folder / (name + "-face-atlas.png")
        atlas.save(atlas_path, optimize=True)
        manifest.update(atlas=atlas_path.name, cue_frames=SHAPES, eye_centers=centers, mouth_center=mouth)
        manifest["sha256"][atlas_path.name] = art.sha(atlas_path)
        if review:
            review.mkdir(parents=True, exist_ok=True)
            x0, y0, w, _ = patches["blink_closed"][0]
            _, my, _, mh = patches["mouth_open"][0]
            b = (x0-8, y0-13, x0+w+8, my+mh+3)
            pose_sheet = Image.new("RGB", ((b[2]-b[0])*3, b[3]-b[1]), "#454850")
            for i, key in enumerate(("", "blink_closed", "mouth_open")):
                pose = base.copy()
                if key:
                    box, piece = patches[key]
                    pose.alpha_composite(piece, box[:2])
                crop = pose.crop(b)
                pose_sheet.paste(crop, (i*crop.width, 0), crop)
            pose_sheet.save(review / (name + "-expressions.jpg"), quality=96)
    (folder / "sprite.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(name, base.size, len(manifest["frames"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    for who in args.names or sorted(json.loads((SOURCE / "portraits.json").read_text())["portraits"]):
        prepare(who, args.review)

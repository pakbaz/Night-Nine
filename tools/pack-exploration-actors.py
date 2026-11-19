"""Register transparent GPT Image poses on a common floor pivot and pack Godot atlases."""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/characters/campaign/performance"
OUTPUT = ROOT / "game/assets/illustrated/campaign/walk"
CELL = (416, 512)
SOLE_Y = 509
HEIGHT = 501
ROLES = ("steve", "stephen", "nora", "pell", "archivist")
RESIDENTS = ("calder", "iris", "agnes")


def poses(path, columns, rows, separate_silhouettes=False):
    image = Image.open(path)
    if image.mode != "RGBA" or image.getchannel("A").histogram()[0] < image.width * image.height / 4:
        raise ValueError(f"Missing transparent silhouette in {path}")
    result = []
    for row in range(rows):
        strip = image.crop((0, round(image.height * row / rows), image.width,
                            round(image.height * (row + 1) / rows)))
        edges = [round(strip.width * column / columns) for column in range(columns + 1)]
        if separate_silhouettes:
            # Generated sheets may place a hand or the back foot across a grid
            # division. Split at transparent space between complete figures.
            occupied = strip.getchannel("A").point(lambda a: 255 if a > 40 else 0).getprojection()[0]
            search = strip.width // (columns * 3)
            for index in range(1, columns):
                target = edges[index]
                gap = [x for x in range(target - search, target + search + 1) if not occupied[x]]
                if not gap:
                    raise ValueError(f"Joined silhouettes in {path}, row {row}, column {index}")
                nearest = min(gap, key=lambda x: abs(x - target))
                first = last = nearest
                while first > 0 and not occupied[first - 1]:
                    first -= 1
                while last + 1 < strip.width and not occupied[last + 1]:
                    last += 1
                edges[index] = (first + last) // 2
        for column in range(columns):
            frame = strip.crop((edges[column], 0, edges[column + 1], strip.height))
            alpha = frame.getchannel("A")
            solid = alpha.point(lambda opacity: 255 if opacity >= 110 else 0)
            box = solid.getbbox()
            if not box or box[3] - box[1] < frame.height * .5:
                raise ValueError(f"Incomplete pose in {path} cell {column},{row}")
            result.append((frame, solid, box))
    return result


def registered(pose, scale, at_rest=False):
    frame, solid, box = pose
    height = box[3] - box[1]
    # Center a walk on the actor's hips so switching the leading foot doesn't
    # shift the entire figure. In gestures anchor the planted feet instead.
    band = (.88, .96) if at_rest else (.45, .54)
    band_y = [round(box[1] + height * fraction) for fraction in band]
    middle = solid.crop((0, band_y[0], frame.width, band_y[1])).getbbox()
    center = (middle[0] + middle[2]) / 2
    scaled = frame.resize((round(frame.width * scale), round(frame.height * scale)), Image.Resampling.LANCZOS)
    x = round(CELL[0] * .5 - center * scale)
    y = round(SOLE_Y - box[3] * scale)
    if x + box[0] * scale < 1 or x + box[2] * scale > CELL[0] - 1:
        raise ValueError("Pose extends outside the sprite cell")
    output = Image.new("RGBA", CELL)
    output.alpha_composite(scaled, (x, y))
    return output


def save(image, path):
    image.save(path, quality=94, method=6, exact=True)


def pack(role):
    walk = poses(SOURCE / f"{role}-walk.png", 4, 2)
    scale = HEIGHT / max(box[3] - box[1] for _, _, box in walk)
    atlas = Image.new("RGBA", (4 * CELL[0], 2 * CELL[1]))
    for index, pose in enumerate(walk):
        frame = registered(pose, scale)
        atlas.paste(frame, (index % 4 * CELL[0], index // 4 * CELL[1]))
    save(atlas, OUTPUT / f"{role}.webp")
    acting = poses(SOURCE / f"{role}-acting.png", 3, 1)
    idle = acting[0][2]
    scale = HEIGHT / (idle[3] - idle[1])
    for pose, name in zip(acting, ("idle", "reach", "listen")):
        save(registered(pose, scale, at_rest=True), OUTPUT / f"{role}-{name}.webp")


def pack_scene_poses(role):
    sources = SOURCE / "scene-aware"
    if role in ROLES:
        depth = poses(sources / f"{role}-depth.png", 4, 2, separate_silhouettes=True)
        scale = HEIGHT / max(box[3] - box[1] for _, _, box in depth)
        for row, name in enumerate(("away", "toward")):
            atlas = Image.new("RGBA", (4 * CELL[0], CELL[1]))
            for column in range(4):
                atlas.paste(registered(depth[row * 4 + column], scale), (column * CELL[0], 0))
            save(atlas, OUTPUT / f"{role}-{name}.webp")
    if role in RESIDENTS or role in ("steve", "nora"):
        resident = role in RESIDENTS
        kinds = ("idle", "greet", "listen", "talk") if resident else (None, "kneel", "read", "operate")
        file = sources / f"{role}-{'resident' if resident else 'interaction'}.png"
        gestures = poses(file, 4, 1, separate_silhouettes=True)
        # Use the standing pose for all four. A crouched actor keeps the same
        # head and hand scale and their planted feet remain on the floor.
        base = gestures[0][2]
        scale = HEIGHT / (base[3] - base[1])
        for gesture, name in zip(gestures, kinds):
            if name:
                save(registered(gesture, scale, at_rest=True), OUTPUT / f"{role}-{name}.webp")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roles", nargs="*")
    parser.add_argument("--scene-aware-only", action="store_true")
    args = parser.parse_args()
    selected = args.roles or ROLES + RESIDENTS
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for actor in selected:
        if actor not in ROLES + RESIDENTS:
            parser.error(f"Unknown actor {actor}")
        if actor in ROLES and not args.scene_aware_only:
            pack(actor)
        pack_scene_poses(actor)

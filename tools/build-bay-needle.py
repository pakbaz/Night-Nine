#!/usr/bin/env python3
"""Cut Frank's radio needle, its brass cap and a phosphor glow out of the bay master painting.

The game paints the needle out of the runtime foreground and draws these three
textures on top, so the needle can swing with the dial while keeping the
painting's own colour and brushwork. Source: assets/environments/bellwether-bay/foreground.png,
which still has the painted needle. Output: game/assets/illustrated/rooms/bay-needle*.png
and bay-dial-glow.png.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "assets/environments/bellwether-bay/foreground.png"
OUT = ROOT / "game/assets/illustrated/rooms"
SS = 2                       # texture pixels per plate pixel
PAINTED_CAP = np.array([548.0, 614.4])
PAINTED_TIP = np.array([-0.3497 * 548.3 + 762.91, 548.3])   # fitted to the painted shaft
NEEDLE_LENGTH = 64.0         # plate pixels, pivot to tip, once re-centred under the scale
HALF_WIDTH = 3.0


def sample(image, xs, ys):
    return np.stack([ndimage.map_coordinates(image[..., c], [ys, xs], order=1, mode="nearest")
                     for c in range(4)], axis=-1)


def orange(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (np.clip((r - g - 0.10) / 0.20, 0, 1) * np.clip((r - 0.36) / 0.20, 0, 1)
            * np.clip((0.42 - b) / 0.15, 0, 1))


def needle(plate):
    length = np.linalg.norm(PAINTED_TIP - PAINTED_CAP)
    along = (PAINTED_TIP - PAINTED_CAP) / length
    across = np.array([-along[1], along[0]])
    width, height = int(2 * HALF_WIDTH * SS) + 1, int(NEEDLE_LENGTH * SS) + 1
    s = np.arange(width) / SS - HALF_WIDTH
    t = (height - 1 - np.arange(height)) / SS          # 0 at the pivot (bottom row)
    S, T = np.meshgrid(s, t * (length / NEEDLE_LENGTH))
    painted = sample(plate, PAINTED_CAP[0] + T * along[0] + S * across[0],
                     PAINTED_CAP[1] + T * along[1] + S * across[1])
    lit = orange(painted[..., :3])
    # The shaft's own colour from pivot to tip, smoothed so tick marks crossing it don't show.
    core = np.zeros((height, 3))
    found = np.zeros(height, bool)
    for i in range(height):
        on = (lit[i] > 0.6) & (np.abs(s) < 1.0)
        if on.any():
            core[i] = painted[i, on, :3].mean(axis=0)
            found[i] = True
    rows = np.where(found)[0]
    for c in range(3):
        core[:, c] = np.interp(np.arange(height), rows, core[rows, c])
        core[:, c] = ndimage.gaussian_filter1d(ndimage.median_filter(core[:, c], 9), 2.0)
    # The painted shape: about 2.8 plate pixels wide at the base, narrowing to a point.
    fraction = t / NEEDLE_LENGTH
    half = np.where(fraction < 0.88, 1.42 - 0.22 * fraction / 0.88,
                    1.20 * np.clip((1.0 - fraction) / 0.12, 0, 1) + 0.12)
    alpha = np.clip((half[:, None] + 0.45 - np.abs(s)[None, :]) / 0.9, 0, 1)
    shade = 1.0 + 0.10 * np.clip(-s[None, :] / 1.4, -1, 1)
    rgb = np.clip(core[:, None, :] * shade[..., None], 0, 1)
    keep = (lit > 0.75) & (np.abs(s)[None, :] < half[:, None] - 0.2)
    rgb = np.where(keep[..., None], 0.55 * painted[..., :3] + 0.45 * rgb, rgb)
    return np.dstack([rgb, alpha])


def cap(plate):
    length = np.linalg.norm(PAINTED_TIP - PAINTED_CAP)
    along = (PAINTED_TIP - PAINTED_CAP) / length
    across = np.array([-along[1], along[0]])
    centre, rx, ry = np.array([548.8, 615.3]), 6.4, 5.0
    ys, xs = np.mgrid[0:int(2 * ry * SS) + 5, 0:int(2 * rx * SS) + 5]
    cx = (xs - (xs.shape[1] - 1) / 2) / SS
    cy = (ys - (ys.shape[0] - 1) / 2) / SS
    image = sample(plate, centre[0] + cx, centre[1] + cy)
    # The painted shaft leaves the cap at its upper right: mirror the clean upper left over it.
    stub = (cx * along[0] + cy * along[1] > 1.5) & (np.abs(cx * across[0] + cy * across[1]) < 1.6)
    image[stub] = sample(plate, centre[0] - cx, centre[1] + cy)[stub]
    ellipse = np.sqrt((cx / (rx - 0.6)) ** 2 + (cy / (ry - 0.5)) ** 2)
    image[..., 3] = np.clip((1.12 - ellipse) / 0.12, 0, 1)
    return image


def glow():
    y, x = np.mgrid[0:48, 0:72]
    falloff = np.clip(1 - np.sqrt(((x - 35.5) / 34) ** 2 + ((y - 23.5) / 22) ** 2), 0, 1) ** 1.6
    return np.dstack([np.ones_like(falloff)] * 3 + [falloff])


def save(name, image):
    Image.fromarray((np.clip(image, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(OUT / name)
    print(name, image.shape[1], "x", image.shape[0])


if __name__ == "__main__":
    plate = np.asarray(Image.open(MASTER).convert("RGBA")).astype(np.float64) / 255
    save("bay-needle.png", needle(plate))
    save("bay-needle-cap.png", cap(plate))
    save("bay-dial-glow.png", glow())

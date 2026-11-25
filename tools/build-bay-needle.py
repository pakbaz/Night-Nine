#!/usr/bin/env python3
"""Build Frank's vintage radio needle, dark brass pivot collar, phosphor glow, and curved glass overlay.

The game paints the original static needle out of the runtime foreground and renders
these layers inside a bezel-clipped aperture so the pointer pivots dead-centre along
the painted scale axis behind the glass. Output: game/assets/illustrated/rooms/
bay-needle.png, bay-needle-cap.png, bay-dial-glow.png, and bay-dial-glass.png.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "assets/environments/bellwether-bay/foreground.png"
OUT = ROOT / "game/assets/illustrated/rooms"
SS = 2                       # texture pixels per plate pixel
NEEDLE_LENGTH = 68.0         # plate pixels, pivot at bottom rim to scale tip
HALF_WIDTH = 3.5

# Inner dial-glass bounding box on the 1672x941 plate (matches room.gd DIAL_APERTURE).
GLASS_X0, GLASS_Y0, GLASS_X1, GLASS_Y1 = 418, 538, 624, 636


def needle():
    """Slender tapered vintage enamel meter pointer with metallic bevel shading."""
    width, height = int(2 * HALF_WIDTH * SS) + 1, int(NEEDLE_LENGTH * SS) + 1
    s = np.arange(width) / SS - HALF_WIDTH
    t = (height - 1 - np.arange(height)) / SS          # 0 at pivot (bottom row)
    frac = t / NEEDLE_LENGTH

    # Real vintage meter pointer: narrow counterweight base tapering smoothly to a crisp tip.
    half = np.where(
        frac < 0.14,
        1.45 - 0.30 * (frac / 0.14),
        np.where(
            frac < 0.85,
            1.15 - 0.50 * ((frac - 0.14) / 0.71),
            0.65 * np.clip((1.0 - frac) / 0.15, 0.0, 1.0) + 0.14,
        ),
    )
    # Anti-aliased silhouette
    alpha = np.clip((half[:, None] + 0.35 - np.abs(s)[None, :]) / 0.70, 0.0, 1.0)
    # Soften the very tip and base slightly so it blends into the glass recess
    alpha *= np.clip((NEEDLE_LENGTH - t[:, None]) / 1.1, 0.0, 1.0)

    # Weathered warm copper-crimson enamel: muted enough to sit *inside* dark backlit glass.
    base_rgb = np.array([0.62, 0.25, 0.12])
    tip_rgb = np.array([0.78, 0.42, 0.19])
    body = base_rgb[None, :] * (1.0 - frac[:, None] * 0.65) + tip_rgb[None, :] * (frac[:, None] * 0.65)

    # Cylindrical bevel shading across the shaft: soft warm specular on left edge, dark rim on right.
    norm_s = np.clip(s[None, :] / np.maximum(half[:, None], 0.25), -1.0, 1.0)
    bevel = 0.82 - 0.28 * norm_s + 0.30 * np.exp(-((norm_s + 0.38) / 0.34) ** 2)
    # Subtle recess shadow near the bottom bezel lip
    recess = 0.58 + 0.42 * np.clip(frac[:, None] / 0.22, 0.0, 1.0)
    rgb = np.clip(body[:, None, :] * bevel[..., None] * recess[..., None], 0.0, 1.0)

    # Dark outline kiss along outer edge so pointer separates cleanly over glowing green scale ticks.
    edge_dark = 1.0 - 0.32 * np.clip((np.abs(norm_s) - 0.65) / 0.35, 0.0, 1.0)
    rgb *= edge_dark[..., None]
    return np.dstack([rgb, alpha])


def cap():
    """Dark weathered brushed-brass pivot hub tucked at the bottom rim."""
    rx, ry = 7.2, 5.6
    w, h = int(2 * rx * SS) + 5, int(2 * ry * SS) + 5
    ys, xs = np.mgrid[0:h, 0:w]
    cx = (xs - (w - 1) / 2.0) / SS
    cy = (ys - (h - 1) / 2.0) / SS
    r = np.sqrt((cx / rx) ** 2 + (cy / ry) ** 2)

    alpha = np.clip((1.04 - r) / 0.14, 0.0, 1.0)
    # Weathered dark olive-brass metallic dome matching the radio chassis
    dome = np.clip(1.0 - r * r, 0.0, 1.0)
    light = np.clip(0.35 - 0.35 * (cx / rx) - 0.55 * (cy / ry), 0.0, 1.0)
    spec = np.exp(-(((cx + 1.8) / 2.6) ** 2 + ((cy + 1.8) / 2.0) ** 2))
    rim_shadow = np.clip(1.0 - np.clip((r - 0.72) / 0.28, 0.0, 1.0) * 0.55, 0.35, 1.0)

    dark_brass = np.array([0.14, 0.11, 0.06])
    mid_brass = np.array([0.36, 0.28, 0.15])
    hi_brass = np.array([0.64, 0.52, 0.31])

    rgb = (
        dark_brass * (1.0 - dome[..., None] * 0.6)
        + mid_brass * (light[..., None] * 0.85)
        + hi_brass * (spec[..., None] * 0.55)
    ) * rim_shadow[..., None]
    return np.dstack([np.clip(rgb, 0.0, 1.0), alpha])


def glow():
    """Soft, restrained phosphor backlight halo along the scale."""
    y, x = np.mgrid[0:48, 0:72]
    falloff = np.clip(1.0 - np.sqrt(((x - 35.5) / 34.0) ** 2 + ((y - 23.5) / 22.0) ** 2), 0.0, 1.0) ** 2.1
    return np.dstack([np.ones_like(falloff)] * 3 + [falloff * 0.72])


def glass_overlay():
    """Subtle curved glass reflection and recessed inner bezel shadow drawn OVER the needle."""
    w = GLASS_X1 - GLASS_X0
    h = GLASS_Y1 - GLASS_Y0
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    nx = (xs - w * 0.5) / (w * 0.5)
    ny = (ys - h * 0.5) / (h * 0.5)

    # Inner recessed bezel shadow around top, bottom, and side rims
    top_sh = np.exp(-((ys / 13.0) ** 2)) * 0.42
    bot_sh = np.exp(-(((h - 1 - ys) / 10.0) ** 2)) * 0.50
    side_sh = np.clip((np.abs(nx) - 0.76) / 0.24, 0.0, 1.0) ** 1.5 * 0.35
    shadow_a = np.clip(top_sh + bot_sh + side_sh, 0.0, 0.62)

    # Delicate diagonal cool-white glass reflection streak across upper-left glass
    diag = (nx * 0.65 + ny * 1.15 + 0.35)
    streak1 = np.exp(-((diag / 0.22) ** 2)) * np.clip(1.0 - (ys / (h * 0.75)), 0.0, 1.0) * 0.095
    streak2 = np.exp(-(((diag - 0.42) / 0.10) ** 2)) * np.clip(1.0 - (ys / (h * 0.65)), 0.0, 1.0) * 0.045
    glare_a = np.clip(streak1 + streak2, 0.0, 0.14)

    # Premultiply-free blend of dark shadow and subtle cool-moonlit glass reflection
    total_a = np.clip(shadow_a + glare_a * (1.0 - shadow_a), 0.0, 1.0)
    glare_rgb = np.array([0.74, 0.86, 0.82])
    shadow_rgb = np.array([0.02, 0.04, 0.02])
    safe_a = np.maximum(total_a, 1e-6)
    rgb = (
        shadow_rgb * (shadow_a * (1.0 - glare_a))[..., None]
        + glare_rgb * glare_a[..., None]
    ) / safe_a[..., None]
    return np.dstack([np.clip(rgb, 0.0, 1.0), total_a])


def save(name, image):
    Image.fromarray((np.clip(image, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(OUT / name)
    print(name, image.shape[1], "x", image.shape[0])


if __name__ == "__main__":
    save("bay-needle.png", needle())
    save("bay-needle-cap.png", cap())
    save("bay-dial-glow.png", glow())
    save("bay-dial-glass.png", glass_overlay())


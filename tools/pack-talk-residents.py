"""Register the existing full-length Bellwether cast drawings as transparent stage figures."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
CAST = ROOT / "assets/characters/campaign"
OUT = ROOT / "game/assets/illustrated/campaign/walk"
# Trim sheet captions and the secondary face studies beside the standing pose.
# Coordinates are fractions of the archived reference, not the runtime stage.
CROPS = {
    "lyle": (0, 0, 1, .938), "carmen": (0, 0, 1, .95), "tomas": (0, 0, 1, .944),
    "rafa": (0, 0, 1, .946), "mateo": (0, 0, 1, .95), "luis": (.044, 0, 1, .953),
    "gus": (0, 0, 1, .94), "rook": (0, 0, 1, .94), "shaw": (0, 0, .78, 1),
    "wen": (.11, 0, .70, 1), "ward": (0, 0, .60, 1),
}


def cutout(name, bounds):
    im = Image.open(CAST / "references" / (name + ".png")).convert("RGB")
    im = im.crop(tuple(round(n * dim) for n, dim in zip(bounds, im.size * 2)))
    if name == "shaw":
        # Keep her elbow, but not the face printed just above it.
        ImageDraw.Draw(im).polygon([(im.width, 0), (im.width*.90, 0),
                                    (im.width*.90, im.height*.24), (im.width, im.height*.282)],
                                   fill=im.getpixel((2, 10)))
    rgb = np.asarray(im, dtype=float)
    bg = np.median(rgb[im.height//3:im.height//2, -2:].reshape(-1, 3), axis=0)
    # The studies share a neutral paper background. Keep the main connected
    # painted silhouette, including its light clothing, but not the ground shadow.
    paper = np.median(np.asarray(Image.open(CAST / "references" / (name + ".png")).convert("RGB"),
                                 dtype=float)[int(im.height*.8):int(im.height*.85), -3:], axis=(0, 1))
    if np.mean(paper) > 145:
        bg = paper
    mask = np.linalg.norm(rgb-bg, axis=2) > 42
    labels, _ = ndimage.label(ndimage.binary_closing(mask, iterations=1, border_value=0))
    largest = np.bincount(labels.ravel())[1:].argmax()+1
    mask = labels == largest
    # The chefs' white coats fade into the paper. Trace their outer silhouettes
    # rather than punching holes in jackets, aprons, or faces.
    chef = {
        "gus": [(.19,.10),(.23,.04),(.32,.008),(.42,.006),(.55,.04),(.60,.10),(.60,.13),(.74,.15),(.85,.21),(.93,.25),(.96,.33),(.99,.37),(.96,.42),(.88,.45),(.94,.57),(.96,.74),(.86,.76),(.88,.93),(.96,.96),(.92,.98),(.68,.98),(.59,.955),(.52,.79),(.48,.94),(.44,.996),(.17,.996),(.12,.96),(.12,.78),(.06,.76),(.085,.50),(.115,.44),(.02,.42),(.008,.36),(.03,.255),(.09,.205),(.25,.16)],
        "rafa": [(.30,.13),(.28,.09),(.31,.045),(.37,.023),(.52,.022),(.60,.047),(.65,.095),(.62,.14),(.76,.16),(.88,.19),(.96,.245),(.94,.32),(.90,.36),(.78,.37),(.81,.45),(.90,.60),(.88,.69),(.77,.69),(.77,.92),(.82,.95),(.86,.98),(.82,.996),(.60,.997),(.55,.96),(.49,.76),(.32,.96),(.25,.993),(.014,.994),(.006,.97),(.07,.92),(.12,.68),(.07,.67),(.09,.48),(.14,.37),(.075,.34),(.07,.27),(.12,.20),(.23,.171),(.34,.153)],
    }
    if name in chef:
        hull = Image.new("1", im.size)
        ImageDraw.Draw(hull).polygon([(x*im.width, y*im.height) for x,y in chef[name]], fill=1)
        mask |= np.asarray(hull)
    # Fill small holes in clothing; preserve daylight between arms and legs.
    holes, _ = ndimage.label(~mask)
    sizes = np.bincount(holes.ravel())
    mask |= (holes > 0) & (sizes[holes] < im.width*im.height*.01)
    # Strip the painted pale-grey paper cast shadow around the shoes in the foot band.
    ys_nonzero = np.where(mask.any(axis=1))[0]
    foot_top = int(ys_nonzero.max() - (ys_nonzero.max() - ys_nonzero.min()) * 0.085)
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    foot_zone = np.zeros_like(mask)
    foot_zone[foot_top:, :] = True
    puddle = foot_zone & (lum > 135) & (sat < 36)
    mask &= ~puddle
    labels, _ = ndimage.label(mask)
    largest = np.bincount(labels.ravel())[1:].argmax() + 1
    mask = labels == largest
    alpha = Image.fromarray((mask*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.65))
    im.putalpha(alpha)
    return im.crop(alpha.getbbox())


def register(im, name):
    im.thumbnail((400, 502), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (416, 512))
    frame.alpha_composite(im, ((416-im.width)//2, 509-im.height))
    frame.save(OUT / (name+"-idle.webp"), quality=94, method=6, exact=True)


def standing_portrait(name, reference, hips, width):
    """Extend the approved three-quarter portrait with trousers from the wardrobe studies."""
    upper = Image.open(CAST/"masters"/(name+".png")).convert("RGBA")
    upper = upper.crop(upper.getbbox())
    upper.thumbnail((380, 330), Image.Resampling.LANCZOS)
    lower = reference.crop((0, round(hips*reference.height), reference.width, reference.height))
    waist = lower.getchannel("A").crop((0, 0, lower.width, 2)).getbbox()
    seam = upper.getchannel("A").crop((0, upper.height-2, upper.width, upper.height)).getbbox()
    scale = (seam[2]-seam[0])*width/(waist[2]-waist[0])
    lower = lower.resize((round(lower.width*scale), round(lower.height*scale)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (max(upper.width, lower.width)+100, upper.height+lower.height-6))
    out.alpha_composite(lower, (round(50+(seam[0]+seam[2])/2-(waist[0]+waist[2])*scale/2),upper.height-6))
    out.alpha_composite(upper,(50,0))
    return out.crop(out.getbbox())


if __name__ == "__main__":
    for who, box in CROPS.items():
        register(cutout(who, box), who)
    for name, ref, fraction, width in [("frank_standing","luis",.62,.94),
                                       ("helen_field","wen",.56,.78), ("iris_epilogue","shaw",.57,.96)]:
        register(standing_portrait(name, cutout(ref, CROPS[ref]), fraction, width), name)

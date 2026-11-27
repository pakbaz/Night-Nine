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
# The shoes and the shadow painted under them sit in this bottom share of a figure.
FOOT = .085


def paper_contrast(rgb):
    """Distance from the paper and local texture of a study on smooth paper."""
    # The paper is a soft left-to-right gradient; model it from both edge columns.
    left = rgb[:, :3].mean(axis=1)
    right = rgb[:, -4:].mean(axis=1)
    across = np.linspace(0, 1, rgb.shape[1])[None, :, None]
    paper = left[:, None, :]*(1-across) + right[:, None, :]*across
    distance = np.linalg.norm(rgb-paper, axis=2)
    lum = rgb @ np.array([.299, .587, .114])
    mean = ndimage.uniform_filter(lum, 5)
    texture = np.sqrt(np.maximum(ndimage.uniform_filter(lum*lum, 5)-mean*mean, 0))
    return distance, texture


def close_clothing(rgb, mask):
    """Enclosed gaps that are plain paper stay open; anything else inside is clothing."""
    distance, texture = paper_contrast(rgb)
    plain = (distance < 20) & (texture < 5)
    mask = mask.copy()
    holes, count = ndimage.label(~mask)
    edge = set(np.unique(np.concatenate([holes[0], holes[-1], holes[:, 0], holes[:, -1]])))
    for hole in range(1, count+1):
        region = holes == hole
        if hole not in edge and plain[region].mean() < .9:
            mask |= region
    return mask


def textured_figure(rgb):
    """Figure mask for a light-clothed study on smooth paper."""
    distance, texture = paper_contrast(rgb)
    mask = (distance > 24) | (texture > 8)
    mask = ndimage.binary_closing(ndimage.binary_opening(mask, iterations=1), iterations=3, border_value=0)
    labels, _ = ndimage.label(mask)
    mask = labels == np.bincount(labels.ravel())[1:].argmax()+1
    return ndimage.binary_erosion(close_clothing(rgb, mask), iterations=1)


def ground_shadow(rgb, mask, paper):
    """The cast shadow painted on the floor around the shoes: paper darkened by a smooth wash."""
    rows = np.where(mask.any(axis=1))[0]
    zone = np.zeros_like(mask)
    zone[int(rows.max() - (rows.max()-rows.min())*FOOT):] = True
    # A wash keeps the paper's hue at a lower value and has no strokes, however steeply it shades.
    shade = (rgb @ paper)/(paper @ paper)
    toned = (shade > .4) & (shade < 1.08) & (np.linalg.norm(rgb - shade[..., None]*paper, axis=2) < 16)
    lum = rgb @ np.array([.299, .587, .114])
    detail = np.sqrt(np.maximum(ndimage.uniform_filter((lum - ndimage.gaussian_filter(lum, 1))**2, 3), 0))
    wash = toned & (detail < 5)
    # Paper-toned slivers the shoe closes around (welts, highlights, scuffs) stay with the shoe.
    shoe = ndimage.binary_closing(mask & ~toned, iterations=2)
    # Only wash that daylight reaches is shadow; then take its soft rim, short of the shoe.
    shadow = ndimage.binary_propagation(zone & ~mask, mask=zone & (~mask | (wash & ~shoe))) & mask
    for _ in range(2):
        shadow |= ndimage.binary_dilation(shadow) & mask & zone & toned & ~shoe
    return shadow


def clean_fringe(rgb, mask, paper, depth=3):
    """Repaint the paper-tinted rim and alpha spill with the colour from just inside the figure."""
    solid = ndimage.distance_transform_edt(mask) > depth
    nearest = ndimage.distance_transform_edt(~solid, return_indices=True)[1]
    figure = rgb[nearest[0], nearest[1]]
    # A rim pixel that lies between the figure colour and the paper is a blend of the two.
    span = figure - paper
    share = ((rgb - paper)*span).sum(axis=2)/np.maximum((span*span).sum(axis=2), 1)
    off_line = np.linalg.norm(rgb - paper - share[..., None]*span, axis=2)
    tinted = mask & ~solid & (share > -.15) & (share < .92) & (off_line < 18)
    out = rgb.copy()
    out[tinted] = figure[tinted]
    # The blurred alpha spills just past the mask: give it the colour of the edge it extends.
    edge = ndimage.distance_transform_edt(~mask, return_indices=True)[1]
    return out[edge[0], edge[1]]


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
    # The chefs' white coats are close to the paper colour, so colour alone punches
    # holes in them. Paper is also smooth: keep what differs from it in colour or
    # in texture, and keep the plain paper showing between their legs.
    if name in ("gus", "rafa"):
        mask = textured_figure(rgb)
    # Fill tiny interior paint specks without filling daylight between arms and waist.
    holes, _ = ndimage.label(~mask)
    sizes = np.bincount(holes.ravel())
    mask |= (holes > 0) & (sizes[holes] < im.width*im.height*.0015)
    mask &= ~ground_shadow(rgb, mask, bg)
    # Carmen's apron, tea towel and dish are as pale as the paper: close the holes colour cuts in them.
    if name == "carmen":
        mask = close_clothing(rgb, mask)
    labels, _ = ndimage.label(mask)
    largest = np.bincount(labels.ravel())[1:].argmax() + 1
    mask = labels == largest
    alpha = Image.fromarray((mask*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.65))
    im = Image.fromarray(clean_fringe(rgb, mask, bg).astype(np.uint8))
    im.putalpha(alpha)
    return im.crop(alpha.getbbox())


def register(im, name):
    im.thumbnail((400, 502), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (416, 512))
    frame.alpha_composite(im, ((416-im.width)//2, 509-im.height))
    frame.save(OUT / (name+"-idle.webp"), quality=94, method=6, exact=True)


def fade_join(upper, lower, top, left, feet, taper=12):
    """Blend a master cut mid-thigh into reference trousers placed `top` rows down its height."""
    u = np.asarray(upper, dtype=float).copy()
    l = np.asarray(lower, dtype=float).copy()
    # The reference as it lies under the master's bottom band, in the master's coordinates.
    under = np.zeros_like(u)
    rows = min(upper.height - top, lower.height)
    x0, x1 = max(left, 0), min(left + lower.width, upper.width)
    under[top:top+rows, x0:x1] = l[:rows, x0-left:x1-left]
    y = np.arange(upper.height)[:, None]
    band = np.broadcast_to(y >= top, u.shape[:2])
    # Paper left opaque between the master's thighs, open at its cut edge, is not trousers.
    lum = u[..., :3] @ np.array([.299, .587, .114])
    sat = u[..., :3].max(axis=2) - u[..., :3].min(axis=2)
    paper = band & (lum > 140) & (sat < 16)
    paper = ndimage.binary_propagation(paper & (y == upper.height-1), mask=paper)
    u[ndimage.binary_dilation(paper) & band, 3] = 0
    # Tone the reference trousers to the master's where both cover the band; the shoes keep theirs.
    both = band & (u[..., 3] > 250) & (under[..., 3] > 250)
    gain = u[both, :3].mean(axis=0)/under[both, :3].mean(axis=0)
    trousers = np.clip((lower.height - feet - np.arange(lower.height))/12 + .5, 0, 1)[:, None, None]
    l[..., :3] = np.clip(l[..., :3]*(1 + (gain - 1)*trousers), 0, 255)
    # Over the trousers the master fades out across the band; where nothing lies underneath,
    # its silhouette tapers off over the last few rows instead of ending in a step.
    cover = under[..., 3]/255
    fade = np.clip((upper.height - y)/(upper.height - top), 0, 1)
    tail = np.clip((upper.height - y)/taper, 0, 1)
    u[..., 3] *= fade*cover + tail*(1 - cover)
    return (Image.fromarray(np.round(u).astype(np.uint8)),
            Image.fromarray(np.round(l).astype(np.uint8)))


def standing_portrait(name, reference, hips, width, blend=0):
    """Join the approved full-head portrait onto the standing trousers from the reference sheet.

    A master cut mid-thigh meets the reference within one garment: with `blend`, tone those
    trousers to the master's and cross-fade the two over that many rows, not a hard paste."""
    upper = Image.open(CAST/"masters"/(name+".png")).convert("RGBA")
    upper = upper.crop(upper.getbbox())
    upper.thumbnail((380, 330), Image.Resampling.LANCZOS)
    cut = round(hips*reference.height)
    waist = reference.getchannel("A").crop((0, cut, reference.width, cut+2)).getbbox()
    seam = upper.getchannel("A").crop((0, upper.height-2, upper.width, upper.height)).getbbox()
    scale = (seam[2]-seam[0])*width/(waist[2]-waist[0])
    rise = int(np.ceil(blend/scale))
    lower = reference.crop((0, cut-rise, reference.width, reference.height))
    lower = lower.resize((round(lower.width*scale), round(lower.height*scale)), Image.Resampling.LANCZOS)
    top = upper.height - 6 - round(rise*scale)
    left = round((seam[0]+seam[2])/2-(waist[0]+waist[2])*scale/2)
    if blend:
        upper, lower = fade_join(upper, lower, top, left, round(FOOT*reference.height*scale))
    out = Image.new("RGBA", (max(upper.width, lower.width)+100, top+lower.height))
    out.alpha_composite(lower, (50+left, top))
    out.alpha_composite(upper, (50, 0))
    return out.crop(out.getbbox())


if __name__ == "__main__":
    # Four reference sheets clip the top of the character's hair at y=0; splice their
    # unclipped approved master portrait onto their standing legs from the same sheet.
    UNCLIPPED = {
        "shaw": ("shaw", .46, .95),
        "ward": ("ward", .52, .96),
        "rook": ("rook", .52, .97),
        "lyle": ("lyle", .48, .96),
    }
    for who, box in CROPS.items():
        if who in UNCLIPPED:
            ref, fraction, width = UNCLIPPED[who]
            register(standing_portrait(who, cutout(ref, CROPS[ref]), fraction, width), who)
        else:
            register(cutout(who, box), who)
    # iris_epilogue's standing figure is a full-length painting kept as the runtime sprite.
    # Frank's master ends mid-thigh, so his trousers are blended into Luis's legs.
    for name, ref, fraction, width, blend in [("frank_standing","luis",.62,.94,24), ("helen_field","wen",.56,.78,0)]:
        register(standing_portrait(name, cutout(ref, CROPS[ref]), fraction, width, blend), name)

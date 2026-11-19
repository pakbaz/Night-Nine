"""Prepare the registered cinematics from the game's GPT Image editing masters."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MASTERS = ROOT / "assets/cinematics/campaign/films"
DEST = ROOT / "game/assets/illustrated/campaign/films"


def add_message(plate):
    # Match the four corners of the photographed LCD. Bake the canonical
    # message into its perspective so the letters follow the camera.
    glyphs = Image.new("RGBA", (300, 300))
    draw = ImageDraw.Draw(glyphs)
    font = ImageFont.load_default(size=32)
    for i, line in enumerate(("he remembers", "june.", "that doesnt", "mean hes", "adrian.")):
        draw.text((12, 22 + i * 46), line, font=font, fill=(14, 55, 72, 228))
    quad = ((.567,.521), (.647,.538), (.619,.677), (.539,.658))
    corners = ((0,0), (300,0), (300,300), (0,300))
    rows, rhs = [], []
    for (x,y), (u,v) in zip(quad, corners):
        x, y = plate.width*x, plate.height*y
        rows.extend(((x,y,1,0,0,0,-u*x,-u*y),(0,0,0,x,y,1,-v*x,-v*y)))
        rhs.extend((u,v))
    overlay = glyphs.transform(plate.size, Image.Transform.PERSPECTIVE,
                              np.linalg.solve(rows, rhs), Image.Resampling.BICUBIC)
    plate.paste(overlay, (0,0), overlay)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    book = json.loads((ROOT / "game/content/films.json").read_text())
    for room, film in book.items():
        if film["plate"].startswith("films/"):
            with Image.open(MASTERS / f"{room}.png") as master:
                plate = ImageOps.fit(master.convert("RGB"), (1600,900), Image.Resampling.LANCZOS)
            if room == "c3_archive":
                add_message(plate)
            plate.save(DEST / f"{room}.webp", quality=93, method=6)
        if "subject" in film:
            name = film["subject"]
            with Image.open(MASTERS / f"{name}.png") as master:
                subject = master.convert("RGBA")
            # Maintain the original registration of the wheels, hulls and keel.
            subject.thumbnail((1400,900), Image.Resampling.LANCZOS)
            subject.save(DEST / f"{name}.webp", quality=94, alpha_quality=100, method=6)


if __name__ == "__main__":
    main()

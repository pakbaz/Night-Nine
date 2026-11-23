#!/usr/bin/env python3
"""Convert story still and bridge masters to the runtime WebP the game loads.

Masters are 1536 x 864 PNGs in assets/cinematics/campaign/{stills,bridges}/. The game
loads 1600 x 900 WebP (LANCZOS, quality 88, method 6) from
game/assets/illustrated/campaign/{stills,bridges}/. Pass master names to convert just
those, or nothing to convert any master that has no runtime file yet.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("stills", "bridges")


def convert(master: Path) -> Path:
    target = ROOT / "game/assets/illustrated/campaign" / master.parent.name / (master.stem + ".webp")
    image = Image.open(master).convert("RGB").resize((1600, 900), Image.LANCZOS)
    image.save(target, "WEBP", quality=88, method=6)
    return target


if __name__ == "__main__":
    names = set(sys.argv[1:])
    for folder in FOLDERS:
        for master in sorted((ROOT / "assets/cinematics/campaign" / folder).glob("*.png")):
            runtime = ROOT / "game/assets/illustrated/campaign" / folder / (master.stem + ".webp")
            if master.stem in names or (not names and not runtime.exists()):
                print(convert(master).relative_to(ROOT))

"""Register the isolated GPT Image foreground art on the same plane as its matching Godot room."""
import json
from pathlib import Path

from PIL import Image, ImageFilter

root = Path(__file__).resolve().parents[1]
source = root / "assets/environments/campaign/foregrounds"
output = root / "game/assets/illustrated/campaign/foregrounds"
output.mkdir(exist_ok=True, parents=True)
for name, placement in json.loads((source / "layout.json").read_text()).items():
    canvas = Image.new("RGBA", (1600, 900))
    x, y, w, h = placement["normalized_bounds"]
    art = Image.open(source / (name + ".png")).convert("RGBA")
    art.thumbnail((round(w * canvas.width), round(h * canvas.height)), Image.Resampling.LANCZOS)
    art = art.filter(ImageFilter.GaussianBlur(.65))
    canvas.alpha_composite(art, (round(x * canvas.width), round(y * canvas.height)))
    canvas.save(output / (name + ".webp"), quality=94, method=6, exact=True)
    print(name, art.size)

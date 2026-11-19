"""Package the Windows export with notices and provenance hashes."""
from pathlib import Path
import hashlib
import json
import zipfile
import re
from desktop_notices import add_notices

root = Path(__file__).resolve().parent.parent
builds = root / "builds"
version = re.search(r'config/version="([^\"]+)"', (root/'game/project.godot').read_text()).group(1)
release = re.fullmatch(r'(\d+\.\d+\.\d+)(?:-[a-z0-9-]+)?', version)
if not release:raise SystemExit('Set a semantic project version before packaging.')
release = release.group(1)
take_count = len(json.loads((root/'game/content/voice-manifest.json').read_text())['takes'])
mac_archive = builds / f"NightNine-{release}-macOS.zip"
if mac_archive.is_file():
    with zipfile.ZipFile(mac_archive, "a", zipfile.ZIP_DEFLATED) as archive:
        add_notices(archive, root, release)

with zipfile.ZipFile(builds / f"NightNine-{release}-Windows-x64.zip", "x", zipfile.ZIP_DEFLATED) as archive:
    generated_notices = {"LICENSE", "MEDIA.md", "LICENSES.txt", "README.txt", "SOURCE.txt"}
    for path in sorted((builds / "windows").rglob("*")):
        relative = path.relative_to(builds / "windows")
        if path.is_file() and relative.as_posix() not in generated_notices:
            archive.write(path, Path("NightNine") / relative)
    archive.write(root / "game/LICENSES.txt", "NightNine/LICENSES.txt")
    add_notices(archive, root, release, "NightNine/")
    archive.writestr("NightNine/README.txt", f"Night Nine {version}\nRun NightNine.exe. Choose New game or Continue.\nClick an object to investigate. In rooms where you can walk, click the floor or use WASD to move. For the opening recording comparison, drag Sunday or use the slider and arrow keys. Compare both recordings, then record your conclusion. Press Space for the next dialogue line, J for the notebook, or Esc for the menu.\nPlay Three Nights, ten chapters, the epilogue and the postcredits signal. You can explore 34 scenes and listen to {take_count} distinct recordings.\nFor the OpenGL graphics option, start NightNine.exe --rendering-method gl_compatibility from the game folder.\nUnsigned Windows x64 development build.\n")
records = []
for path in (builds / f"NightNine-{release}-Windows-x64.zip", mac_archive):
	if not path.is_file():
		continue
	hash_ = hashlib.sha256()
	with path.open("rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			hash_.update(chunk)
	records.append({"file": path.name, "bytes": path.stat().st_size,
	                "sha256": hash_.hexdigest()})
manifest=json.dumps({"version": version, "godot": "4.7.2", "packages": records}, indent=2) + "\n"
(builds / "manifest.json").write_text(manifest)
(builds / f"manifest-{release}.json").write_text(manifest)
print(json.dumps(records, indent=2))

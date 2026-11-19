"""Bundle the matching editable source for the illustrated native desktop presets."""
import argparse
import json
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STORY_DOCS = ("campaign-transcript.md", "campaign-walkthrough.md", "cutscene-script.md", "toolchain-provenance.json")
TOOLS = (
    "build-native.sh", "godot.sh", "package-windows.py", "desktop_notices.py", "check-log.py",
    "test-campaign.sh", "check-qa-result.py", "build-story.py", "early_puzzles.py",
    "late_chapter_puzzles.py", "caseboards.py", "early_caseboards.py", "late_caseboards.py", "build-soundscape.py",
    "build-campaign-ambience.py", "build-prologue-ambience.py", "prepare-campaign-cast.py",
    "prepare-archivist-sprite.py", "prepare-mercer-sprites.py", "prepare-delegate-expressions.py",
    "prepare-chapter-animations.py", "prepare-story-films.py", "pack-campaign-foregrounds.py", "generate-lipsync.py",
    "inspect-face-landmarks.swift", "prepare-board-reference.swift", "build-music-sync.py", "music_tempo.py", "story_rework.py",
    "package-desktop-source.py", "pack-exploration-actors.py", "test-windows-package.ps1",
    "build-footfalls.py", "build-ui-sounds.py"
)
MEDIA_TREES = (
    "assets/environments/campaign", "assets/characters/campaign", "assets/cinematics/campaign",
    "assets/audio/ambience-campaign", "assets/audio/ambience-prologue", "assets/audio/delegate-reaction",
    "assets/audio/elevenlabs-v4/recordings", "assets/audio/lipsync-elevenlabs-v4",
    "assets/characters/archivist/voice", "assets/cover", "assets/concepts/characters"
)
MEDIA_EXTENSIONS = {".png", ".jpg", ".webp", ".json", ".mp3", ".wav", ".flac", ".txt"}


def source_files():
    """Use an explicit release inventory so machine settings and account records stay private."""
    files = {Path("LICENSE"), Path("MEDIA.md"), Path("assets/illustrated-prologue.json"),
             Path("docs/desktop-source.md"), Path("docs/story-arc-rework.md"),
             Path("assets/audio/soundtrack/tempo.json")}
    files.update(Path("assets/audio/soundtrack") / name for name in
                 ("cue-sheet.csv", "measurements.json", "README.md"))
    files.update(Path("docs") / name for name in STORY_DOCS)
    files.update(Path("tools") / name for name in TOOLS)
    prologue = json.loads((ROOT / "assets/illustrated-prologue.json").read_text())
    for name in [r["master"] for r in prologue["files"]] + list(prologue["character_references"].values()):
        files.add(Path("assets") / name)
    cast = json.loads((ROOT / "assets/characters/campaign/portraits.json").read_text())
    for actor in cast["portraits"].values():
        files.update(Path(ref) for ref in actor["references"])
    for directory in MEDIA_TREES:
        for p in (ROOT / directory).rglob("*"):
            if p.is_file() and p.suffix in MEDIA_EXTENSIONS and not p.name.endswith(".raw.json"):
                files.add(p.relative_to(ROOT))
    films = ROOT / "assets/cinematics/campaign/films"
    files.update(p.relative_to(ROOT) for p in films.rglob("*.md") if p.is_file())
    # These are the three development-only asset directories excluded by both
    # desktop export presets. Keep all scripts, import sidecars and fallback WAVs.
    project = ROOT / "game"
    for p in project.rglob("*"):
        rel = p.relative_to(project)
        if not p.is_file() or any(s.startswith(".") for s in rel.parts):
            continue
        if rel.parts[:2] in (("assets", "characters"), ("assets", "environments"), ("assets", "materials")):
            continue
        if p.name == "export_credentials.cfg":
            continue
        files.add(p.relative_to(ROOT))
    return sorted(files)


def public_bytes(path):
    # Vision records the workstation filename in otherwise portable landmark JSON.
    # Retain all facial coordinates and rewrite the path relative to the sources.
    data = (ROOT / path).read_bytes()
    if path.parent == Path("assets/characters/campaign/landmarks"):
        record = json.loads(data)
        record["source"] = "assets/characters/campaign/masters/" + path.stem + ".png"
        return (json.dumps(record, indent=2) + "\n").encode()
    return data


def main():
    version = re.search(r'config/version="(\d+\.\d+\.\d+)', (ROOT / "game/project.godot").read_text()).group(1)
    folder = "NightNine-" + version + "-source"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "builds" / (folder + ".zip"))
    output = parser.parse_args().output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = source_files()
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        archive_path = Path(tmp) / output.name
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
            for path in files:
                if path.is_absolute() or ".." in path.parts or (ROOT / path).is_symlink():
                    raise ValueError("Unexpected source path: " + str(path))
                info = zipfile.ZipInfo.from_file(ROOT / path, folder + "/" + path.as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, public_bytes(path), compresslevel=5)
            archive.write(ROOT / "docs/desktop-source.md", folder + "/README.md")
        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError("Corrupt source member: " + bad)
        archive_path.replace(output)
    print(output, len(files) + 1, "files,", output.stat().st_size, "bytes")


if __name__ == "__main__":
    main()

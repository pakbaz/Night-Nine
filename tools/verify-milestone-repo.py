#!/usr/bin/env python3
"""Clone annotated checkpoints, import Godot from zero cache, play every room and verify package contents."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]


def git(where, *cmd):
    return subprocess.run(
        ["git", "-C", str(where), *cmd], text=True, check=True, capture_output=True
    ).stdout.strip()


def run_log(cmd, path, env=None, timeout=240):
    with path.open("w") as handle:
        subprocess.run(
            [str(v) for v in cmd],
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=env,
            check=True,
            timeout=timeout,
        )
    return path.read_text()


def read(p):
    return json.loads(p.read_text())


def resource_records(value):
    if isinstance(value, dict):
        if str(value.get("file", "")).startswith("res://"):
            yield value
        for item in value.values():
            yield from resource_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from resource_records(item)


def validate_checkout(repo, tag, bin, out):
    path = out / tag.replace("/", "-")
    path.mkdir()
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=out) as tmp:
        clone = Path(tmp) / "clone"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--local",
                "--branch",
                tag,
                "--single-branch",
                str(repo),
                str(clone),
            ],
            stdout=subprocess.DEVNULL,
            check=True,
        )
        assert git(clone, "cat-file", "-t", tag) == "tag"
        assert git(clone, "status", "--porcelain") == ""
        assert (clone / "LICENSE").read_bytes() == (BASE / "LICENSE").read_bytes()
        if git(repo, "rev-parse", "HEAD") == git(clone, "rev-parse", "HEAD"):
            assert (clone / "MEDIA.md").read_bytes() == (BASE / "MEDIA.md").read_bytes()
        else:
            assert "GPL-3.0-only" in (clone / "MEDIA.md").read_text()
        assert (clone / "MEDIA.md").is_file() and (
            clone / "art/night-nine.jpg"
        ).stat().st_size > 0
        game = clone / "game"
        checkpoint = read(game / "content/checkpoint.json")
        story = read(game / "content/campaign.json")
        takes = read(game / "content/voice-manifest.json")["takes"]
        cues = read(game / "content/lipsync-manifest.json")["takes"]
        assert set(takes) == set(cues)
        assert not (game / ".godot").exists()
        for key, v in takes.items():
            wav = game / v["file"][6:]
            assert (
                hashlib.sha256(wav.read_bytes()).hexdigest()
                == v["sha256"]
                == cues[key]["audio_sha256"]
            )
        allowed = {s["id"] for s in story["scenes"]}
        books = read(game / "content/storybook.json")["books"] if (game / "content/storybook.json").is_file() else {}
        story_paintings = {panel["image"] for book in books.values() for panel in book["panels"]}
        narration = {line["narration"][6:] for book in books.values() for panel in book["panels"] for line in panel["lines"]}
        assert all(book["before"] in allowed for book in books.values())
        assert all((game / path[6:]).is_file() for path in story_paintings)
        assert all((game / path).is_file() for path in narration)
        score_script = game / "audio/campaign_score.gd"
        if score_script.is_file():
            music = read(game / "content/music.json")
            chapters = {s["chapter"] for s in story["scenes"]} - {"After the credits"}
            assert chapters == music["chapters"].keys()
            expected = {Path(cue["file"]).stem: cue for cue in resource_records(music)
                        if cue["file"].endswith(".mp3")}
            tracks = game / "assets/audio/music"
            assert {p.stem for p in tracks.glob("*.mp3")} == expected.keys()
            for stem, cue in expected.items():
                mp3 = tracks / f"{stem}.mp3"
                assert cue["file"] == "res://assets/audio/music/" + mp3.name
                assert isinstance(cue["lufs"], (float, int)) and mp3.stat().st_size > 0
                assert mp3.with_suffix(".mp3.import").is_file()
        floor_file = game / "content/illustrated-floor.json"
        if floor_file.is_file():
            floors = read(floor_file)
            assert floors.keys() <= allowed
            for room_id, floor in floors.items():
                if floor.get("doors"):
                    door = game / "assets/illustrated/campaign/doors" / f"{room_id}.webp"
                    assert (game / "render/illustrated/story_door.gd").is_file()
                    assert door.is_file() and door.with_suffix(".webp.import").is_file(), (tag, door)
            if (game / "render/illustrated/social_direction.gd").is_file() and "c9_gallery" in allowed:
                assert (game / "render/illustrated/portrait_eyes.gdshader").is_file()
                for role in ("steve_toward_nora", "nora_toward_steve"):
                    folder = game / "assets/illustrated/cast" / role
                    performance = read(folder / "sprite.json")
                    assert (folder / performance["base"]).is_file() and (folder / performance["atlas"]).is_file()
            titlescreen = game / "assets/illustrated/title.webp"
            assert titlescreen.is_file() and titlescreen.with_suffix(".webp.import").is_file()
            walkers = {role for room in floors.values() for role in room["spawn"]}
            residents = {role for room in floors.values() for role in room.get("residents", {})}
            for role in walkers | residents:
                poses = ("", "-idle", "-reach", "-listen") if role in walkers else ("-idle",)
                if role in {"calder", "iris", "agnes"} and role in residents:
                    poses += ("-greet", "-listen", "-talk")
                if role in walkers and (game / "render/illustrated/ground_navigation.gd").is_file():
                    poses += ("-away", "-toward")
                    if role in {"steve", "nora"}:
                        poses += ("-kneel", "-read", "-operate")
                for pose in poses:
                    sprite = game / "assets/illustrated/campaign/walk" / f"{role}{pose}.webp"
                    assert sprite.is_file() and sprite.with_suffix(".webp.import").is_file(), (tag, sprite)
            for surface in {room.get("surface", "timber") for room in floors.values()}:
                for side in (0, 1):
                    step = game / "assets/audio/steps" / f"{surface}-{side}.wav"
                    assert step.is_file() and step.with_suffix(".wav.import").is_file(), (tag, step)
            available_tasks = {task["id"] for scene in story["scenes"] for task in scene["tasks"]}
            for case in story["notebook_cases"].values():
                assert available_tasks.issuperset(case["clues"])
                assert all(theory["after"] in available_tasks for theory in case["theories"])
        illustrations = game / "assets/illustrated/campaign/rooms"
        if illustrations.exists():
            names = {p.stem for p in illustrations.glob("*.webp")}
            main_rooms = {s for s in allowed if not s.startswith("p_")}
            assert main_rooms <= names
            assert all(name.split("-", 1)[0] in main_rooms or
                       f"res://assets/illustrated/campaign/rooms/{name}.webp" in story_paintings for name in names)
            if score_script.is_file() and "postcredits" in allowed:
                assert "postcredits-dawn" in names
        actual_audio = {
            str(p.relative_to(game))
            for p in (game / "assets/audio/voices").rglob("*.wav")
        }
        assert actual_audio == {v["file"][6:] for v in takes.values()} | narration
        tracked = git(clone, "ls-files").splitlines()
        for name in tracked:
            item = clone / name
            if (
                item.suffix
                not in {
                    ".gd",
                    ".json",
                    ".tscn",
                    ".md",
                    ".cfg",
                    ".txt",
                    ".godot",
                    ".gdshader",
                    ".import",
                    ".tres",
                    ".uid",
                }
                or item.name == "LICENSES.txt"
            ):
                continue
            text = item.read_text()
            for private in [
                "/Users/",
                ".codex/",
                "access_token=",
                "api_key=",
                "X-Amz-Signature=",
                "hf_token",
                "discord.com/api/webhooks",
            ]:
                assert private not in text, (tag, name, private)
        public_assets = game / "assets/illustrated/campaign"
        if public_assets.exists():
            for branch in ["inserts", "foregrounds", "wide"]:
                for item in (public_assets / branch).glob("*"):
                    base = (
                        item.name.split(".")[0]
                        .removesuffix("-flow")
                        .removesuffix("-motion")
                    )
                    resource = "res://" + str(item.relative_to(game)).removesuffix(".import")
                    assert base in allowed or resource in story_paintings, (tag, item.name)
        film_catalog = game / "content/films.json"
        if film_catalog.is_file():
            films = read(film_catalog)
            assert films.keys() <= allowed
            art = [p for p in (public_assets / "films").glob("*") if p.suffix in {".png", ".webp"}]
            assert {p.stem.split("-", 1)[0] for p in art} == films.keys()
            assert all(p.with_suffix(p.suffix + ".import").is_file() for p in art)

        assert all(
            (clone / name).stat().st_size < 100_000_000
            and not (clone / name).is_symlink()
            for name in tracked
        )
        assert not any(
            "/.godot/" in name or name.endswith((".pdf", ".glb", ".fbx", ".blend"))
            for name in tracked
        )
        import_log = run_log(
            [
                bin,
                "--headless",
                "--path",
                game,
                "--import",
                "--log-file",
                path / "import-engine.log",
            ],
            path / "import.txt",
        )
        env = {**os.environ, "NIGHT_NINE_SAVE_DIR": str(Path(tmp) / "isolated-save")}
        log = run_log(
            [
                bin,
                "--headless",
                "--path",
                game,
                "--audio-driver",
                "Dummy",
                "--script",
                "res://qa/checkpoint.gd",
                "--log-file",
                path / "game-engine.log",
            ],
            path / "game.txt",
            env,
        )
        fatal = (
            "ERROR:",
            "SCRIPT ERROR",
            "Parse Error",
            "Failed loading resource",
            "Failed to load script",
            "No loader found",
            "Cannot open file",
            "Invalid access",
            "Invalid call",
        )
        if any(s in import_log or s in log for s in fatal):
            raise RuntimeError(f"Godot import or runtime error in {path}")
        matches = re.findall(r"^NIGHT_NINE_CHECKPOINT_QA (\{.*\})$", log, re.M)
        assert len(matches) == 1, tag
        result = json.loads(matches[0])
        assert (
            not result["errors"]
            and result["rooms"] == [s["id"] for s in story["scenes"]]
            and result["tasks"] == checkpoint["tasks"]
            and result["ending"] == checkpoint["ending"]
        )
        assert result["lines"] == len(story["lines"]) == checkpoint["lines"]
        changes = git(clone, "status", "--porcelain")
        assert not changes, (
            tag,
            "Changes after clean import and gameplay test",
            changes,
        )
        return {
            "tag": tag,
            "commit": git(clone, "rev-parse", "HEAD"),
            "rooms": len(result["rooms"]),
            "tasks": result["tasks"],
            "lines": len(story["lines"]),
            "verified_wavs": len(takes),
            "runtime_checks": result["checks"],
            "ending": result["ending"],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=BASE / "GitHub/Night-Nine")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tag", action="append")
    parser.add_argument(
        "--godot",
        default=os.getenv("GODOT_BIN")
        or shutil.which("godot")
        or str(BASE / ".tools/godot-4.7.2/Godot.app/Contents/MacOS/Godot"),
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    chapters = ["checkpoint/prologue"] + [
        f"checkpoint/chapter-{i:02}" for i in range(1, 11)
    ]
    refs = git(repo, "tag", "--list").splitlines()
    releases = sorted(
        (t for t in refs if re.fullmatch(r"v\d+\.\d+\.\d+", t)),
        key=lambda t: tuple(map(int, t[1:].split("."))),
    )
    tags = args.tag or chapters + releases
    if not args.tag:
        edition_refs = {t for t in refs if re.fullmatch(r"chapters-\d+\.\d+\.\d+/(?:prologue|chapter-\d\d)", t)}
        assert set(refs) == set(tags) | edition_refs
        history = git(
            repo, "rev-list", "--first-parent", "--reverse", "main"
        ).splitlines()
        assert history == [git(repo, "rev-list", "-1", tag) for tag in tags], (
            "Unexpected milestone lineage"
        )
        assert git(repo, "remote") == "" and git(repo, "status", "--porcelain") == ""
        for prefix in sorted({t.split("/")[0] for t in edition_refs}):
            series = [t.replace("checkpoint", prefix) for t in chapters]
            assert set(series) == {t for t in edition_refs if t.startswith(prefix + "/")}
            assert git(repo, "rev-list", "--first-parent", "--reverse", series[-1]).splitlines() == [
                git(repo, "rev-parse", t + "^{commit}") for t in series
            ]
            tags.extend(series)
    results = []
    for tag in tags:
        r = validate_checkout(repo, tag, args.godot, out)
        print(tag, r["rooms"], r["runtime_checks"], "checks passed", flush=True)
        results.append(r)
    (out / "report.json").write_text(json.dumps(results, indent=2) + "\n")

#!/usr/bin/env python3
"""Create the chapter history or stage a new release on top of an existing local history."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]
GAME = BASE / "game"
SUPPORT = BASE / "tools/checkpoint-handoff"
TITLES = [
    "Three Nights",
    "Good Morning, Sleepyhead",
    "The Aquarium Is Closed",
    "Please Prove You Exist",
    "Federal Hospitality",
    "Wanted: Steve Mercer (Two of Him)",
    "Iris",
    "The President’s Other Appointment",
    "The Biggest Lie on Earth",
    "The Long Patience",
    "Good Morning, Bellwether",
]
ENDS = [
    "p_bay",
    "c1_escape",
    "c2_ship",
    "p_veyr",
    "c4_escape",
    "c5_station",
    "i2_nora",
    "c7_swap",
    "c8_rig",
    "c9_choir",
    "postcredits",
]
TAGS = ["checkpoint/prologue"] + [f"checkpoint/chapter-{i:02}" for i in range(1, 11)]
PROLOGUE_CAST = {"archivist", "general_cn", "general_us", "helen", "frank"}
PAINTED_NIGHTS = {"p_bay", "p_veyr", "p_meeting"}
ALIASES = {
    "agnes_original": "agnes",
    "lyle_copy": "lyle",
    "rook_copy": "rook",
    "dale": "pell",
}
MEDIA_EXT = {".png", ".webp", ".ogg", ".wav", ".svg", ".mp3"}


def read(path):
    return json.loads(Path(path).read_text())


def serialized(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


def copy_sources(files, relative):
    path = GAME / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    files["game/" + relative] = path
    side = path.with_name(
        path.name + (".uid" if path.suffix in {".gd", ".gdshader"} else ".import")
    )
    if side.exists():
        files["game/" + str(side.relative_to(GAME))] = side


def asset(files, resource):
    if not resource.startswith("res://") or ".." in Path(resource[6:]).parts:
        raise ValueError(resource)
    copy_sources(files, resource[6:])


def catalog_assets(files, value):
    if isinstance(value, dict):
        for item in value.values():
            catalog_assets(files, item)
    elif isinstance(value, list):
        for item in value:
            catalog_assets(files, item)
    elif isinstance(value, str) and value.startswith("res://"):
        asset(files, value)


def add_cast(files, ids):
    for cast in sorted(ids):
        folder = GAME / "assets/illustrated/cast" / ALIASES.get(cast, cast)
        if not folder.is_dir():
            continue  # Radio-only roles have no portrait.
        manifest = read(folder / "sprite.json")
        transferable = {
            k: v
            for k, v in manifest.items()
            if k
            not in {
                "source",
                "reference",
                "source_sha256",
                "reference_sha256",
                "full_canvas_examples",
                "sha256",
            }
        }
        files["game/" + str((folder / "sprite.json").relative_to(GAME))] = serialized(
            transferable
        )
        for p in folder.iterdir():
            if p.suffix in MEDIA_EXT:
                copy_sources(files, str(p.relative_to(GAME)))


def campaign_script(last, stage_no):
    source = (GAME / "scripts/campaign.gd").read_text()
    # The production-only QA routes refer to private studio diagnostics and development scenes.
    begin = source.index('\n\tif "--campaign-qa"')
    end = source.index("\n\tget_tree().auto_accept_quit", begin)
    source = source[:begin] + source[end:]
    if stage_no < 10:
        label = (
            "Prologue checkpoint complete"
            if not stage_no
            else f"Chapter {stage_no} checkpoint complete"
        )
        if '"The End"' not in source:
            raise RuntimeError("Completion card schema changed")
        source = source.replace('"The End"', json.dumps(label)).replace(
            "Night Nine completed.", label + "."
        )
    return source.encode()


def public_project(stage):
    text = (GAME / "project.godot").read_text()
    text = re.sub(
        r"^run/main_scene=.*$",
        'run/main_scene="res://scenes/campaign.tscn"',
        text,
        flags=re.M,
    )
    text = re.sub(r"^run/main_scene\.painted_desktop=.*\n", "", text, flags=re.M)
    text = re.sub(r"^config/(?:use_custom_user_dir|custom_user_dir_name)\.web=.*\n", "", text, flags=re.M)
    save_folder = TAGS[stage].removeprefix("checkpoint/")
    text = text.replace(
        "[application]",
        f'[application]\nconfig/use_custom_user_dir=true\nconfig/custom_user_dir_name="NightNineCommunity/{save_folder}"',
    )
    return text.encode()


def criteria(scenes, tags=None):
    previous = -1
    rows = []
    for i, tag in enumerate(tags or TAGS):
        end = next(k for k, s in enumerate(scenes) if s["id"] == ENDS[i])
        added = scenes[previous + 1 : end + 1]
        names = ", ".join(s["title"] for s in added)
        tasks = sum(len(s["tasks"]) for s in added)
        milestone = ("Prologue" if i == 0 else f"Chapter {i}") + " · " + TITLES[i]
        rows.append(
            f"| `{tag}` | {milestone} | Complete {tasks} new investigations across {names}. Reach the completion card and reopen your saved notebook. |"
        )
        previous = end
    return (
        "# Chapter milestones\n\nEach annotated tag includes the preceding chapters. The checks apply to the newly added scenes. The Chapter 10 checkpoint includes the epilogue, the one-year return and the post-credits transmission.\n\n| Git tag | Official title | Acceptance criteria |\n| --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n"
    ).encode()


def public_control_files(files, stage, all_scenes):
    for dest, src in [
        ("README.md", "README-public.md"),
        ("game/qa/checkpoint.gd", "checkpoint.gd"),
        ("game/qa/checkpoint.gd.uid", "checkpoint.gd.uid"),
    ]:
        files[dest] = SUPPORT / src
    for name in ["LICENSE", "MEDIA.md"]:
        files[name] = BASE / name
    files["tools/create-github-milestones.py"] = SUPPORT / "create-github-milestones.py"
    files["art/night-nine.jpg"] = BASE / "assets/cover/night-nine.jpg"
    files["MILESTONES.md"] = criteria(all_scenes)
    files[".gitignore"] = b".godot/\n.DS_Store\nbuilds/\nexport_credentials.cfg\n"
    files[".gitattributes"] = (
        b"* text=auto\n*.wav binary\n*.ogg binary\n*.mp3 binary\n*.png binary\n*.webp binary\n*.jpg binary\n"
    )
    files["game/project.godot"] = public_project(stage)
    version = re.search(rb'^config/version="(\d+\.\d+\.\d+)', files["game/project.godot"], re.M).group(1)
    files["PUBLISHING.md"] = (SUPPORT / "PUBLISHING.md").read_bytes().replace(b"@@VERSION@@", version)
    files["README.md"] = (SUPPORT / "README-public.md").read_bytes().replace(b"@@VERSION@@", version)
    files["game/scripts/campaign.gd"] = campaign_script(ENDS[stage], stage)
    files["game/LICENSES.txt"] = (
        (GAME / "LICENSES.txt")
        .read_text()
        .replace(
            "Environment texture: wood_floor_deck by Dimitrios Savva, Poly Haven. CC0-1.0.\nSource: https://polyhaven.com/a/wood_floor_deck\nLicense: https://polyhaven.com/license\n\n",
            "",
        )
        .encode()
    )
    preset = (GAME / "export_presets.cfg").read_text()
    preset = re.sub(
        r'^(custom_template/(?:debug|release))="[^"]*"', r'\1=""', preset, flags=re.M
    )
    preset = re.sub(r"^exclude_filter=.*$", 'exclude_filter="qa/*"', preset, flags=re.M)
    files["game/export_presets.cfg"] = preset.encode()
    for name in [
        "icon.svg",
        "icon.png",
        "default_bus_layout.tres",
        "scenes/campaign.tscn",
        "core/campaign_state.gd",
        "core/tape_recording.gd",
        "platform/desktop_platform.gd",
        "platform/platform_services.gd",
        "ui/tape_compare.gd",
        "ui/tape_trace.gd",
        "ui/evidence_trace.gd",
        "ui/hypothesis_notebook.gd",
        "ui/setting_row.gd",
        "ui/case_board.gd",
        "ui/closing_credits.gd",
        "ui/storybook.gd",
        "ui/title_card.gd",
        "ui/browser_storage.gd",
        "ui/fullscreen_button.gd",
        "audio/campaign_score.gd",
    ]:
        copy_sources(files, name)
    copy_sources(files, "core/save_repository.gd")
    saves = (
        (GAME / "core/save_repository.gd")
        .read_text()
        .replace(
            "state_validator: Callable = NightState.validate",
            "state_validator: Callable",
        )
    )
    files["game/core/save_repository.gd"] = saves.encode()
    for p in (GAME / "render/illustrated").iterdir():
        if p.suffix in {".gd", ".gdshader"}:
            copy_sources(files, str(p.relative_to(GAME)))
    if (GAME / "scripts/campaign.gd.uid").is_file():
        files["game/scripts/campaign.gd.uid"] = GAME / "scripts/campaign.gd.uid"


def include_literal_media(files, allowed):
    # Shared artwork such as the title illustration can be referenced directly by
    # a production script. Scene-specific packs still enter with their own chapter.
    for name, value in list(files.items()):
        if Path(name).suffix not in {".gd", ".tscn", ".tres", ".gdshader"}:
            continue
        source = value.read_text() if isinstance(value, Path) else value.decode()
        for reference in re.findall(
            r'"(res://[^"\n]+\.(?:png|webp|wav|ogg|svg))"', source
        ):
            asset_name = Path(reference[6:])
            if (
                asset_name.parent.name in {"rooms", "inserts", "foregrounds", "doors", "films"}
                and "campaign" in asset_name.parts
            ):
                id = asset_name.stem.split("-", 1)[0]
                if id not in allowed:
                    continue
            if (GAME / asset_name).is_file():
                asset(files, reference)


def make_snapshot(stage, strict):
    files = {}
    campaign = read(GAME / "content/campaign.json")
    all_scenes = campaign["scenes"]
    lines = campaign["lines"]
    ending = ENDS[stage]
    end = next(i for i, s in enumerate(all_scenes) if s["id"] == ending)
    scenes = deepcopy(all_scenes[: end + 1])
    scene_ids = {s["id"] for s in scenes}
    public_control_files(files, stage, all_scenes)
    music = read(GAME / "content/music.json")
    chapters = {scene["chapter"] for scene in scenes} - {"After the credits"}
    if missing := chapters - music["chapters"].keys():
        raise ValueError(f"Soundtrack missing for {sorted(missing)}")
    music["chapters"] = {
        name: entry for name, entry in music["chapters"].items() if name in chapters
    }
    for name in ("scene_music", "departures"):
        music[name] = {key: value for key, value in music[name].items() if key in scene_ids}
    catalog_assets(files, music)
    files["game/content/music.json"] = serialized(music)
    storybooks = read(GAME / "content/storybook.json")
    storybooks["books"] = {
        key: book for key, book in storybooks["books"].items() if book["before"] in scene_ids
    }
    catalog_assets(files, storybooks)
    files["game/content/storybook.json"] = serialized(storybooks)
    narration = read(GAME / "content/narration.json")
    narration["books"] = {
        key: entry for key, entry in narration["books"].items()
        if key in storybooks["books"]
    }
    catalog_assets(files, narration)
    files["game/content/narration.json"] = serialized(narration)
    films = read(GAME / "content/films.json")
    files["game/content/films.json"] = serialized({room: film for room, film in films.items() if room in scene_ids})
    used_lines = set()
    signals = set()
    fx = {"ninth_night"}
    cast = set(PROLOGUE_CAST)
    for scene in scenes:
        used_lines.update(scene["intro"] + scene["outro"] + scene.get("recap", []))
        catalog_assets(files, scene)
        cast.update(scene["actors"])
        for t in scene["tasks"]:
            used_lines.update(t["lines"] + t.get("lead", []))
            if t.get("finding"):
                used_lines.add(t["finding"])
            signals.update(t.get("sounds", []))
            if t.get("puzzle", {}).get("recording"):
                signals.add(t["puzzle"]["recording"])
            if t.get("actor"):
                cast.add(t["actor"])
    visible_lines = {k: v for k, v in lines.items() if k in used_lines}
    assert set(visible_lines) == used_lines
    for line in visible_lines.values():
        cast.add(line["speaker"])
        if line.get("cue"):
            fx.add(line["cue"])
        if line.get("reaction"):
            fx.add(line["reaction"]["sound"])
    fx.update(s[7:] for s in signals if s.startswith("effect."))
    take_ids = {s for s in signals if not s.startswith("effect.")} | {
        line["audio"] for line in visible_lines.values()
    }
    voice_manifest = read(GAME / "content/voice-manifest.json")
    if strict and (
        not voice_manifest.get("enabled", True)
        or not narration.get("enabled", True)
    ):
        raise RuntimeError("Voice playback is not approved; use --rehearsal for a text-only snapshot.")
    voice = voice_manifest["takes"]
    timing = read(GAME / "content/lipsync-manifest.json")["takes"]
    takes = {}
    cues = {}
    for id in sorted(take_ids):
        if id.startswith("effect."):
            fx.add(id[7:])
            continue
        v = voice[id]
        c = timing[id]
        if strict and v.get("model") not in {"elevenlabs_v4", "eleven_v4"}:
            raise RuntimeError("Final ElevenLabs take pending: " + id)
        if v["sha256"] != c["audio_sha256"]:
            raise RuntimeError("Stale timing " + id)
        takes[id] = dict(v)
        asset(files, v["file"])
        cues[id] = c
    campaign.update(
        {
            "source": "Night Nine original story",
            "adaptation_status": "Playable illustrated campaign checkpoint.",
            "scenes": scenes,
            "lines": visible_lines,
            "cast": {k: v for k, v in campaign["cast"].items() if k in cast},
            "sound_labels": {
                k: v for k, v in campaign["sound_labels"].items() if k in signals
            },
        }
    )
    available_tasks = {task["id"] for scene in scenes for task in scene["tasks"]}
    cases = {}
    for id, case in campaign.get("notebook_cases", {}).items():
        theories = [theory for theory in case["theories"] if theory["after"] in available_tasks]
        if theories:
            cases[id] = {
                **case,
                "clues": [clue for clue in case["clues"] if clue in available_tasks],
                "theories": theories,
            }
    campaign["notebook_cases"] = cases
    files["game/content/campaign.json"] = serialized(campaign)
    files["game/content/voice-manifest.json"] = serialized(
        {**voice_manifest, "takes": takes}
    )
    files["game/content/lipsync-manifest.json"] = serialized(
        {"schema": 1, "generator": "Rhubarb Lip Sync", "takes": cues}
    )
    book = read(GAME / "content/illustrated-campaign.json")
    directions = {k: v for k, v in book.items() if k in scene_ids}
    landmarks = read(GAME / "content/illustrated-landmarks.json")
    files["game/content/illustrated-campaign.json"] = serialized(directions)
    files["game/content/illustrated-landmarks.json"] = serialized(
        {k: v for k, v in landmarks.items() if k in scene_ids}
    )
    floors = read(GAME / "content/illustrated-floor.json")
    included_floors = {k: v for k, v in floors.items() if k in scene_ids}
    files["game/content/illustrated-floor.json"] = serialized(included_floors)
    for room_id, floor in included_floors.items():
        if floor.get("doors"):
            copy_sources(files, f"assets/illustrated/campaign/doors/{room_id}.webp")
    walking_roles = {role for layout in included_floors.values() for role in layout["spawn"]}
    resident_roles = {role for layout in included_floors.values() for role in layout.get("residents", {})}
    sprites = GAME / "assets/illustrated/campaign/walk"
    for role in sorted(walking_roles | resident_roles):
        if role in walking_roles:
            copy_sources(files, str((sprites / f"{role}.webp").relative_to(GAME)))
        copy_sources(files, str((sprites / f"{role}-idle.webp").relative_to(GAME)))
        for pose in sorted(sprites.glob(f"{role}-*.webp")):
            copy_sources(files, str(pose.relative_to(GAME)))
    for surface in sorted({room.get("surface", "timber") for room in included_floors.values()}):
        for side in (0, 1):
            copy_sources(files, f"assets/audio/steps/{surface}-{side}.wav")
    for d in directions.values():
        cast.update(d["company"])
        cast.update(d.get("appearances", {}).values())
        cast.update(p["id"] for p in d.get("creatures", []))
        if d.get("resident"):
            cast.add(d["resident"])
        if d.get("cutaway") and d["cutaway"]["room"] not in scene_ids:
            raise ValueError(d["cutaway"])
    if "c9_gallery" in scene_ids:
        cast.update({"steve_toward_nora", "nora_toward_steve"})
    add_cast(files, cast)
    for p in (GAME / "assets/illustrated/rooms").glob("*.png"):
        copy_sources(files, str(p.relative_to(GAME)))
    for s in scenes:
        id = s["id"]
        folder = (
            "ambience-prologue" if id in PAINTED_NIGHTS else "ambience-campaign"
        )
        asset(files, "res://assets/audio/" + folder + "/" + id + ".ogg")
        if id not in PAINTED_NIGHTS:
            copy_sources(files, "assets/illustrated/campaign/rooms/" + id + ".webp")
            for folder in ["rooms", "foregrounds", "inserts", "wide", "films"]:
                group = GAME / "assets/illustrated/campaign" / folder
                for p in sorted(group.glob(id + "*")):
                    if p.suffix in MEDIA_EXT and (
                        p.stem == id or p.stem.startswith(id + "-")
                    ):
                        copy_sources(files, str(p.relative_to(GAME)))
    sounds = read(GAME / "assets/audio/soundscape-manifest.json")
    public_sounds = {}
    for id in sorted(fx):
        entry = sounds[id]
        asset(files, entry["file"])
        public_sounds[id] = {
            k: entry[k] for k in ["file", "sha256", "seconds"] if k in entry
        }
    files["game/assets/audio/soundscape-manifest.json"] = serialized(public_sounds)
    if stage == 10:
        for painting in sorted((GAME / "assets/illustrated/campaign/rewards").glob("*.webp")):
            copy_sources(files, str(painting.relative_to(GAME)))
        for name in ("test_physical_navigation.gd", "test_social_staging.gd", "test_campaign_music.gd", "test_case_boards.gd", "test_animation_handoff.gd"):
            for suffix in ("", ".uid"):
                files["game/qa/" + name + suffix] = GAME / "tests" / (name + suffix)
        files["tools/build-pages.py"] = SUPPORT / "build-pages.py"
        files["site/index.html"] = SUPPORT / "pages-index.html"
        for name in [
            "campaign-transcript.md",
            "cutscene-script.md",
            "campaign-walkthrough.md",
        ]:
            files["docs/" + name] = BASE / "docs" / name
    include_literal_media(files, scene_ids)
    if strict:
        for name in files:
            if (
                name.startswith("game/")
                and Path(name).suffix in MEDIA_EXT
                and name + ".import" not in files
            ):
                raise RuntimeError(
                    "Import the final Godot asset before making its checkpoint: " + name
                )
    return files, {
        "title": TITLES[stage],
        "tag": TAGS[stage],
        "scenes": len(scenes),
        "tasks": sum(len(s["tasks"]) for s in scenes),
        "lines": len(visible_lines),
        "takes": len(takes),
        "ending": ending,
    }


def git(repo, *command):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Night Nine checkpoint builder",
        "GIT_COMMITTER_NAME": "Night Nine checkpoint builder",
        "GIT_AUTHOR_EMAIL": "checkpoint-builder@users.noreply.invalid",
        "GIT_COMMITTER_EMAIL": "checkpoint-builder@users.noreply.invalid",
    }
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgsign=false",
            "-C",
            str(repo),
            *map(str, command),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def append_release(source, destination, tag):
    """Stage a clean descendant in a separate local repository for testing and a fast-forward."""
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Use a release tag in the form v0.8.0.")
    version = re.search(r'^config/version="(\d+\.\d+\.\d+)', (GAME / "project.godot").read_text(), re.M)
    if not version or tag[1:] != version.group(1):
        raise ValueError("The release tag must match the Godot project version.")
    if destination.exists() or not source.is_dir():
        raise ValueError("Choose an existing chapter repository and a new release staging directory.")
    if git(source, "status", "--porcelain") or git(source, "branch", "--show-current") != "main":
        raise ValueError("Commit pending source changes and check out main before staging a release.")
    tags = git(source, "tag", "--list").splitlines()
    if tag in tags or set(TAGS) - set(tags):
        raise ValueError("A release needs a new tag and the original eleven chapter tags.")
    git(source, "merge-base", "--is-ancestor", TAGS[-1], "HEAD")
    old_head = git(source, "rev-parse", "HEAD")
    previous_refs = {t: git(source, "rev-parse", t) for t in tags}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".release-build-", dir=destination.parent) as directory:
        temp = Path(directory)
        repo = temp / "Night-Nine"
        git(temp, "clone", "--local", "--no-checkout", source, repo)
        git(repo, "remote", "remove", "origin")
        if git(repo, "rev-parse", "HEAD") != old_head:
            raise RuntimeError("The source branch moved while staging the release.")
        # A no-checkout clone has an empty worktree. Only public files from
        # this version enter its new commit, including removed resources.
        files, meta = make_snapshot(10, True)
        meta["tag"] = tag
        files["game/content/checkpoint.json"] = serialized(meta)
        edition_tags = [name.replace("checkpoint/", f"chapters-{tag[1:]}/") for name in TAGS]
        edition_note = (f"Use the annotated `chapters-{tag[1:]}/*` tags below for this edition. "
                        "The original chapter tags are available under `checkpoint/*`.\n\n")
        files["MILESTONES.md"] = criteria(read(GAME / "content/campaign.json")["scenes"], edition_tags).replace(
            b"Each annotated tag", edition_note.encode() + b"Each annotated tag", 1)
        for name, data in files.items():
            dest = repo / name
            raw = data.read_bytes() if isinstance(data, Path) else data
            if len(raw) >= 100_000_000 or Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Unexpected public release file: " + name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        git(repo, "add", "--all")
        git(repo, "commit", "-m", f"Release {tag} of the illustrated campaign",
            "-m", "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>")
        git(repo, "tag", "-a", tag, "-m", f"Night Nine {tag}. Playable through {meta['ending']}.")
        if git(repo, "rev-parse", "HEAD^") != old_head or git(repo, "status", "--porcelain"):
            raise RuntimeError("Expected one clean release commit after the supplied main branch.")
        if any(git(repo, "rev-parse", t) != original for t, original in previous_refs.items()):
            raise RuntimeError("A pre-existing tag changed during release staging.")
        git(repo, "fsck", "--full")
        repo.rename(destination)
    print(f"{tag} {git(destination, 'rev-parse', 'HEAD')} staged in {destination}", flush=True)


def build(destination, strict):
    if destination.exists():
        raise SystemExit(
            "Choose a new output directory. Existing repositories are preserved."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    last = {}
    logs = []
    with tempfile.TemporaryDirectory(
        prefix=".checkpoint-build-", dir=destination.parent
    ) as base:
        repo = Path(base) / "Night-Nine"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        for stage, tag in enumerate(TAGS):
            files, meta = make_snapshot(stage, strict)
            files["game/content/checkpoint.json"] = serialized(meta)
            paths = {}
            for path, data in files.items():
                raw = data.read_bytes() if isinstance(data, Path) else data
                if len(raw) >= 100_000_000:
                    raise RuntimeError("Oversized " + path)
                digest = sha256(raw).digest()
                paths[path] = digest
                if last.get(path) == digest:
                    continue
                f = repo / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(raw)
            for old in last.keys() - paths.keys():
                (repo / old).unlink()
            git(repo, "add", "--all")
            git(
                repo,
                "commit",
                "-m",
                ("Prologue" if stage == 0 else f"Chapter {stage}")
                + " · "
                + TITLES[stage],
                "-m",
                "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>",
            )
            git(
                repo,
                "tag",
                "-a",
                tag,
                "-m",
                f"{TITLES[stage]}. Playable through {meta['ending']}, {meta['scenes']} rooms, {meta['tasks']} investigations.",
            )
            last = paths
            meta["commit"] = git(repo, "rev-parse", "HEAD")
            logs.append(meta)
            print(tag, meta["commit"][:10], meta["scenes"], meta["lines"], flush=True)
        if git(repo, "status", "--porcelain") or git(repo, "remote"):
            raise RuntimeError("Expected a clean, local repository")
        git(repo, "fsck", "--full")
        if destination.exists():
            raise RuntimeError("Destination appeared during assembly.")
        repo.rename(destination)
    return logs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE / "GitHub/Night-Nine")
    parser.add_argument("--chapter-series", metavar="VERSION",
                        help="Create eleven independent annotated chapters-VERSION/* tags for this edition.")
    parser.add_argument("--append-release", metavar="TAG",
                        help="Stage one descendant of --base-repo in a new --output directory.")
    parser.add_argument("--base-repo", type=Path, default=BASE / "GitHub/Night-Nine")
    parser.add_argument(
        "--rehearsal",
        action="store_true",
        help="Allow provisional voices, restrict output to the QA directory.",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    if args.rehearsal and not out.is_relative_to(BASE / "tmp/qa"):
        parser.error("Rehearsals belong inside tmp/qa.")
    if args.chapter_series:
        version = re.search(r'^config/version="(\d+\.\d+\.\d+)', (GAME / "project.godot").read_text(), re.M)
        if args.rehearsal or args.append_release or not version or args.chapter_series != version[1]:
            parser.error("A chapter series requires the current exact project version and final assets.")
        TAGS = [tag.replace("checkpoint/", f"chapters-{args.chapter_series}/") for tag in TAGS]
    if args.append_release:
        if args.rehearsal:
            parser.error("Release commits require final assets.")
        append_release(args.base_repo.resolve(), out, args.append_release)
    else:
        build(out, not args.rehearsal)

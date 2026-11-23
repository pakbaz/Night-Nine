#!/usr/bin/env python3
"""Reapply a verified script-v2 voice overlay after script_v2.py rebuilds content."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERLAY = ROOT / "assets/audio/elevenlabs-v4-script-v2/approved-overlay.json"
# Lines written or changed after the frozen script-v2 recording, recorded in later batches.
DEFAULT_ADDITIONS = ROOT / "assets/audio/elevenlabs-v4-additions/approved-additions.json"
ACCEPTED_STATUSES = {"automated_qa_passed", "manual_review_passed"}
DEFAULT_CASTING = ROOT / "docs/voice-casting-2026-11-20.json"
ALIASES = {
    "stephen": "steve",
    "iris": "nora",
    "pell": "dale",
    "agnes_original": "agnes",
    "rook_copy": "rook",
    "lyle_copy": "lyle",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value, compact=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = f".partial-{uuid.uuid4().hex}"
    pending = path.with_name(path.name + suffix)
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    pending.write_text(json.dumps(value, ensure_ascii=False, **options) + "\n", encoding="utf-8")
    os.chmod(pending, 0o644)
    os.replace(pending, path)


def storybook_inventory(storybook):
    result = {}
    for name, book in storybook.get("books", {}).items():
        for panel_index, panel in enumerate(book.get("panels", []), 1):
            for line_index, line in enumerate(panel.get("lines", []), 1):
                key = f"book.{name}.{panel_index}.{line_index}"
                result[key] = line
    return result


def restore_missing_storybook_panels(storybook, book_takes, root=ROOT):
    """Restore unchanged timed panels that script_v2's playable projection truncated."""
    base_path = root / "tools/script_v2/base/storybook.json"
    if not base_path.is_file():
        return
    base = read_json(base_path)
    for name, book in storybook.get("books", {}).items():
        source = base.get("books", {}).get(name, {})
        panels = book.get("panels", [])
        source_panels = source.get("panels", [])
        while len(panels) < len(source_panels):
            panel_index = len(panels) + 1
            source_panel = source_panels[panel_index - 1]
            expected = []
            for line_index, line in enumerate(source_panel.get("lines", []), 1):
                line_id = f"book.{name}.{panel_index}.{line_index}"
                take = book_takes.get(line_id)
                if not take or take.get("text") != line.get("text"):
                    expected = []
                    break
                expected.append(line_id)
            if not expected:
                break
            restored = copy.deepcopy(source_panel)
            for line in restored.get("lines", []):
                line["narration"] = ""
            panels.append(restored)


def validate_runtime_take(
    audio_id, take, expected_text, expected_speakers, expected_identity,
    expected_voice_id, timing, plan_sha256, root=ROOT,
):
    if take.get("id") != audio_id or take.get("text") != expected_text:
        raise ValueError(f"Voice overlay text identity mismatch for {audio_id}")
    if take.get("speaker") not in expected_speakers:
        raise ValueError(f"Voice overlay speaker mismatch for {audio_id}")
    if take.get("identity") != expected_identity:
        raise ValueError(f"Voice overlay cast identity mismatch for {audio_id}")
    if take.get("voice_id") != expected_voice_id or take.get("model") != "eleven_v4":
        raise ValueError(f"Voice overlay voice/model mismatch for {audio_id}")
    if take.get("plan_sha256") != plan_sha256:
        raise ValueError(f"Voice overlay plan mismatch for {audio_id}")
    expected_hash = hashlib.sha256(expected_text.encode()).hexdigest()[:16]
    if take.get("text_hash") != expected_hash:
        raise ValueError(f"Voice overlay text hash mismatch for {audio_id}")
    path = root / "game" / str(take.get("file", "")).removeprefix("res://")
    if not path.is_file() or digest(path) != take.get("sha256"):
        raise ValueError(f"Voice overlay audio missing or changed for {audio_id}")
    if timing.get("audio_sha256") != take.get("sha256"):
        raise ValueError(f"Voice overlay mouth cues mismatch for {audio_id}")
    cues = timing.get("cues", [])
    if not cues or abs(float(cues[-1]["end"]) - float(take["seconds"])) > .011:
        raise ValueError(f"Voice overlay mouth cue duration mismatch for {audio_id}")


def validate_addition_take(audio_id, take, expected_text, expected_speakers, expected_identity,
                           expected_voice_id, root=ROOT):
    """A later take is checked like a frozen one, except that speech no longer needs mouth cues."""
    if take.get("id") != audio_id or take.get("text") != expected_text:
        raise ValueError(f"Voice addition text identity mismatch for {audio_id}")
    if take.get("speaker") not in expected_speakers:
        raise ValueError(f"Voice addition speaker mismatch for {audio_id}")
    if take.get("identity") != expected_identity:
        raise ValueError(f"Voice addition cast identity mismatch for {audio_id}")
    if take.get("voice_id") != expected_voice_id or take.get("model") != "eleven_v4":
        raise ValueError(f"Voice addition voice/model mismatch for {audio_id}")
    if take.get("text_hash") != hashlib.sha256(expected_text.encode()).hexdigest()[:16]:
        raise ValueError(f"Voice addition text hash mismatch for {audio_id}")
    if take.get("status") not in ACCEPTED_STATUSES:
        raise ValueError(f"Voice addition has not passed quality checks: {audio_id}")
    path = root / "game" / str(take.get("file", "")).removeprefix("res://")
    if not path.is_file() or digest(path) != take.get("sha256"):
        raise ValueError(f"Voice addition audio missing or changed for {audio_id}")


def merge_overlay(
    campaign, storybook, voice, lipsync, narration, overlay, root=ROOT,
    casting_path=None, additions=None,
):
    if overlay.get("schema") != 1 or overlay.get("model") != "eleven_v4":
        raise ValueError("Unsupported script-v2 voice overlay")
    casting_path = Path(casting_path or (root / "docs/voice-casting-2026-11-20.json"))
    casting = read_json(casting_path)
    casting_sha256 = digest(casting_path)
    if overlay.get("casting_sha256") != casting_sha256:
        raise ValueError("Voice overlay casting fingerprint is stale")
    additions = additions or {}
    if additions and (additions.get("schema") != 1 or additions.get("model") != "eleven_v4"):
        raise ValueError("Unsupported voice additions overlay")
    if additions and additions.get("casting_sha256") != casting_sha256:
        raise ValueError("Voice additions casting fingerprint is stale")
    roles = casting.get("roles", {})
    campaign_required = {}
    for line in campaign.get("lines", {}).values():
        role = ALIASES.get(line["speaker"], line["speaker"])
        if role not in roles:
            raise ValueError(f"Voice overlay has no cast role for {line['speaker']}")
        expected = {
            "text": line["text"],
            "speakers": {line["speaker"]},
            "identity": role,
            "voice_id": roles[role]["voice_id"],
        }
        previous = campaign_required.setdefault(line["audio"], expected)
        if (
            previous["text"] != expected["text"]
            or previous["identity"] != expected["identity"]
            or previous["voice_id"] != expected["voice_id"]
        ):
            raise ValueError(f"Conflicting reused audio text for {line['audio']}")
        previous["speakers"].add(line["speaker"])
    frozen_takes = overlay.get("campaign", {}).get("takes", {})
    frozen_book = overlay.get("narration", {}).get("takes", {})
    frozen_timings = overlay.get("lipsync", {}).get("takes", {})
    added_takes = additions.get("campaign", {}).get("takes", {})
    added_book = additions.get("narration", {}).get("takes", {})
    restore_missing_storybook_panels(storybook, frozen_book, root)
    book_required = storybook_inventory(storybook)
    # A line keeps its frozen take only while its words are unchanged. New or rewritten
    # lines use a later checked take, or stay text-only and are reported as missing.
    campaign_takes = {}
    timings = {}
    missing = []
    for audio_id, expected in campaign_required.items():
        added = added_takes.get(audio_id)
        frozen = frozen_takes.get(audio_id)
        if added and added.get("text") == expected["text"]:
            validate_addition_take(
                audio_id, added, expected["text"], expected["speakers"],
                expected["identity"], expected["voice_id"], root,
            )
            campaign_takes[audio_id] = added
        elif frozen and frozen.get("text") == expected["text"]:
            if audio_id not in frozen_timings:
                raise ValueError("Voice overlay lip-sync inventory is incomplete")
            validate_runtime_take(
                audio_id, frozen, expected["text"], expected["speakers"],
                expected["identity"], expected["voice_id"], frozen_timings[audio_id],
                overlay.get("plan_sha256"), root,
            )
            campaign_takes[audio_id] = frozen
            timings[audio_id] = frozen_timings[audio_id]
        else:
            missing.append(audio_id)
            continue
        # A local fallback was recorded for the base wording; a reworded line must not inherit it.
        base_take = voice.get("takes", {}).get(audio_id, {})
        fallback = base_take.get("fallback")
        if fallback and base_take.get("text") == expected["text"] and "fallback" not in campaign_takes[audio_id]:
            campaign_takes[audio_id]["fallback"] = fallback
    # Keep the frozen order so regenerated manifests stay diff-friendly.
    order = list(frozen_takes) + [key for key in campaign_takes if key not in frozen_takes]
    campaign_takes = {key: campaign_takes[key] for key in order if key in campaign_takes}
    timings = {key: timings[key] for key in frozen_timings if key in timings}
    book_takes = {}
    for line_id, line in book_required.items():
        added = added_book.get(line_id)
        if added and added.get("text") == line["text"]:
            validate_addition_take(
                line_id, added, line["text"], {"steve"}, "steve", roles["steve"]["voice_id"], root,
            )
            book_takes[line_id] = added
            continue
        take = frozen_book.get(line_id)
        if not take or take.get("id") != line_id or take.get("text") != line["text"]:
            missing.append(line_id)
            continue
        book_takes[line_id] = take
        if (
            take.get("speaker") != "steve"
            or take.get("identity") != "steve"
            or take.get("voice_id") != roles["steve"]["voice_id"]
            or take.get("model") != "eleven_v4"
            or take.get("plan_sha256") != overlay.get("plan_sha256")
        ):
            raise ValueError(f"Voice overlay storybook cast mismatch for {line_id}")
        expected_hash = hashlib.sha256(line["text"].encode()).hexdigest()[:16]
        if take.get("text_hash") != expected_hash:
            raise ValueError(f"Voice overlay storybook text hash mismatch for {line_id}")
        path = root / "game" / str(take.get("file", "")).removeprefix("res://")
        if not path.is_file() or digest(path) != take.get("sha256"):
            raise ValueError(f"Voice overlay storybook audio missing or changed for {line_id}")
    approved = bool(overlay.get("quality_approved"))
    all_takes = list(campaign_takes.values()) + list(book_takes.values())
    allowed_statuses = {"automated_qa_passed", "manual_review_passed"}
    if approved and (
        overlay.get("review", {}).get("hard_holds")
        or any(take.get("status") not in allowed_statuses for take in all_takes)
    ):
        raise ValueError("Voice overlay cannot activate with incomplete quality validation")
    voice = {"schema": 1, "enabled": approved, "takes": campaign_takes, "missing": sorted(missing)}
    lipsync = {
        "schema": 1,
        "generator": overlay["lipsync"].get("generator", lipsync.get("generator", "")),
        "source": overlay["lipsync"].get("source", lipsync.get("source", "")),
        "takes": timings,
    }
    narration = {
        "schema": 1,
        "enabled": approved,
        "voice": "ElevenLabs v4, approved Night Nine cast",
        "books": {},
    }
    for name, book in storybook.get("books", {}).items():
        entries = []
        for panel_index, panel in enumerate(book.get("panels", []), 1):
            for line_index, line in enumerate(panel.get("lines", []), 1):
                line_id = f"book.{name}.{panel_index}.{line_index}"
                take = book_takes.get(line_id)
                if take is None:
                    line["narration"] = ""
                    entries.append({"file": "", "seconds": float(line.get("seconds", 0)),
                                    "caption": line["text"], "status": "missing",
                                    "text_hash": hashlib.sha256(line["text"].encode()).hexdigest()[:16]})
                    continue
                line["narration"] = take["file"] if approved else ""
                line["seconds"] = take["seconds"] if approved else float(line.get("seconds", 0))
                entries.append({
                    "file": take["file"] if approved else "",
                    "seconds": take["seconds"],
                    "caption": line["text"],
                    "status": take["status"],
                    "text_hash": take["text_hash"],
                })
        narration["books"][name] = entries
    return voice, lipsync, storybook, narration


def apply_overlay_to_content_dir(content_dir, overlay_path=DEFAULT_OVERLAY, root=ROOT,
                                 additions_path=DEFAULT_ADDITIONS):
    content_dir = Path(content_dir)
    overlay_path = Path(overlay_path)
    if not overlay_path.is_file():
        return False
    additions_path = Path(additions_path) if additions_path else None
    additions = read_json(additions_path) if additions_path and additions_path.is_file() else None
    paths = {
        "campaign": content_dir / "campaign.json",
        "storybook": content_dir / "storybook.json",
        "voice": content_dir / "voice-manifest.json",
        "lipsync": content_dir / "lipsync-manifest.json",
        "narration": content_dir / "narration.json",
    }
    values = {key: read_json(path) for key, path in paths.items()}
    merged = merge_overlay(
        values["campaign"], values["storybook"], values["voice"], values["lipsync"],
        values["narration"], read_json(overlay_path), root, additions=additions,
    )
    for key, value in zip(("voice", "lipsync", "storybook", "narration"), merged):
        atomic_json(paths[key], value, compact=(key == "lipsync"))
    if merged[0]["missing"]:
        print(f"Voice: {len(merged[0]['missing'])} lines have no recording yet and play as text only.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-dir", type=Path, default=ROOT / "game/content")
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    args = parser.parse_args()
    changed = apply_overlay_to_content_dir(args.content_dir, args.overlay)
    print(json.dumps({"overlay_applied": changed, "overlay": str(args.overlay)}))


if __name__ == "__main__":
    main()

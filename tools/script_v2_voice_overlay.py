#!/usr/bin/env python3
"""Reapply a verified script-v2 voice overlay after script_v2.py rebuilds content."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERLAY = ROOT / "assets/audio/elevenlabs-v4-script-v2/approved-overlay.json"
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


def merge_overlay(
    campaign, storybook, voice, lipsync, narration, overlay, root=ROOT,
    casting_path=None,
):
    if overlay.get("schema") != 1 or overlay.get("model") != "eleven_v4":
        raise ValueError("Unsupported script-v2 voice overlay")
    casting_path = Path(casting_path or (root / "docs/voice-casting-2026-11-20.json"))
    casting = read_json(casting_path)
    casting_sha256 = digest(casting_path)
    if overlay.get("casting_sha256") != casting_sha256:
        raise ValueError("Voice overlay casting fingerprint is stale")
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
    book_required = storybook_inventory(storybook)
    campaign_takes = overlay.get("campaign", {}).get("takes", {})
    book_takes = overlay.get("narration", {}).get("takes", {})
    timings = overlay.get("lipsync", {}).get("takes", {})
    if set(campaign_takes) != set(campaign_required):
        raise ValueError("Voice overlay campaign inventory is stale")
    if set(book_takes) != set(book_required):
        raise ValueError("Voice overlay storybook inventory is stale")
    if set(timings) != set(campaign_takes):
        raise ValueError("Voice overlay lip-sync inventory is incomplete")
    for audio_id, expected in campaign_required.items():
        validate_runtime_take(
            audio_id, campaign_takes[audio_id], expected["text"], expected["speakers"],
            expected["identity"], expected["voice_id"], timings[audio_id],
            overlay.get("plan_sha256"), root,
        )
        fallback = voice.get("takes", {}).get(audio_id, {}).get("fallback")
        if fallback and "fallback" not in campaign_takes[audio_id]:
            campaign_takes[audio_id]["fallback"] = fallback
    for line_id, line in book_required.items():
        take = book_takes[line_id]
        if take.get("id") != line_id or take.get("text") != line["text"]:
            raise ValueError(f"Voice overlay storybook text mismatch for {line_id}")
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
    voice = {"schema": 1, "enabled": approved, "takes": campaign_takes}
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
                take = book_takes[line_id]
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


def apply_overlay_to_content_dir(content_dir, overlay_path=DEFAULT_OVERLAY, root=ROOT):
    content_dir = Path(content_dir)
    overlay_path = Path(overlay_path)
    if not overlay_path.is_file():
        return False
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
        values["narration"], read_json(overlay_path), root,
    )
    for key, value in zip(("voice", "lipsync", "storybook", "narration"), merged):
        atomic_json(paths[key], value, compact=(key == "lipsync"))
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

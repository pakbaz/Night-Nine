#!/usr/bin/env python3
"""Safely record, validate, and stage dialogue added after the frozen voice production."""
import argparse
from array import array
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import statistics
import subprocess
import sys
import urllib.parse
import uuid
import wave

import elevenlabs_v4_pipeline as pipeline

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "assets/audio/elevenlabs-v4-additions"
PLAN_PATH = PRODUCTION / "plan.json"
OVERLAY_PATH = PRODUCTION / "approved-additions.json"
CASTING_PATH = ROOT / "docs/voice-casting-2026-11-20.json"
MODEL = pipeline.MODEL
OUTPUT_FORMAT = pipeline.OUTPUT_FORMAT
MAX_ATTEMPTS = 3
ACCEPTED_STATUSES = {"automated_qa_passed", "manual_review_passed"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def canonical_sha(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def atomic_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + f".partial-{uuid.uuid4().hex}")
    pending.write_bytes(payload)
    os.chmod(pending, 0o644)
    os.replace(pending, path)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def create_inflight(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise ValueError(f"Unresolved speech request exists: {path.name}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def safe_id(audio_id):
    return pipeline.safe_id(audio_id)


def content_paths(root):
    root = Path(root)
    return {
        "campaign": root / "game/content/campaign.json",
        "storybook": root / "game/content/storybook.json",
        "voice_manifest": root / "game/content/voice-manifest.json",
        "casting": root / "docs/voice-casting-2026-11-20.json",
    }


def input_hashes(root, production):
    paths = content_paths(root)
    overlay = Path(production) / "approved-additions.json"
    return {
        key: file_sha(path) for key, path in paths.items()
    } | {"existing_additions": file_sha(overlay) if overlay.is_file() else None}


def scene_line_ids(scene):
    ordered = []

    def extend(values):
        for line_id in values or []:
            if isinstance(line_id, str) and line_id:
                ordered.append(line_id)

    extend(scene.get("context"))
    extend(scene.get("intro"))
    for task in scene.get("tasks", []):
        extend(task.get("lead"))
        extend(task.get("lines"))
        finding = task.get("finding")
        if isinstance(finding, str) and finding:
            ordered.append(finding)
    extend(scene.get("recap"))
    extend(scene.get("outro"))
    return ordered


def campaign_inventory(campaign, casting):
    roles = casting.get("roles", {})
    required = {}
    for line in campaign.get("lines", {}).values():
        audio_id = safe_id(line["audio"])
        role = pipeline.cast_key(line["speaker"])
        if role not in roles:
            raise ValueError(f"Uncast speaker {line['speaker']} for {audio_id}")
        expected = {
            "text": line["text"],
            "speakers": {line["speaker"]},
            "identity": role,
            "voice_id": roles[role]["voice_id"],
        }
        previous = required.setdefault(audio_id, expected)
        if any(previous[key] != expected[key] for key in ("text", "identity", "voice_id")):
            raise ValueError(f"Conflicting reused audio text or cast for {audio_id}")
        previous["speakers"].add(line["speaker"])
    return required


def storybook_inventory(storybook, casting):
    roles = casting.get("roles", {})
    if "steve" not in roles:
        raise ValueError("Casting has no Steve voice for storybook narration")
    result = {}
    for name, book in storybook.get("books", {}).items():
        for panel_index, panel in enumerate(book.get("panels", []), 1):
            for line_index, line in enumerate(panel.get("lines", []), 1):
                audio_id = f"book.{name}.{panel_index}.{line_index}"
                result[audio_id] = {
                    "text": line["text"],
                    "speakers": {"steve"},
                    "identity": "steve",
                    "voice_id": roles["steve"]["voice_id"],
                }
    return result


def historical_credit_rates(root):
    production = Path(root) / "assets/audio/elevenlabs-v4-script-v2"
    plan_path = production / "plan.json"
    if not plan_path.is_file():
        return {}
    plan = read_json(plan_path)
    rates = {}
    for audio_id, item in plan.get("items", {}).items():
        if item.get("kind") != "speech" or not item.get("synthesis_text"):
            continue
        receipt_path = production / "receipts" / f"{safe_id(audio_id)}.json"
        if not receipt_path.is_file():
            continue
        cost = read_json(receipt_path).get("character_cost")
        if not isinstance(cost, int) or cost < 0:
            continue
        rate = cost / max(1, len(item["synthesis_text"]))
        rates[item["voice_id"]] = max(rates.get(item["voice_id"], 1.0), rate)
    return rates


def build_plan(root=ROOT, production=PRODUCTION):
    root = Path(root)
    production = Path(production)
    paths = content_paths(root)
    campaign = read_json(paths["campaign"])
    storybook = read_json(paths["storybook"])
    manifest = read_json(paths["voice_manifest"])
    casting = read_json(paths["casting"])
    existing_path = production / "approved-additions.json"
    if existing_path.is_file():
        existing = read_json(existing_path)
        if (
            existing.get("schema") != 1
            or existing.get("model") != MODEL
            or existing.get("casting_sha256") != file_sha(paths["casting"])
        ):
            raise ValueError("Existing voice additions overlay is unsupported or stale")

    missing = manifest.get("missing")
    if not isinstance(missing, list) or any(not isinstance(value, str) for value in missing):
        raise ValueError("Voice manifest missing inventory is invalid")
    if len(missing) != len(set(missing)):
        raise ValueError("Voice manifest missing inventory contains duplicates")

    rates = historical_credit_rates(root)
    campaign_required = campaign_inventory(campaign, casting)
    book_required = storybook_inventory(storybook, casting)
    campaign_occurrences = {}
    placed = set()
    lines = campaign.get("lines", {})
    for scene in campaign.get("scenes", []):
        sequence = [line_id for line_id in scene_line_ids(scene) if line_id in lines]
        placed.update(sequence)
        for index, line_id in enumerate(sequence):
            line = lines[line_id]
            campaign_occurrences.setdefault(line["audio"], []).append({
                "line": line,
                "scene": scene.get("id", ""),
                "previous_text": lines[sequence[index - 1]]["text"] if index else None,
                "next_text": lines[sequence[index + 1]]["text"]
                if index + 1 < len(sequence) else None,
            })
    unplaced = [line_id for line_id in lines if line_id not in placed]
    for index, line_id in enumerate(unplaced):
        line = lines[line_id]
        campaign_occurrences.setdefault(line["audio"], []).append({
            "line": line,
            "scene": line.get("scene", ""),
            "previous_text": lines[unplaced[index - 1]]["text"] if index else None,
            "next_text": lines[unplaced[index + 1]]["text"]
            if index + 1 < len(unplaced) else None,
        })

    book_occurrences = {}
    for name, book in storybook.get("books", {}).items():
        sequence = []
        for panel_index, panel in enumerate(book.get("panels", []), 1):
            for line_index, line in enumerate(panel.get("lines", []), 1):
                sequence.append((f"book.{name}.{panel_index}.{line_index}", line))
        for index, (audio_id, line) in enumerate(sequence):
            book_occurrences[audio_id] = {
                "line": line,
                "scene": f"storybook:{name}",
                "previous_text": sequence[index - 1][1]["text"] if index else None,
                "next_text": sequence[index + 1][1]["text"]
                if index + 1 < len(sequence) else None,
            }

    items = {}
    for audio_id in missing:
        safe_id(audio_id)
        if audio_id in campaign_required:
            occurrence = (campaign_occurrences.get(audio_id) or [None])[0]
            if occurrence is None:
                raise ValueError(f"Missing campaign audio ID has no script occurrence: {audio_id}")
            line = occurrence["line"]
            speaker = line["speaker"]
            role = pipeline.cast_key(speaker)
            delivery = line.get("delivery") or "live"
            direction = line.get("direction") or ""
            text = line["text"]
            context = occurrence
            kind = "campaign"
        elif audio_id in book_required:
            occurrence = book_occurrences[audio_id]
            speaker = role = "steve"
            delivery = "narration"
            direction = ""
            text = occurrence["line"]["text"]
            context = occurrence
            kind = "narration"
        else:
            raise ValueError(f"Missing audio ID is not present in campaign or storybook: {audio_id}")
        voice_id = casting["roles"][role]["voice_id"]
        tag = pipeline.synthesis_tag(direction)
        synthesis_text = f"{tag} {text}" if tag else text
        rate = rates.get(voice_id, 1.0)
        items[audio_id] = {
            "audio_id": audio_id,
            "kind": kind,
            "scene": context["scene"],
            "speaker": speaker,
            "cast_role": role,
            "voice_id": voice_id,
            "text": text,
            "text_sha256": text_sha(text),
            "synthesis_text": synthesis_text,
            "synthesis_text_sha256": text_sha(synthesis_text),
            "delivery": delivery,
            "direction": direction,
            "v4_audio_tag": tag,
            "previous_text": context["previous_text"],
            "next_text": context["next_text"],
            "voice_settings": pipeline.voice_settings(delivery),
            "language_code": "en",
            "model_id": MODEL,
            "output_format": OUTPUT_FORMAT,
            "estimated_credit_rate": rate,
            "estimated_credits": math.ceil(len(synthesis_text) * rate),
        }
    body = {
        "schema": 1,
        "batch": "later-additions",
        "model_id": MODEL,
        "output_format": OUTPUT_FORMAT,
        "inputs": input_hashes(root, production),
        "ordered_audio_ids": list(missing),
        "items": items,
        "count": len(items),
        "characters": sum(len(item["text"]) for item in items.values()),
        "request_characters": sum(len(item["synthesis_text"]) for item in items.values()),
        "estimated_credits": sum(item["estimated_credits"] for item in items.values()),
    }
    body["plan_sha256"] = canonical_sha(body)
    for audio_id, item in body["items"].items():
        item["attempt_seeds"] = [
            int(text_sha(f"{body['plan_sha256']}:{audio_id}:attempt-{attempt}")[:8], 16)
            for attempt in range(1, MAX_ATTEMPTS + 1)
        ]
    return body


def verify_plan(plan, root=ROOT, production=PRODUCTION):
    if plan.get("schema") != 1 or plan.get("model_id") != MODEL:
        raise ValueError("Unsupported voice additions plan")
    candidate = copy.deepcopy(plan)
    claimed = candidate.pop("plan_sha256", None)
    for item in candidate.get("items", {}).values():
        item.pop("attempt_seeds", None)
    if not claimed or canonical_sha(candidate) != claimed:
        raise ValueError("Plan content does not match its hash")
    for audio_id, item in plan.get("items", {}).items():
        expected_seeds = [
            int(text_sha(f"{claimed}:{audio_id}:attempt-{attempt}")[:8], 16)
            for attempt in range(1, MAX_ATTEMPTS + 1)
        ]
        if item.get("attempt_seeds") != expected_seeds:
            raise ValueError(f"Plan attempt seeds changed for {audio_id}")
    if plan.get("inputs") != input_hashes(root, production):
        raise ValueError("Frozen additions inputs are stale; rebuild the plan")
    return True


def authorize(plan, supplied_plan_sha256, allow_billed_generation):
    if not allow_billed_generation:
        raise ValueError("--allow-billed-generation is required")
    if supplied_plan_sha256 != plan.get("plan_sha256"):
        raise ValueError(f"Pass the exact frozen plan hash: {plan.get('plan_sha256')}")


def attempt_paths(audio_id, attempt, production=PRODUCTION):
    safe_id(audio_id)
    stem = f"{audio_id}.attempt-{attempt}"
    production = Path(production)
    return (
        production / "downloads" / f"{stem}.mp3",
        production / "receipts" / f"{stem}.json",
        production / "masters" / f"{stem}.wav",
        production / "checks" / f"{stem}.json",
    )


def proven_attempt(item, plan_sha256, attempt, production=PRODUCTION):
    audio_path, receipt_path, _, _ = attempt_paths(item["audio_id"], attempt, production)
    if not audio_path.exists() and not receipt_path.exists():
        return False
    if not audio_path.is_file() or not receipt_path.is_file():
        raise ValueError(f"Partial generation artifacts exist for {item['audio_id']} attempt {attempt}")
    receipt = read_json(receipt_path)
    expected = {
        "plan_sha256": plan_sha256,
        "audio_id": item["audio_id"],
        "attempt": attempt,
        "model_id": MODEL,
        "voice_id": item["voice_id"],
        "text_sha256": item["text_sha256"],
        "synthesis_text_sha256": item["synthesis_text_sha256"],
        "audio_sha256": file_sha(audio_path),
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError(f"Stale or changed generation receipt for {item['audio_id']} attempt {attempt}")
    if not receipt.get("request_id") or int(receipt.get("character_cost", -1)) < 0:
        raise ValueError(f"Incomplete billing receipt for {item['audio_id']} attempt {attempt}")
    return True


def inflight_files(production=PRODUCTION):
    folder = Path(production) / "inflight/speech"
    return sorted(folder.glob("*.json")) if folder.is_dir() else []


def latest_attempt(item, plan_sha256, production=PRODUCTION):
    latest = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if proven_attempt(item, plan_sha256, attempt, production):
            latest = attempt
    return latest


def generate_attempts(plan, candidates, client, production=PRODUCTION, limit=None):
    production = Path(production)
    if inflight_files(production):
        raise ValueError("Unresolved speech request exists; do not risk a duplicate billed take")
    if limit is not None and limit < 0:
        raise ValueError("--limit cannot be negative")
    selected = candidates[:limit] if limit is not None else candidates
    needed = sum(item["estimated_credits"] for item, _attempt in selected)
    pipeline.subscription_guard(client.get_json("/v1/user/subscription"), needed)
    generated = []
    for item, attempt in selected:
        audio_id = item["audio_id"]
        marker = production / "inflight/speech" / f"{audio_id}.attempt-{attempt}.json"
        action = {
            "operation": "text_to_speech",
            "plan_sha256": plan["plan_sha256"],
            "audio_id": audio_id,
            "attempt": attempt,
            "voice_id": item["voice_id"],
            "model_id": MODEL,
            "text_sha256": item["text_sha256"],
            "synthesis_text_sha256": item["synthesis_text_sha256"],
        }
        create_inflight(marker, action)
        body = {
            "text": item["synthesis_text"],
            "model_id": MODEL,
            "language_code": item["language_code"],
            "voice_settings": item["voice_settings"],
            "seed": item["attempt_seeds"][attempt - 1],
            "apply_text_normalization": "auto",
        }
        if item.get("previous_text"):
            body["previous_text"] = item["previous_text"]
        if item.get("next_text"):
            body["next_text"] = item["next_text"]
        audio, headers = client.post_audio(
            f"/v1/text-to-speech/{urllib.parse.quote(item['voice_id'])}",
            body, {"output_format": OUTPUT_FORMAT},
        )
        request_id = headers.get("request-id")
        character_cost = headers.get("character-cost")
        if not audio or not request_id or character_cost is None:
            raise RuntimeError(f"Uncertain paid response for {audio_id}; inflight marker retained")
        audio_path, receipt_path, _, _ = attempt_paths(audio_id, attempt, production)
        atomic_bytes(audio_path, audio)
        atomic_json(receipt_path, action | {
            "request_id": request_id,
            "trace_id": headers.get("x-trace-id"),
            "character_cost": int(character_cost),
            "output_format": OUTPUT_FORMAT,
            "audio_sha256": file_sha(audio_path),
            "response_bytes": len(audio),
            "seed": item["attempt_seeds"][attempt - 1],
        })
        marker.unlink()
        generated.append(audio_id)
    return generated


def generate(plan, client, root=ROOT, production=PRODUCTION, supplied_plan_sha256=None,
             allow_billed_generation=False, limit=None):
    authorize(plan, supplied_plan_sha256, allow_billed_generation)
    verify_plan(plan, root, production)
    candidates = [
        (plan["items"][audio_id], 1)
        for audio_id in plan["ordered_audio_ids"]
        if not proven_attempt(plan["items"][audio_id], plan["plan_sha256"], 1, production)
    ]
    return generate_attempts(plan, candidates, client, production, limit)


def retake(plan, client, root=ROOT, production=PRODUCTION, supplied_plan_sha256=None,
           allow_billed_generation=False, include_short=False):
    authorize(plan, supplied_plan_sha256, allow_billed_generation)
    verify_plan(plan, root, production)
    if inflight_files(production):
        raise ValueError("Unresolved speech request exists; do not risk a duplicate billed take")
    candidates = []
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        attempt = latest_attempt(item, plan["plan_sha256"], production)
        if not attempt:
            raise ValueError(f"Initial generation is missing for {audio_id}")
        _, _, master_path, check_path = attempt_paths(audio_id, attempt, production)
        if not check_path.is_file():
            raise ValueError(f"Validate {audio_id} attempt {attempt} before requesting a retake")
        check = read_json(check_path)
        if (
            check.get("plan_sha256") != plan["plan_sha256"]
            or check.get("wav_sha256") != (file_sha(master_path) if master_path.is_file() else None)
        ):
            raise ValueError(f"Stale validation report for {audio_id} attempt {attempt}")
        if check.get("status") in ACCEPTED_STATUSES:
            continue
        # A short line with an exact local transcript only lacks a second, independent check.
        if check.get("failure_reason") == "short_asr_ambiguity" and not include_short:
            continue
        if attempt < MAX_ATTEMPTS:
            candidates.append((item, attempt + 1))
    return generate_attempts(plan, candidates, client, production)


SCRIBE_FIELDS = {
    "model_id": "scribe_v3", "language_code": "eng", "tag_audio_events": "false",
    "diarize": "false", "temperature": "0", "timestamps_granularity": "word",
}


def independent(plan, client, root=ROOT, production=PRODUCTION, supplied_plan_sha256=None,
                allow_billed_transcription=False, checker=None, audio_ids=None):
    """Ask ElevenLabs Scribe, without the script or key terms, what each held take says."""
    if not allow_billed_transcription:
        raise ValueError("--allow-billed-transcription is required")
    if supplied_plan_sha256 != plan["plan_sha256"]:
        raise ValueError("Pass the exact frozen plan hash")
    verify_plan(plan, root, production)
    production = Path(production)
    checker = checker or runpy.run_path(str(Path(root) / "tools/check-voice-candidates.py"))
    done = []
    for audio_id in plan["ordered_audio_ids"]:
        if audio_ids is not None and audio_id not in audio_ids:
            continue
        item = plan["items"][audio_id]
        attempt = latest_attempt(item, plan["plan_sha256"], production)
        if not attempt:
            continue
        _, _, master, check_path = attempt_paths(audio_id, attempt, production)
        if not master.is_file() or not check_path.is_file():
            continue
        check = read_json(check_path)
        if audio_ids is None and check.get("status") in ACCEPTED_STATUSES:
            continue
        marker = production / "inflight/transcription" / f"{audio_id}.json"
        create_inflight(marker, {"operation": "speech_to_text", "audio_id": audio_id, "attempt": attempt})
        response, headers = client.post_multipart(
            "/v1/speech-to-text", SCRIBE_FIELDS, master.name, master.read_bytes(),
        )
        recognized = response.get("text")
        if not isinstance(recognized, str):
            raise RuntimeError(f"Uncertain transcription response for {audio_id}; inflight marker retained")
        evidence = {
            "audio_id": audio_id,
            "audio_sha256": file_sha(master),
            "file": master.relative_to(Path(root)).as_posix() if master.is_relative_to(Path(root)) else str(master),
            "production_plan_sha256": plan["plan_sha256"],
            "model_id": SCRIBE_FIELDS["model_id"],
            "request_fields": dict(SCRIBE_FIELDS),
            "script_or_keyterm_prompt_sent": False,
            "expected": item["text"],
            "recognized": recognized,
            "word_edits": pipeline.comparison_distance(item["text"], recognized, checker),
            "request_id": headers.get("request-id"),
            "trace_id": headers.get("x-trace-id"),
            "character_cost": headers.get("character-cost"),
            "response": response,
            "listening_reviewed": False,
        }
        atomic_json(production / "independent-asr/scribe-v3" / f"{audio_id}.json", evidence)
        marker.unlink()
        done.append(audio_id)
    return done


def decode_attempt(audio_id, attempt, production=PRODUCTION):
    source, _, target, _ = attempt_paths(audio_id, attempt, production)
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(target.name + f".partial-{uuid.uuid4().hex}.wav")
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
        "-map", "0:a:0", "-map_metadata", "-1", "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(pending),
    ], check=True)
    os.replace(pending, target)
    return target


def read_pcm16(path):
    with wave.open(str(path), "rb") as handle:
        if (
            handle.getnchannels() != 1
            or handle.getsampwidth() != 2
            or handle.getframerate() != 48000
            or handle.getcomptype() != "NONE"
        ):
            raise ValueError("expected mono 48 kHz PCM16 WAV")
        frames = handle.getnframes()
        samples = array("h")
        samples.frombytes(handle.readframes(frames))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples, 48000


def audio_facts(path):
    samples, rate = read_pcm16(path)
    if not samples:
        raise ValueError("empty WAV")
    peak_value = max(abs(value) for value in samples)
    peak = peak_value / 32768.0
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768.0
    seconds = len(samples) / rate
    if not .005 < peak < 1 or not .15 < seconds < 90 or not math.isfinite(rms):
        raise ValueError("WAV level or duration is outside production bounds")
    return {
        "seconds": seconds,
        "sample_rate": rate,
        "peak": peak,
        "rms": rms,
    }


def reference_levels(root):
    overlay_path = Path(root) / "assets/audio/elevenlabs-v4-script-v2/approved-overlay.json"
    if not overlay_path.is_file():
        return {}
    overlay = read_json(overlay_path)
    values = {}
    all_rms = []
    for section in ("campaign", "narration"):
        for take in overlay.get(section, {}).get("takes", {}).values():
            rms = take.get("rms")
            if not isinstance(rms, (int, float)) or rms <= 0:
                continue
            all_rms.append(float(rms))
            values.setdefault(take.get("identity"), []).append(float(rms))
    fallback = statistics.median(all_rms) if all_rms else None
    result = {role: statistics.median(levels) for role, levels in values.items()}
    if fallback:
        result[None] = fallback
    return result


def level_match(path, target_rms):
    facts = audio_facts(path)
    if not target_rms or facts["rms"] <= 0:
        return facts | {"level_match_gain_db": 0.0}
    difference_db = 20 * math.log10(target_rms / facts["rms"])
    if abs(difference_db) <= 3.0:
        return facts | {"level_match_gain_db": 0.0}
    samples, rate = read_pcm16(path)
    gain = 10 ** (difference_db / 20)
    peak = max(abs(value) for value in samples) / 32768.0
    if peak * gain > .95:
        gain = .95 / peak
    adjusted = array("h", (
        max(-32768, min(32767, round(value * gain))) for value in samples
    ))
    pending = Path(path).with_name(Path(path).name + f".partial-{uuid.uuid4().hex}")
    with wave.open(str(pending), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(adjusted.tobytes())
    os.replace(pending, path)
    return audio_facts(path) | {"level_match_gain_db": 20 * math.log10(gain)}


def local_transcriber():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from mlx_audio.stt import load
    model = load(str(ROOT / ".tools/models/whisper-qa"))

    def transcribe(path, _item):
        result = model.generate(
            str(path), language="en", temperature=0, condition_on_previous_text=False,
        )
        return result.text.strip()

    return transcribe


def validate(plan, root=ROOT, production=PRODUCTION, transcriber=None, checker=None, decoder=None):
    verify_plan(plan, root, production)
    production = Path(production)
    checker = checker or runpy.run_path(str(Path(root) / "tools/check-voice-candidates.py"))
    transcriber = transcriber or local_transcriber()
    decoder = decoder or decode_attempt
    levels = reference_levels(root)
    checks = {}
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        attempt = latest_attempt(item, plan["plan_sha256"], production)
        if not attempt:
            raise ValueError(f"Generation is incomplete for {audio_id}")
        master = decoder(audio_id, attempt, production)
        try:
            facts = level_match(master, levels.get(item["cast_role"], levels.get(None)))
            recognized = transcriber(master, item)
            report = {
                "schema": 1,
                "audio_id": audio_id,
                "attempt": attempt,
                "plan_sha256": plan["plan_sha256"],
                "wav_sha256": file_sha(master),
                "expected": item["text"],
                "recognized": recognized,
                "local_recognized": recognized,
                "transcript_comparison": "strict normalized English spoken forms",
                **facts,
            }
            hold = pipeline.assess_transcript(report, checker, production)
            report["status"] = "retake_required" if hold else "automated_qa_passed"
            report["failure_reason"] = hold
        except Exception as error:
            report = {
                "schema": 1,
                "audio_id": audio_id,
                "attempt": attempt,
                "plan_sha256": plan["plan_sha256"],
                "wav_sha256": file_sha(master) if Path(master).is_file() else None,
                "expected": item["text"],
                "recognized": "",
                "status": "retake_required",
                "failure_reason": f"audio_or_transcript_error: {error}",
            }
        _, _, _, check_path = attempt_paths(audio_id, attempt, production)
        atomic_json(check_path, report)
        checks[audio_id] = report
    atomic_json(production / "validation-summary.json", {
        "schema": 1,
        "plan_sha256": plan["plan_sha256"],
        "passed": sorted(key for key, value in checks.items()
                         if value["status"] in ACCEPTED_STATUSES),
        "retake_required": {
            key: value["failure_reason"] for key, value in checks.items()
            if value["status"] not in ACCEPTED_STATUSES
        },
    })
    return checks


def valid_existing_takes(existing, root, campaign_required, book_required):
    from script_v2_voice_overlay import validate_addition_take
    kept = {"campaign": {}, "narration": {}}
    for section, inventory in (("campaign", campaign_required), ("narration", book_required)):
        for audio_id, take in existing.get(section, {}).get("takes", {}).items():
            expected = inventory.get(audio_id)
            if not expected:
                continue
            try:
                validate_addition_take(
                    audio_id, take, expected["text"], expected["speakers"],
                    expected["identity"], expected["voice_id"], root,
                )
            except ValueError:
                continue
            kept[section][audio_id] = take
    return kept


def import_settings(runtime, wav_sha256, game_root):
    resource = "res://" + runtime.relative_to(game_root).as_posix()
    suffix = hashlib.md5(resource.encode()).hexdigest()
    imported = f"res://.godot/imported/{runtime.name}-{suffix}.sample"
    uid = "uid://" + hashlib.sha256((resource + ":" + wav_sha256).encode()).hexdigest()[:13]
    return (
        f'[remap]\n\nimporter="wav"\ntype="AudioStreamWAV"\nuid="{uid}"\n'
        f'path="{imported}"\n\n[deps]\n\nsource_file="{resource}"\n'
        f'dest_files=["{imported}"]\n\n[params]\n\nforce/8_bit=false\n'
        'force/mono=false\nforce/max_rate=false\nforce/max_rate_hz=44100\n'
        'edit/trim=false\nedit/normalize=false\nedit/loop_mode=0\n'
        'edit/loop_begin=0\nedit/loop_end=-1\ncompress/mode=2\n'
    )


def stage(plan, root=ROOT, production=PRODUCTION, partial=False):
    """Stage checked takes. With partial, takes that failed stay missing and are reported."""
    verify_plan(plan, root, production)
    root = Path(root)
    production = Path(production)
    paths = content_paths(root)
    casting = read_json(paths["casting"])
    campaign = read_json(paths["campaign"])
    storybook = read_json(paths["storybook"])
    campaign_required = campaign_inventory(campaign, casting)
    book_required = storybook_inventory(storybook, casting)
    existing_path = production / "approved-additions.json"
    existing = read_json(existing_path) if existing_path.is_file() else {
        "schema": 1,
        "model": MODEL,
        "casting_sha256": file_sha(paths["casting"]),
        "campaign": {"takes": {}},
        "narration": {"takes": {}},
    }
    if (
        existing.get("schema") != 1
        or existing.get("model") != MODEL
        or existing.get("casting_sha256") != file_sha(paths["casting"])
    ):
        raise ValueError("Existing voice additions overlay is unsupported or stale")
    kept = valid_existing_takes(existing, root, campaign_required, book_required)
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        attempt = latest_attempt(item, plan["plan_sha256"], production)
        if not attempt:
            raise ValueError(f"{audio_id} has not been generated")
        _, receipt_path, master_path, check_path = attempt_paths(audio_id, attempt, production)
        check = read_json(check_path) if check_path.is_file() and master_path.is_file() else {}
        if (
            check.get("plan_sha256") != plan["plan_sha256"]
            or check.get("wav_sha256") != file_sha(master_path)
            or check.get("status") not in ACCEPTED_STATUSES
        ):
            if partial:
                continue
            raise ValueError(f"{audio_id} has not passed validation")
        runtime = (
            root / "game/assets/audio/voices/elevenlabs-v4-additions" / f"{audio_id}.wav"
        )
        atomic_bytes(runtime, master_path.read_bytes())
        runtime_sha = file_sha(runtime)
        atomic_bytes(runtime.with_name(runtime.name + ".import"),
                     import_settings(runtime, runtime_sha, root / "game").encode())
        receipt = read_json(receipt_path)
        take = {
            "id": audio_id,
            "text": item["text"],
            "text_hash": text_sha(item["text"])[:16],
            "speaker": item["speaker"],
            "identity": item["cast_role"],
            "voice_id": item["voice_id"],
            "model": MODEL,
            "file": "res://" + runtime.relative_to(root / "game").as_posix(),
            "sha256": runtime_sha,
            "seconds": check["seconds"],
            "status": check["status"],
            "sample_rate": check["sample_rate"],
            "peak": check["peak"],
            "rms": check["rms"],
            "provider": "ElevenLabs API",
            "request_id": receipt["request_id"],
            "plan_sha256": plan["plan_sha256"],
            "attempt": attempt,
            "asr_report": check_path.relative_to(root).as_posix(),
            "word_error_rate": check["word_error_rate"],
        }
        kept[item["kind"]][audio_id] = take
    result = {
        "schema": 1,
        "model": MODEL,
        "casting_sha256": file_sha(paths["casting"]),
        "campaign": {"takes": kept["campaign"]},
        "narration": {"takes": kept["narration"]},
    }
    atomic_json(existing_path, result)
    return result


BATCH_ITEMS = ("downloads", "receipts", "masters", "checks", "independent-asr", "inflight",
               "validation-summary.json", "plan.json")


def archive(plan, root=ROOT, production=PRODUCTION):
    """Move a finished batch aside so the next plan can reuse audio ids without stale receipts."""
    root = Path(root)
    production = Path(production)
    if inflight_files(production) or any((production / "inflight").glob("*/*.json")):
        raise ValueError("Resolve inflight requests before archiving a batch")
    batch = production / "batches" / plan["plan_sha256"][:16]
    if batch.exists():
        raise ValueError(f"Batch {batch.name} is already archived")
    batch.mkdir(parents=True)
    for name in BATCH_ITEMS:
        source = production / name
        if source.exists():
            source.rename(batch / name)
    overlay_path = production / "approved-additions.json"
    if overlay_path.is_file():
        overlay = read_json(overlay_path)
        old = (production / "checks").relative_to(root).as_posix() + "/"
        new = (batch / "checks").relative_to(root).as_posix() + "/"
        for section in ("campaign", "narration"):
            for take in overlay.get(section, {}).get("takes", {}).values():
                if take.get("plan_sha256") == plan["plan_sha256"] and str(take.get("asr_report", "")).startswith(old):
                    take["asr_report"] = new + take["asr_report"][len(old):]
        atomic_json(overlay_path, overlay)
    return batch


def command_plan(_args):
    plan = build_plan()
    atomic_json(PLAN_PATH, plan)
    print(json.dumps({
        "plan_sha256": plan["plan_sha256"],
        "count": plan["count"],
        "characters": plan["characters"],
        "estimated_credits": plan["estimated_credits"],
    }, indent=2))
def command_generate(args):
    plan = read_json(PLAN_PATH)
    generated = generate(
        plan, pipeline.ApiClient(), ROOT, PRODUCTION, args.plan_sha256,
        args.allow_billed_generation, args.limit,
    )
    print(json.dumps({"generated": len(generated), "audio_ids": generated}, indent=2))


def command_validate(_args):
    checks = validate(read_json(PLAN_PATH))
    failed = {
        key: value["failure_reason"] for key, value in checks.items()
        if value["status"] not in ACCEPTED_STATUSES
    }
    print(json.dumps({"passed": len(checks) - len(failed), "retake_required": failed}, indent=2))


def command_retake(args):
    plan = read_json(PLAN_PATH)
    generated = retake(
        plan, pipeline.ApiClient(), ROOT, PRODUCTION, args.plan_sha256,
        args.allow_billed_generation, args.include_short,
    )
    print(json.dumps({"retakes_generated": len(generated), "audio_ids": generated}, indent=2))


def command_independent(args):
    plan = read_json(PLAN_PATH)
    done = independent(
        plan, pipeline.ApiClient(), ROOT, PRODUCTION, args.plan_sha256,
        args.allow_billed_transcription, audio_ids=args.ids or None,
    )
    print(json.dumps({"transcribed": len(done), "audio_ids": done}, indent=2))


def command_stage(args):
    result = stage(read_json(PLAN_PATH), partial=args.partial)
    print(json.dumps({
        "campaign_takes": len(result["campaign"]["takes"]),
        "narration_takes": len(result["narration"]["takes"]),
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan").set_defaults(function=command_plan)
    generation = sub.add_parser("generate")
    generation.add_argument("--plan-sha256", required=True)
    generation.add_argument("--allow-billed-generation", action="store_true")
    generation.add_argument("--limit", type=int)
    generation.set_defaults(function=command_generate)
    sub.add_parser("validate").set_defaults(function=command_validate)
    retakes = sub.add_parser("retake")
    retakes.add_argument("--plan-sha256", required=True)
    retakes.add_argument("--allow-billed-generation", action="store_true")
    retakes.add_argument("--include-short", action="store_true",
                         help="Also regenerate short lines that only lack an independent transcript")
    retakes.set_defaults(function=command_retake)
    check = sub.add_parser("independent", help="Independent Scribe transcripts for held takes")
    check.add_argument("--plan-sha256", required=True)
    check.add_argument("--allow-billed-transcription", action="store_true")
    check.add_argument("--ids", nargs="*")
    check.set_defaults(function=command_independent)
    staging = sub.add_parser("stage")
    staging.add_argument("--partial", action="store_true",
                         help="Stage passing takes and leave failed lines missing")
    staging.set_defaults(function=command_stage)
    sub.add_parser("archive", help="Move the finished batch under batches/").set_defaults(
        function=lambda _args: print(archive(read_json(PLAN_PATH)).relative_to(ROOT)))
    args = parser.parse_args()
    try:
        args.function(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

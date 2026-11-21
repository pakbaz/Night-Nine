#!/usr/bin/env python3
"""Plan, preflight, record, validate, and stage Night Nine's ElevenLabs v4 cast.

The default commands are read-only or offline. Account writes and billed speech
generation require explicit flags and the exact frozen plan hash.
"""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "assets/audio/elevenlabs-v4-script-v2"
PLAN_PATH = PRODUCTION / "plan.json"
PREFLIGHT_PATH = PRODUCTION / "preflight.json"
OVERLAY_PATH = PRODUCTION / "approved-overlay.json"
RECORDING_LIST = ROOT / "docs/script-v2/recording-list.csv"
SCRIPT = ROOT / "docs/script-v2/script.json"
CASTING = ROOT / "docs/voice-casting-2026-11-20.json"
MODEL = "eleven_v4"
OUTPUT_FORMAT = "mp3_44100_192"
ALIASES = {
    "stephen": "steve",
    "iris": "nora",
    "pell": "dale",
    "agnes_original": "agnes",
    "rook_copy": "rook",
    "lyle_copy": "lyle",
}
DERIVED = {
    "recording.saren_splice": {
        "source_audio_id": "recording.voicemail",
        "kind": "voicemail_splice",
        "gap_seconds": .22,
    }
}
TAG_RULES = (
    ("frightened whisper", "[whispers]"),
    ("a whisper", "[whispers]"),
    ("barely audible", "[whispers]"),
)


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


def atomic_json(path, value, compact=False):
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, **options) + "\n").encode())


def safe_id(audio_id):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", audio_id):
        raise ValueError(f"Unsafe audio ID: {audio_id}")
    return audio_id


def cast_key(speaker):
    return ALIASES.get(speaker, speaker)


def synthesis_tag(direction):
    lowered = direction.lower()
    for needle, tag in TAG_RULES:
        if needle in lowered:
            return tag
    return ""


def voice_settings(delivery):
    stability = .62 if delivery == "narration" else .55 if delivery in {
        "radio", "phone", "intercom", "broadcast", "recorded_playback",
        "private_recording", "voicemail", "memory",
    } else .46
    return {"stability": stability, "similarity_boost": .78}


def load_rows(path=RECORDING_LIST):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Recording list is empty")
    required = {
        "order", "line_id", "scene", "speaker_key", "voice_id", "delivery",
        "direction", "text", "characters", "audio_key", "plan",
    }
    if not required.issubset(rows[0]):
        raise ValueError("Recording list columns changed")
    if [int(row["order"]) for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("Recording list order is not contiguous")
    return rows


def build_plan(recording_list=RECORDING_LIST, script_path=SCRIPT, casting_path=CASTING):
    rows = load_rows(recording_list)
    casting = read_json(casting_path)
    inputs = {
        "recording_list": file_sha(recording_list),
        "script": file_sha(script_path),
        "casting": file_sha(casting_path),
    }
    items = {}
    ordered_ids = []
    for index, row in enumerate(rows):
        audio_id = safe_id(row["audio_key"])
        role = cast_key(row["speaker_key"])
        if role not in casting["roles"]:
            raise ValueError(f"Uncast speaker {row['speaker_key']} on {row['line_id']}")
        expected_voice = casting["roles"][role]["voice_id"]
        if row["voice_id"] != expected_voice:
            raise ValueError(f"Voice ID drift for {row['line_id']}")
        item = items.get(audio_id)
        if item:
            if (item["text"], item["voice_id"], item["cast_role"]) != (
                row["text"], row["voice_id"], role,
            ):
                raise ValueError(f"Conflicting reuse for {audio_id}")
            item["line_ids"].append(row["line_id"])
            item["scenes"].append(row["scene"])
            continue
        tag = synthesis_tag(row["direction"])
        synthesis_text = f"{tag} {row['text']}" if tag else row["text"]
        previous_text = rows[index - 1]["text"] if index and rows[index - 1]["scene"] == row["scene"] else None
        next_text = rows[index + 1]["text"] if index + 1 < len(rows) and rows[index + 1]["scene"] == row["scene"] else None
        item = {
            "audio_id": audio_id,
            "kind": "derived" if audio_id in DERIVED else "speech",
            "line_ids": [row["line_id"]],
            "scenes": [row["scene"]],
            "speaker": row["speaker_key"],
            "cast_role": role,
            "voice_id": row["voice_id"],
            "text": row["text"],
            "text_sha256": text_sha(row["text"]),
            "synthesis_text": synthesis_text,
            "synthesis_text_sha256": text_sha(synthesis_text),
            "delivery": row["delivery"],
            "direction": row["direction"],
            "v4_audio_tag": tag,
            "previous_text": previous_text,
            "next_text": next_text,
            "voice_settings": voice_settings(row["delivery"]),
            "language_code": "en",
            "model_id": MODEL,
            "output_format": OUTPUT_FORMAT,
        }
        if audio_id in DERIVED:
            item["derivation"] = DERIVED[audio_id]
        items[audio_id] = item
        ordered_ids.append(audio_id)
    body = {
        "schema": 1,
        "campaign": "script-v2",
        "model_id": MODEL,
        "output_format": OUTPUT_FORMAT,
        "inputs": inputs,
        "rows": len(rows),
        "row_characters": sum(len(row["text"]) for row in rows),
        "unique_audio_ids": len(items),
        "speech_requests": sum(item["kind"] == "speech" for item in items.values()),
        "derived_edits": sum(item["kind"] == "derived" for item in items.values()),
        "utterance_characters": sum(len(item["text"]) for item in items.values() if item["kind"] == "speech"),
        "request_characters": sum(len(item["synthesis_text"]) for item in items.values() if item["kind"] == "speech"),
        "ordered_audio_ids": ordered_ids,
        "items": items,
    }
    body["plan_sha256"] = canonical_sha(body)
    for audio_id, item in body["items"].items():
        item["seed"] = int(text_sha(body["plan_sha256"] + ":" + audio_id)[:8], 16)
    return body


def verify_frozen_inputs(plan):
    live = {
        "recording_list": file_sha(RECORDING_LIST),
        "script": file_sha(SCRIPT),
        "casting": file_sha(CASTING),
    }
    if live != plan.get("inputs"):
        raise ValueError(f"Frozen voice inputs are stale: expected {plan.get('inputs')}, found {live}")
    candidate = copy.deepcopy(plan)
    claimed = candidate.pop("plan_sha256")
    for item in candidate["items"].values():
        item.pop("seed", None)
    if canonical_sha(candidate) != claimed:
        raise ValueError("Plan content does not match its hash")
    return True


def keychain_api_key():
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "elevenlabs-api-key", "-w"],
        check=True, capture_output=True, text=True,
    )
    key = result.stdout.strip()
    if not key:
        raise RuntimeError("ElevenLabs API key is empty")
    return key


class ApiClient:
    def __init__(self, api_key=None, base_url="https://api.elevenlabs.io"):
        self.api_key = api_key or keychain_api_key()
        self.base_url = base_url.rstrip("/")

    def _request(self, method, path, body=None, params=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"xi-api-key": self.api_key}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode()
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            return urllib.request.urlopen(request, timeout=180)
        except urllib.error.HTTPError as error:
            detail = error.read(2048).decode(errors="replace")
            raise RuntimeError(f"ElevenLabs HTTP {error.code} for {method} {path}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Uncertain ElevenLabs outcome for {method} {path}: {error.reason}") from error

    def get_json(self, path, params=None):
        with self._request("GET", path, params=params) as response:
            return json.loads(response.read())

    def post_json(self, path, body):
        with self._request("POST", path, body=body) as response:
            return json.loads(response.read()), dict(response.headers.items())

    def post_audio(self, path, body, params=None):
        with self._request("POST", path, body=body, params=params) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}


def models_list(raw):
    return raw if isinstance(raw, list) else raw.get("models", [])


def account_voices(raw):
    return raw if isinstance(raw, list) else raw.get("voices", [])


def subscription_guard(subscription, needed_credits):
    available = int(subscription["character_limit"]) - int(subscription["character_count"])
    overage_enabled = (
        bool(subscription.get("allowed_to_extend_character_limit"))
        or bool(subscription.get("can_extend_character_limit"))
        or int(subscription.get("max_character_limit_extension", 0)) > 0
        or int(subscription.get("max_credit_limit_extension", 0)) > 0
        or float(subscription.get("current_overage", {}).get("amount", 0)) > 0
    )
    if overage_enabled:
        raise ValueError("Paid overage is enabled or already in use; refusing generation")
    if available < needed_credits:
        raise ValueError(f"Quota refusal: need {needed_credits} credits, only {available} remain")
    return available


def shared_voice_result(client, voice_id, name):
    queries = [name.strip(), name.split("-", 1)[0].strip(), voice_id]
    for query in dict.fromkeys(q for q in queries if q):
        raw = client.get_json("/v1/shared-voices", {
            "page_size": 100,
            "search": query,
            "include_custom_rates": "true",
        })
        matches = [voice for voice in raw.get("voices", []) if voice.get("voice_id") == voice_id]
        if len(matches) == 1:
            return matches[0]
    raise ValueError(f"Shared voice {voice_id} is unavailable or ambiguous")


def collect_preflight(plan, client):
    verify_frozen_inputs(plan)
    casting = read_json(CASTING)
    models = models_list(client.get_json("/v1/models"))
    model = next((item for item in models if item.get("model_id", item.get("id")) == MODEL), None)
    if not model or not model.get("can_do_text_to_speech", True):
        raise ValueError("Required model eleven_v4 is not currently available for text to speech")
    subscription = client.get_json("/v1/user/subscription")
    current_voices = {voice.get("voice_id"): voice for voice in account_voices(client.get_json("/v1/voices"))}
    metadata = {}
    missing_shared = 0
    for role, spec in casting["roles"].items():
        voice_id = spec["voice_id"]
        shared = "shared" in spec["source"].lower()
        if shared:
            info = shared_voice_result(client, voice_id, spec["library_name"])
            verified = {entry.get("model_id") for entry in info.get("verified_languages") or []}
            if verified and MODEL not in verified:
                raise ValueError(f"{voice_id} is not currently verified for {MODEL}")
            added = voice_id in current_voices or bool(info.get("is_added_by_user"))
            missing_shared += not added
            metadata[voice_id] = {
                "role": role,
                "source": "shared",
                "name": info["name"],
                "public_owner_id": info["public_owner_id"],
                "rate": float(info.get("rate") or 1),
                "fiat_rate": info.get("fiat_rate"),
                "notice_period_days": info.get("notice_period"),
                "added": added,
                "verified_models": sorted(verified),
            }
        else:
            if voice_id not in current_voices:
                raise ValueError(f"Premade voice {voice_id} is not available to this account")
            metadata[voice_id] = {
                "role": role, "source": "premade", "name": spec["library_name"],
                "rate": 1.0, "fiat_rate": None, "added": True,
            }
    weighted = 0
    by_voice = {}
    for item in plan["items"].values():
        if item["kind"] != "speech":
            continue
        rate = metadata[item["voice_id"]]["rate"]
        cost = math.ceil(len(item["synthesis_text"]) * rate)
        weighted += cost
        by_voice.setdefault(item["voice_id"], {"requests": 0, "request_characters": 0, "estimated_credits": 0})
        by_voice[item["voice_id"]]["requests"] += 1
        by_voice[item["voice_id"]]["request_characters"] += len(item["synthesis_text"])
        by_voice[item["voice_id"]]["estimated_credits"] += cost
    available = subscription_guard(subscription, weighted)
    slots_available = int(subscription["voice_limit"]) - int(subscription["voice_slots_used"])
    if missing_shared > slots_available:
        raise ValueError(f"Voice slot refusal: need {missing_shared}, only {slots_available} remain")
    result = {
        "schema": 1,
        "plan_sha256": plan["plan_sha256"],
        "model": {
            "id": MODEL,
            "name": model.get("name"),
            "can_do_text_to_speech": model.get("can_do_text_to_speech", True),
        },
        "subscription": {
            "status": subscription["status"],
            "sufficient_included_credits": available >= weighted,
            "estimated_credits": weighted,
            "overage_allowed": False,
            "missing_shared_voices": missing_shared,
        },
        "voices": metadata,
        "by_voice": by_voice,
    }
    result["preflight_sha256"] = canonical_sha(result)
    return result


def verify_preflight(plan, preflight):
    if preflight.get("plan_sha256") != plan["plan_sha256"]:
        raise ValueError("Preflight belongs to a different plan")
    candidate = dict(preflight)
    claimed = candidate.pop("preflight_sha256")
    if canonical_sha(candidate) != claimed:
        raise ValueError("Preflight content does not match its hash")


def require_gate(plan, supplied):
    if supplied != plan["plan_sha256"]:
        raise ValueError(f"Pass the exact frozen plan hash: {plan['plan_sha256']}")


def inflight_files(kind):
    folder = PRODUCTION / "inflight" / kind
    return sorted(folder.glob("*.json")) if folder.is_dir() else []


def add_voices(plan, preflight, client):
    verify_frozen_inputs(plan)
    verify_preflight(plan, preflight)
    if inflight_files("voice-add"):
        raise ValueError("Unresolved voice-add operation exists; inspect it before continuing")
    casting = read_json(CASTING)
    completed = []
    for voice_id, info in preflight["voices"].items():
        if info["source"] != "shared" or info["added"]:
            continue
        live = shared_voice_result(client, voice_id, info["name"])
        if live.get("is_added_by_user"):
            completed.append({"voice_id": voice_id, "status": "already_added"})
            continue
        action = {
            "operation": "add_shared_voice",
            "plan_sha256": plan["plan_sha256"],
            "voice_id": voice_id,
            "public_owner_id": info["public_owner_id"],
        }
        marker = PRODUCTION / "inflight/voice-add" / f"{voice_id}.json"
        atomic_json(marker, action)
        role = info["role"]
        new_name = casting["roles"][role]["library_name"]
        response, headers = client.post_json(
            f"/v1/voices/add/{urllib.parse.quote(info['public_owner_id'])}/{urllib.parse.quote(voice_id)}",
            {"new_name": new_name, "bookmarked": True},
        )
        if response.get("voice_id") != voice_id:
            raise RuntimeError(f"Uncertain add-voice response for {voice_id}")
        receipt = action | {
            "status": "added",
            "request_id": headers.get("request-id") or headers.get("Request-Id"),
            "response": response,
        }
        atomic_json(PRODUCTION / "account-voice-receipts" / f"{voice_id}.json", receipt)
        marker.unlink()
        completed.append({"voice_id": voice_id, "status": "added"})
    return completed


def receipt_paths(audio_id, production=None):
    safe_id(audio_id)
    production = production or PRODUCTION
    return (
        production / "downloads" / f"{audio_id}.mp3",
        production / "receipts" / f"{audio_id}.json",
    )


def proven_generation(item, plan_sha, production=None):
    audio, receipt = receipt_paths(item["audio_id"], production)
    if not audio.exists() and not receipt.exists():
        return False
    if not audio.is_file() or not receipt.is_file():
        raise ValueError(f"Partial generation artifacts exist for {item['audio_id']}")
    data = read_json(receipt)
    expected = {
        "plan_sha256": plan_sha,
        "audio_id": item["audio_id"],
        "model_id": MODEL,
        "voice_id": item["voice_id"],
        "text_sha256": item["text_sha256"],
        "synthesis_text_sha256": item["synthesis_text_sha256"],
        "audio_sha256": file_sha(audio),
    }
    if any(data.get(key) != value for key, value in expected.items()):
        raise ValueError(f"Stale or changed generation receipt for {item['audio_id']}")
    if not data.get("request_id") or int(data.get("character_cost", -1)) < 0:
        raise ValueError(f"Incomplete billing receipt for {item['audio_id']}")
    return True


def remaining_estimated_credits(plan, preflight):
    total = 0
    for item in plan["items"].values():
        if item["kind"] != "speech" or proven_generation(item, plan["plan_sha256"]):
            continue
        rate = preflight["voices"][item["voice_id"]]["rate"]
        total += math.ceil(len(item["synthesis_text"]) * rate)
    return total


def generate(plan, preflight, client, limit=None):
    verify_frozen_inputs(plan)
    verify_preflight(plan, preflight)
    if inflight_files("speech"):
        raise ValueError("Unresolved speech request exists; do not risk a duplicate billed take")
    remaining = remaining_estimated_credits(plan, preflight)
    subscription_guard(client.get_json("/v1/user/subscription"), remaining)
    live_voices = {voice.get("voice_id") for voice in account_voices(client.get_json("/v1/voices"))}
    missing = sorted({item["voice_id"] for item in plan["items"].values()
                      if item["kind"] == "speech"} - live_voices)
    if missing:
        raise ValueError(f"Required voices have not been added: {missing}")
    generated = []
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        if item["kind"] != "speech" or proven_generation(item, plan["plan_sha256"]):
            continue
        if limit is not None and len(generated) >= limit:
            break
        marker = PRODUCTION / "inflight/speech" / f"{audio_id}.json"
        action = {
            "operation": "text_to_speech",
            "plan_sha256": plan["plan_sha256"],
            "audio_id": audio_id,
            "voice_id": item["voice_id"],
            "model_id": MODEL,
            "text_sha256": item["text_sha256"],
            "synthesis_text_sha256": item["synthesis_text_sha256"],
        }
        atomic_json(marker, action)
        body = {
            "text": item["synthesis_text"],
            "model_id": MODEL,
            "language_code": item["language_code"],
            "voice_settings": item["voice_settings"],
            "seed": item["seed"],
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
        trace_id = headers.get("x-trace-id")
        character_cost = headers.get("character-cost")
        if not audio or not request_id or character_cost is None:
            raise RuntimeError(f"Uncertain paid response for {audio_id}; inflight marker retained")
        audio_path, receipt_path = receipt_paths(audio_id)
        atomic_bytes(audio_path, audio)
        receipt = action | {
            "request_id": request_id,
            "trace_id": trace_id,
            "character_cost": int(character_cost),
            "output_format": OUTPUT_FORMAT,
            "audio_sha256": file_sha(audio_path),
            "response_bytes": len(audio),
        }
        atomic_json(receipt_path, receipt)
        marker.unlink()
        generated.append(audio_id)
    return generated


def decode_mp3(audio_id, production=None):
    production = production or PRODUCTION
    source, _ = receipt_paths(audio_id, production)
    target = production / "masters" / f"{audio_id}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(target.name + f".partial-{uuid.uuid4().hex}.wav")
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
        "-map", "0:a:0", "-map_metadata", "-1", "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(pending),
    ], check=True)
    plan_path = production / "plan.json"
    if plan_path.is_file():
        item = read_json(plan_path).get("items", {}).get(audio_id, {})
        gain_db = item.get("master_gain_db", 0)
        if not isinstance(gain_db, (int, float)) or not math.isfinite(gain_db) or abs(gain_db) > 12:
            raise ValueError(f"Invalid master gain for {audio_id}")
        if gain_db:
            import numpy as np
            import soundfile as sf
            samples, rate = sf.read(pending, dtype="float32")
            peak = float(np.max(np.abs(samples))) if len(samples) else 0
            gain = 10 ** (gain_db / 20)
            if peak * gain > .95:
                gain = .95 / peak
            sf.write(pending, samples * gain, rate, subtype="PCM_16")
    os.replace(pending, target)
    return target


def transcript_words(text, checker):
    words = checker["words"](text.replace("space-fold", "spacefold"))
    spellings = {
        "favourites": "favorites",
        "labelled": "labeled",
    }
    return [spellings.get(word, word) for word in words]


def _clock_marker(hour, minute):
    letters = str.maketrans("0123456789", "zotfvsxeni")
    return "clocktime" + (f"{int(hour):02d}{minute}").translate(letters)


def _possessive_stems(text):
    text = text.lower().replace("’", "'")
    stems = {match.group(1) for match in re.finditer(r"\b([\w]+)'s\b", text)}
    stems.update(match.group(1) for match in re.finditer(r"\b([\w]+s)'(?=\W|$)", text))
    return stems


def _replace_possessive_pair(left, right):
    left = left.replace("’", "'")
    right = right.replace("’", "'")
    for stem in sorted(_possessive_stems(left), key=len, reverse=True):
        marker = "possessive" + re.sub(r"\W+", "", stem.lower())
        possessive = re.compile(rf"\b{re.escape(stem)}(?:'s|')(?=\W|$)", re.IGNORECASE)
        plain = re.compile(rf"\b{re.escape(stem)}s\b", re.IGNORECASE)
        if possessive.search(left) and (possessive.search(right) or plain.search(right)):
            left = possessive.sub(marker, left)
            right = possessive.sub(marker, right)
            right = plain.sub(marker, right)
    for stem in sorted(_possessive_stems(right), key=len, reverse=True):
        marker = "possessive" + re.sub(r"\W+", "", stem.lower())
        possessive = re.compile(rf"\b{re.escape(stem)}(?:'s|')(?=\W|$)", re.IGNORECASE)
        plain = re.compile(rf"\b{re.escape(stem)}s\b", re.IGNORECASE)
        if possessive.search(right) and (possessive.search(left) or plain.search(left)):
            right = possessive.sub(marker, right)
            left = possessive.sub(marker, left)
            left = plain.sub(marker, left)
    return left, right


def comparison_words(expected, recognized, checker):
    expected, recognized = _replace_possessive_pair(expected, recognized)
    times = {
        (match.group(1), match.group(2))
        for match in re.finditer(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)", expected)
    }
    for hour, minute in sorted(times, key=lambda value: len(value[0]), reverse=True):
        marker = _clock_marker(hour, minute)
        hours = sorted({str(int(hour)), f"{int(hour):02d}"}, key=len, reverse=True)
        separated = re.compile(
            rf"(?<!\d)(?:{'|'.join(map(re.escape, hours))})[:.]{re.escape(minute)}(?!\d)"
        )
        compact_values = sorted({f"{int(hour):02d}{minute}", f"{int(hour)}{minute}"}, key=len, reverse=True)
        compact = re.compile(rf"(?<!\d)(?:{'|'.join(compact_values)})(?!\d)")
        expected = separated.sub(marker, expected)
        recognized = separated.sub(marker, recognized)
        recognized = compact.sub(marker, recognized)
    return transcript_words(expected, checker), transcript_words(recognized, checker)


def comparison_distance(expected, recognized, checker):
    left, right = comparison_words(expected, recognized, checker)
    return checker["distance"](left, right)


def assess_transcript(report, checker):
    expected = report["expected"]
    local = report.get("local_recognized", report["recognized"])
    local_edits = comparison_distance(expected, local, checker)
    word_count = len(transcript_words(expected, checker))
    report.update(recognized=local, word_edits=local_edits,
                  word_error_rate=local_edits / max(1, word_count))
    report.pop("independent_asr", None)
    independent_edits = None
    audio_id = safe_id(report["audio_id"])
    for path in sorted((PRODUCTION / "independent-asr").glob(f"scribe-v3*/{audio_id}.json")):
        evidence = read_json(path)
        if evidence.get("audio_sha256") != report["wav_sha256"]:
            continue
        fields = evidence.get("request_fields", {})
        recognized = evidence.get("recognized")
        if (
            evidence.get("audio_id") != audio_id
            or evidence.get("production_plan_sha256") != report["plan_sha256"]
            or evidence.get("expected") != expected
            or evidence.get("model_id") != "scribe_v3"
            or fields.get("model_id") != "scribe_v3"
            or evidence.get("script_or_keyterm_prompt_sent") is not False
            or any(key in fields for key in ("keyterms", "transcript_edit", "prompt", "text"))
            or not isinstance(recognized, str)
            or recognized != evidence.get("response", {}).get("text")
        ):
            raise ValueError(f"Unverified independent transcript for {audio_id}")
        edits = comparison_distance(expected, recognized, checker)
        if edits != evidence.get("word_edits") or independent_edits is not None:
            raise ValueError(f"Changed or duplicate independent transcript for {audio_id}")
        independent_edits = edits
        report["local_recognized"] = local
        report["independent_asr"] = {
            "file": path.relative_to(PRODUCTION).as_posix(), "sha256": file_sha(path),
            "model": "scribe_v3", "word_edits": edits, "listening_reviewed": False,
        }
        report.update(recognized=recognized, word_edits=edits,
                      word_error_rate=edits / max(1, word_count))
    if independent_edits is None:
        report.pop("local_recognized", None)
    if report["word_edits"]:
        return "asr_mismatch"
    if word_count <= 4 and (local_edits or independent_edits != 0):
        return "short_asr_ambiguity"
    return None


def verified_retakes(plan, checker):
    selected = {}
    for folder in sorted((PRODUCTION / "retakes").glob("*")):
        if not (folder / "plan.json").is_file() or not (folder / "results.json").is_file():
            continue
        candidate_plan = read_json(folder / "plan.json")
        verify_frozen_inputs(candidate_plan)
        if candidate_plan.get("source_plan_sha256") != plan["plan_sha256"]:
            raise ValueError(f"Stale retake source plan: {folder.name}")
        manual_review_path = folder / "manual-review.json"
        manual_review = read_json(manual_review_path) if manual_review_path.is_file() else {}
        if manual_review and (
            manual_review.get("schema") != 1
            or manual_review.get("decision") != "reviewed"
            or not str(manual_review.get("reviewed_by", "")).strip()
            or not str(manual_review.get("reviewed_at", "")).strip()
            or manual_review.get("plan_sha256") != candidate_plan["plan_sha256"]
            or manual_review.get("source_plan_sha256") != plan["plan_sha256"]
            or set(manual_review.get("decisions", {})) != set(candidate_plan["items"])
            or any(value not in {"accept", "retake"} for value in manual_review["decisions"].values())
            or set(manual_review.get("audio_sha256", {})) != set(candidate_plan["items"])
        ):
            raise ValueError(f"Invalid or stale manual retake review: {folder.name}")
        pronunciations = candidate_plan.get("user_approved_pronunciations", {})
        for audio_id, candidate in candidate_plan["items"].items():
            original = plan["items"][audio_id]
            override = pronunciations.get(audio_id)
            if any(candidate.get(key) != value for key, value in original.items()
                   if key not in {"voice_settings", "seed", "synthesis_text", "synthesis_text_sha256"}):
                raise ValueError(f"Retake changed script or casting: {audio_id}")
            if candidate.get("synthesis_text") != original["synthesis_text"]:
                if (
                    not isinstance(override, dict)
                    or override.get("canonical_text") != original["text"]
                    or override.get("synthesis_text") != candidate["synthesis_text"]
                    or candidate.get("text") != original["text"]
                    or candidate.get("synthesis_text_sha256") != text_sha(candidate["synthesis_text"])
                    or not str(override.get("spoken_as", "")).strip()
                ):
                    raise ValueError(f"Unapproved phonetic spelling change: {audio_id}")
            elif override and override.get("synthesis_text") != candidate["synthesis_text"]:
                raise ValueError(f"Retake pronunciation evidence does not match: {audio_id}")
            if not proven_generation(candidate, candidate_plan["plan_sha256"], folder):
                continue
            report_path = folder / "checks" / f"{audio_id}.json"
            if not report_path.is_file():
                continue
            report = read_json(report_path)
            if (
                report.get("plan_sha256") != candidate_plan["plan_sha256"]
                or report.get("source_plan_sha256") != plan["plan_sha256"]
                or report.get("expected") != original["text"]
                or report.get("wav_sha256") != file_sha(folder / "masters" / f"{audio_id}.wav")
            ):
                raise ValueError(f"Stale retake check: {audio_id}")
            report["plan_sha256"] = plan["plan_sha256"]
            if comparison_distance(original["text"], report["recognized"], checker):
                if manual_review.get("decisions", {}).get(audio_id) != "accept":
                    continue
            elif (
                manual_review.get("decisions", {}).get(audio_id) != "accept"
                and assess_transcript(report, checker) is not None
            ):
                continue
            if manual_review.get("decisions", {}).get(audio_id) == "accept":
                master_sha = file_sha(folder / "masters" / f"{audio_id}.wav")
                if manual_review["audio_sha256"].get(audio_id) != master_sha:
                    raise ValueError(f"Manual retake review is stale: {audio_id}")
            if manual_review.get("decisions", {}).get(audio_id) == "accept" or (
                assess_transcript(report, checker) is None and report.get("independent_asr")
            ):
                selected[audio_id] = (folder, candidate_plan["plan_sha256"])
    return selected


def transcribe_pauses(model, master, audio_id):
    import numpy as np
    import soundfile as sf
    samples, rate = sf.read(master, dtype="float32")
    width = round(rate * .02)
    squared = np.pad(samples ** 2, (0, (-len(samples)) % width))
    level = np.sqrt(squared.reshape(-1, width).mean(axis=1))
    voice = np.flatnonzero(level > .013)
    if not len(voice):
        return ""
    breaks = np.flatnonzero(np.diff(voice) >= 15) + 1
    phrases = np.split(voice, breaks)
    if len(phrases) < 2:
        return ""
    folder = PRODUCTION / "asr-phrases" / safe_id(audio_id)
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    recognized = []
    try:
        for index, phrase in enumerate(phrases):
            start = max(0, int(phrase[0]) * width - round(rate * .09))
            end = min(len(samples), (int(phrase[-1]) + 1) * width + round(rate * .09))
            chunk = np.pad(samples[start:end], (round(rate * .24), round(rate * .24)))
            path = folder / f"phrase-{index}.wav"
            sf.write(path, chunk, rate, "PCM_16")
            recognized.append(model.generate(
                str(path), language="en", temperature=0,
                condition_on_previous_text=False,
            ).text.strip())
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return " ".join(recognized)


def word_timings(segments):
    words = []
    for segment in segments or []:
        source = segment if isinstance(segment, dict) else vars(segment)
        for word in source.get("words") or []:
            item = word if isinstance(word, dict) else vars(word)
            token = re.sub(r"[^\w']+", "", str(item.get("word", "")).lower())
            if token:
                words.append({"word": token, "start": float(item["start"]), "end": float(item["end"])})
    return words


def create_saren_splice(source_path, source_sha, timings):
    import numpy as np
    import soundfile as sf
    alignment_path = PRODUCTION / "independent-asr/scribe-v3/recording.voicemail.json"
    if not alignment_path.is_file():
        raise ValueError("Saren splice requires independent source-word alignment")
    alignment = read_json(alignment_path)
    response = alignment.get("response", {})
    fields = alignment.get("request_fields", {})
    if (
        file_sha(source_path) != source_sha
        or alignment.get("audio_sha256") != source_sha
        or alignment.get("audio_id") != "recording.voicemail"
        or alignment.get("model_id") != "scribe_v3"
        or fields.get("model_id") != "scribe_v3"
        or fields.get("timestamps_granularity") != "word"
        or alignment.get("script_or_keyterm_prompt_sent") is not False
        or any(key in fields for key in ("keyterms", "transcript_edit", "prompt", "text"))
        or alignment.get("word_edits") != 0
        or response.get("text") != alignment.get("recognized")
    ):
        raise ValueError("Stale or unverified Saren source alignment")
    previous_timings = timings
    timings = word_timings([{"words": [
        {"word": entry["text"], "start": entry["start"], "end": entry["end"]}
        for entry in response.get("words", []) if entry.get("type") == "word"
    ]}])
    tokens = [entry["word"] for entry in timings]
    wanted = ["come", "out", "with", "us", "kiddo", "the", "bay", "is", "singing", "tonight"]
    if tokens != wanted or re.findall(r"\w+", response.get("text", "").lower()) != wanted:
        raise ValueError("Unexpected transcript in Saren source alignment")
    start = next((index for index in range(len(tokens) - len(wanted) + 1)
                  if tokens[index:index + len(wanted)] == wanted), None)
    if start is None:
        raise ValueError("Cannot prove the Helen voicemail word boundaries for the Saren splice")
    phrase = timings[start:start + 5]
    tonight = timings[start + 9]
    samples, rate = sf.read(source_path, dtype="float32")
    if samples.ndim != 1 or rate != 48000:
        raise ValueError("Saren splice source must be mono 48 kHz")
    previous_end = 0.0
    for entry in timings:
        if not previous_end <= entry["start"] < entry["end"] <= len(samples) / rate:
            raise ValueError("Invalid source-word alignment bounds for Saren splice")
        previous_end = entry["end"]
    pad = round(rate * .025)
    first = samples[max(0, round(phrase[0]["start"] * rate) - pad):
                    min(len(samples), round(phrase[-1]["end"] * rate) + pad)]
    final = samples[max(0, round(tonight["start"] * rate) - pad):
                    min(len(samples), round(tonight["end"] * rate) + pad)]
    gap = np.zeros(round(rate * DERIVED["recording.saren_splice"]["gap_seconds"]), dtype=np.float32)
    output = PRODUCTION / "masters/recording.saren_splice.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(output.name + f".partial-{uuid.uuid4().hex}.wav")
    sf.write(pending, np.concatenate((first, gap, final)), rate, "PCM_16")
    receipt_path = PRODUCTION / "edit-receipts/recording.saren_splice.json"
    if output.is_file() and file_sha(output) != file_sha(pending):
        previous_sha = file_sha(output)
        if not receipt_path.is_file() or read_json(receipt_path).get("output_sha256") != previous_sha:
            raise ValueError("Cannot preserve the previous Saren splice without its matching receipt")
        atomic_bytes(PRODUCTION / "masters/history" / f"{previous_sha}.wav", output.read_bytes())
        atomic_bytes(PRODUCTION / "edit-receipts/history" / f"{previous_sha}.json", receipt_path.read_bytes())
    os.replace(pending, output)
    receipt = {
        "schema": 1,
        "audio_id": "recording.saren_splice",
        "source_audio_id": "recording.voicemail",
        "source_sha256": source_sha,
        "alignment": {
            "file": alignment_path.relative_to(PRODUCTION).as_posix(),
            "sha256": file_sha(alignment_path),
            "model": alignment["model_id"],
        },
        "superseded_word_timings": previous_timings,
        "source_intervals": [
            [phrase[0]["start"], phrase[-1]["end"]],
            [tonight["start"], tonight["end"]],
        ],
        "gap_seconds": DERIVED["recording.saren_splice"]["gap_seconds"],
        "output_sha256": file_sha(output),
    }
    atomic_json(receipt_path, receipt)
    return output, receipt


def audio_facts(path):
    import numpy as np
    import soundfile as sf
    samples, rate = sf.read(path, dtype="float32")
    info = sf.info(path)
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) else 0.0
    seconds = len(samples) / rate
    if (
        samples.ndim != 1 or not np.isfinite(samples).all() or rate != 48000
        or info.subtype != "PCM_16" or not .005 < peak < 1
        or not .15 < seconds < 90
    ):
        raise ValueError(f"Invalid production WAV: {path.name}")
    return {"seconds": seconds, "sample_rate": rate, "peak": peak, "rms": rms}


def preserve_recorder_pcm(runtime):
    settings = runtime.with_name(runtime.name + ".import")
    resource = "res://" + runtime.relative_to(ROOT / "game").as_posix()
    if settings.exists():
        original = settings.read_text(encoding="utf-8")
        revised, count = re.subn(r"(?m)^compress/mode=\d+$", "compress/mode=0", original)
        if count != 1:
            raise ValueError("Cannot prove the greeting WAV import mode")
    else:
        suffix = hashlib.md5(resource.encode()).hexdigest()
        imported = f"res://.godot/imported/{runtime.name}-{suffix}.sample"
        revised = (
            f'[remap]\n\nimporter="wav"\ntype="AudioStreamWAV"\npath="{imported}"\n\n'
            f'[deps]\n\nsource_file="{resource}"\ndest_files=["{imported}"]\n\n'
            '[params]\n\ncompress/mode=0\n'
        )
    atomic_bytes(settings, revised.encode())


def write_manual_review_files(plan, checks, hard_holds, review_root=None):
    review_root = Path(review_root or PRODUCTION)
    entries = []
    for audio_id, reason in sorted(hard_holds.items()):
        item = plan["items"][audio_id]
        report = checks[audio_id]
        audio = PRODUCTION / report.get("master", f"masters/{audio_id}.wav")
        try:
            relative_audio = os.path.relpath(audio, review_root)
        except ValueError as error:
            raise ValueError(f"Cannot create local review link for {audio_id}") from error
        entries.append({
            "audio_id": audio_id,
            "reason": reason,
            "speaker": item["speaker"],
            "identity": item["cast_role"],
            "voice_id": item["voice_id"],
            "line_ids": item["line_ids"],
            "expected": item["text"],
            "recognized": report["recognized"],
            "word_edits": report["word_edits"],
            "wav": relative_audio,
            "check": f"checks/{audio_id}.json",
        })
    payload = {
        "schema": 1,
        "plan_sha256": plan["plan_sha256"],
        "casting_sha256": plan["inputs"]["casting"],
        "count": len(entries),
        "entries": entries,
    }
    atomic_json(review_root / "manual-review-required.json", payload)
    csv_path = review_root / "manual-review-required.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    pending = csv_path.with_name(csv_path.name + f".partial-{uuid.uuid4().hex}")
    with pending.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "audio_id", "reason", "speaker", "identity", "voice_id", "line_ids",
            "word_edits", "expected", "recognized", "wav", "check",
        ])
        for entry in entries:
            writer.writerow([
                entry["audio_id"], entry["reason"], entry["speaker"], entry["identity"],
                entry["voice_id"], " ".join(entry["line_ids"]), entry["word_edits"],
                entry["expected"], entry["recognized"], entry["wav"], entry["check"],
            ])
    os.chmod(pending, 0o644)
    os.replace(pending, csv_path)
    cards = []
    for entry in entries:
        cards.append(
            '<section><h2><code>{}</code></h2><p><strong>{}</strong> · {} · edits {}</p>'
            '<audio controls preload="none" src="{}"></audio>'
            '<p><b>Expected:</b> {}</p><p><b>ASR:</b> {}</p></section>'.format(
                html.escape(entry["audio_id"]), html.escape(entry["reason"]),
                html.escape(entry["speaker"]), entry["word_edits"],
                html.escape(entry["wav"]), html.escape(entry["expected"]),
                html.escape(entry["recognized"]),
            )
        )
    heading = "Night Nine: required voice review" if entries else "Night Nine: voice review status"
    message = (
        f"Review only these {len(entries)} held takes. This page does not approve anything."
        if entries else "No listening review is pending. Decisions are recorded in the final voice review receipt."
    )
    page = """<!doctype html><meta charset="utf-8"><title>Night Nine voice review</title>
<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;background:#151719;color:#eee}
section{border:1px solid #555;border-radius:8px;padding:1rem;margin:1rem 0}audio{width:100%%}
code{color:#d8ba7d}b{color:#a9d6ce}</style>
<h1>%s</h1>
<p><strong>Story spoilers below.</strong> Listen before judging transcript differences.</p>
<p>Plan <code>%s</code>. %s</p>
%s""" % (
        html.escape(heading), html.escape(plan["plan_sha256"]),
        html.escape(message), "\n".join(cards),
    )
    atomic_bytes(review_root / "manual-review.html", page.encode())


def validate_and_stage(plan):
    verify_frozen_inputs(plan)
    previous_overlay = read_json(OVERLAY_PATH) if OVERLAY_PATH.is_file() else {}
    missing = [audio_id for audio_id, item in plan["items"].items()
               if item["kind"] == "speech" and not proven_generation(item, plan["plan_sha256"])]
    if missing:
        raise ValueError(f"Generation is incomplete: {len(missing)} speech requests remain")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from mlx_audio.stt import load
    checker = runpy.run_path(str(ROOT / "tools/check-voice-candidates.py"))
    lips = runpy.run_path(str(ROOT / "tools/generate-lipsync.py"))
    model = load(str(ROOT / ".tools/models/whisper-qa"))
    retakes = verified_retakes(plan, checker)
    checks = {}
    hard_holds = {}
    automated = []
    masters = {}
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        if item["kind"] != "speech":
            continue
        folder, generation_plan_sha = retakes.get(audio_id, (PRODUCTION, plan["plan_sha256"]))
        master = decode_mp3(audio_id, folder)
        facts = audio_facts(master)
        wav_sha = file_sha(master)
        check_path = PRODUCTION / "checks" / f"{audio_id}.json"
        cached = read_json(check_path) if check_path.is_file() else {}
        if folder != PRODUCTION and cached.get("wav_sha256") != wav_sha:
            cached = read_json(folder / "checks" / f"{audio_id}.json")
            cached["plan_sha256"] = plan["plan_sha256"]
        if (
            cached.get("audio_id") == audio_id
            and cached.get("plan_sha256") == plan["plan_sha256"]
            and cached.get("wav_sha256") == wav_sha
            and cached.get("expected") == item["text"]
            and (audio_id != "recording.voicemail" or cached.get("word_timings"))
        ):
            report = cached
            recognized = report.get("local_recognized", report["recognized"])
        else:
            result = model.generate(
                str(master), language="en", temperature=0, condition_on_previous_text=False,
                word_timestamps=(audio_id == "recording.voicemail"),
            )
            recognized = result.text.strip()
            report = {
                "audio_id": audio_id,
                "plan_sha256": plan["plan_sha256"],
                "wav_sha256": wav_sha,
                "expected": item["text"],
                "listening_review_required": True,
                **facts,
            }
            if audio_id == "recording.voicemail":
                report["word_timings"] = word_timings(result.segments)
        expected_words, recognized_words = comparison_words(item["text"], recognized, checker)
        first_recognition = report.get("first_recognition", recognized)
        edits = checker["distance"](expected_words, recognized_words)
        recognition_pass = report.get("recognition_pass", "independent")
        if edits and report.get("asr_revision") != 2:
            vocabularies = (
                "Character and place names in this recording may include Nora, Bellwether, "
                "Biscuit, Stephen, Pell, Dale, K7BLW, Gus, Calder, Veyr, Saren, Rook, "
                "Iris, Evelyn, June, Cal, or Helen.",
                "Night Nine. Steve Mercer, Stephen, Nora Reyes, Iris, Helen, Frank, Agnes Penhallow, "
                "June Calder, Evelyn Shaw, Mateo, Rafa, La Marea, Rook, Saren, Wick, Veyr, Tirel, "
                "Bellwether, K7BLW. Sound engineering terms: all-call, cue number, re-sync.",
                "Names of places in this story: Bellwether Bay, Veyr, Sentinel Point, Tirel, La Marea.",
            )
            for index, vocabulary in enumerate(vocabularies, 1):
                alternate = model.generate(
                    str(master), language="en", temperature=0,
                    condition_on_previous_text=False, initial_prompt=vocabulary,
                ).text.strip()
                alternate_expected, alternate_words = comparison_words(
                    item["text"], alternate, checker,
                )
                alternate_edits = checker["distance"](alternate_expected, alternate_words)
                if alternate_edits < edits:
                    recognized, edits = alternate, alternate_edits
                    recognition_pass = f"story_vocabulary_{index}"
                if edits == 0:
                    break
        segmented = report.get("independent_phrase_transcription", "")
        if edits and report.get("asr_revision") != 2:
            segmented = transcribe_pauses(model, master, audio_id)
            segmented_expected, segmented_words = comparison_words(
                item["text"], segmented, checker,
            ) if segmented else (expected_words, [])
            segmented_edits = checker["distance"](
                segmented_expected, segmented_words,
            ) if segmented else edits
            if segmented and segmented_edits < edits:
                recognized, edits = segmented, segmented_edits
                recognition_pass = "independent_phrases"
        report.update({
            "recognized": recognized,
            "first_recognition": first_recognition,
            "recognition_pass": recognition_pass,
            "word_edits": edits,
            "word_error_rate": edits / max(1, len(expected_words)),
            "asr_revision": 2,
            "transcript_comparison": "strict normalized English spoken forms",
            "local_recognized": recognized,
        })
        if folder != PRODUCTION:
            report["generation_plan_sha256"] = generation_plan_sha
            report["master"] = master.relative_to(PRODUCTION).as_posix()
        else:
            report.pop("generation_plan_sha256", None)
            report.pop("master", None)
        if segmented:
            report["independent_phrase_transcription"] = segmented
        hold = assess_transcript(report, checker)
        atomic_json(PRODUCTION / "checks" / f"{audio_id}.json", report)
        checks[audio_id] = report
        masters[audio_id] = master
        if hold:
            hard_holds[audio_id] = hold
        else:
            automated.append(audio_id)
    source = checks["recording.voicemail"]
    try:
        splice, edit_receipt = create_saren_splice(
            masters["recording.voicemail"], source["wav_sha256"], source.get("word_timings", []),
        )
    except Exception as error:
        atomic_json(PRODUCTION / "validation-blockers.json", {
            "plan_sha256": plan["plan_sha256"],
            "casting_sha256": plan["inputs"]["casting"],
            "hard_holds": {"recording.saren_splice": "uncertain_source_or_word_boundaries"},
            "detail": str(error),
        })
        raise
    splice_item = plan["items"]["recording.saren_splice"]
    splice_result = model.generate(
        str(splice), language="en", temperature=0, condition_on_previous_text=False,
    )
    splice_expected, splice_words_heard = comparison_words(
        splice_item["text"], splice_result.text.strip(), checker,
    )
    splice_edits = checker["distance"](splice_expected, splice_words_heard)
    splice_report = {
        "audio_id": "recording.saren_splice",
        "plan_sha256": plan["plan_sha256"],
        "wav_sha256": file_sha(splice),
        "expected": splice_item["text"],
        "recognized": splice_result.text.strip(),
        "word_edits": splice_edits,
        "word_error_rate": splice_edits / max(1, len(transcript_words(splice_item["text"], checker))),
        "listening_review_required": True,
        "edit_receipt": "assets/audio/elevenlabs-v4-script-v2/edit-receipts/recording.saren_splice.json",
        **audio_facts(splice),
    }
    splice_hold = assess_transcript(splice_report, checker)
    atomic_json(PRODUCTION / "checks/recording.saren_splice.json", splice_report)
    checks["recording.saren_splice"] = splice_report
    masters["recording.saren_splice"] = splice
    if splice_hold:
        hard_holds["recording.saren_splice"] = splice_hold
    else:
        automated.append("recording.saren_splice")
    takes = {}
    timing = {}
    generator_hash = file_sha(lips["BINARY"])
    generator_version = subprocess.check_output([str(lips["BINARY"]), "--version"], text=True).strip()
    script_data = read_json(SCRIPT)
    evidence_audio_ids = {
        sound
        for scene in script_data.get("scenes", [])
        for task in scene.get("tasks", [])
        if task.get("evidence_labels") or task.get("audition_labels")
        for sound in task.get("sounds", [])
        if not sound.startswith("effect.")
    }
    fallback_manifest = read_json(ROOT / "tools/script_v2/base/voice-manifest.json")
    for audio_id in evidence_audio_ids | {"recording.greeting"}:
        fallback = fallback_manifest.get("takes", {}).get(audio_id, {}).get("fallback", {})
        fallback_file = str(fallback.get("file", ""))
        if fallback_file:
            fallback_path = ROOT / "game" / fallback_file.removeprefix("res://")
            if fallback_path.is_file():
                preserve_recorder_pcm(fallback_path)
    cue_jobs = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for audio_id in plan["ordered_audio_ids"]:
            item = plan["items"][audio_id]
            report = checks[audio_id]
            master = masters[audio_id]
            runtime = ROOT / "game/assets/audio/voices/elevenlabs-v4-script-v2" / f"{audio_id}.wav"
            runtime.parent.mkdir(parents=True, exist_ok=True)
            atomic_bytes(runtime, master.read_bytes())
            if audio_id == "recording.greeting" or audio_id in evidence_audio_ids:
                preserve_recorder_pcm(runtime)
            folder, generation_plan_sha = retakes.get(audio_id, (PRODUCTION, plan["plan_sha256"]))
            receipt = read_json(folder / "receipts" / f"{audio_id}.json") if item["kind"] == "speech" else {}
            revision = "elevenlabs-v4-script-v2"
            if item["kind"] == "derived" or audio_id in retakes:
                revision += "-" + file_sha(runtime)[:12]
            take = {
                "id": audio_id,
                "speaker": item["speaker"],
                "identity": item["cast_role"],
                "text": item["text"],
                "spoken_text": item["text"],
                "file": "res://" + runtime.relative_to(ROOT / "game").as_posix(),
                "sha256": file_sha(runtime),
                **{key: report[key] for key in ("seconds", "sample_rate", "peak", "rms")},
                "model": MODEL,
                "provider": "ElevenLabs API",
                "voice_id": item["voice_id"],
                "request_id": receipt.get("request_id"),
                "source_request_id": receipt.get("request_id") if item["kind"] == "derived" else None,
                "status": "manual_review_required" if audio_id in hard_holds else "automated_qa_passed",
                "listening_reviewed": False,
                "asr_report": f"assets/audio/elevenlabs-v4-script-v2/checks/{audio_id}.json",
                "word_error_rate": report["word_error_rate"],
                "lip_sync_revision": revision,
                "text_hash": text_sha(item["text"])[:16],
                "plan_sha256": plan["plan_sha256"],
            }
            if folder != PRODUCTION:
                take["generation_plan_sha256"] = generation_plan_sha
            if item["kind"] == "derived":
                take["derived_from"] = edit_receipt
                take["source_request_id"] = read_json(
                    PRODUCTION / "receipts/recording.voicemail.json"
                )["request_id"]
            takes[audio_id] = take
            cue_jobs[pool.submit(
                lips["generate_cues"], audio_id, take,
                ROOT / "assets/audio" / ("lipsync-" + revision),
                generator_hash, generator_version,
            )] = audio_id
        for future in as_completed(cue_jobs):
            audio_id = cue_jobs[future]
            cue = future.result()
            timing[audio_id] = {key: cue[key] for key in (
                "audio_sha256", "seconds", "cues", "visual_timing_reviewed",
            )}
    campaign_set = {audio_id for audio_id, item in plan["items"].items()
                    if not item["line_ids"][0].startswith("book.")}
    narration_set = set(plan["items"]) - campaign_set
    def existing_order(section, required):
        previous = previous_overlay.get(section, {}).get("takes", {})
        return ([key for key in previous if key in required]
                + [key for key in plan["ordered_audio_ids"] if key in required and key not in previous])
    campaign_ids = existing_order("campaign", campaign_set)
    narration_ids = existing_order("narration", narration_set)
    overlay = {
        "schema": 1,
        "model": MODEL,
        "plan_sha256": plan["plan_sha256"],
        "casting_sha256": plan["inputs"]["casting"],
        "quality_approved": False,
        "campaign": {"takes": {key: takes[key] for key in campaign_ids}},
        "narration": {"takes": {key: takes[key] for key in narration_ids}},
        "lipsync": {
            "generator": generator_version,
            "source": "https://github.com/DanielSWolf/rhubarb-lip-sync",
            "takes": {key: timing[key] for key in campaign_ids},
        },
        "review": {
            "hard_holds": {key: hard_holds[key] for key in sorted(hard_holds)},
            "automated_qa_passed": sorted(automated),
            "automated_qa_count": len(automated),
            "manual_review_required_count": len(hard_holds),
            "activation_ready": not hard_holds and len(automated) == len(plan["items"]),
        },
    }
    atomic_json(OVERLAY_PATH, overlay)
    write_manual_review_files(plan, checks, hard_holds)
    return overlay


def apply_manual_review(overlay, review, receipt_ref, reviewer_root=ROOT):
    all_takes = overlay["campaign"]["takes"] | overlay["narration"]["takes"]
    holds = overlay.get("review", {}).get("hard_holds", {})
    decisions = review.get("decisions")
    if not isinstance(decisions, dict):
        reviewed = set(review.get("reviewed_audio_ids", []))
        decisions = {audio_id: "accept" for audio_id in reviewed}
    if (
        review.get("decision") not in {"accepted", "reviewed"}
        or not str(review.get("reviewed_by", "")).strip()
        or not str(review.get("reviewed_at", "")).strip()
        or set(decisions) != set(holds)
        or any(value not in {"accept", "retake"} for value in decisions.values())
        or set(decisions) - set(all_takes)
    ):
        raise ValueError("Manual review receipt must truthfully decide every held take")
    accepted = {audio_id for audio_id, decision in decisions.items() if decision == "accept"}
    retakes = {audio_id for audio_id, decision in decisions.items() if decision == "retake"}
    for audio_id in accepted:
        all_takes[audio_id]["listening_reviewed"] = True
        all_takes[audio_id]["status"] = "manual_review_passed"
    for audio_id in retakes:
        all_takes[audio_id]["listening_reviewed"] = True
        all_takes[audio_id]["status"] = "retake_requested"
    overlay["review"]["resolved_holds"] = {
        **overlay["review"].get("resolved_holds", {}),
        **{audio_id: holds[audio_id] for audio_id in accepted},
    }
    overlay["review"]["hard_holds"] = {
        audio_id: holds[audio_id] for audio_id in sorted(retakes)
    }
    receipts = overlay["review"].get("manual_review_receipts", [])
    receipt_ref = str(Path(receipt_ref).resolve().relative_to(Path(reviewer_root).resolve()))
    if receipt_ref not in receipts:
        receipts.append(receipt_ref)
    overlay["review"]["manual_review_receipts"] = receipts
    overlay["review"]["retake_requests"] = {
        **overlay["review"].get("retake_requests", {}),
        **{audio_id: review.get("retake_notes", {}).get(audio_id, "") for audio_id in sorted(retakes)},
    }
    overlay["review"]["reviewed_by"] = review["reviewed_by"]
    overlay["review"]["reviewed_at"] = review["reviewed_at"]
    invalid = {
        audio_id: take.get("status")
        for audio_id, take in all_takes.items()
        if take.get("status") not in {"automated_qa_passed", "manual_review_passed"}
        and not (take.get("status") == "retake_requested" and audio_id in retakes)
    }
    if invalid:
        raise ValueError(f"Voice overlay still has invalid takes: {invalid}")
    ready = not overlay.get("review", {}).get("hard_holds") and all(
        take.get("status") in {"automated_qa_passed", "manual_review_passed"}
        for take in all_takes.values()
    )
    overlay["review"]["activation_ready"] = ready
    overlay["quality_approved"] = ready
    return overlay


def activate_overlay(plan, review_path=None):
    verify_frozen_inputs(plan)
    overlay = read_json(OVERLAY_PATH)
    if (
        overlay.get("plan_sha256") != plan["plan_sha256"]
        or overlay.get("casting_sha256") != plan["inputs"]["casting"]
    ):
        raise ValueError("Staged overlay is stale")
    all_takes = overlay["campaign"]["takes"] | overlay["narration"]["takes"]
    if set(all_takes) != set(plan["items"]):
        raise ValueError("Staged overlay is incomplete")
    holds = overlay.get("review", {}).get("hard_holds", {})
    if holds and review_path is None:
        raise ValueError("Actual review is required for held takes")
    if review_path is not None:
        review = read_json(review_path)
        if (
            review.get("plan_sha256") != plan["plan_sha256"]
            or review.get("casting_sha256") != plan["inputs"]["casting"]
        ):
            raise ValueError("Manual review receipt is stale")
        overlay = apply_manual_review(overlay, review, review_path)
    elif not holds:
        all_takes = overlay["campaign"]["takes"] | overlay["narration"]["takes"]
        invalid = {
            audio_id: take.get("status")
            for audio_id, take in all_takes.items()
            if take.get("status") not in {"automated_qa_passed", "manual_review_passed"}
        }
        if invalid:
            raise ValueError(f"Voice overlay still has invalid takes: {invalid}")
        overlay["review"]["activation_ready"] = True
        overlay["quality_approved"] = True
    atomic_json(OVERLAY_PATH, overlay)
    return overlay


def command_plan(_args):
    plan = build_plan()
    atomic_json(PLAN_PATH, plan)
    print(json.dumps({
        "plan_sha256": plan["plan_sha256"],
        "rows": plan["rows"],
        "unique_audio_ids": plan["unique_audio_ids"],
        "speech_requests": plan["speech_requests"],
        "derived_edits": plan["derived_edits"],
        "utterance_characters": plan["utterance_characters"],
        "request_characters": plan["request_characters"],
    }, indent=2))


def command_preflight(_args):
    plan = read_json(PLAN_PATH)
    result = collect_preflight(plan, ApiClient())
    atomic_json(PREFLIGHT_PATH, result)
    print(json.dumps(result["subscription"], indent=2))


def command_add_voices(args):
    plan = read_json(PLAN_PATH)
    require_gate(plan, args.plan_sha256)
    if not args.allow_account_write:
        raise ValueError("--allow-account-write is required")
    result = add_voices(plan, read_json(PREFLIGHT_PATH), ApiClient())
    print(json.dumps({"voice_actions": result}, indent=2))


def command_generate(args):
    plan = read_json(PLAN_PATH)
    require_gate(plan, args.plan_sha256)
    if not args.allow_billed_generation:
        raise ValueError("--allow-billed-generation is required")
    result = generate(plan, read_json(PREFLIGHT_PATH), ApiClient(), args.limit)
    print(json.dumps({"generated": len(result), "audio_ids": result}, indent=2))


def command_validate(_args):
    overlay = validate_and_stage(read_json(PLAN_PATH))
    print(json.dumps(overlay["review"], indent=2))


def command_activate(args):
    plan = read_json(PLAN_PATH)
    require_gate(plan, args.plan_sha256)
    overlay = activate_overlay(plan, args.review_receipt)
    print(json.dumps({"quality_approved": overlay["quality_approved"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan").set_defaults(function=command_plan)
    sub.add_parser("preflight").set_defaults(function=command_preflight)
    add = sub.add_parser("add-voices")
    add.add_argument("--plan-sha256", required=True)
    add.add_argument("--allow-account-write", action="store_true")
    add.set_defaults(function=command_add_voices)
    generation = sub.add_parser("generate")
    generation.add_argument("--plan-sha256", required=True)
    generation.add_argument("--allow-billed-generation", action="store_true")
    generation.add_argument("--limit", type=int)
    generation.set_defaults(function=command_generate)
    sub.add_parser("validate-stage").set_defaults(function=command_validate)
    activate = sub.add_parser("activate")
    activate.add_argument("--plan-sha256", required=True)
    activate.add_argument("--review-receipt", type=Path)
    activate.set_defaults(function=command_activate)
    args = parser.parse_args()
    try:
        args.function(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

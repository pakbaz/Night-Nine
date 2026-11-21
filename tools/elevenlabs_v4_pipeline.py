#!/usr/bin/env python3
"""Plan, preflight, record, validate, and stage Night Nine's ElevenLabs v4 cast.

The default commands are read-only or offline. Account writes and billed speech
generation require explicit flags and the exact frozen plan hash.
"""
import argparse
import copy
import csv
import hashlib
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
            "tier": subscription["tier"],
            "status": subscription["status"],
            "character_count": subscription["character_count"],
            "character_limit": subscription["character_limit"],
            "available_credits": available,
            "estimated_credits": weighted,
            "overage_allowed": False,
            "voice_slots_used": subscription["voice_slots_used"],
            "voice_limit": subscription["voice_limit"],
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


def receipt_paths(audio_id):
    safe_id(audio_id)
    return (
        PRODUCTION / "downloads" / f"{audio_id}.mp3",
        PRODUCTION / "receipts" / f"{audio_id}.json",
    )


def proven_generation(item, plan_sha):
    audio, receipt = receipt_paths(item["audio_id"])
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


def decode_mp3(audio_id):
    source, _ = receipt_paths(audio_id)
    target = PRODUCTION / "masters" / f"{audio_id}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(target.name + f".partial-{uuid.uuid4().hex}.wav")
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(source),
        "-map", "0:a:0", "-map_metadata", "-1", "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(pending),
    ], check=True)
    os.replace(pending, target)
    return target


def transcript_words(text, checker):
    return checker["words"](text.replace("space-fold", "spacefold"))


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
    tokens = [entry["word"] for entry in timings]
    wanted = ["come", "out", "with", "us", "kiddo", "the", "bay", "is", "singing", "tonight"]
    start = next((index for index in range(len(tokens) - len(wanted) + 1)
                  if tokens[index:index + len(wanted)] == wanted), None)
    if start is None:
        raise ValueError("Cannot prove the Helen voicemail word boundaries for the Saren splice")
    phrase = timings[start:start + 5]
    tonight = timings[start + 9]
    samples, rate = sf.read(source_path, dtype="float32")
    if samples.ndim != 1 or rate != 48000:
        raise ValueError("Saren splice source must be mono 48 kHz")
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
    os.replace(pending, output)
    receipt = {
        "schema": 1,
        "audio_id": "recording.saren_splice",
        "source_audio_id": "recording.voicemail",
        "source_sha256": source_sha,
        "source_intervals": [
            [phrase[0]["start"], phrase[-1]["end"]],
            [tonight["start"], tonight["end"]],
        ],
        "gap_seconds": DERIVED["recording.saren_splice"]["gap_seconds"],
        "output_sha256": file_sha(output),
    }
    atomic_json(PRODUCTION / "edit-receipts/recording.saren_splice.json", receipt)
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


def validate_and_stage(plan):
    verify_frozen_inputs(plan)
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
    checks = {}
    hard_holds = {}
    automated = []
    masters = {}
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        if item["kind"] != "speech":
            continue
        master = decode_mp3(audio_id)
        result = model.generate(
            str(master), language="en", temperature=0, condition_on_previous_text=False,
            word_timestamps=(audio_id == "recording.voicemail"),
        )
        recognized = result.text.strip()
        edits = checker["distance"](
            transcript_words(item["text"], checker), transcript_words(recognized, checker),
        )
        facts = audio_facts(master)
        report = {
            "audio_id": audio_id,
            "plan_sha256": plan["plan_sha256"],
            "wav_sha256": file_sha(master),
            "expected": item["text"],
            "recognized": recognized,
            "word_edits": edits,
            "word_error_rate": edits / max(1, len(transcript_words(item["text"], checker))),
            "listening_review_required": True,
            **facts,
        }
        if audio_id == "recording.voicemail":
            report["word_timings"] = word_timings(result.segments)
        atomic_json(PRODUCTION / "checks" / f"{audio_id}.json", report)
        checks[audio_id] = report
        masters[audio_id] = master
        word_count = len(transcript_words(item["text"], checker))
        if edits:
            hard_holds[audio_id] = "asr_mismatch"
        elif word_count <= 4:
            hard_holds[audio_id] = "short_asr_ambiguity"
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
    splice_edits = checker["distance"](
        transcript_words(splice_item["text"], checker),
        transcript_words(splice_result.text.strip(), checker),
    )
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
    atomic_json(PRODUCTION / "checks/recording.saren_splice.json", splice_report)
    checks["recording.saren_splice"] = splice_report
    masters["recording.saren_splice"] = splice
    splice_words = len(transcript_words(splice_item["text"], checker))
    if splice_edits:
        hard_holds["recording.saren_splice"] = "asr_mismatch"
    elif splice_words <= 4:
        hard_holds["recording.saren_splice"] = "short_asr_ambiguity"
    else:
        automated.append("recording.saren_splice")
    takes = {}
    timing = {}
    generator_hash = file_sha(lips["BINARY"])
    generator_version = subprocess.check_output([str(lips["BINARY"]), "--version"], text=True).strip()
    for audio_id in plan["ordered_audio_ids"]:
        item = plan["items"][audio_id]
        report = checks[audio_id]
        master = masters[audio_id]
        runtime = ROOT / "game/assets/audio/voices/elevenlabs-v4-script-v2" / f"{audio_id}.wav"
        runtime.parent.mkdir(parents=True, exist_ok=True)
        atomic_bytes(runtime, master.read_bytes())
        if audio_id == "recording.greeting":
            preserve_recorder_pcm(runtime)
        receipt = read_json(PRODUCTION / "receipts" / f"{audio_id}.json") if item["kind"] == "speech" else {}
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
            "lip_sync_revision": "elevenlabs-v4-script-v2",
            "text_hash": text_sha(item["text"])[:16],
            "plan_sha256": plan["plan_sha256"],
        }
        if item["kind"] == "derived":
            take["derived_from"] = edit_receipt
            take["source_request_id"] = read_json(
                PRODUCTION / "receipts/recording.voicemail.json"
            )["request_id"]
        takes[audio_id] = take
        cue = lips["generate_cues"](
            audio_id, take, ROOT / "assets/audio/lipsync-elevenlabs-v4-script-v2",
            generator_hash, generator_version,
        )
        timing[audio_id] = {key: cue[key] for key in (
            "audio_sha256", "seconds", "cues", "visual_timing_reviewed",
        )}
    campaign_ids = {audio_id for audio_id, item in plan["items"].items()
                    if not item["line_ids"][0].startswith("book.")}
    narration_ids = set(plan["items"]) - campaign_ids
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
    if holds:
        if review_path is None:
            raise ValueError("Actual review is required for held takes")
        review = read_json(review_path)
        reviewed = set(review.get("reviewed_audio_ids", []))
        if (
            review.get("plan_sha256") != plan["plan_sha256"]
            or review.get("casting_sha256") != plan["inputs"]["casting"]
            or review.get("decision") != "accepted"
            or not str(review.get("reviewed_by", "")).strip()
            or not str(review.get("reviewed_at", "")).strip()
            or reviewed != set(holds)
        ):
            raise ValueError("Manual review receipt must truthfully cover every held take")
        for audio_id in reviewed:
            all_takes[audio_id]["listening_reviewed"] = True
            all_takes[audio_id]["status"] = "manual_review_passed"
        overlay["review"]["resolved_holds"] = holds
        overlay["review"]["hard_holds"] = {}
        overlay["review"]["manual_review_receipt"] = str(Path(review_path).relative_to(ROOT))
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

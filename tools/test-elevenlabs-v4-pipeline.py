#!/usr/bin/env python3
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp/qa/elevenlabs-v4-pipeline-tests"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pipeline = load_module("elevenlabs_v4_pipeline", ROOT / "tools/elevenlabs_v4_pipeline.py")
overlay = load_module("script_v2_voice_overlay", ROOT / "tools/script_v2_voice_overlay.py")


class FakeApi:
    def __init__(self):
        self.posts = 0

    def get_json(self, path, params=None):
        if path == "/v1/user/subscription":
            return {
                "character_limit": 1000, "character_count": 0,
                "allowed_to_extend_character_limit": False,
                "can_extend_character_limit": False,
                "max_character_limit_extension": 0,
                "max_credit_limit_extension": 0,
                "current_overage": {"amount": "0"},
            }
        if path == "/v1/voices":
            return {"voices": [{"voice_id": "voice-one"}]}
        raise AssertionError(path)

    def post_audio(self, path, body, params=None):
        self.posts += 1
        return b"mock-mp3", {
            "request-id": f"request-{self.posts}",
            "x-trace-id": f"trace-{self.posts}",
            "character-cost": str(len(body["text"])),
        }


class PipelineTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        SCRATCH.mkdir(parents=True)
        self.csv_path = SCRATCH / "recording-list.csv"
        self.script_path = SCRATCH / "script.json"
        self.cast_path = SCRATCH / "casting.json"
        self.script_path.write_text("{}\n")
        self.cast_path.write_text(json.dumps({
            "roles": {
                "steve": {
                    "voice_id": "voice-one",
                    "library_name": "Voice One",
                    "source": "ElevenLabs premade voice",
                }
            }
        }) + "\n")
        fields = [
            "order", "line_id", "scene", "speaker_key", "shown_as", "voice", "voice_id",
            "delivery", "direction", "text", "status", "characters", "audio_key", "plan",
        ]
        with self.csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for order, line_id, plan in ((1, "scene.a", "record"), (2, "scene.b", "record")):
                writer.writerow({
                    "order": order, "line_id": line_id, "scene": "scene",
                    "speaker_key": "steve", "shown_as": "Steve", "voice": "Voice One",
                    "voice_id": "voice-one", "delivery": "live", "direction": "",
                    "text": "One proven take.", "status": "kept", "characters": 16,
                    "audio_key": "shared.take", "plan": plan,
                })

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def globals(self):
        return (
            patch.object(pipeline, "PRODUCTION", SCRATCH / "production"),
            patch.object(pipeline, "RECORDING_LIST", self.csv_path),
            patch.object(pipeline, "SCRIPT", self.script_path),
            patch.object(pipeline, "CASTING", self.cast_path),
        )

    def test_single_take_reuse_and_stale_input_refusal(self):
        plan = pipeline.build_plan(self.csv_path, self.script_path, self.cast_path)
        self.assertEqual(plan["rows"], 2)
        self.assertEqual(plan["unique_audio_ids"], 1)
        self.assertEqual(plan["speech_requests"], 1)
        patches = self.globals()
        with patches[0], patches[1], patches[2], patches[3]:
            self.assertTrue(pipeline.verify_frozen_inputs(plan))
            self.script_path.write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError, "stale"):
                pipeline.verify_frozen_inputs(plan)

    def test_resume_skips_only_proven_same_take(self):
        plan = pipeline.build_plan(self.csv_path, self.script_path, self.cast_path)
        preflight = {
            "plan_sha256": plan["plan_sha256"],
            "voices": {"voice-one": {"rate": 1}},
        }
        preflight["preflight_sha256"] = pipeline.canonical_sha(preflight)
        api = FakeApi()
        patches = self.globals()
        with patches[0], patches[1], patches[2], patches[3]:
            first = pipeline.generate(plan, preflight, api)
            second = pipeline.generate(plan, preflight, api)
        self.assertEqual(first, ["shared.take"])
        self.assertEqual(second, [])
        self.assertEqual(api.posts, 1)

    def test_quota_and_paid_overage_are_refused(self):
        base = {
            "character_limit": 100, "character_count": 90,
            "allowed_to_extend_character_limit": False,
            "can_extend_character_limit": False,
            "max_character_limit_extension": 0,
            "max_credit_limit_extension": 0,
            "current_overage": {"amount": "0"},
        }
        with self.assertRaisesRegex(ValueError, "Quota refusal"):
            pipeline.subscription_guard(base, 11)
        enabled = dict(base)
        enabled["character_count"] = 0
        enabled["allowed_to_extend_character_limit"] = True
        with self.assertRaisesRegex(ValueError, "Paid overage"):
            pipeline.subscription_guard(enabled, 1)

    def test_manifest_integrity_checks_audio_text_and_timing(self):
        root = SCRATCH / "root"
        casting_path = root / "docs/voice-casting-2026-11-20.json"
        casting_path.parent.mkdir(parents=True)
        casting_path.write_text(json.dumps({
            "roles": {"steve": {"voice_id": "voice-one"}}
        }) + "\n")
        campaign_audio = root / "game/assets/audio/voices/line.wav"
        book_audio = root / "game/assets/audio/voices/book.wav"
        campaign_audio.parent.mkdir(parents=True)
        campaign_audio.write_bytes(b"campaign")
        book_audio.write_bytes(b"book")
        campaign = {"lines": {
            "line.1": {"audio": "line.take", "text": "Line text.", "speaker": "steve"}
        }}
        storybook = {"books": {"opening": {"panels": [{"lines": [{"text": "Book text.", "seconds": 1.0}]}]}}}
        campaign_take = {
            "id": "line.take", "text": "Line text.", "text_hash": hashlib.sha256(b"Line text.").hexdigest()[:16],
            "file": "res://assets/audio/voices/line.wav", "sha256": pipeline.file_sha(campaign_audio),
            "seconds": 1.0, "status": "automated_qa_passed", "speaker": "steve",
            "identity": "steve", "voice_id": "voice-one", "model": "eleven_v4",
            "plan_sha256": "plan-one",
        }
        book_take = {
            "id": "book.opening.1.1", "text": "Book text.",
            "text_hash": hashlib.sha256(b"Book text.").hexdigest()[:16],
            "file": "res://assets/audio/voices/book.wav", "sha256": pipeline.file_sha(book_audio),
            "seconds": 1.0, "status": "automated_qa_passed", "speaker": "steve",
            "identity": "steve", "voice_id": "voice-one", "model": "eleven_v4",
            "plan_sha256": "plan-one",
        }
        voice_overlay = {
            "schema": 1, "model": "eleven_v4", "quality_approved": True,
            "plan_sha256": "plan-one", "casting_sha256": pipeline.file_sha(casting_path),
            "campaign": {"takes": {"line.take": campaign_take}},
            "narration": {"takes": {"book.opening.1.1": book_take}},
            "lipsync": {
                "generator": "test", "source": "test",
                "takes": {"line.take": {
                    "audio_sha256": campaign_take["sha256"], "seconds": 1.0,
                    "cues": [{"start": 0.0, "end": 1.0, "value": "X"}],
                    "visual_timing_reviewed": False,
                }},
            },
            "review": {"hard_holds": {}},
        }
        merged = overlay.merge_overlay(
            campaign, storybook, {"takes": {}}, {"takes": {}}, {}, voice_overlay, root,
        )
        self.assertTrue(merged[0]["enabled"])
        self.assertEqual(
            merged[2]["books"]["opening"]["panels"][0]["lines"][0]["narration"],
            book_take["file"],
        )
        campaign_audio.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            overlay.merge_overlay(
                campaign, storybook, {"takes": {}}, {"takes": {}}, {}, voice_overlay, root,
            )

    def test_changed_cast_is_rejected_even_when_text_is_unchanged(self):
        root = SCRATCH / "cast-root"
        casting_path = root / "docs/voice-casting-2026-11-20.json"
        casting_path.parent.mkdir(parents=True)
        casting_path.write_text(json.dumps({
            "roles": {"nora": {"voice_id": "old-voice"}}
        }) + "\n")
        audio = root / "game/assets/audio/voices/greeting.wav"
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b"same audio")
        text = "Good morning, sleepyhead."
        take = {
            "id": "recording.greeting", "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            "file": "res://assets/audio/voices/greeting.wav", "sha256": pipeline.file_sha(audio),
            "seconds": 1.0, "status": "automated_qa_passed", "speaker": "iris",
            "identity": "nora", "voice_id": "old-voice", "model": "eleven_v4",
            "plan_sha256": "plan-two",
        }
        voice_overlay = {
            "schema": 1, "model": "eleven_v4", "quality_approved": True,
            "plan_sha256": "plan-two", "casting_sha256": pipeline.file_sha(casting_path),
            "campaign": {"takes": {"recording.greeting": take}},
            "narration": {"takes": {}},
            "lipsync": {"takes": {"recording.greeting": {
                "audio_sha256": take["sha256"], "seconds": 1.0,
                "cues": [{"start": 0.0, "end": 1.0, "value": "X"}],
            }}},
            "review": {"hard_holds": {}},
        }
        campaign = {"lines": {
            "first": {"audio": "recording.greeting", "text": text, "speaker": "iris"},
            "reuse": {"audio": "recording.greeting", "text": text, "speaker": "iris"},
        }}
        overlay.merge_overlay(
            campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {},
            voice_overlay, root,
        )
        casting_path.write_text(json.dumps({
            "roles": {"nora": {"voice_id": "new-voice"}}
        }) + "\n")
        with self.assertRaisesRegex(ValueError, "casting fingerprint"):
            overlay.merge_overlay(
                campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {},
                voice_overlay, root,
            )
        voice_overlay["casting_sha256"] = pipeline.file_sha(casting_path)
        with self.assertRaisesRegex(ValueError, "voice/model"):
            overlay.merge_overlay(
                campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {},
                voice_overlay, root,
            )

    def test_activation_keeps_automated_status_truthful(self):
        plan = pipeline.build_plan(self.csv_path, self.script_path, self.cast_path)
        audio_id = next(iter(plan["items"]))
        staged = {
            "plan_sha256": plan["plan_sha256"],
            "casting_sha256": plan["inputs"]["casting"],
            "quality_approved": False,
            "campaign": {"takes": {audio_id: {
                "status": "automated_qa_passed", "listening_reviewed": False,
            }}},
            "narration": {"takes": {}},
            "review": {"hard_holds": {}, "activation_ready": True},
        }
        patches = self.globals()
        with patches[0], patches[1], patches[2], patches[3], \
                patch.object(pipeline, "OVERLAY_PATH", SCRATCH / "overlay.json"):
            pipeline.atomic_json(pipeline.OVERLAY_PATH, staged)
            result = pipeline.activate_overlay(plan)
        self.assertTrue(result["quality_approved"])
        self.assertEqual(result["campaign"]["takes"][audio_id]["status"], "automated_qa_passed")
        self.assertFalse(result["campaign"]["takes"][audio_id]["listening_reviewed"])
        staged["campaign"]["takes"][audio_id]["status"] = "manual_review_required"
        staged["review"] = {
            "hard_holds": {audio_id: "short_asr_ambiguity"},
            "activation_ready": False,
        }
        staged["quality_approved"] = False
        with patches[0], patches[1], patches[2], patches[3], \
                patch.object(pipeline, "OVERLAY_PATH", SCRATCH / "held-overlay.json"):
            pipeline.atomic_json(pipeline.OVERLAY_PATH, staged)
            with self.assertRaisesRegex(ValueError, "Actual review"):
                pipeline.activate_overlay(plan)


if __name__ == "__main__":
    unittest.main()

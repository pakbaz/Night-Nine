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

    def test_asr_comparator_normalizes_only_proven_formatting_equivalents(self):
        checker = {
            "words": lambda text: __import__("re").findall(r"[a-z0-9']+", text.lower()),
            "distance": lambda left, right: 0 if left == right else 1,
        }
        equivalent = [
            ("The ident ran at 06:01.", "The ident ran at 0601."),
            ("At 23:42 the lamp failed.", "At 23.42 the lamp failed."),
            ("Nora arrived at 7:15.", "Nora arrived at 7.15."),
            ("The Prefect’s file is sealed.", "The prefects file is sealed."),
        ]
        for expected, recognized in equivalent:
            self.assertEqual(
                pipeline.comparison_distance(expected, recognized, checker), 0,
                (expected, recognized),
            )
        different = [
            ("The ident ran at 06:01.", "The ident ran at 06:02."),
            ("At 23:42 the lamp failed.", "At 23:24 the lamp failed."),
            ("The ident ran at 06:01.", "The ident at 0601."),
            ("The ident ran at 06:01.", "The ident ran at 0601 again."),
            ("Nora arrived at 20:04.", "Nora arrived at 2014."),
            ("The click was at 0.5 seconds.", "The click was at 5 seconds."),
            ("The plate will be warm.", "The plate will be worn."),
            ("A fresh Pier flash.", "A fresh peer flash."),
            ("They rowed into the bay.", "They rode into the bay."),
            ("Wen returned to the station.", "When returned to the station."),
            ("We arrived at Tirel.", "We arrived at Tyrell."),
        ]
        for expected, recognized in different:
            self.assertNotEqual(
                pipeline.comparison_distance(expected, recognized, checker), 0,
                (expected, recognized),
            )

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

    def splice_fixture(self):
        import numpy as np
        import soundfile as sf
        source = SCRATCH / "voicemail.wav"
        samples = np.zeros(48000 * 4, dtype=np.float32)
        samples[round(3.20 * 48000):round(3.50 * 48000)] = .5
        sf.write(source, samples, 48000, "PCM_16")
        text = "Come out with us, kiddo. The bay is singing tonight."
        tokens = ["come", "out", "with", "us", "kiddo", "the", "bay", "is", "singing", "tonight"]
        boundaries = [(0.06, .2), (.28, .4), (.44, .56), (.64, .76), (.88, 1.2),
                      (1.76, 1.9), (1.96, 2.16), (2.24, 2.48), (2.60, 2.98), (3.04, 3.52)]
        timings = [{"word": word, "start": start, "end": end}
                   for word, (start, end) in zip(tokens, boundaries)]
        evidence = {
            "audio_id": "recording.voicemail", "audio_sha256": pipeline.file_sha(source),
            "model_id": "scribe_v3", "script_or_keyterm_prompt_sent": False,
            "request_fields": {"model_id": "scribe_v3", "timestamps_granularity": "word"},
            "expected": text, "recognized": text, "word_edits": 0,
            "response": {"text": text, "words": [
                {"text": item["word"], "start": item["start"], "end": item["end"], "type": "word"}
                for item in timings
            ]},
        }
        path = SCRATCH / "production/independent-asr/scribe-v3/recording.voicemail.json"
        pipeline.atomic_json(path, evidence)
        timings[-1] = {"word": "tonight", "start": 2.84, "end": 3.16}
        return source, timings, path, evidence

    def test_splice_keeps_entire_final_word_using_source_bound_alignment(self):
        import numpy as np
        import soundfile as sf
        source, timings, _, _ = self.splice_fixture()
        with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
            output, receipt = pipeline.create_saren_splice(source, pipeline.file_sha(source), timings)
        samples, _ = sf.read(output)
        self.assertEqual(np.count_nonzero(samples == .5), round(.30 * 48000))
        self.assertEqual(receipt["source_intervals"][-1], [3.04, 3.52])

    def test_splice_rejects_stale_or_prompted_alignment(self):
        source, timings, path, evidence = self.splice_fixture()
        for changes in (
            {"audio_sha256": "stale"},
            {"script_or_keyterm_prompt_sent": True},
            {"response": {"text": "Come out with us, kiddo.", "words": evidence["response"]["words"]}},
        ):
            with self.subTest(changes=changes):
                pipeline.atomic_json(path, evidence | changes)
                with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
                    with self.assertRaisesRegex(ValueError, "alignment"):
                        pipeline.create_saren_splice(source, pipeline.file_sha(source), timings)

    def test_short_lines_need_two_exact_transcripts_and_keep_local_evidence(self):
        checker = {
            "words": lambda text: __import__("re").findall(r"[a-z0-9']+", text.lower()),
            "distance": lambda left, right: 0 if left == right else 1,
        }
        report = {"audio_id": "short", "plan_sha256": "plan", "wav_sha256": "wav",
                  "expected": "Hold the line.", "recognized": "Hold the line."}
        evidence = {
            "audio_id": "short", "production_plan_sha256": "plan", "audio_sha256": "wav",
            "expected": report["expected"], "recognized": report["expected"], "word_edits": 0,
            "model_id": "scribe_v3", "script_or_keyterm_prompt_sent": False,
            "request_fields": {"model_id": "scribe_v3"},
            "response": {"text": report["expected"]},
        }
        path = SCRATCH / "production/independent-asr/scribe-v3/short.json"
        with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
            self.assertEqual(pipeline.assess_transcript(dict(report), checker), "short_asr_ambiguity")
            pipeline.atomic_json(path, evidence)
            self.assertIsNone(pipeline.assess_transcript(dict(report), checker))
            ambiguous = report | {"recognized": "Hold line."}
            self.assertEqual(pipeline.assess_transcript(ambiguous, checker), "short_asr_ambiguity")
            self.assertEqual(pipeline.assess_transcript(ambiguous, checker), "short_asr_ambiguity")
            self.assertEqual(ambiguous["local_recognized"], "Hold line.")
            pipeline.atomic_json(path, evidence | {"audio_sha256": "old-wav"})
            self.assertEqual(pipeline.assess_transcript(dict(report), checker), "short_asr_ambiguity")

    def test_independent_review_rejects_changed_clue_and_edited_response(self):
        checker = {
            "words": lambda text: __import__("re").findall(r"[a-z0-9']+", text.lower()),
            "distance": lambda left, right: 0 if left == right else 1,
        }
        report = {"audio_id": "clue", "plan_sha256": "plan", "wav_sha256": "wav",
                  "expected": "Set the clock to 06:01.", "recognized": "Set the clock to 06:02."}
        evidence = {
            "audio_id": "clue", "production_plan_sha256": "plan", "audio_sha256": "wav",
            "expected": report["expected"], "recognized": report["recognized"], "word_edits": 1,
            "model_id": "scribe_v3", "script_or_keyterm_prompt_sent": False,
            "request_fields": {"model_id": "scribe_v3"},
            "response": {"text": report["recognized"]},
        }
        path = SCRATCH / "production/independent-asr/scribe-v3/clue.json"
        with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
            pipeline.atomic_json(path, evidence)
            self.assertEqual(pipeline.assess_transcript(dict(report), checker), "asr_mismatch")
            pipeline.atomic_json(path, evidence | {"recognized": report["expected"], "word_edits": 0})
            with self.assertRaisesRegex(ValueError, "independent transcript"):
                pipeline.assess_transcript(dict(report), checker)

    def test_retakes_require_original_cast_and_both_transcripts(self):
        checker = {
            "words": lambda text: text.lower().split(),
            "distance": lambda left, right: 0 if left == right else 1,
        }
        plan = pipeline.build_plan(self.csv_path, self.script_path, self.cast_path)
        candidate = json.loads(json.dumps(plan))
        candidate["source_plan_sha256"] = plan["plan_sha256"]

        def freeze(value):
            payload = json.loads(json.dumps(value))
            payload.pop("plan_sha256", None)
            for item in payload["items"].values():
                item.pop("seed", None)
            value["plan_sha256"] = pipeline.canonical_sha(payload)

        freeze(candidate)
        folder = SCRATCH / "production/retakes/automatic-01"
        preflight = {"plan_sha256": candidate["plan_sha256"], "voices": {"voice-one": {"rate": 1}}}
        preflight["preflight_sha256"] = pipeline.canonical_sha(preflight)
        patches = self.globals()
        with patches[0], patches[1], patches[2], patches[3]:
            with patch.object(pipeline, "PRODUCTION", folder):
                pipeline.generate(candidate, preflight, FakeApi())
            pipeline.atomic_json(folder / "plan.json", candidate)
            pipeline.atomic_json(folder / "results.json", {"passed": ["shared.take"], "held": []})
            master = folder / "masters/shared.take.wav"
            pipeline.atomic_bytes(master, b"fixture-audio")
            report = {
                "audio_id": "shared.take", "plan_sha256": candidate["plan_sha256"],
                "source_plan_sha256": plan["plan_sha256"], "wav_sha256": pipeline.file_sha(master),
                "expected": "One proven take.", "recognized": "One proven take.",
            }
            pipeline.atomic_json(folder / "checks/shared.take.json", report)
            self.assertEqual(pipeline.verified_retakes(plan, checker), {})
            evidence = {
                "audio_id": "shared.take", "production_plan_sha256": plan["plan_sha256"],
                "audio_sha256": report["wav_sha256"], "expected": report["expected"],
                "recognized": report["recognized"], "word_edits": 0,
                "model_id": "scribe_v3", "request_fields": {"model_id": "scribe_v3"},
                "script_or_keyterm_prompt_sent": False, "response": {"text": report["recognized"]},
            }
            pipeline.atomic_json(SCRATCH / "production/independent-asr/scribe-v3/shared.take.json", evidence)
            with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
                self.assertEqual(pipeline.verified_retakes(plan, checker),
                                 {"shared.take": (folder, candidate["plan_sha256"])})
            evidence_path = SCRATCH / "production/independent-asr/scribe-v3/shared.take.json"
            evidence_path.unlink()
            report["recognized"] = "A transcript that does not match."
            pipeline.atomic_json(folder / "checks/shared.take.json", report)
            manual_review = {
                "schema": 1, "decision": "reviewed", "reviewed_by": "S3PehR",
                "reviewed_at": "2026-11-21T11:19:35-08:00",
                "plan_sha256": candidate["plan_sha256"],
                "source_plan_sha256": plan["plan_sha256"],
                "decisions": {"shared.take": "accept"},
                "audio_sha256": {"shared.take": report["wav_sha256"]},
            }
            pipeline.atomic_json(folder / "manual-review.json", manual_review)
            with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
                self.assertEqual(pipeline.verified_retakes(plan, checker),
                                 {"shared.take": (folder, candidate["plan_sha256"])})
            manual_review["audio_sha256"]["shared.take"] = "stale-audio"
            pipeline.atomic_json(folder / "manual-review.json", manual_review)
            with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
                with self.assertRaisesRegex(ValueError, "Manual retake review is stale"):
                    pipeline.verified_retakes(plan, checker)
            (folder / "manual-review.json").unlink()
            candidate["items"]["shared.take"]["voice_id"] = "different-voice"
            freeze(candidate)
            pipeline.atomic_json(folder / "plan.json", candidate)
            with patch.object(pipeline, "PRODUCTION", SCRATCH / "production"):
                with self.assertRaisesRegex(ValueError, "script or casting"):
                    pipeline.verified_retakes(plan, checker)

    def test_partial_review_records_accepted_takes_and_retakes_without_activation(self):
        overlay_data = {
            "campaign": {"takes": {
                "accepted": {"status": "automated_qa_passed"},
                "retake": {"status": "manual_review_required"},
            }},
            "narration": {"takes": {}},
            "review": {"hard_holds": {"accepted": "asr_mismatch", "retake": "asr_mismatch"}},
        }
        receipt = {
            "decision": "reviewed", "reviewed_by": "S3PehR", "reviewed_at": "2026-11-21T11:19:35-08:00",
            "decisions": {"accepted": "accept", "retake": "retake"},
            "retake_notes": {"retake": "Needs a new take."},
        }
        result = pipeline.apply_manual_review(
            overlay_data, receipt, SCRATCH / "root/review.json", SCRATCH / "root",
        )
        self.assertEqual(result["review"]["hard_holds"], {"retake": "asr_mismatch"})
        self.assertEqual(result["campaign"]["takes"]["accepted"]["status"], "manual_review_passed")
        self.assertEqual(result["campaign"]["takes"]["retake"]["status"], "retake_requested")
        self.assertFalse(result["quality_approved"])
        self.assertEqual(result["review"]["retake_requests"], {"retake": "Needs a new take."})

        result["campaign"]["takes"]["retake"]["status"] = "manual_review_required"
        resolved = pipeline.apply_manual_review(
            result,
            receipt | {"decisions": {"retake": "accept"}, "retake_notes": {}},
            SCRATCH / "root/retake-review.json", SCRATCH / "root",
        )
        self.assertTrue(resolved["quality_approved"])

    def test_empty_manual_review_page_reports_no_pending_review(self):
        plan = {
            "plan_sha256": "a" * 64,
            "inputs": {"casting": "b" * 64},
            "items": {},
        }
        review_root = SCRATCH / "empty-review"
        pipeline.write_manual_review_files(plan, {}, {}, review_root)
        page = (review_root / "manual-review.html").read_text()
        self.assertIn("No listening review is pending.", page)
        self.assertNotIn("Review only these 0 held takes", page)

    def additions_fixture(self):
        root = SCRATCH / "additions-root"
        casting_path = root / "docs/voice-casting-2026-11-20.json"
        casting_path.parent.mkdir(parents=True)
        casting_path.write_text(json.dumps({
            "roles": {"steve": {"voice_id": "voice-steve"}, "nora": {"voice_id": "voice-nora"}}
        }) + "\n")
        voices = root / "game/assets/audio/voices"
        voices.mkdir(parents=True)

        def take(audio_id, text, speaker, identity, name, extra=None):
            path = voices / name
            path.write_bytes(text.encode())
            entry = {
                "id": audio_id, "text": text, "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                "file": "res://assets/audio/voices/" + name, "sha256": pipeline.file_sha(path),
                "seconds": 1.0, "status": "automated_qa_passed", "speaker": speaker,
                "identity": identity, "voice_id": "voice-" + identity, "model": "eleven_v4",
            }
            entry.update(extra or {})
            return entry

        kept = take("kept.1", "Kept line.", "steve", "steve", "kept.wav", {"plan_sha256": "plan-one"})
        edited = take("edited.1", "Old wording.", "steve", "steve", "edited-old.wav", {"plan_sha256": "plan-one"})
        base = {
            "schema": 1, "model": "eleven_v4", "quality_approved": True,
            "plan_sha256": "plan-one", "casting_sha256": pipeline.file_sha(casting_path),
            "campaign": {"takes": {"kept.1": kept, "edited.1": edited}},
            "narration": {"takes": {}},
            "lipsync": {"takes": {audio_id: {
                "audio_sha256": entry["sha256"], "seconds": 1.0,
                "cues": [{"start": 0.0, "end": 1.0, "value": "X"}],
            } for audio_id, entry in (("kept.1", kept), ("edited.1", edited))}},
            "review": {"hard_holds": {}},
        }
        campaign = {"lines": {
            "kept.1": {"audio": "kept.1", "text": "Kept line.", "speaker": "steve"},
            "edited.1": {"audio": "edited.1", "text": "New wording.", "speaker": "steve"},
            "talk.1": {"audio": "talk.1", "text": "Coffee?", "speaker": "iris"},
        }}
        additions = {
            "schema": 1, "model": "eleven_v4", "casting_sha256": pipeline.file_sha(casting_path),
            "campaign": {"takes": {
                "edited.1": take("edited.1", "New wording.", "steve", "steve", "edited-new.wav"),
                "talk.1": take("talk.1", "Coffee?", "iris", "nora", "talk.wav"),
            }},
            "narration": {"takes": {}},
        }
        return root, campaign, base, additions

    def test_new_and_edited_lines_stay_text_only_until_recorded(self):
        root, campaign, base, _additions = self.additions_fixture()
        voice, lipsync, _book, _narration = overlay.merge_overlay(
            campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {}, base, root,
        )
        self.assertEqual(set(voice["takes"]), {"kept.1"})
        self.assertEqual(voice["missing"], ["edited.1", "talk.1"])
        self.assertEqual(set(lipsync["takes"]), {"kept.1"})

    def test_additions_cover_new_and_edited_lines_without_mouth_cues(self):
        root, campaign, base, additions = self.additions_fixture()
        voice, _lipsync, _book, _narration = overlay.merge_overlay(
            campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {}, base, root,
            additions=additions,
        )
        self.assertTrue(voice["enabled"])
        self.assertEqual(voice["missing"], [])
        self.assertEqual(voice["takes"]["edited.1"]["file"], "res://assets/audio/voices/edited-new.wav")
        self.assertEqual(voice["takes"]["talk.1"]["identity"], "nora")
        additions["campaign"]["takes"]["talk.1"]["voice_id"] = "voice-steve"
        with self.assertRaisesRegex(ValueError, "voice/model"):
            overlay.merge_overlay(
                campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {}, base, root,
                additions=additions,
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

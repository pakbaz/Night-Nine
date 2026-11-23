#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp/qa/voice-additions-tests"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


additions = load_module("voice_additions", ROOT / "tools/voice_additions.py")
voice_overlay = load_module("script_v2_voice_overlay_additions_test",
                            ROOT / "tools/script_v2_voice_overlay.py")


class FakeApi:
    def __init__(self, subscription=None):
        self.posts = 0
        self.bodies = []
        self.subscription = subscription or {
            "character_limit": 1000,
            "character_count": 0,
            "allowed_to_extend_character_limit": False,
            "can_extend_character_limit": False,
            "max_character_limit_extension": 0,
            "max_credit_limit_extension": 0,
            "current_overage": {"amount": "0"},
        }

    def get_json(self, path, params=None):
        if path == "/v1/user/subscription":
            return self.subscription
        raise AssertionError(path)

    def post_audio(self, path, body, params=None):
        self.posts += 1
        self.bodies.append(body)
        return b"fake-mp3-" + str(self.posts).encode(), {
            "request-id": f"request-{self.posts}",
            "x-trace-id": f"trace-{self.posts}",
            "character-cost": str(len(body["text"])),
        }

    def post_multipart(self, path, fields, file_name, payload):
        self.transcriptions = getattr(self, "transcriptions", [])
        self.transcriptions.append({"path": path, "fields": dict(fields), "file": file_name})
        text = self.heard.get(file_name.split(".attempt-")[0], "") if hasattr(self, "heard") else ""
        return {"language_code": "eng", "language_probability": 1.0, "text": text, "words": []}, {
            "x-trace-id": f"stt-trace-{len(self.transcriptions)}", "character-cost": "0",
        }


def write_wav(path, seconds=1.0, amplitude=4000):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = round(48000 * seconds)
    samples = b"".join(struct.pack("<h", amplitude if index % 2 else -amplitude)
                       for index in range(frames))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(samples)


class VoiceAdditionsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        self.root = SCRATCH / "root"
        self.production = self.root / "assets/audio/elevenlabs-v4-additions"
        content = self.root / "game/content"
        content.mkdir(parents=True)
        casting = self.root / "docs/voice-casting-2026-11-20.json"
        casting.parent.mkdir(parents=True)
        casting.write_text(json.dumps({
            "roles": {
                "steve": {"voice_id": "voice-steve"},
                "nora": {"voice_id": "voice-nora"},
            }
        }) + "\n")
        campaign = {
            "lines": {
                "scene.before": {
                    "id": "scene.before", "speaker": "steve", "text": "Before.",
                    "audio": "scene.before",
                },
                "scene.new": {
                    "id": "scene.new", "speaker": "iris", "text": "A new clue arrives tonight.",
                    "audio": "scene.new", "delivery": "radio", "direction": "a whisper",
                },
                "scene.after": {
                    "id": "scene.after", "speaker": "steve", "text": "After.",
                    "audio": "scene.after",
                },
            },
            "scenes": [{
                "id": "scene", "context": [], "intro": ["scene.before", "scene.new"],
                "tasks": [{
                    "id": "scene.task", "lead": [], "lines": ["scene.after"],
                    "finding": "",
                }],
                "recap": [], "outro": [],
            }],
        }
        storybook = {"books": {"opening": {"panels": [{"lines": [
            {"text": "First page."}, {"text": "A later page."}, {"text": "Last page."},
        ]}]}}}
        (content / "campaign.json").write_text(json.dumps(campaign) + "\n")
        (content / "storybook.json").write_text(json.dumps(storybook) + "\n")
        (content / "voice-manifest.json").write_text(json.dumps({
            "schema": 1, "missing": ["scene.new", "book.opening.1.2"],
        }) + "\n")

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def build_plan(self):
        plan = additions.build_plan(self.root, self.production)
        additions.atomic_json(self.production / "plan.json", plan)
        return plan

    def test_plan_selects_missing_ids_with_cast_and_context(self):
        plan = self.build_plan()
        self.assertEqual(plan["ordered_audio_ids"], ["scene.new", "book.opening.1.2"])
        campaign = plan["items"]["scene.new"]
        self.assertEqual(campaign["cast_role"], "nora")
        self.assertEqual(campaign["voice_id"], "voice-nora")
        self.assertEqual(campaign["previous_text"], "Before.")
        self.assertEqual(campaign["next_text"], "After.")
        self.assertEqual(campaign["v4_audio_tag"], "[whispers]")
        narration = plan["items"]["book.opening.1.2"]
        self.assertEqual(narration["speaker"], "steve")
        self.assertEqual(narration["previous_text"], "First page.")
        self.assertEqual(narration["next_text"], "Last page.")
        self.assertEqual(len(campaign["attempt_seeds"]), 3)
        self.assertEqual(plan["estimated_credits"],
                         sum(item["estimated_credits"] for item in plan["items"].values()))
        changed = json.loads(json.dumps(plan))
        changed["items"]["scene.new"]["attempt_seeds"][0] += 1
        with self.assertRaisesRegex(ValueError, "attempt seeds changed"):
            additions.verify_plan(changed, self.root, self.production)

    def test_generate_requires_gate_and_refuses_unsafe_subscription(self):
        plan = self.build_plan()
        with self.assertRaisesRegex(ValueError, "allow-billed-generation"):
            additions.generate(plan, FakeApi(), self.root, self.production,
                               plan["plan_sha256"], False)
        with self.assertRaisesRegex(ValueError, "exact frozen plan hash"):
            additions.generate(plan, FakeApi(), self.root, self.production, "wrong", True)
        overage = FakeApi(FakeApi().subscription | {"allowed_to_extend_character_limit": True})
        with self.assertRaisesRegex(ValueError, "Paid overage"):
            additions.generate(plan, overage, self.root, self.production,
                               plan["plan_sha256"], True)
        short = FakeApi(FakeApi().subscription | {"character_limit": 1})
        with self.assertRaisesRegex(ValueError, "Quota refusal"):
            additions.generate(plan, short, self.root, self.production,
                               plan["plan_sha256"], True)

    def test_generate_writes_receipts_resumes_and_never_rebills_inflight(self):
        plan = self.build_plan()
        api = FakeApi()
        first = additions.generate(plan, api, self.root, self.production,
                                   plan["plan_sha256"], True, limit=1)
        second = additions.generate(plan, api, self.root, self.production,
                                    plan["plan_sha256"], True, limit=1)
        self.assertEqual(first, ["scene.new"])
        self.assertEqual(second, ["book.opening.1.2"])
        self.assertEqual(api.posts, 2)
        third = additions.generate(plan, api, self.root, self.production,
                                   plan["plan_sha256"], True)
        self.assertEqual(third, [])
        self.assertEqual(api.posts, 2)
        receipt = json.loads(
            (self.production / "receipts/scene.new.attempt-1.json").read_text()
        )
        self.assertEqual(receipt["request_id"], "request-1")
        self.assertEqual(receipt["audio_sha256"], hashlib.sha256(b"fake-mp3-1").hexdigest())

        marker = self.production / "inflight/speech/scene.new.attempt-2.json"
        additions.atomic_json(marker, {"operation": "text_to_speech"})
        with self.assertRaisesRegex(ValueError, "Unresolved speech request"):
            additions.generate(plan, FakeApi(), self.root, self.production,
                               plan["plan_sha256"], True)

    def test_retake_uses_the_next_seed_and_stops_after_three_attempts(self):
        (self.root / "game/content/voice-manifest.json").write_text(json.dumps({
            "schema": 1, "missing": ["scene.new"],
        }) + "\n")
        plan = self.build_plan()
        api = FakeApi()
        additions.generate(plan, api, self.root, self.production,
                           plan["plan_sha256"], True)

        def fail_attempt(attempt):
            _, _, master, check = additions.attempt_paths(
                "scene.new", attempt, self.production,
            )
            write_wav(master)
            additions.atomic_json(check, {
                "audio_id": "scene.new",
                "attempt": attempt,
                "plan_sha256": plan["plan_sha256"],
                "wav_sha256": additions.file_sha(master),
                "status": "retake_required",
                "failure_reason": "asr_mismatch",
            })

        fail_attempt(1)
        self.assertEqual(
            additions.retake(plan, api, self.root, self.production,
                             plan["plan_sha256"], True),
            ["scene.new"],
        )
        fail_attempt(2)
        self.assertEqual(
            additions.retake(plan, api, self.root, self.production,
                             plan["plan_sha256"], True),
            ["scene.new"],
        )
        fail_attempt(3)
        self.assertEqual(
            additions.retake(plan, api, self.root, self.production,
                             plan["plan_sha256"], True),
            [],
        )
        self.assertEqual(api.posts, 3)
        self.assertEqual(
            [body["seed"] for body in api.bodies],
            plan["items"]["scene.new"]["attempt_seeds"],
        )

    def validated_short_line(self):
        plan = self.build_plan()
        additions.generate(plan, FakeApi(), self.root, self.production,
                           plan["plan_sha256"], True)

        def decoder(audio_id, attempt, _production):
            target = self.production / f"masters/{audio_id}.attempt-{attempt}.wav"
            write_wav(target)
            return target

        checker = {"words": lambda text: text.lower().strip(".").split(),
                   "distance": lambda left, right: 0 if left == right else 1}
        checks = additions.validate(
            plan, self.root, self.production,
            transcriber=lambda _path, item: item["text"], checker=checker, decoder=decoder,
        )
        return plan, checks, checker, decoder

    def test_retake_skips_short_lines_that_only_need_an_independent_check(self):
        plan, checks, _checker, _decoder = self.validated_short_line()
        self.assertEqual(checks["scene.new"]["status"], "automated_qa_passed")
        self.assertEqual(checks["book.opening.1.2"]["failure_reason"], "short_asr_ambiguity")
        api = FakeApi()
        self.assertEqual(additions.retake(plan, api, self.root, self.production,
                                          plan["plan_sha256"], True), [])
        self.assertEqual(api.posts, 0)
        self.assertEqual(additions.retake(plan, api, self.root, self.production,
                                          plan["plan_sha256"], True, include_short=True),
                         ["book.opening.1.2"])

    def test_independent_transcript_clears_a_short_line_only_when_it_matches(self):
        plan, _checks, checker, decoder = self.validated_short_line()
        api = FakeApi()
        api.heard = {"book.opening.1.2": "A later page."}
        with self.assertRaisesRegex(ValueError, "allow-billed-transcription"):
            additions.independent(plan, api, self.root, self.production,
                                  plan["plan_sha256"], False, checker=checker)
        done = additions.independent(plan, api, self.root, self.production,
                                     plan["plan_sha256"], True, checker=checker)
        self.assertEqual(done, ["book.opening.1.2"])
        request = api.transcriptions[0]
        self.assertEqual(request["path"], "/v1/speech-to-text")
        self.assertEqual(request["fields"]["model_id"], "scribe_v3")
        self.assertFalse({"keyterms", "prompt", "text"} & set(request["fields"]))
        evidence = json.loads((self.production / "independent-asr/scribe-v3/book.opening.1.2.json").read_text())
        self.assertFalse(evidence["script_or_keyterm_prompt_sent"])
        self.assertEqual(evidence["production_plan_sha256"], plan["plan_sha256"])
        checks = additions.validate(
            plan, self.root, self.production,
            transcriber=lambda _path, item: item["text"], checker=checker, decoder=decoder,
        )
        self.assertEqual(checks["book.opening.1.2"]["status"], "automated_qa_passed")
        self.assertEqual(checks["book.opening.1.2"]["independent_asr"]["word_edits"], 0)
        api.heard = {"book.opening.1.2": "A lighter page."}
        additions.independent(plan, api, self.root, self.production,
                              plan["plan_sha256"], True, checker=checker,
                              audio_ids=["book.opening.1.2"])
        checks = additions.validate(
            plan, self.root, self.production,
            transcriber=lambda _path, item: item["text"], checker=checker, decoder=decoder,
        )
        self.assertEqual(checks["book.opening.1.2"]["status"], "retake_required")

    def test_partial_stage_and_archive_allow_a_second_batch_with_reused_ids(self):
        plan = self.build_plan()
        additions.generate(plan, FakeApi(), self.root, self.production,
                           plan["plan_sha256"], True)

        def decoder(audio_id, attempt, production):
            target = Path(production) / f"masters/{audio_id}.attempt-{attempt}.wav"
            write_wav(target)
            return target

        checker = {"words": lambda text: text.lower().strip(".").split(),
                   "distance": lambda left, right: 0 if left == right else 1}
        heard = {"scene.new": "A new clue arrives tonight.", "book.opening.1.2": "Something else entirely."}
        additions.validate(plan, self.root, self.production,
                           transcriber=lambda _path, item: heard[item["audio_id"]],
                           checker=checker, decoder=decoder)
        with self.assertRaisesRegex(ValueError, "not passed validation"):
            additions.stage(plan, self.root, self.production)
        staged = additions.stage(plan, self.root, self.production, partial=True)
        self.assertEqual(set(staged["campaign"]["takes"]), {"scene.new"})
        self.assertEqual(staged["narration"]["takes"], {})
        batch = additions.archive(plan, self.root, self.production)
        self.assertFalse((self.production / "receipts").exists())
        self.assertTrue((batch / "receipts/scene.new.attempt-1.json").is_file())
        overlay = json.loads((self.production / "approved-additions.json").read_text())
        report = overlay["campaign"]["takes"]["scene.new"]["asr_report"]
        self.assertTrue((self.root / report).is_file(), report)
        # The writer rewords the failing line; the same audio id gets a fresh batch.
        storybook_path = self.root / "game/content/storybook.json"
        storybook = json.loads(storybook_path.read_text())
        storybook["books"]["opening"]["panels"][0]["lines"][1]["text"] = "A quieter page."
        storybook_path.write_text(json.dumps(storybook) + "\n")
        (self.root / "game/content/voice-manifest.json").write_text(json.dumps({
            "schema": 1, "missing": ["book.opening.1.2"],
        }) + "\n")
        second = self.build_plan()
        self.assertEqual(second["ordered_audio_ids"], ["book.opening.1.2"])
        api = FakeApi()
        self.assertEqual(additions.generate(second, api, self.root, self.production,
                                            second["plan_sha256"], True), ["book.opening.1.2"])
        api.heard = {"book.opening.1.2": "A quieter page."}
        additions.validate(second, self.root, self.production,
                           transcriber=lambda _path, item: item["text"], checker=checker, decoder=decoder)
        additions.independent(second, api, self.root, self.production,
                              second["plan_sha256"], True, checker=checker)
        additions.validate(second, self.root, self.production,
                           transcriber=lambda _path, item: item["text"], checker=checker, decoder=decoder)
        staged = additions.stage(second, self.root, self.production)
        self.assertEqual(set(staged["campaign"]["takes"]), {"scene.new"})
        self.assertEqual(set(staged["narration"]["takes"]), {"book.opening.1.2"})

    def test_failed_transcript_blocks_staging(self):
        plan = self.build_plan()
        additions.generate(plan, FakeApi(), self.root, self.production,
                           plan["plan_sha256"], True)

        def decoder(audio_id, attempt, _production):
            target = self.production / f"masters/{audio_id}.attempt-{attempt}.wav"
            write_wav(target)
            return target

        checks = additions.validate(
            plan, self.root, self.production,
            transcriber=lambda _path, _item: "Wrong words entirely.",
            checker={"words": lambda text: text.lower().strip(".").split(),
                     "distance": lambda left, right: 0 if left == right else 1},
            decoder=decoder,
        )
        self.assertTrue(all(check["status"] == "retake_required" for check in checks.values()))
        with self.assertRaisesRegex(ValueError, "not passed validation"):
            additions.stage(plan, self.root, self.production)

    def test_stage_overlay_is_accepted_by_merge_overlay(self):
        (self.root / "game/content/voice-manifest.json").write_text(json.dumps({
            "schema": 1, "missing": ["scene.new"],
        }) + "\n")
        plan = self.build_plan()
        additions.generate(plan, FakeApi(), self.root, self.production,
                           plan["plan_sha256"], True)

        def decoder(audio_id, attempt, _production):
            target = self.production / f"masters/{audio_id}.attempt-{attempt}.wav"
            write_wav(target)
            return target

        additions.validate(
            plan, self.root, self.production,
            transcriber=lambda _path, item: item["text"],
            checker={"words": lambda text: text.lower().strip(".").split(),
                     "distance": lambda left, right: 0 if left == right else 1},
            decoder=decoder,
        )
        staged = additions.stage(plan, self.root, self.production)
        take = staged["campaign"]["takes"]["scene.new"]
        self.assertTrue(
            (self.root / "game/assets/audio/voices/elevenlabs-v4-additions/scene.new.wav").is_file()
        )
        self.assertTrue(
            (self.root / "game/assets/audio/voices/elevenlabs-v4-additions/scene.new.wav.import").is_file()
        )
        casting_path = self.root / "docs/voice-casting-2026-11-20.json"
        frozen = {
            "schema": 1,
            "model": "eleven_v4",
            "quality_approved": True,
            "plan_sha256": "frozen",
            "casting_sha256": hashlib.sha256(casting_path.read_bytes()).hexdigest(),
            "campaign": {"takes": {}},
            "narration": {"takes": {}},
            "lipsync": {"generator": "test", "source": "test", "takes": {}},
            "review": {"hard_holds": {}},
        }
        campaign = json.loads((self.root / "game/content/campaign.json").read_text())
        campaign["lines"] = {"scene.new": campaign["lines"]["scene.new"]}
        merged = voice_overlay.merge_overlay(
            campaign, {"books": {}}, {"takes": {}}, {"takes": {}}, {},
            frozen, self.root, casting_path=casting_path, additions=staged,
        )
        self.assertEqual(merged[0]["missing"], [])
        self.assertEqual(merged[0]["takes"]["scene.new"]["sha256"], take["sha256"])

        # A reworded line keeps no fallback recorded for its old wording, but an unchanged
        # line keeps its fallback.
        fallback = {"file": "res://assets/audio/voices/scene.new.wav", "sha256": "old",
                    "timing": {"audio_sha256": "old", "cues": []}}
        for base_text, keeps in (("An old clue arrived last night.", False), (campaign["lines"]["scene.new"]["text"], True)):
            voice = {"takes": {"scene.new": {"text": base_text, "fallback": fallback}}}
            merged = voice_overlay.merge_overlay(
                campaign, {"books": {}}, voice, {"takes": {}}, {},
                frozen, self.root, casting_path=casting_path, additions=staged,
            )
            self.assertEqual("fallback" in merged[0]["takes"]["scene.new"], keeps, base_text)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Generate three bounded, user-directed ElevenLabs v4 voice candidates."""
import argparse
import copy
import importlib.util
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_ID = "62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889"
RETAKES_ROOT = ROOT / "assets/audio/elevenlabs-v4-script-v2/retakes"
REQUESTS = {
    "book.opening.5.1": "Same voice, firmer and more dominant, with more vocal variation; louder alone is not enough.",
    "c10_live.second.01": "Keep the exact words and voice. Use a clear pause and direct-address emphasis for Wen as a person's name; add no words.",
    "c7_swap.in.02": "Do not say T-Roll. Make the first Tee syllable longer and separate it clearly from Rel; keep the written subtitle Tirel.",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-billed-generation", action="store_true")
    parser.add_argument("--attempt", type=int, default=4)
    args = parser.parse_args()
    if not args.allow_billed_generation:
        parser.error("--allow-billed-generation is required for the requested ElevenLabs API calls.")
    if args.attempt < 1:
        parser.error("--attempt must be a positive integer")
    output = RETAKES_ROOT / f"user-review-2026-11-21-attempt-{args.attempt}"
    spec = importlib.util.spec_from_file_location("pipeline", ROOT / "tools/elevenlabs_v4_pipeline.py")
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    source = pipeline.read_json(pipeline.PLAN_PATH)
    pipeline.verify_frozen_inputs(source)
    if source["plan_sha256"] != PLAN_ID:
        raise ValueError("The user's review belongs to a different production plan.")
    reviewed_candidate = RETAKES_ROOT / (
        "user-review-2026-11-21" if args.attempt == 4
        else f"user-review-2026-11-21-attempt-{args.attempt - 1}"
    )
    prior_review = pipeline.read_json(reviewed_candidate / "manual-review.json")
    if (
        prior_review.get("decision") != "reviewed"
        or set(prior_review.get("decisions", {})) != set(REQUESTS)
        or any(value != "retake" for value in prior_review["decisions"].values())
    ):
        raise ValueError("The prior candidates must have a complete, recorded retake decision.")
    plan = copy.deepcopy(source)
    plan.pop("plan_sha256")
    plan["source_plan_sha256"] = source["plan_sha256"]
    plan["retake_attempt"] = args.attempt
    plan["user_review_feedback"] = REQUESTS
    plan["ordered_audio_ids"] = list(REQUESTS)
    plan["items"] = {key: copy.deepcopy(source["items"][key]) for key in REQUESTS}
    for audio_id, item in plan["items"].items():
        item.pop("seed", None)
        settings = item["voice_settings"]
        if audio_id == "book.opening.5.1":
            settings.update({"stability": 0.45, "style": 0.55, "speed": 0.94})
            item["master_gain_db"] = 4
        elif audio_id == "c10_live.second.01":
            settings.update({"stability": 0.4, "style": 0.2, "speed": 0.95})
            synthesis = "Holding. Now... Wen."
            plan.setdefault("user_approved_pronunciations", {})[audio_id] = {
                "canonical_text": item["text"],
                "spoken_as": "Wen as a person's name, with direct-address emphasis; no added words.",
                "synthesis_text": synthesis,
                "approved_by": prior_review["reviewed_by"],
                "approved_at": prior_review["reviewed_at"],
            }
            item["synthesis_text"] = synthesis
            item["synthesis_text_sha256"] = pipeline.text_sha(synthesis)
        else:
            settings.update({"stability": 0.4, "style": 0.25})
            synthesis = "What’s Teee... Rel?"
            plan.setdefault("user_approved_pronunciations", {})[audio_id] = {
                "canonical_text": item["text"],
                "spoken_as": "Tee-rel",
                "synthesis_text": synthesis,
                "approved_by": prior_review["reviewed_by"],
                "approved_at": prior_review["reviewed_at"],
            }
            item["synthesis_text"] = synthesis
            item["synthesis_text_sha256"] = pipeline.text_sha(synthesis)
    plan["rows"] = sum(len(item["line_ids"]) for item in plan["items"].values())
    plan["row_characters"] = sum(len(item["text"]) * len(item["line_ids"]) for item in plan["items"].values())
    plan["unique_audio_ids"] = plan["speech_requests"] = len(plan["items"])
    plan["derived_edits"] = 0
    plan["utterance_characters"] = sum(len(item["text"]) for item in plan["items"].values())
    plan["request_characters"] = sum(len(item["synthesis_text"]) for item in plan["items"].values())
    plan["plan_sha256"] = pipeline.canonical_sha(plan)
    for audio_id, item in plan["items"].items():
        item["seed"] = int(pipeline.text_sha(plan["plan_sha256"] + ":" + audio_id)[:8], 16)
    pipeline.verify_frozen_inputs(plan)
    if (output / "plan.json").exists():
        if pipeline.read_json(output / "plan.json") != plan:
            raise ValueError("This candidate plan already differs; preserve it and do not overwrite.")
    else:
        pipeline.atomic_json(output / "plan.json", plan)
    pipeline.PRODUCTION = output
    client = pipeline.ApiClient()
    preflight = pipeline.collect_preflight(plan, client)
    pipeline.atomic_json(output / "preflight.json", preflight)
    estimated = pipeline.remaining_estimated_credits(plan, preflight)
    before = pipeline.subscription_guard(client.get_json("/v1/user/subscription"), estimated)
    if before < 1000:
        raise ValueError("Refusing to use included credits without a 1,000-credit reserve.")
    pipeline.atomic_json(output / "retake-notes.json", {
        "source_plan_sha256": source["plan_sha256"],
        "candidate_plan_sha256": plan["plan_sha256"],
        "requests": REQUESTS,
        "pronunciation_overrides": plan.get("user_approved_pronunciations", {}),
        "reviewed_candidate_directory": reviewed_candidate.name,
        "original_texts_unchanged": True,
        "original_masters_preserved": True,
    })
    generated = pipeline.generate(plan, preflight, client)
    facts = []
    for audio_id in generated:
        audio, receipt = pipeline.receipt_paths(audio_id)
        facts.append({"audio_id": audio_id, "character_cost": pipeline.read_json(receipt)["character_cost"],
                      "request_id": pipeline.read_json(receipt)["request_id"],
                      "audio_sha256": pipeline.file_sha(audio)})
    after = pipeline.subscription_guard(client.get_json("/v1/user/subscription"), 0)
    pipeline.atomic_json(output / "generation-summary.json", {
        "candidate_plan_sha256": plan["plan_sha256"], "generated": facts,
        "estimated_included_credits": estimated, "included_credits_before": before,
        "included_credits_after": after, "paid_overage_enabled": False,
    })
    print(json.dumps({"candidate_plan_sha256": plan["plan_sha256"], "generated": facts,
                      "included_credits_before": before, "included_credits_after": after,
                      "paid_overage_enabled": False}, indent=2))

    checker = runpy.run_path(str(ROOT / "tools/check-voice-candidates.py"))
    model_path = ROOT / ".tools/models/whisper-qa"
    import os
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from mlx_audio.stt import load
    model = load(str(model_path))
    reports = {}
    for audio_id in generated:
        wav = pipeline.decode_mp3(audio_id)
        report_path = output / "checks" / f"{audio_id}.json"
        result = model.generate(str(wav), language="en", temperature=0, condition_on_previous_text=False)
        recognized = result.text.strip()
        item = plan["items"][audio_id]
        edits = pipeline.comparison_distance(item["text"], recognized, checker)
        report = {
            "audio_id": audio_id, "source_plan_sha256": source["plan_sha256"],
            "plan_sha256": plan["plan_sha256"], "expected": item["text"],
            "synthesis_text": item["synthesis_text"], "recognized": recognized,
            "word_edits": edits, "listening_reviewed": False,
            "candidate_audio_sha256": pipeline.file_sha(wav),
            "wav_sha256": pipeline.file_sha(wav),
            "generation_plan_sha256": plan["plan_sha256"],
            "pronunciation_override": plan.get("user_approved_pronunciations", {}).get(audio_id),
            "review_direction": REQUESTS[audio_id],
            **pipeline.audio_facts(wav),
        }
        pipeline.atomic_json(report_path, report)
        reports[audio_id] = report
        print(json.dumps({"audio_id": audio_id, "recognized": recognized, "word_edits": edits}))
    pipeline.atomic_json(output / "results.json", {
        "plan_sha256": plan["plan_sha256"],
        "passed": [audio_id for audio_id, report in reports.items() if report["word_edits"] == 0],
        "held": [audio_id for audio_id, report in reports.items() if report["word_edits"] != 0],
        "listening_reviewed": False, "original_masters_preserved": True,
    })
    print("Candidate generation and local transcription complete. No playback gate was enabled.")


if __name__ == "__main__":
    main()

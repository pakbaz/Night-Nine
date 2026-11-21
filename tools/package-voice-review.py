#!/usr/bin/env python3
"""Create a portable, offline review folder with audio for each held take."""
import argparse
import csv
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "assets/audio/elevenlabs-v4-script-v2/plan.json"
DEFAULT_PRODUCTION = ROOT / "assets/audio/elevenlabs-v4-script-v2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "builds/voice-review")
    parser.add_argument("--production", type=Path, default=DEFAULT_PRODUCTION)
    parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args()
    production = args.production.resolve()
    output = args.output.resolve()
    plan_path = args.plan.resolve()
    if output == production or production in output.parents or output in production.parents:
        parser.error("Output and source review evidence must be separate, non-nested folders.")
    manifest = json.loads((production / "manual-review-required.json").read_text())
    plan = json.loads(plan_path.read_text())
    if manifest["plan_sha256"] != plan["plan_sha256"] or manifest["count"] != len(manifest["entries"]):
        raise ValueError("Held-review list does not match the current frozen plan.")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for entry in manifest["entries"]:
        source = (production / entry["wav"]).resolve()
        if not source.is_file() or source.stat().st_size == 0:
            raise FileNotFoundError(f"Missing held recording: {source}")
        audio_id = entry["audio_id"]
        record = dict(entry)
        record["wav"] = f"audio/{audio_id}.wav"
        record["audio_sha256"] = sha(source)
        target = output / record["wav"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        records.append(record)
    portable_manifest = dict(manifest, entries=records, bundle="local audio copied and hash-verified")
    (output / "review-manifest.json").write_text(json.dumps(portable_manifest, ensure_ascii=False, indent=2) + "\n")
    with (output / "review-list.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "audio_id", "reason", "speaker", "line_ids", "word_edits", "expected",
            "recognized", "wav", "audio_sha256",
        ])
        writer.writeheader()
        for item in records:
            writer.writerow({key: item[key] for key in writer.fieldnames})
    cards = []
    for item in records:
        audio_id = html.escape(item["audio_id"])
        cards.append(
            f'<section id="{audio_id}"><h2><code>{audio_id}</code></h2>'
            f'<p><b>{html.escape(item["speaker"])}</b> · {html.escape(item["reason"])} · '
            f'{item["word_edits"]} edit(s)</p>'
            f'<audio controls preload="none" src="{html.escape(item["wav"])}"></audio>'
            f'<p><b>Expected:</b> {html.escape(item["expected"])}</p>'
            f'<p><b>Requested:</b> {html.escape(item.get("review_direction", "Listen and review this take."))}</p>'
            f'<p><b>ASR:</b> {html.escape(item["recognized"])}</p>'
            f'<label><input type="checkbox" class="reviewed"> I listened to this clip</label> '
            f'<label><select class="decision"><option value="">Choose</option>'
            f'<option value="accept">Accept this take</option>'
            f'<option value="retake">Request a new take</option></select></label>'
            f'<label>Notes <input class="notes" type="text"></label></section>'
        )
    page = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Night Nine voice review</title>
<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;background:#151719;color:#eee}
section{border:1px solid #555;border-radius:8px;padding:1rem;margin:1rem 0}audio{width:100%}
code{color:#d8ba7d}b{color:#a9d6ce}label{margin-right:1em}input[type=text]{min-width:16em}</style>
<h1>Night Nine: review """ + str(len(records)) + """ held clips</h1>
<p><strong>Story spoilers below.</strong> Play each clip and decide from what you hear. These controls are only a local checklist;
they do not approve recordings or enable game playback. The session folder includes the actual audio, manifest and CSV.</p>
<p>Listen to each clip. If it is acceptable, select “Accept this take.” If it needs replacement, select “Request a new take.”
An unchecked/unselected row remains unresolved.</p>
""" + "\n".join(cards)
    (output / "index.html").write_text(page + "\n")
    print(json.dumps({"clips": len(records), "audio_files": len(list((output / "audio").glob("*.wav"))),
                      "output": str(output), "plan_sha256": manifest["plan_sha256"]}))


if __name__ == "__main__":
    main()

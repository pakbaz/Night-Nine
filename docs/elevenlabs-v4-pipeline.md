# ElevenLabs v4 production pipeline

Status: all 873 audio IDs have been generated and structurally validated. Automated QA passes 829; playback remains disabled while 44 takes require listening review.

## Frozen production

- Plan: `assets/audio/elevenlabs-v4-script-v2/plan.json`
- Plan SHA-256: `62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889`
- 874 CSV recording entries; the full campaign and storybook inventory has 878 references, deduplicated to 873 audio IDs
- 872 billed speech requests and one verified local edit, `recording.saren_splice`
- 66,442 unique utterance characters
- 66,497 request characters after supported Eleven v4 whisper tags
- 872 complete billed-request receipts and one locally verified splice receipt

The estimate includes the Voice Library multiplier reported for AGEIS-7: 3x credits for its seven lines. Its `fiat_rate` metadata is 0.25, but ElevenLabs documents this legacy custom rate as a credit multiplier, not automatic account overage. Every other selected voice reports a 1x rate.

The read-only preflight confirmed `eleven_v4`, the approved voices, sufficient included credits, and disabled paid overage before generation.

## Safety and resume behavior

`tools/elevenlabs_v4_pipeline.py` freezes the recording list, final script, casting-file fingerprint, model, voice IDs, text, context, supported v4 controls, and deterministic seeds. It deduplicates by audio ID, including the delayed Nora message that the CSV currently marks twice as `record`.

Each paid request gets an adjacent MP3 and JSON receipt with its exact request ID, trace ID, character cost, model, voice ID, plan hash, text hashes, and audio hash. An inflight marker is written before every POST. Any auth, rights, rate, network, or uncertain-response failure stops the run. A restart skips only matching, complete receipts and refuses unresolved inflight requests.

Staging is offline. It can consume saved, explicitly authorized independent transcription evidence:

- Decode to mono 48 kHz PCM without overwriting historical masters.
- Run the local Whisper QA model without downloading weights.
- Mark exact independent ASR matches as `automated_qa_passed` only after format, finite-sample, level, duration, hash, and lip-sync checks also pass.
- Never claim an automated take was listening-reviewed.
- Hard-hold unresolved transcript differences, short clips without two exact model transcripts, and uncertain voicemail/splice boundaries for actual review.
- Build and verify Rhubarb mouth cues.
- Preserve `recording.greeting` as one uncompressed waveform everywhere it is reused.
- Build `recording.saren_splice` only from proven word boundaries in the new Helen voicemail, with a source/edit receipt.
- Stage new runtime WAVs under `game/assets/audio/voices/elevenlabs-v4-script-v2/`.
- Keep voice and storybook narration disabled until the complete set has either passed automated QA or received actual review for its hard holds.
- On every replay, reject a changed casting fingerprint or any take whose exact speaker, canonical copy identity, voice ID, or model no longer matches the authoritative cast. This includes reused fixed recordings.

The original lip-sync receipts and raw output are a local cache under `assets/audio/lipsync-elevenlabs-v4-script-v2/`. Fresh checkouts generate that cache locally. Corrected takes use separate hash-named revisions, preserving their previous cues.

## Recovery and validation commands

Rebuild the plan and repeat the read-only checks first. A changed script or cast produces a new hash and blocks stale resume.

```bash
python3 tools/elevenlabs_v4_pipeline.py plan
python3 tools/elevenlabs_v4_pipeline.py preflight
```

With the exact hash printed by `plan`:

```bash
python3 tools/elevenlabs_v4_pipeline.py add-voices \
  --plan-sha256 62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889 \
  --allow-account-write

python3 tools/elevenlabs_v4_pipeline.py generate \
  --plan-sha256 62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889 \
  --allow-billed-generation

.tools/local-media-env/bin/python tools/elevenlabs_v4_pipeline.py validate-stage
```

If validation reports no hard holds, activate the complete automatically validated set directly:

```bash
.tools/local-media-env/bin/python tools/elevenlabs_v4_pipeline.py activate \
  --plan-sha256 62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889
```

If validation reports hard holds, listen only to those takes. Create a truthful review receipt containing the frozen plan and casting hashes, `decision: "accepted"`, reviewer and time fields, and exactly the held audio IDs. Then run:

```bash
.tools/local-media-env/bin/python tools/elevenlabs_v4_pipeline.py activate \
  --plan-sha256 62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889 \
  --review-receipt assets/audio/elevenlabs-v4-script-v2/manual-review.json
```

## Required `script_v2.py --apply` hook

This hook is installed at the end of `apply_content`, after all generated content files are written:

```python
from script_v2_voice_overlay import apply_overlay_to_content_dir

apply_overlay_to_content_dir(content_dir)
```

The helper is a no-op before an overlay exists. Once recordings are staged, it verifies the current casting fingerprint, copy aliases, speaker and voice identities, model, campaign/storybook inventories, exact text hashes, audio hashes, and mouth-cue hashes before restoring the overlay. It injects storybook narration only when the complete validated set has been activated.

## Later additions

New or rewritten dialogue is recorded separately from the frozen 873-take production:

```bash
python3 tools/script_v2.py --apply
python3 tools/voice_additions.py plan
python3 tools/voice_additions.py generate \
  --plan-sha256 <hash printed by plan> \
  --allow-billed-generation
.tools/local-media-env/bin/python tools/voice_additions.py validate
```

If validation lists failures, first ask ElevenLabs Scribe for an independent transcript of the held takes. No script, key terms or prompt is sent. Then validate again:

```bash
.tools/local-media-env/bin/python tools/voice_additions.py independent \
  --plan-sha256 <same hash> \
  --allow-billed-transcription
.tools/local-media-env/bin/python tools/voice_additions.py validate
```

The same rules as the frozen production apply: a longer line passes on an exact independent transcript, and a line of four words or fewer needs exact local and independent transcripts. For takes that still fail, request only their next bounded attempt, check them again, and validate:

```bash
python3 tools/voice_additions.py retake \
  --plan-sha256 <same hash> \
  --allow-billed-generation
```

`retake` skips short lines whose local transcript is already exact, because only an independent check is missing; pass `--include-short` to regenerate them anyway. Each line is limited to three deterministic attempts. Generation refuses a changed plan hash, missing billing flag, enabled paid overage, insufficient included credits, partial receipt, or unresolved inflight marker. Never delete an inflight marker until the uncertain request has been reconciled; doing so could bill the same line twice.

When every take passes (or with `--partial`, leaving failed lines missing), stage, archive the batch and rebuild the content:

```bash
.tools/local-media-env/bin/python tools/voice_additions.py stage
python3 tools/voice_additions.py archive
python3 tools/script_v2.py --apply
```

`archive` moves the batch's attempts, receipts, checks and transcripts to `batches/<first 16 characters of the plan hash>/`, so a later batch can record a reworded line under the same audio ID. If a line keeps failing after three attempts, reword it and record it in a new batch rather than relaxing the comparison.

The additions tool keeps raw attempts and receipts under `assets/audio/elevenlabs-v4-additions/`, stages 48 kHz mono PCM16 runtime files under `game/assets/audio/voices/elevenlabs-v4-additions/`, and merges only takes whose current text, cast identity, voice, waveform hash, and QA status still match. It does not generate mouth cues. Confirm that `game/content/voice-manifest.json` has an empty `missing` list before release.

## Current blockers

Strict automated QA initially passed 753 of 873 audio IDs and held 120: 63 exact-ASR mismatches and 57 short ASR-ambiguous clips. After the independent check and correction below, 829 pass and 44 remain held: 42 transcript differences and two short ambiguities. Review only the current held takes with:

- `assets/audio/elevenlabs-v4-script-v2/manual-review.html`
- `assets/audio/elevenlabs-v4-script-v2/manual-review-required.csv`
- `assets/audio/elevenlabs-v4-script-v2/manual-review-required.json`

Deterministic comparator triage cleared 17 false positives caused only by equivalent clock formatting or possessive punctuation. Different times, changed clue values, dropped/added words, and lexical or homophone differences remain held.

The final comparator audit removed automatic `Wen`/`when` and `Tirel`/`Tyrell` substitutions. A failing regression demonstrated the unsafe acceptance before the fix. Revalidation added six holds and reclassified one existing short hold as a mismatch, producing the earlier 120. The 114-hold count in `comparator-triage.json` describes the intermediate formatting-only pass.

Fresh Godot import validation passes all 2,623 voice-asset checks. The publishing copy initially failed to draw the legacy voicemail waveform because four fallback `.wav.import` settings had not been copied. Those evidence imports now retain uncompressed PCM, matching the production preparation and preserving the actual-sample comparison assertions.

Open `manual-review.html` in a browser beside its `masters/` directory to listen. The page contains story spoilers and does not approve or change recordings. Account preflight, account-add receipts, quota summaries and inflight state stay local and are excluded from the public repository.

Final activation requires a truthful review receipt for every remaining held ID. No unresolved mismatch or ambiguity is auto-accepted.

The additional native story-flow rerun also remains blocked by timing failures in both tested renderers. See the voice-staging follow-up in `docs/play-report-2026-11-20.md`. Passing the audio-file checks does not make the complete voiced game release-ready.

## November 21 automatic retakes

At the user's request, two bounded passes re-recorded 17 lines with unresolved word differences. The first pass used a new frozen seed and stability of at least 0.62. Only its 11 remaining failures received a second take at stability 0.78. Script text, model, casting and voice identities stayed unchanged.

The 28 requests consumed **1,163 included credits**, summed from the API billing receipts. Read-only account checks confirmed that paid overage remained disabled before and after generation. That generation pass used local transcription only; the separately authorized Scribe check is recorded below.

All candidates, request receipts, frozen plans, decoded masters and independent local ASR reports are preserved under `assets/audio/elevenlabs-v4-script-v2/retakes/automatic-01/` and `automatic-02/`. The original production masters and receipts are untouched.

Eight lines now have a candidate with zero word edits: `c10_live.first.02`, `c1_dinner.out.03`, `c1_flat.compare.02`, `c4_escape.out.01`, `c7_gate.out.05`, `c7_swap.recap.03`, `c8_lab.lastpage.find` and `c9_wake.agnes.find`. Nine selected lines still disagree with the local recognizer after both attempts. No short-line or homophone gate was relaxed.

These were candidate results, not a listening approval or an activated voice pack. Subsequent independent checking accepted six candidates for staging, as described below. Further repeated generation is paused rather than spending credits on the same unresolved recognition results.

The latest text-only CoreAudio/Compatibility story-flow run passed all 94 executed assertions. Earlier Dummy-driver failures remain recorded in the play report.

## Independent transcription and splice repair

The user explicitly authorized ElevenLabs transcription within included credits only. Scribe v3 processed the 120 originally held clips, the source voicemail, and the repaired splice: **122 requests, 183 credits reported in saved billing headers**. The observed account-wide included-credit change was 219; the difference is not reconciled, so the header sum is not an exact account-usage total. Paid overage was checked and remained disabled. No expected script, keyterms or transcript-edit instructions were sent. Raw responses, word timings, input hashes and request metadata are retained under `independent-asr/scribe-v3*/`.

The original splice really lost a word: both models omitted "Tonight." The source-bound Scribe alignment located it at 3.04-3.52 seconds; the old cached alignment cut at 2.84-3.16. The corrected 1.94-second splice now transcribes exactly. Its old waveform and edit receipt are preserved in hash-named `masters/history/` and `edit-receipts/history/` files. Future staging requires the matching independent source alignment and rejects stale, prompted or inconsistent evidence.

Independent evidence is compared with the unchanged strict comparator and bound to the actual waveform, script and production plan. Longer lines can pass an exact independent transcription. Lines of four words or fewer require exact local and independent transcripts. Local recognition is retained separately so replaying a saved Scribe result cannot masquerade as two independent checks. `listening_reviewed` remains false.

Six retakes passed both models and were adopted with fresh mouth cues: `c10_live.first.02`, `c1_dinner.out.03`, `c7_gate.out.05`, `c7_swap.recap.03`, `c8_lab.lastpage.find` and `c9_wake.agnes.find`. Each keeps its actual candidate generation-plan hash and request ID alongside the canonical script-plan identity. Original masters and generation receipts remain intact. The two other locally passing candidates disagreed with Scribe and were not adopted.

The resulting inventory is **829 automated passes and 44 holds**, not a listening-approved release. Some remaining differences are names, homophones, spelling or date formatting; others may be real word errors. No lexical substitutions or script edits were used to hide them. Both playback gates remain disabled pending listening review, followed by a complete voiced walkthrough.

## November 21 Chapter 1 additions

Chapter 1 and the prologue gained 100 new or reworded voiced lines: small talk, ordinary morning conversation, the pier and work-order leads, and updated findings. Two batches used 4,765 + 167 characters of speech, plus 7 retakes and 27 Scribe transcription requests (the saved evidence keeps the latest per line), within included credits with paid overage disabled. Local Whisper passed 79 of the first 100 takes. Independent Scribe transcripts and retakes cleared all but two lines, where both recognizers wrote "AutoRick" as two words. Those two lines were reworded ("the new radio host", "the radio") and recorded in the second batch, which passed. No comparison rule was relaxed and no take was marked as listening-reviewed.

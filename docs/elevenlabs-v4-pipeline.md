# ElevenLabs v4 production pipeline

Status: prepared and dry-run only. No voices were added and no speech was generated.

## Frozen dry run

- Plan: `assets/audio/elevenlabs-v4-script-v2/plan.json`
- Plan SHA-256: `62defb34544fc3952ffeaad2e9c50f3f5b631cdea29074defa724e17996ca889`
- 874 CSV recording entries; the full campaign and storybook inventory has 878 references, deduplicated to 873 audio IDs
- 872 billed speech requests and one verified local edit, `recording.saren_splice`
- 66,442 unique utterance characters
- 66,497 request characters after supported Eleven v4 whisper tags
- Estimated charge: 67,405 plan credits

The estimate includes the Voice Library multiplier reported for AGEIS-7: 3x credits for its seven lines. Its `fiat_rate` metadata is 0.25, but ElevenLabs documents this legacy custom rate as a credit multiplier, not automatic account overage. Every other selected voice reports a 1x rate.

The read-only preflight confirmed:

- `eleven_v4` is currently available for text to speech.
- The account has sufficient included credits for the frozen plan.
- Paid overage is disabled and the pipeline refuses to run if it becomes enabled.
- All 24 shared voices are currently discoverable and fit in the available slots.
- The two premade voices are available.

## Safety and resume behavior

`tools/elevenlabs_v4_pipeline.py` freezes the recording list, final script, casting-file fingerprint, model, voice IDs, text, context, supported v4 controls, and deterministic seeds. It deduplicates by audio ID, including the delayed Nora message that the CSV currently marks twice as `record`.

Each paid request gets an adjacent MP3 and JSON receipt with its exact request ID, trace ID, character cost, model, voice ID, plan hash, text hashes, and audio hash. An inflight marker is written before every POST. Any auth, rights, rate, network, or uncertain-response failure stops the run. A restart skips only matching, complete receipts and refuses unresolved inflight requests.

Validation is offline:

- Decode to mono 48 kHz PCM without overwriting historical masters.
- Run the local Whisper QA model without downloading weights.
- Mark exact independent ASR matches as `automated_qa_passed` only after format, finite-sample, level, duration, hash, and lip-sync checks also pass.
- Never claim an automated take was listening-reviewed.
- Hard-hold true transcript mismatches, short ASR-ambiguous clips, and uncertain voicemail/splice boundaries for actual review.
- Build and verify Rhubarb mouth cues.
- Preserve `recording.greeting` as one uncompressed waveform everywhere it is reused.
- Build `recording.saren_splice` only from proven word boundaries in the new Helen voicemail, with a source/edit receipt.
- Stage new runtime WAVs under `game/assets/audio/voices/elevenlabs-v4-script-v2/`.
- Keep voice and storybook narration disabled until the complete set has either passed automated QA or received actual review for its hard holds.
- On every replay, reject a changed casting fingerprint or any take whose exact speaker, canonical copy identity, voice ID, or model no longer matches the authoritative cast. This includes reused fixed recordings.

## Commands after parent GO

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

## Current blockers

1. Parent GO after art review, full play, and walkthrough.
2. The 24 shared voices still need to be added to the account.
3. Final activation requires complete local ASR/lip-sync validation. Only hard-held mismatches or ambiguities require actual listening review. No quality failure is auto-accepted.

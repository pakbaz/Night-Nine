# Script v2: how the revision tool works

This folder holds the reviewable output of the Night Nine script revision. The revision itself lives in `tools/script_v2/*.json`. The tool that merges, checks and renders it is `tools/script_v2.py`. Read this page first if you are picking the work up cold.

## In one paragraph

The base story is a pristine copy of the game content in `tools/script_v2/base/` (mainly `campaign.json` and `storybook.json`). Each edit file in `tools/script_v2/` describes changes to some scenes: new or rewritten lines, puzzle text, hints, wrong-answer feedback, findings and recaps. The tool applies every edit on top of the base, checks the result against the project rules, and writes the full revised script into this folder. Nothing in `game/` changes unless you ask for it with `--apply`.

## Commands

```
cd "/Users/pakbaz/code/Night Nine"
python3 tools/script_v2.py           # merge, validate, render docs/script-v2/
python3 tools/script_v2.py --apply   # same, then write game/content/*.json (only if there are 0 errors)
```

The first command prints a one-line total and `N errors, M warnings`. Keep it at **0 errors and 0 warnings** after every batch of edits. It exits with code 1 when there are errors.

`--apply` writes the revised scenes, lines, cast, storybooks, notebook cases and dependent catalogs (narration, voice manifest, lip sync, staging, hotspots, films, music) into `game/content/`. Applying twice produces identical content. Scene-specific portraits and the ending reward music also survive this regeneration.

## Files

| File | What it holds |
| --- | --- |
| `tools/script_v2.py` | The tool. Merge, validate, render, and apply. |
| `tools/script_v2/base/*.json` | Pristine base content. Do not edit. |
| `tools/script_v2/00-global.json` | Display rules, spoiler rules, tasks with no finding, notebook cases. |
| `tools/script_v2/01-prologue-ch01.json` | Opening storybooks, prologue, Chapter 1. |
| `tools/script_v2/02-ch02.json` to `09-ch09.json` | One chapter each. Interlude 1 is in `03`, Interlude 2 in `06`, the flashback in `08`. |
| `tools/script_v2/10-ch10-epilogue.json` | Chapter 10, epilogue, one year later, after the credits, closing storybook. |
| `tools/script_v2/11-character-art.json` | Scene-specific portrait selections, keyed by the existing speaker identities. |
| `docs/story-walkthrough.md` | Complete spoiler-marked story walkthrough, puzzle solutions, clue support and final continuity review. |
| `docs/script-v2/script.md` | Generated. The whole revised script in play order, for reading. |
| `docs/script-v2/script.json` | Generated. The merged content, for tools and the engine. |
| `docs/script-v2/recording-list.csv` | Generated. Every voiced line with speaker, voice, delivery and plan. |
| `docs/script-v2/report.md` | Generated. Totals, errors, warnings, engine features the script needs. |
| `docs/script-v2/changes.md` | Hand written. What changed and why, per chapter and per plan item. |
| `docs/script-v2/README.md` | This page. |

Never edit the generated files by hand. Change an edit file and run the tool.

## Edit file format

Each edit file is a JSON object with up to three keys: `global`, `scenes` and `storybooks`. A scene may be edited in one file only.

### Scene fields

`title`, `place`, `when`, `objective`, `objective_steps` (later objectives, in order), `coach` (a tip card), `card` (chapter card), `present` (speaker keys shown and checked as present), `next`, `chapter`, `actors`, `departure_art` (optional resource path for the outro painting).

Line groups, each a list of line references (see below):
- `context`: narration before the intro. New lines here default to narration.
- `intro`: the opening conversation.
- `recap`: narration when the scene is cleared. New lines default to narration.
- `outro`: the departure.

Also: `tasks` (by task key), `task_order`, `delete` (base line ids you mean to drop), `changes` (plan item codes, for the record) and `notes` (implementation notes for the engine, sound and art).

### Task fields

`title`, `type` (`beat`, `choice`, `compare`, `rows`, `tape`, `dial`, `board`), `difficulty`, `actor`, `requires` (task keys in the same scene), `goal`, `background` (shown as "What Steve knows"), `prompt`, `options`, `answer`, `wrong` (feedback per wrong option index), `hints` (exactly three), `lead` (lines played when the lead first opens), `lines` (lines played on success), `finding` (one narration line after success), `note` (notebook text, defaults to the finding), `evidence_labels`, `audition_labels`, `sounds`.

Rows puzzles use `instruction` and `rows`: `[{"label", "options", "answer"}]`.
Case boards use `board`: `{"instruction", "evidence", "stages", "wrong_text"}`. Each stage has `mode` (`order`, `match`, `route`), `prompt`, `slots`, `pieces` and `answer` (one piece index per slot). More pieces than slots means decoys.

Optional task `art` is a resource path shown with the lead, puzzle and finding. Both task art and departure paintings are checked for missing files.

### Character variations and completion reward

`global.scene_appearances` maps scene IDs to `{speaker: portrait_folder}`. It merges into the existing illustrated directions without changing the speaker, voice, save identity or walking sprite. Unspecified portraits retain their existing selection. The ten new portraits each have their own blink and mouth atlas; their masters and provenance are listed in `assets/characters/campaign/variations.json`.

The three new paintings in `game/assets/illustrated/campaign/rewards/` are reserved for the completion credit film, not the pre-game credits. The original **Epilogue (BGM)** by S3pehR, generated with Google Lyria 3.5, accompanies that film from bar 15 (about 50.2 seconds). `tools/ending_reward.py` keeps it out of exploration, including the generic Epilogue fallback. The short **Epilogue** theme remains the final end-card cue after the last signal. No new music was generated.

### Line references

| Form | Meaning |
| --- | --- |
| `"c1_flat.in.02"` | Keep a base line. If it came from another place it is marked as moved. |
| `"steve|Text."` | A new line, speaker key before the bar. |
| `{"id": "...", "text": "...", "direction": "...", "delivery": "..."}` | Rewrite or restyle a base line. Only a text or speaker change counts as a rewrite. |
| `{"new": "speaker|Text.", "delivery": "...", "direction": "...", "display": "...", "display_text": "...", "sfx": "..."}` | A new line with extras. |

New line ids are made from their place, for example `c1_pier.ctx.01` or `c2_ship.intake.lead.01`, numbered in order. Inserting a new line before another new line renumbers the later one. That is harmless now, but once recording starts, add new lines at the end of a group.

Deliveries: `live`, `narration`, `phone`, `radio`, `intercom`, `broadcast`, `memory`, `voicemail`, `recorded_playback`, `private_recording`.

`display` changes the speaker label for one line (for example "Steve Mercer?" before Stephen names himself). `display_text` shows different text from what is spoken (pinyin on screen, a lowercase text message).

## What the validator checks

Errors:
- every edited task has a goal, a background, a prompt and exactly three hints;
- every task has a finding, except the ones listed in `no_finding`;
- beats have one option; choices have two or more, a valid answer and wrong-answer feedback for every wrong option;
- rows have a valid answer per row; boards have one to three stages and answers that fit their slots and pieces;
- `requires` points at real tasks; notebook cases point at real tasks;
- every speaker is in the cast; every delivery is known; no line is used twice;
- no spoiler pattern appears in any visible text before its allowed scene.

Warnings:
- a new or rewritten live line whose speaker is not in the scene's `present` list;
- a base line that is no longer used and is not listed in `delete`.

It cannot check that a puzzle is fair, that hints do not give the answer, or that facts agree across chapters. Those need a human or agent read of `script.md`. See `changes.md` for the last audit.

## Spoiler and display rules

Both live in `00-global.json`.

- `spoilers`: each rule has a regular expression and the first scene where it may appear (`from`), or `banned` for never. Visible text means titles, objectives, coach tips, goals, backgrounds, prompts, options, wrong feedback, hints, board text, notes shown to the player, line text and speaker labels. Examples: the word "copy" from `c2_aquarium`, "Iris" from `c6_iris`, "Stephen" from `c5_station`, "echo" and "Veyri" from `i1_archive`, the bluff from `c7_swap`, Mrs. Penhallow's secret from `c10_town`. Watch ordinary words too: "Copy every detail" in a Chapter 1 hint is an error.
- `display`: `[speaker, last scene, label]`. Up to and including that scene the speaker is shown with that label. For example Nora's copy is "Nora Reyes" through `c1_escape` and "Nora's copy" through `c6_iris`; the Prefect is "The Prefect" until the Archivist's interlude; the sleeping Mrs. Penhallow is "Mrs. Penhallow, row three" through `c9_wake`.
- Writing rules for player-facing text: short plain sentences, no em dashes, no irony or jargon, hints escalate and never state the answer, wrong-answer feedback is kind, specific and does not reveal the right option, every lead comes from a relationship or a role in town.

## Voice and recording

- Casting: `docs/voice-casting.md` and `docs/voice-casting-2026-11-20.json` (ElevenLabs `eleven_v4`, one library voice per role; aliases such as `iris` to `nora` share a voice).
- `recording-list.csv` lists every line in play order with `voice`, `voice_id`, `delivery`, `direction`, `text`, `status` and `plan`. `plan` is `record`, or `reuse <line>` when the same fixed recording (for example `recording.release`) plays again.
- The user authorized new recordings on November 20, **after the art, full walkthrough and final review/playthrough**. The voice manifest switch `enabled` stays false until recording and validation are complete. The engine plays a recording only when its text hash matches the line, so any line edited after recording falls back to subtitles.
- Read-only ElevenLabs preflight is allowed; generation remains the last production step. On-screen-only text (hints, wrong feedback, board text, prompts) is never recorded.
- Some sounds are edits, not new takes: `recording.saren_splice` is cut from the new Helen voicemail take. Scene `notes` list every new sound asset.

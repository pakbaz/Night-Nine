# Script v2 runtime content contract

`python3 tools/script_v2.py --apply` writes this contract to
`game/content/campaign.json`. The immutable merge base is
`tools/script_v2/base/`; the command never merges against its own output.
`status`, `changes`, `edited`, `deleted_tasks`, `from`, scene `notes`, and the
review-only `storybooks`/`display_rules` are intentionally omitted from runtime
content.

## Top level

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `schema` | integer | File format revision. | `1` |
| `version` | string | Campaign content revision. | `"campaign-3"` |
| `title` | string | Game title. | `"Night Nine"` |
| `source` | string | Adaptation source note. | `"User-approved final Plot.pdf..."` |
| `adaptation_status` | string | Scope/status note. | `"Complete playable English adaptation..."` |
| `cast` | object<string,string> | Stable speaker key to full character name. | `"steve": "Steve Mercer"` |
| `scenes` | array<scene> | Ordered campaign scenes. | `[{ "id": "p_bay", ... }]` |
| `lines` | object<string,line> | Dialogue records keyed by stable line id. | `"p_bay.in.01": {...}` |
| `sound_labels` | object<string,string> | Player-facing labels for auditionable sounds. | `"effect.wick": "Listen: Wick’s signal"` |
| `notebook_cases` | object<string,case> | Hypothesis notebook pages. | `"greeting": {...}` |

## Scene

Fields marked **new** were added by script v2.

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Stable scene key. | `"c2_ship"` |
| `chapter` | string | Chapter grouping. | `"Chapter 2"` |
| `title` | string | Scene title. | `"Sixty-one percent"` |
| `place` | string | Displayed location. | `"The Long Patience, scan chamber"` |
| `style` | string | Room/ambience style key. | `"ship"` |
| `actors` | array<string> | Playable investigator keys. | `["steve"]` |
| `present` **new** | array<string> | People who may speak live in the scene. | `["steve","iris","saren"]` |
| `when` **new** | string | Player-facing date/time. | `"Sunday, October 21..."` |
| `objective` | string | Current scene objective. | `"Record a command..."` |
| `objective_steps` **new** | array<string> | Later objective text, in order. | `["Get out of the locked apartment."]` |
| `coach` | string | Initial interaction tip. | `"Click the glowing radio..."` |
| `card` | object | Chapter-card metadata; normally `chapter` with `kicker`, `title`, `when`, and `goal`. | `{"chapter":{"title":"The Bay Is Singing"}}` |
| `context` **new** | array<string> | Line ids played before `intro`. | `["c1_flat.ctx.01"]` |
| `intro` | array<string> | Arrival line ids. | `["c2_ship.in.01"]` |
| `tasks` | array<task> | Ordered leads. | `[{ "id": "c2_ship.command", ... }]` |
| `recap` **new** | array<string> | Lines played after the last task and before departure. | `["c2_ship.recap.01"]` |
| `outro` | array<string> | Departure line ids. | `["c2_ship.out.02"]` |
| `next` **new** | string | Authored transition instruction/copy. | `"Chapter 3 begins..."` |
| `departure_art` **new** | string | Optional painting shown during the outro and departure cut. Takes priority over `chapter_insert`. | `"res://assets/illustrated/campaign/inserts/c3_archive-boathouse-stakeout.webp"` |
| `shots` | array<object> | Existing cinematic shot directions (`duration`, `move`, `direction`). | `{"duration":5.0,"move":"establish",...}` |

`context`, `intro`, `lead`, success `lines`, `finding`, `recap`, and `outro`
contain line ids. Resolve each id through top-level `lines`.

## Task / lead

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Stable task key, prefixed by scene id. | `"c2_ship.intake"` |
| `title` | string | Hotspot/panel title. | `"The flooded intake"` |
| `type` **new** | enum string | UI contract: `beat`, `choice`, `rows`, `board`, `tape`, `dial`, or `compare`. | `"choice"` |
| `kind` | string | Story/gameplay semantic retained for specialized behavior. | `"playback"` |
| `difficulty` **new** | integer | Authored relative difficulty. | `2` |
| `actor` | string | Required playable actor, or `""`. | `"steve"` |
| `requires` | array<string> | Task ids that must be done first. All are in the same scene. | `["c2_ship.nora"]` |
| `goal` **new** | string | What the player is trying to accomplish. | `"Call for help..."` |
| `background` **new** | string | Fair, spoiler-safe “What Steve knows” context. | `"The tunnel runs back..."` |
| `prompt` | string | Immediate question or action. | `"Which spool will bring help?"` |
| `lead` **new** | array<string> | Conversation played once when the lead first opens, before the puzzle. | `["c2_ship.out.01"]` |
| `options` | array<string> | Choice/beat answers. A beat has exactly one. | `["Spool A...", "Spool B..."]` |
| `answer` | integer | Zero-based correct `options` index. | `0` |
| `wrong` **new** | object<string,string> | Wrong option index to its specific reason. | `"1": "That’s the whistle..."` |
| `hints` | array<string> | Exactly three hints, least to most direct. | `["Who has never once ignored...?", ...]` |
| `lines` | array<string> | Success dialogue line ids. | `["c2_ship.intake.01"]` |
| `finding` **new** | string | One narration line id played after solve. | `"c2_ship.intake.find"` |
| `note` | string | Evidence/notebook summary. | `"Nora is alive..."` |
| `sounds` | array<string> | Voice/effect ids available for audition. | `["effect.nora_whistle", ...]` |
| `evidence_labels` | array<string> | Labels parallel to `sounds` for comparison evidence. | `["Pump corridor","Filter corridor"]` |
| `audition_labels` | array<string> | Labels parallel to `sounds` for choice audition buttons. | `["Spool A...", ...]` |
| `art` **new** | string | Optional evidence painting shown in the lead panel, the puzzle, and its finding. | `"res://assets/illustrated/campaign/inserts/c1_escape-north-wing-work-order.webp"` |
| `puzzle` | object | Specialized rows, tape, dial, or board data below. | `{"instruction":"Mark the command...",...}` |

`requires` is an AND dependency. A lead is locked until every listed task is
done; the lock message should name those prerequisites. Play `lead` only on the
first opening. On success play `lines`, then `finding`. After the last task,
play scene `recap`, then `outro`/transition.

For choices, use `wrong[str(index)]` after a miss, disable that missed option,
and offer hint 1 after two misses. `goal` and `background` belong on every
puzzle panel. A `beat` is one Continue action, not a quiz.

### `puzzle`

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `instruction` | string | Specialized puzzle directions. | `"Place each event..."` |
| `rows` | array<object> | Rows with `label` and `options`. | `{"label":"Date","options":["May 29",...]}` |
| `solution` | array<int> | Correct option index per row; for boards, flattened stage answers. | `[1,0,2]` |
| `presentation` | string | Specialized renderer: `case_board` or `tape_alignment`. | `"case_board"` |
| `hints` | array<string> | Same three hints, copied for specialized renderers. | `[...]` |
| `recording` | string | Tape audio id. | `"recording.greeting"` |
| `lead_a`, `lead_b` | number | Initial tape alignment positions. | `0.2` |
| `evidence` | array<string> | Case-board facts shown above the board. | `["Tape edge, left to right..."]` |
| `stages` | array<stage> | One to three board stages. | `[{ "mode": "match", ... }]` |
| `wrong_text` | string | Board-level incorrect-placement response. | `"Something here doesn’t match..."` |

A board stage has `mode` (`order`, `match`, or `route`), `prompt`,
`slots` (1–5 unique labels), `pieces` (unique labels, count at least the slot
count), and `answer` (one distinct zero-based piece index per slot). Extra
pieces are decoys. No decoy index appears in `answer`.

## Line

| Field | Type | Meaning | Example |
| --- | --- | --- | --- |
| `id` | string | Stable line id. | `"c2_ship.intake.01"` |
| `speaker` | string | Stable cast key; never use it as display copy. | `"iris"` |
| `display` **new** | string | Effective name to show in this scene. Present on every line. | `"Nora’s copy"` |
| `display_speaker` | string | Compatibility alias of `display`. | `"Nora’s copy"` |
| `text` | string | Exact spoken/subtitle text and voice-hash source. | `"Come on, Admiral..."` |
| `display_text` | string | Optional alternate visible text while `text` remains spoken audio. | `"“he remembers june...”"` |
| `audio` | string | Voice-manifest take key. | `"c2_ship.intake.01"` |
| `delivery` | enum string | `live`, `narration`, `phone`, `radio`, `intercom`, `broadcast`, `memory`, `voicemail`, `recorded_playback`, or `private_recording`. Missing means `live`. | `"intercom"` |
| `direction` **new** | string | Performance/staging direction. | `"a whisper"` |
| `cue` | string | One sound effect key triggered with the line. | `"ninth_night"` |
| `sfx` **new** | string | Authored sound-direction text, sometimes naming layered effects. | `"effect.harbor_winch under effect.nora_whistle_flat"` |
| `reaction` | object | Timed non-verbal reaction with `sound` and visible `caption`. | `{"sound":"delegates_laugh",...}` |

`display` is authoritative visible speaker text. `delivery` selects caption
styling: `phone` is a call, `radio` a receiver, `intercom` a live PA,
`broadcast` a wide public transmission, `memory` remembered speech,
`narration` internal/story narration, `voicemail` a message,
`recorded_playback` an audible replay, and `private_recording` a recording
created now but not audibly replayed in that scene.

## Notebook and voice

Scene portrait selection lives in illustrated directions as `appearances`:
`{"steve": "steve_morning", "iris": "nora_warm"}`. Author this through
`global.scene_appearances` in `tools/script_v2/11-character-art.json`, not the
generated file. Values name `game/assets/illustrated/cast/<profile>/sprite.json`
folders. They change appearance only, never character or voice identity.
Explicit selections take priority over the default paired conversation pose.
Omitted entries preserve existing appearances, including Iris's ending identity.

A notebook case has `title`, `clues` (task ids), and `theories`. Each theory has
stable `id`, unlock task `after`, and `text`. The existing notebook UI reads
this shape unchanged.

`voice-manifest.json` has `enabled: false` during the text-only milestone.
Every take has `text_hash`, the first 16 lowercase hex characters of SHA-256 of
the exact `take.text` it was recorded from. Playback requires both global
`enabled == true` and equality with SHA-256 of the current line `text`.
Missing audio must never suppress subtitles.

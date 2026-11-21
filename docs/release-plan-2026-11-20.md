# Night Nine release plan: script v2, zero-cost hosting, credits, first full play

Written 2026-11-20; hosting and credits updated 2026-11-21. This is the working brief for any agent that continues the project. It replaces earlier open questions.

## Hard rules

1. **Zero spend.** Hosting uses free tiers only. No paid plan, no Workers or R2 usage that needs a payment method, no per-request compute.
2. **Recording is the final step.** On November 20 the user authorized ElevenLabs recording (eleven_v4, casting in `docs/voice-casting.md`) after the new art, full walkthrough and final review/text-only play. Read-only account preflight is allowed. Do not generate before those prerequisites are complete or enable paid overage.
3. **Every deployed file is 24 MiB or smaller.** Cloudflare Pages allows 25 MiB per asset and 20,000 files per site on the free plan (checked 2026-11-20 at developers.cloudflare.com/pages/platform/limits/). We keep 1 MiB of margin.
4. **Script rules.** No spoilers before a scene's allowed point, hints never give the answer, every lead has a reason that comes from the relationships and the town's roles. The rules live in `tools/script_v2/00-global.json` and are enforced by `python3 tools/script_v2.py`.
5. **Scope.** Do the smallest complete change. No extra features. Finish a milestone before starting the next one.

## Decisions

| Topic | Decision |
| --- | --- |
| Game host | Cloudflare Pages free plan, direct upload (no Cloudflare build minutes). Static files only, no Functions. Bandwidth for static assets is not metered. |
| Code host | GitHub (`pakbaz/Night-Nine`). The site links to its exact committed source archive. Optional local source ZIPs are not deployed. GitHub Pages is retired. |
| Large files | Split `play.pck` and `play.wasm` into parts of at most 24 MiB. A small loader in the page rebuilds them in the browser. The engine does not change. |
| Scale | Browsers cache the parts after the first visit (service worker plus HTTP cache). Part names carry their hash, so they cache forever. A new release only re-downloads changed parts. |
| Voice during testing | Text only with subtitles. The engine plays a recording only when the recording's text hash matches the line. Until recording, the manifest switch `enabled` is false. |
| Art | GPT Image 2.6, only where the script needs a new picture. Match the painted style of the existing rooms and inserts. |
| Credits | Cards listed in "Credits text" below. |

## Credits text

Four pages: original creator, browser engine, all creative AI credits, and GitHub/Copilot/Cloudflare together. Each entry keeps its role and name. Preserve the 56.4-second film and its existing artwork and music.

- Original story (written 25 years ago), plot, music, voice and creative design decisions: S3PehR
- Built using: Godot Engine for Browsers
- Creative narration, game script refinements and gameplay design: Claude Opus 5.5
- Game engine core design and stages setup: GPT Astra 6.2
- Artwork and pictures, including characters: GPT Image 2.6
- Music creation: Google Lyria 3.5
- Voices: ElevenLabs 4
- Deployment, verification, testing and game debugging: GitHub Copilot Fusion
- Code hosting: GitHub
- Game hosting: Cloudflare Pages

Credit names follow the user's requested spelling, including "S3PehR" and "GPT Astra 6.2".

## Milestones

### M1. Script rundown (done when the user has read it)
`docs/script-v2/changes.md` lists what changed per chapter and how every item C01 to C37 and every critic item was handled. `docs/script-v2/README.md` explains the tool, the edit format and the integration. The script validates with 0 errors and 0 warnings.

### M2. Engine and content integration
- `python3 tools/script_v2.py --apply` writes the revised scenes, lines, cast, storybooks, notebook cases and sound labels into `game/content/*.json`. It can run twice with the same result.
- Engine features (smallest version of each):
  1. Lead-in conversation when a lead opens, before its puzzle.
  2. Finding narration after each solved puzzle.
  3. Recap narration when a scene is cleared, then the automatic move to the next area or cutscene.
  4. Wrong answers show their reason in the panel, the missed option is disabled, and hint 1 is offered after two misses.
  5. Goal and "What Steve knows" are shown on every puzzle panel and board.
  6. Beats use one Continue button.
  7. Case boards accept decoy pieces (more pieces than slots) and 1 to 5 slots.
  8. Hint buttons say "Hint 1 of 3".
  9. Locked leads say what unlocks them.
  10. Delivery styles (phone, radio, intercom, memory, narration) change the caption look.
  11. Text-only playback: no recording means the subtitle stays for a time based on its length, and a click or key continues.
- Saves written before this change still load (old task ids are migrated or ignored safely).
- `bash tools/test-campaign.sh` passes, with tests updated for the new content and rules.

### M3. Extra art
List every art need from the scene `notes` in `docs/script-v2/script.json`. Make only the pictures a puzzle needs (for example Carmen's photo strip and the work order). Generate with GPT Image 2.6 using existing paintings as style references. Store in `game/assets/illustrated/campaign/inserts/`, keep each file well under 24 MiB, and register them in the content.

User expansion on November 20: ten main-character variations across nineteen scenes, plus three exclusive happy-ending paintings. The variations preserve face, voice identity and wardrobe continuity and include individual facial animation atlases. Completion paintings play only in the ending credit film. Use the existing Epilogue BGM exclusively there; generate no new music. See `assets/characters/campaign/variations.json` and `tools/script_v2/11-character-art.json`.

### M4. Size limit and loader (Cloudflare Pages)
- `tools/build-pages.py` produces a site where every file is 24 MiB or smaller and the file count is far below 20,000.
- `tools/split-site.py` (or the same script) writes `chunks.json` with part names, sizes and SHA-256 hashes.
- The page shell rebuilds `play.pck` and `play.wasm` from parts with progress, retries and hash checks, then starts the engine.
- The service worker caches parts and works offline after a full first load.
- `_headers` sets long cache lifetimes for hashed parts and short ones for the HTML.
- `tools/check-site.py` fails the build on any file over 24 MiB or any broken manifest. It runs in the GitHub workflow.
- `source.zip` stays outside the site. The landing page links to the exact GitHub commit archive.
- A local test serves the site and loads it in a real browser.

### M5. Credits
Update `game/ui/closing_credits.gd`, the tests that count credit cards, `README.md`, `MEDIA.md`, and the landing page.

### M6. One full text-only play
Play the whole game from the prologue to the final signal with subtitles and no voice using the scripted QA runs (`--story-qa`, `--campaign-qa`), then run the same full Control-input walkthrough in an isolated browser test export. Also inspect the ordinary chunked browser build directly: opening, puzzles, feedback, automatic transitions, portraits, and save/reload behavior. Distinguish scripted coverage from direct browser interaction in `docs/play-report-2026-11-20.md`; do not call an automated run a human playthrough. Record every problem and fix blocking ones. A blocker is a puzzle that cannot be solved, a lead that never unlocks, a missing line, a spoiler, or text that does not fit its panel.

### M7. Deploy (review preview authorized)
The user authorized the live preview at https://review.night-nine.pages.dev. Pushes to `main` deploy checked builds to the Cloudflare `review` branch. GitHub Pages and its publishing workflow are retired. Keep the production branch separate from the review preview; the planned final release date remains December 24, 2026.

### M8. Voices (authorized after M3 and M6 plus walkthrough presentation)
Add the 24 library voices to the account, record the lines in `docs/script-v2/recording-list.csv` with `eleven_v4`, install them, set the manifest switch to true, and rerun M6 with sound.

## Free-tier safety notes

- Cloudflare Pages static requests are free and not capped. The limits that matter are 25 MiB per file, 20,000 files, and 500 builds per month. Direct upload does not use builds.
- Do not add Pages Functions or Workers. They count against a request quota.
- Keep GitHub Actions on standard runners in a public repository. That is free.
- If traffic ever grows beyond the plan, the first action is to turn nothing on. Static delivery needs no change.

## Handoff list

- Script tool and edits: `tools/script_v2.py`, `tools/script_v2/*.json`
- Review output: `docs/script-v2/` (script.md, script.json, recording-list.csv, report.md)
- Voices: `docs/voice-casting.md`, `docs/voice-casting-2026-11-20.json`
- Original problem list: `docs/revision-plan-2026-11-20.md`
- Hosting numbers: `PUBLISHING.md`

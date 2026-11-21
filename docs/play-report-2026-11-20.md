# Night Nine: script-v2 play report

Completed November 20 local time / November 21, 2026 UTC. This report covers the text-only game before replacement voices.

## Result

The complete illustrated campaign reaches the final signal, saves completion, reloads the ending, and opens the final notebook transcript. Both the native rendered walkthrough and the browser walkthrough completed **34 scenes and 101 tasks, with 6,284 checks and zero failed assertions**.

This is automated Control-input coverage, supplemented by direct browser interaction and visual inspection. It is not a human first-time-player study or proof of performance on every device.

## Coverage

| Run | Result |
| --- | --- |
| Script merge and validation | 874 recording entries; zero errors and warnings |
| Native campaign core | 1,833 checks |
| Exploration floor / navigation / walking input | 782 / 732 / 28 checks |
| Tape / voice assets / animation | 23 / 2,617 / 10 checks |
| Soundtrack route | 351 checks, including all 30 recordings |
| Native boards / social staging | 767 / 151 checks |
| Native full rendered campaign | 6,284 checks; 34 scenes; completed |
| Rendered input / prologue / story / tape | 31 / 169 / 90 / 34 checks |
| Rendered boards / social / staging | 773 / 165 / 134 checks |
| Chromium WebGL 2 full campaign | 6,284 checks; 34 scenes; completed |
| Voice pipeline identity and validation guards | 6 Python tests passed |
| Portrait overrides / ending reward routing | 2 / 2 Python tests passed |
| Production chunking, retry and cache regressions | 7 tests passed |

Native runs used `bash tools/test-campaign.sh` and `bash tools/test-campaign.sh --render`. The browser run used an isolated copy with the same `campaign_runtime_qa.gd` and assertions, a test-only startup scene, isolated saves, and a JavaScript result handoff. No gameplay assertions were removed or weakened for the browser.

The staging count changed from 135 to 134 because two obsolete preparatory tasks were removed by the revised story and an automatic-departure assertion was added. This was not a removed staging check.

## Direct browser checks

The ordinary production-style export was split into 18 verified parts. Its static site had 39 files, with a maximum file size of 24 MiB. The local release manifest was `fe75003f5dd733a61e7d87d494b81a881040911ea532ac2870ad5634ac8bba33`.

Direct interaction covered the title, opening film, prologue object list, radio tuning and narrow-band control, recording the hum, finding narration, the unlocked phone puzzle, a deliberately wrong answer and its authored explanation, disabled rejected options, correct deduction, recap/departure, aftermath film, and Chapter 1's new morning portraits.

After a page reload, Continue restored the saved campaign. The local HTTP server was then stopped completely. A further reload still started the cached game, and Continue restored Chapter 1 offline. This verifies this build's first-load cache and same-origin browser save behavior.

The browser test's worst scene-level p95 frame time was 34.5 ms; the five slowest p95 scenes had median frame times of 16.6-16.7 ms. These measurements include test automation and screenshot work. Occasional roughly 1.2-1.4-second samples occurred during this instrumented run, so these figures are not a clean player-performance benchmark.

## Fixes and observations

- Fixed the `p_meeting` recorder camera crash. Its old task index no longer existed after script revision. The camera now uses the authored recorder position rather than indexing a removed hotspot.
- Verified lead-ins, findings, automatic recaps/departure, non-answer hints, confirmed Show Answer, contextual actor labels, delivery styling, saved progress and old-save migration.
- Verified scene portrait overrides, evidence/departure paintings and ending-only reward art. The existing Epilogue BGM is reserved for the completion film.
- The final credit spellings now match the request: **S3PehR** and **GPT Astra 5.2**. The 351-check soundtrack/credits suite passed again after that display-only change.
- Chromium emitted repeated WebGL buffer-binding warnings. The inspected scenes rendered and the complete walkthrough passed; these warnings remain a browser/engine compatibility observation.
- The browser test's explicit process-quit step emitted Godot allocator/resource cleanup diagnostics after the completed result. They are recorded separately from gameplay assertions. The ordinary browser game did not emit script errors during the direct interaction pass.
- The app's native browser-canvas read and screenshot tools timed out, so the browser review used Playwright instead.

## Remaining release gates

Replacement speech is now authorized for production. Activation still requires a complete checked set, correct cast identities, fixed-recording reuse, verified voicemail editing, and valid audio/lip-sync hashes. Ambiguous or failed takes must remain held rather than receive invented listening approval.

The two legacy chapter-snapshot packaging tests are currently blocked by missing new-voice timings while the script is text-only. They are not counted among the seven passing static-site tests. Reconcile those snapshot tests and validate the final voice-enabled release before shipping.

The code repository is public. This work has not deployed a public game build. Cloudflare deployment remains subject to the user's separate go-ahead.

## Local evidence

- `tmp/full-browser-qa-results.json`: complete browser result and per-scene frame timings.
- `tmp/full-browser-qa-console.log` and `tmp/full-browser-qa-errors.log`: browser diagnostics.
- `tmp/final-text-web-*.png`: direct browser screenshots, including wrong-answer feedback, Chapter 1 portraits, reload and offline continuation.
- `tmp/final-credits-qa/score-route.json`: final credit spelling and soundtrack check.
- `docs/story-walkthrough.md`: full spoiler-marked story and puzzle solutions.

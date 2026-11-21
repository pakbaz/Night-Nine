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

The legacy chapter-snapshot packager has since been repaired to retain script-v2 lead-ins, findings, recaps, narration, ending artwork, take metadata and the disabled-playback gate. Its structural tests use rehearsal snapshots; a separate regression confirms strict releases reject unapproved playback. All 11 publishing-repository packaging tests pass. These are structural checks, not a voice-enabled chapter playthrough.

All 873 replacement audio IDs have now been produced: 872 speech requests and one verified local splice. Strict automated QA passes 753; 120 remain held for listening review (63 transcript mismatches and 57 short ambiguities). The final audit removed name-to-homophone substitutions instead of treating them as approval. Campaign voices and storybook narration remain disabled.

The fresh publishing import now passes all 2,623 voice-asset checks. Its initial legacy-voicemail waveform failure was traced to compressed fallback import settings omitted during copying. Restoring uncompressed PCM fixed it without changing the recording or weakening the waveform checks. See `docs/elevenlabs-v4-pipeline.md` for the review handoff.

The exported and fully played browser build above predates these voice-staging changes. A complete approved voice-enabled run and a new size/memory check are still required before a voiced release.

### Voice-staging follow-up: unresolved native timing

The fresh staging copy passes 1,845 campaign-core checks, 351 soundtrack checks, 2,623 voice-asset checks, seven pipeline tests and 11 packaging tests. Restoring the two previously truncated closing panels adds 12 campaign-content checks and six rendered-story checks.

The additional rendered story-flow run is **not passing**: 24 of 96 assertions failed with Metal, and 23 of 96 with the compatibility renderer, both using the silent Dummy audio driver. The first failure is the expected transition from the opening book to the prologue card; later checks cascade from that state. A diagnostic captured the opening still visible at audio time 61.19 seconds, before its 63.27-second end, after the test's wait expired. Neither complete run recorded a frame longer than 0.15 seconds.

A separate short Dummy-driver probe also showed audio time behind wall time, but this does not establish the cause of the full-run failures. The current native story timing remains an unresolved release gate. The completed browser walkthrough earlier in this report is historical evidence, not a passing result for this new staging revision. No timing assertions were weakened. An earlier attempt with a frame cutoff was incomplete and is not counted as a complete run.

The code repository is public. This work has not deployed a public game build. Cloudflare deployment remains subject to the user's separate go-ahead.

## Local evidence

- `tmp/full-browser-qa-results.json`: complete browser result and per-scene frame timings.
- `tmp/full-browser-qa-console.log` and `tmp/full-browser-qa-errors.log`: browser diagnostics.
- `tmp/final-text-web-*.png`: direct browser screenshots, including wrong-answer feedback, Chapter 1 portraits, reload and offline continuation.
- `tmp/final-credits-qa/score-route.json`: final credit spelling and soundtrack check.
- `docs/story-walkthrough.md`: full spoiler-marked story and puzzle solutions.
- `GitHub/Night-Nine/tmp/voice-story-recheck/`: complete Metal failure report and clock diagnostics in the local publishing checkout.
- `GitHub/Night-Nine/tmp/voice-story-compatibility/`: complete compatibility-renderer failure report in the local publishing checkout.

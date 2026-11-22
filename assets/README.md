# Production assets

This directory contains the editable production sources. Godot loads the optimized copies under `game/assets/`; those are separate, required assets rather than disposable duplicates.

| Directory | Contents |
| --- | --- |
| `environments/campaign/` | Location paintings, foreground layers and doors |
| `characters/campaign/` | Portrait masters, animation sheets and facial landmarks |
| `cinematics/campaign/` | Chapter-film artwork, moving subjects and shot directions |
| `audio/elevenlabs-v4/recordings/` | Existing approved dialogue recordings |
| `audio/lipsync-elevenlabs-v4/` | Timing data for the existing dialogue |
| `audio/elevenlabs-v4-script-v2/` | Frozen ElevenLabs v4 production plan, receipts, masters, checks and approved overlay |
| `audio/elevenlabs-v4-additions/` | Resumable later-dialogue batches, validation reports and approved additions overlay; runtime WAVs live under `game/assets/audio/voices/elevenlabs-v4-additions/` |
| `audio/ambience-campaign/` | Location ambience masters |
| `audio/ambience-prologue/` | Flashback ambience masters |
| `audio/soundtrack/` | Cue sheet and recording measurements; in-game MP3s are in `game/assets/audio/music/`, and the standalone loading theme is in `site/loading-screen-music.mp3` |
| `concepts/characters/` | Approved character references used by the production artwork |
| `cover/` | Cover artwork |

Keep the current recordings until replacement voices have been selected and reviewed. Re-recordings must also update the runtime WAVs, voice manifest, mouth timing and any sound-comparison evidence that uses the replaced recordings.

Engine imports, temporary QA exports, obsolete build copies, credentials, billing records and raw provider responses do not belong in this asset library.

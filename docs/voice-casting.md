# Voice casting

**Status: confirmed by the user on November 20, 2026**, after listening to every voice's ElevenLabs sample. Use these voices for every line, with the ElevenLabs **v4** model (`eleven_v4`). Machine-readable copy: [voice-casting-2026-11-20.json](voice-casting-2026-11-20.json) (also at `assets/audio/elevenlabs-v4/casting-2026-11-20.json`).

Characters with a copy share one voice, so the copy sounds exactly like the person it replaced. Narration lines (storybooks, scene context, findings and recaps) use the narrating character's own voice.

| Character | Speaker key | Also voices | Lines today | ElevenLabs voice | Voice ID | Source |
| --- | --- | --- | ---: | --- | --- | --- |
| Steve Mercer | `steve` | Stephen | 121 | Jonah Vale - Calm, Soft (cast as “Jonah Vale”) | `vveagfomyMCJLZsOPRP2` | Library |
| Nora Reyes | `nora` | Iris | 41 | Sloane - Bold and Polished | `m8AHWg36LJTQWKmfeGVv` | Library |
| The Archivist | `archivist` | - | 22 | Delphi - Transformational Narrator | `6HXfTcSnxaoT6uM4pTRP` | Library |
| Helen Mercer | `helen` | - | 17 | Carol - Relatable, Real, Likeable Grandma (cast as “Carol - Relatable, Real, Cool, Senior”) | `5u41aNhyCU6hXOcjPPv0` | Library, notice 90 days |
| Sheriff June Calder | `calder` | - | 17 | Eryn – Strong Female Military Commander (cast as “Eryn - Strong Female Military Commander”) | `wa4sQVgbDDzUDEzJwch3` | Library |
| Dale Kittredge | `dale` | Pell | 12 | Mike - Multi Trade Expert | `kSSJYNGo5Kev6qgwVloV` | Library |
| Agnes Penhallow | `agnes` | Agnes Penhallow, original | 12 | Nan - Warm Vintage Storyteller | `jVMsZEw3hfmEAe9OUUtS` | Library |
| Prefect Saren | `saren` | - | 12 | Brendan - English & Polite | `zWuETeFKPJFmK8TgAMRf` | Library |
| Dr. Lin Wen | `wen` | - | 9 | Christine - Deep, Real & Sincere (cast as “Christine - Deep, Real and Sincere”) | `OtI9u7gjScKYR7rOqBX2` | Library, notice 30 days |
| Dr. Evelyn Shaw | `shaw` | - | 9 | Jarin - Sarcastic and Raspy (cast as “Gretchen”) | `lRGgBdmdfHYNiqPVpbiS` | Library |
| Special Agent Adrian Rook | `rook` | Rook’s copy | 9 | Michael - Gruff and Serious | `iPYqcpY8j8Ap4jUf28I3` | Library |
| Frank Mercer | `frank` | - | 9 | Bill - Wise, Mature, Balanced | `pqHfZKP75CvOlQylNhV4` | Premade |
| President Elena Ward | `ward` | - | 5 | Deborah - Trustworthy, confident (cast as “Deborah- Trustworthy, confident”) | `lVpo6IOLjDX4LxkYRZyj` | Library |
| Thursday club operator | `operator` | - | 5 | Paul - Friendly Midwestern Storyteller | `yeV5pw6QxLLhU2SzG4vx` | Library |
| DJ AutoRick | `autorick` | - | 5 | Danny DJ - Radio Announcer Voice | `KLoixBflzS2a9rg6nT8x` | Library |
| The Choir | `choir` | - | 5 | Elariel X - Epic Queen Ethereal (cast as “Elariel X - Epic Ethereal Queen”) | `ksryVoNAGZT8GxWCTiVm` | Library |
| Carmen Reyes | `carmen` | - | 5 | Vanessa - Friendly & Engaging | `XjJZDs8qBsxY4vx0TGuV` | Library |
| Gus Albano | `gus` | - | 4 | Kelvin - Cheerful Call Center (cast as “Kelvin Southern Cheerful Call Center Voice”) | `bO5Ny9R2uMBrCDk66aEj` | Library |
| Lyle Boone | `lyle` | Lyle’s copy | 4 | Roger - Laid-Back, Casual, Resonant | `CwhRBWXzGAHq8TQ4Fs17` | Premade |
| Chinese delegate | `general_cn` | - | 3 | Junfeng (cast as “Junfeng - Confident & Calm”) | `RBUtdrDRjER5aScqHwAS` | Library |
| Tomás Reyes | `tomas` | - | 3 | HecBel - Conversational  (cast as “HecBel18 English”) | `KcCKZnyrGenSzoMrpu7I` | Library |
| Luis Reyes | `luis` | - | 3 | Luis - Poetic, Soft-Spoken Artist (cast as “Luis Carlos - Northern Mexican Accent”) | `5sPGxVw5vqj7a08c5Xbw` | Library, notice 180 days |
| American delegate | `general_us` | - | 2 | Kenton | `IUG7kl2EzGm6iS3Zorj4` | Library |
| Mateo Reyes | `mateo` | - | 2 | Luis - Narrator (cast as “Luis”) | `pHTIXPU0D9wgfJsumeMt` | Library |
| Rafa Reyes | `rafa` | - | 1 | Sebastian | `PbznH31DjtgyM0idevI0` | Library, notice 180 days |
| Ship attendant | `guard` | - | 1 | AGEIS-7 - AI Alignment == 10/10 | `55AvudlJMfCwL9pocDVh` | Library |

Some creators renamed their voices after casting. The voice IDs and samples are unchanged, so the picks stand. Always address voices by **voice ID**, not by name. "Luis - Poetic, Soft-Spoken Artist" (Luis Reyes) and "Luis - Narrator" (Mateo Reyes) are different voices.

## Checks on November 20, 2026

- ElevenLabs account: Creator plan, active, 0 of 128,995 monthly characters used, 1 of 30 voice slots used.
- Model `eleven_v4` is available, and all 26 voices are verified for it: 24 shared library voices and 2 premade voices (Bill and Roger).
- Each voice's current library sample has the same audio as the clip heard during casting. The listening page lives at `tmp/casting/confirm/` (local only).
- Access: the local ElevenLabs MCP server (`elevenlabs` in `~/.copilot/mcp-config.json`, started by `~/.copilot/bin/elevenlabs-mcp.sh` with the API key from the macOS Keychain service `elevenlabs-api-key`) supports `text_to_speech` with `model_id: eleven_v4`. The hosted server (`io-elevenlabs-mcp`, OAuth) is also configured.

## Before recording

1. Finish and freeze the revised script first. No audio has been generated for it.
2. Add the 24 shared library voices to the ElevenLabs account. This uses 24 of the 29 free voice slots. Premade voices need no slot.
3. Record soon after adding them. If a creator withdraws a voice, access lasts only for its notice period: Christine (Wen) 30 days, Carol (Helen) 90 days, Luis (Luis Reyes) and Sebastian (Rafa) 180 days.
4. Every role is recast, so re-record every line, including the fixed recordings that several scenes reuse (the greeting, the voicemail, Rook's reassurance, Saren's offer and release command). Do not mix old and new voices.

## How the voices were chosen

- Seven searches of the ElevenLabs library, one per group of characters, shortlisted four voices for each role from the character sheet in `docs/source-text/characters.txt` and the art prompts. A second round added five more per role, matched to each character's background and build. That made 8 to 10 options per role, each with its own preview clip.
- The casting page showed each character's portrait, line count by chapter and current in-game voice next to the candidates. The user picked 25 roles there.
- Nora: the user asked for the voice President Ward had before, a Higgsfield preset called "Sloane" that is not in the ElevenLabs library. Fifteen library voices were measured against Ward's five recorded lines on pitch, pitch range, brightness and timbre. "Sloane - Bold and Polished" was the closest by a clear margin and is cast for Nora and Iris. President Ward is now Deborah.

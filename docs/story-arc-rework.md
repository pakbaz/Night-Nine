# Story arc rework, November 18, 2026

The game used to open on the Archivist on Veyr, 900 years ago, with a decibel puzzle. Players met an alien they could not place before they knew who Steve was. The opening now eases in, and the ending mirrors it.

## New order

1. **Before the ninth night** (storybook, about one minute). Steve introduces Bellwether, his night shift at KBWR, his father's ham radio, his mother's quiet government work and the night they rowed out without him.
2. **Prologue: The Bay Is Singing** (playable). Frank and Helen on the boat. You tune the radio by ear and Helen leaves Steve the voicemail. This scene teaches clicking objects with one hands-on puzzle.
3. **Eighteen months** (storybook, about 45 seconds). The empty boat, the voicemail Steve still plays, losing his job to DJ AutoRick, and Nora. The final panel pulls back to reveal the title painting.
4. Chapters 1 to 10 as before, with two flashbacks moved to where the story explains them:
   - **Veyr** now closes Interlude 1. The Archivist has just left her report untouched, and the player enters her oldest memory.
   - **Sentinel Point** now opens Chapter 8. Dr. Lin Wen reads Helen's notebook, the player plays Helen in that room, and the chapter continues with "Your mother recorded the meeting accurately."
5. **Epilogue: A Place to Live**. The three visits are now plain conversations with one action each. There is nothing left to solve.
6. **After the ninth night** (storybook, about 70 seconds) between the lantern festival and "one year later". It mirrors the opening: the same harbor, La Marea, Frank's shack and KBWR, now changed.
7. **Good Morning** (one year later), credits, then the post-credits signal.

Every chapter now starts with a card: the chapter title, when and where it happens, and what Steve wants, taken from the "Steve wants" line in the plot. Flashbacks and the time jump get their own card page. The first scenes that introduce a tool show a one-line tip.

## Music and picture sync

We measured the tempo, first downbeat and per-bar loudness of all 30 recordings ([tempo cache](../assets/audio/soundtrack/tempo.json), [tool](../tools/build-music-sync.py)) and gave each one a bar grid in `game/content/music.json`. All 29 tracks you re-uploaded were byte-identical to the game's copies. The problem was where they played: each chapter's main theme was heard only for about 12 seconds over its closing film.

**Where each recording plays now**

- **Every chapter:** by default the first location plays the chapter's main theme and the later locations play its BGM. Since November 23, 2026, scenes follow their mood instead where that fits better: the quieter BGMs score sneaking, suspicion and quiet work (the aquarium, the safe house, the Gallery), and the themes score the escapes and emotional peaks (the ship, the safe-house escape, Saren's offer, the Choir). In Chapter 1 the BGM plays in the apartment and the theme on the busy Sunday harbor. The closing film returns to the theme at its loudest stretch, picked from the per-bar loudness. A chapter with one regular location (both interludes) plays its BGM there and closes on its theme. All recordings are heard in a playthrough.
- **Bellwether Bay (Tape Anomaly)**, the new track, scores the uneasy ninth night that ends Chapter 1.
- **The three "nights"** (the bay, Veyr and Sentinel Point) keep the Three Nights BGM wherever they sit, so the music marks them as the same kind of memory.
- **The opening:** the Three Nights theme plays under the backstory. The light rising over the bay starts on bar 34, and the same recording carries the "Eighteen months" storybook to its own ending.
- **The finale is more epic.** The Chapter 10 recordings and the Epilogue theme are the thinnest in the score (Chapter 10 BGM has 10 dB less low end than the fullest tracks). The main title, which builds to the biggest peak, now scores the live broadcast, the ship rising (on its peak bars), the last film and the credits.
- **The ending:** the lanterns on the water bring back the Three Nights theme, and the closing storybook runs over the same bars as "Eighteen months", over the same places, now changed. The short Epilogue theme plays once under the end card.

**Sync**

- Storybook panels and captions are placed on bars, and the game reads the music's real playback position. Measured in the game, every panel change landed within 0.02 seconds of its bar line.
- Chapter-ending films last a whole number of bars of their music (rounded up, so a film is never rushed by more than about 3 percent), and chapter cards end on a bar line of the new chapter's music.
- Crossfades are longer: 2.4 seconds between location tracks, 1.2 seconds into a theme.
- **Level riding.** Several location tracks have long near-silent passages (the Epilogue BGM opens with about 27 seconds at -30 to -38 LUFS). While you explore, the score reads the per-bar loudness map one bar ahead and raises the music by up to 9 dB through a quiet passage, at 1.5 dB per second. It comes back down at 9 dB per second when the current or next bar is loud, so a loud passage never arrives boosted.
- Chapter cards lift the music by 6 dB while they are on screen, and neither scene that uses the Epilogue BGM starts on its eight near-silent opening bars: the Epilogue starts on the soft build at bar 8, and "One year later" on bar 15, one bar before the full band comes in.

## Voices

Every character uses one voice across all of their lines, and each copy shares the voice of its original (Steve and Stephen, Nora and Iris, both Rooks, both Lyles, both Agneses, Dale and Pell). We compared each voice with the character sheet by measured pitch and by the voice's own preview description, and re-recorded 25 lines for five characters on the same ElevenLabs v4 engine through Higgsfield (7.59 credits):

| Character | Character sheet | Before | After |
| --- | --- | --- | --- |
| Gus Albano | round, cheerful baker who sings opera badly | Bram, a "YouTube video" voice, 216 Hz | Jake, comic storyteller, 143 Hz |
| Mateo Reyes | protective firefighter, 40 | Evan, a young voice, 216 Hz | Knox, 138 Hz |
| Dr. Evelyn Shaw | loud, practical, 59 | Tamsin, a soft audiobook voice | Linda, wry and lower, 162 Hz |
| Carmen Reyes | warm, notices everything, 64 | Marisol, a "news delivery" voice | Isabella, warm and dramatic |
| DJ AutoRick | relentlessly upbeat synthetic host | Jasper, deep and calm | John, bright and a little nasal |

All 25 new takes passed the local Whisper transcript check with no word errors and have new lip-sync cues. The previous takes are kept in `tmp/voice-recast-previous/`. Accent cannot be measured this way: the Chinese delegate at Sentinel Point (Callum) and Mrs. Penhallow (Mabel, whose preview mentions "a bit of Southern heart") are worth a listen.

## Saves

The campaign content version is now `campaign-2`. Older saves load and keep their place. A save inside the old three-night prologue restarts at the bay. A save past Chapter 4 replays the Sentinel Point flashback when Chapter 8 begins.

## Narration, dialogue and finishing touches

- **Steve narrates the storybooks** in his own voice. Each storybook was recorded as one continuous take, aligned word by word with the local Whisper model, and cut into one clip per caption ([tool](../tools/split-narration.py)). The builder times every picture from those clips: a picture appears on a bar or half bar, Steve starts a quarter bar later, and the next picture waits for his line. The score dips under his voice.
- **24 spoken lines were rewritten and re-recorded**, and Pell now shows as Dale until Chapter 6. [Before and after](dialogue-revision-2026-11-19.md)
- **Chapter cards** now sit over the scene's own painting, dimmed and slowly pushing in, which brightens into the scene as the card opens.
- **Feedback sounds** for a solved lead, a wrong try and a hint, synthesized locally ([tool](../tools/build-ui-sounds.py)).
- **Story stings** on five silent beats, and the score drops out under them. See the [tone map](tone-map.md) for where each mood lands, chapter by chapter.
- **Readable titles:** a soft shade and shadowed text keep the scene title and objective legible over bright paintings. The end screen shows only its own buttons.
- **Verification on the final build:** full campaign walk 3,646 checks, story flow 78, input 31, painted scenes 159, tape comparison 32, core 1,794, voices 2,063, soundtrack 315 (all 30 recordings), case boards 181, staging 149. No failures.

## Recorded showreels

To hear the game the way a player does, we recorded three stretches in Godot's Movie Maker mode, with the real picture and the full mix, dialogue on auto-advance ([runner](../game/tests/showreel_capture.gd), [measuring tool](../tools/review-showreel.py)). The videos are in `tmp/showreel/`.

The recorder renders every frame itself. macOS can stop drawing a covered or minimized window while the game keeps running, and Movie Maker then writes the last drawn frame again and again. One ending recording froze this way for most of the closing storybook, while the game log showed every panel and caption on its bar. With the window minimized on purpose, a recording without the forced render froze in long stretches and one with it had no frozen frames.

| Reel | What it covers | Length | Loudness | Range | True peak | Gaps over 2 s |
| --- | --- | --- | --- | --- | --- | --- |
| Opening | Title, the narrated backstory, the prologue card, the first lines on the boat | 93.7 s | -22.3 LUFS | 7.2 LU | -7.2 dBFS | none |
| Fear | The end of Chapter 1: the locked door, the ninth-night tone over the procession, the Chapter 2 card | 48.9 s | -22.4 LUFS | 6.3 LU | -7.4 dBFS | none |
| Ending | The ship rises, the epilogue, the lanterns, the closing storybook, one year later | 200.1 s | -22.8 LUFS | 8.2 LU | -7.0 dBFS | one 2.4 s pause, kept on purpose: the closing storybook's music ends before "One year later" |

The first recordings showed four problems, now fixed:

- **Dead air under the prologue card.** The card now lifts the music by 6 dB.
- **Near silence while exploring.** The first ending reel measured -26.2 LUFS with silent stretches of 3, 23 and 22 seconds, where location music sat in its quiet passages. The score now rides those passages up (see Music and picture sync).
- **A quiet "Good Morning" card.** It sat at -32 to -36 LUFS over the Epilogue BGM's soft opening. It now starts on bar 15 and measures -18 to -24 LUFS.
- **A drop after the finale.** The Epilogue card followed the main title's biggest peak with the Epilogue BGM's near-silent first bars, down to about -45 LUFS. The Epilogue now starts on bar 8, where the track begins to build.

All three reels now sit within 0.5 LU of each other, with peaks at least 7 dB below full scale. A few single-second dips remain where a line pauses over a soft bar of music.

[Tone map](tone-map.md) · [Cleanup record](cleanup-2026-11-18.md) · [Story rework source](../tools/story_rework.py) · [Storybook data](../game/content/storybook.json) · [Updated transcript](campaign-transcript.md)

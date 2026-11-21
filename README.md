# Night Nine

![Night Nine illustrated cover](art/night-nine.jpg)

A painted point-and-click mystery set in Bellwether. Steve Mercer hears the same greeting twice, with the same breath and hesitation. He sets out to learn how two mornings could sound exactly alike.

## Play

**[Cloudflare Pages review build](https://review.night-nine.pages.dev)** (first deployment pending). The preview is deployed from `main` to a separate `review` branch. First deployment requires the `night-nine` Cloudflare Pages project and the repository Actions secrets described in [PUBLISHING.md](PUBLISHING.md). The review build uses subtitles; generated replacement voices remain disabled, and native story timing is still under investigation.

Play in a desktop browser with WebGL 2. There is no installer. To edit or test the source, open `game/project.godot` in Godot 4.7.2, wait for import, then press F5.

Select **New game**. Click an object to investigate, or use **Objects** for a keyboard-accessible list. In rooms with a walkable floor, click a spot or use WASD to move. Open the notebook to review evidence, case theories and the transcript. After initial setup, you can play the full story offline.

At a case board, read the case notes, choose an evidence piece, then choose its destination. You can also drag pieces or use Tab and Enter. Swap two pieces by choosing their occupied positions in turn. Your placements and confirmed stages are saved as you work. Use **Hint** for another clue.

We estimate **3.5 to 5 hours for a first playthrough**. We budgeted 2 to 2½ minutes for each of the 84 stages across 32 case boards, or 168 to 210 minutes. We allowed another 42 to 90 minutes for conversations, movement, other puzzles and films. We have yet to measure first-time players.

Resources are cached for repeat visits and offline play after the first complete load. Updates can require another download. Saves use IndexedDB on the same browser and site address; they do not sync between devices. **Menu → Browser storage** can request persistent storage and export/import checksummed save backups. Browsers can deny persistent storage, and clearing site data still removes saves and cached files. [Build or host the browser edition](PUBLISHING.md)

In the soundtrack edition, you can hear the title music and a background piece and theme for each chapter, interlude, the prologue and the epilogue. You can find the original MP3s in `game/assets/audio/music/` and edit their cues in `game/content/music.json`.

## Chapter checkpoints

To play the prologue or one of ten cumulative chapters with this edition’s puzzles, films and music, choose a `chapters-0.9.2/*` tag. For example, run `git worktree add --detach ../Night-Nine-chapter-04 chapters-0.9.2/chapter-04` and open `game/project.godot` in that directory. You can still find the original development editions at `checkpoint/*`. Each checkpoint has a separate default save directory. Play Interlude 1 after Chapter 3 and Interlude 2 after Chapter 6. Play through Chapter 10 for the epilogue and the post-credits scene. You can find subsequent complete editions at the version tags. [Chapter goals](MILESTONES.md)

## Build and test

The source includes the editable production art and audio masters in `assets/`, their preparation tools in `tools/`, and the runtime copies in `game/assets/`. Keep both forms: the masters are for editing, while the optimized runtime files are used by Godot. Temporary exports, engine caches, credentials and provider response dumps are excluded. [Asset layout](assets/README.md)

For the complete native development suite, set `GODOT_BIN` to Godot 4.7.2 and run `bash tools/test-campaign.sh --render`. Use `NIGHT_NINE_QA_AUDIO_DRIVER=Dummy` when physical sound output is unavailable. The fixed version tags and chapter tags retain their original release contents.

Install Godot's 4.7.2 standard editor and matching single-threaded Web export template. The only production export is **Web**. From a clean checkout on macOS or Linux you can run the portable checkpoint test as follows.

```sh
godot --headless --path game --import
NIGHT_NINE_SAVE_DIR="$(mktemp -d)" godot --headless --path game --audio-driver Dummy --script res://qa/checkpoint.gd
```

The test opens the normal campaign, follows each room through its departure, completes the available story, reloads a completed save and opens the notebook.

In the complete release, run `godot --headless --path game --script res://qa/test_physical_navigation.gd` to check obstacle and door geometry. For a visual check of walking poses and conversations, choose empty directories for `NIGHT_NINE_SAVE_DIR` and `NIGHT_NINE_QA_DIR`, then run `godot --path game --script res://qa/test_social_staging.gd`. You can inspect the captured frames in your QA directory.

In the soundtrack edition, you can use the same isolated save and QA directories with `godot --headless --path game --script res://qa/test_campaign_music.gd` to check the score against the campaign.

## Official credits

| Credit | Contributor |
| --- | --- |
| Original Story (Written 25 Years Ago), Plot, Music, Voice and Creative Design Decisions | S3PehR |
| Music Generated By | Google Lyria 3.5 |
| Game Script and Creative Narration | Claude Opus 5.5 |
| Core Game Engine, Builds and Creative Stage Design | GPT Astra 5.2 |
| Artworks and Pictures, Including Characters | GPT Image 2.6 |
| Voices | ElevenLabs 4 |
| Game Hosting | Cloudflare Pages |
| Code Hosting | GitHub |
| Deployment Script and Bug Fixes | GitHub Copilot Fusion |

## Publication

You can play the official release for free. The Night Nine contributors license their original game code under GNU GPL version 3 only. You may share, modify or sell copies under the applicable terms. [GPLv3](LICENSE) · [Media terms](MEDIA.md) · [Third-party notices](game/LICENSES.txt)

When publishing downloads, provide the matching complete corresponding source alongside the binaries. See [the GitHub publishing guide](PUBLISHING.md) for the local branch, annotated tags and release steps.

The review site will be a public preview, not a final release. The revised script currently runs with subtitles and voice playback disabled while 120 generated takes await listening review. The native story-timing investigation is also open. Historical recordings remain preserved. [Complete story walkthrough (spoilers)](docs/story-walkthrough.md) · [Script and recording handoff](docs/script-v2/README.md)

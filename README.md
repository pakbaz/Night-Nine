# Night Nine

![Night Nine illustrated cover](art/night-nine.jpg)

A painted point-and-click mystery set in Bellwether. Steve Mercer hears the same greeting twice, with the same breath and hesitation. He sets out to learn how two mornings could sound exactly alike.

## Play

Open `game/project.godot` in Godot 4.7.2, wait for import, then press F5. Select **New game**. Click a marked object to investigate, use **Objects** for a keyboard-accessible list, and open the notebook to review evidence and dialogue. From a terminal, run `godot --path game` after the first import. All game data, recordings and textures are available locally.

## Chapter checkpoints

See [the checkpoint list](MILESTONES.md) for tags, official chapter titles and acceptance criteria. Open an earlier tag in another directory, for example with `git worktree add --detach ../Night-Nine-chapter-01 checkpoint/chapter-01`. Each tag starts at the three-part prologue and ends at its own completion card. Each checkpoint has a separate default save directory. Interlude 1 belongs to Chapter 3 and Interlude 2 to Chapter 6. Chapter 10 includes the epilogue and post-credits scene.

## Build and test

Install Godot's 4.7.2 desktop export templates from the editor for Mac and Windows builds. Choose the supplied macOS or Windows Desktop preset under **Project → Export**. From a clean checkout on macOS or Linux you can run the portable checkpoint test as follows.

```sh
godot --headless --path game --import
NIGHT_NINE_SAVE_DIR="$(mktemp -d)" godot --headless --path game --audio-driver Dummy --script res://qa/checkpoint.gd
```

The test opens the normal campaign, follows each room through its departure, completes the available story, reloads a completed save and opens the notebook.

## Publication

You can play the official release for free. The Night Nine contributors license their original game code under GNU GPL version 3 only. You may share, modify or sell copies under the applicable terms. [GPLv3](LICENSE) · [Media terms](MEDIA.md) · [Third-party notices](game/LICENSES.txt)

When publishing downloads, provide the matching complete corresponding source alongside the binaries. See [the GitHub publishing guide](PUBLISHING.md) for the local branch, annotated tags and release steps.

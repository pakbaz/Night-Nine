# Story stills and story layers

**Stills** (`stills/*.png`, runtime `game/assets/illustrated/campaign/stills/*.webp`) are full-frame story paintings. A scene's `stills` entry in `tools/script_v2/base/illustrated-campaign.json` shows one in place of the room while the listed lines play. A list item can name a line, a lead or a line group (`c7_swap.tone`, `epilogue.talk.iris`).

**Layers** (`assets/environments/campaign/layers/*.png`, runtime `game/assets/illustrated/campaign/layers/*.webp`) are transparent paintings the size of the room plate. A scene's `layers` entry paints one over the room, its clickable objects and, with `wide_file`, the walking view, from `after` a lead until `until` a lead. `after`, `until` and `reveal_after` can also name a single line, so a coat can appear when Steve hangs it up or a person when they first speak. `painted` hides those people's separate portraits while it shows, and `walking: false` keeps everyone in place.

Most were painted with GPT Image from the room plate and the character sheets in `assets/concepts/characters/`. A layer starts as a full repaint of the plate; `tools/graft_region.py` aligns it to the original (SIFT features and a homography fitted outside the changed region, typically under 1 px of error), colour-matches the seam and keeps only the changed region, so every object stays exactly where the room painting has it.

Chapter 4's parked van, rear-door jump and creek stills combine Steve's existing walk poses with the transport bay and roadside paintings. Feed 3 uses the same sleeping Rook and berth seen in Chapter 9. The van's two departure paintings play during the transfer; the `chapter_frames` at the end continue from the creek instead.

`python3 tools/script_v2.py --apply` validates that every painting exists and every line or lead it names is real.

**Bridges** (`assets/cinematics/campaign/bridges/<from>-<to>.png`, runtime `game/assets/illustrated/campaign/bridges/*.webp`) show the way from one place to the next. A scene's `bridge` entry dissolves the painting in when the scene ends, the next place's ambience and music rise under it, and the next room dissolves out of it. `tools/test_script_v2_staging.py` requires a bridge, film or departure painting for every scene change within a chapter.

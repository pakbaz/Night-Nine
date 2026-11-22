# Story stills and story layers

**Stills** (`stills/*.png`, runtime `game/assets/illustrated/campaign/stills/*.webp`) are full-frame story paintings. A scene's `stills` entry in `tools/script_v2/base/illustrated-campaign.json` shows one in place of the room while the listed lines play. A list item can name a line, a lead or a line group (`c7_swap.tone`, `epilogue.talk.iris`).

**Layers** (`assets/environments/campaign/layers/*.png`, runtime `game/assets/illustrated/campaign/layers/*.webp`) are transparent paintings the size of the room plate. A scene's `layers` entry paints one over the room, its clickable objects and, with `wide_file`, the walking view, from `after` a lead until `until` a lead. `painted` hides those people's separate portraits while it shows, and `walking: false` keeps everyone in place.

All of them were painted with GPT Image from the room plate and the character sheets in `assets/concepts/characters/`. A layer starts as a full repaint of the plate; `tools/graft_region.py` aligns it to the original (SIFT features and a homography fitted outside the changed region, typically under 1 px of error), colour-matches the seam and keeps only the changed region, so every object stays exactly where the room painting has it.

`python3 tools/script_v2.py --apply` validates that every painting exists and every line or lead it names is real.

# Godot web audio fixture

`sample-node.js` is the `GodotAudio.SampleNode` class exactly as exported by the Godot web template this project ships. It is Godot Engine code under the MIT license (Copyright (c) 2014-present Godot Engine contributors; Copyright (c) 2007-2014 Juan Linietsky, Ariel Manzur).

`tools/test_release_packaging.py` runs `build-pages.py`'s playback-position patch against it. If a Godot upgrade changes this code, the patch refuses to build. Refresh the fixture from the new export, then check whether the upgrade already reports positions from the first audio block and resumes paused samples where they stopped.

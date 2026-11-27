# Godot service worker fixture

`play.service.worker.js` is `godot.service.worker.js` from the official Godot 4.7.2 `web_nothreads_release.zip`, with its export placeholders filled the way the editor fills them for this project: the cache version, the project name `Night Nine`, the `play.offline.html` page, no cross-origin isolation headers, the shell files Godot caches on install and its on-demand `play.wasm` and `play.pck` list. It is Godot Engine code under the MIT license (Copyright (c) 2014-present Godot Engine contributors; Copyright (c) 2007-2014 Juan Linietsky, Ariel Manzur).

`tools/test_release_packaging.py` runs `build-pages.py`'s service worker changes against it and plays install, activate and fetch events through the result. If a Godot upgrade changes the worker, the build refuses to patch it. Refresh the fixture from the new export template, then check that a returning player still gets a new release on the next visit and that the game still opens offline.

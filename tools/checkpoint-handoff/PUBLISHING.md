# Build a Night Nine chapter checkpoint

Night Nine is a web game hosted on Cloudflare Pages. This generated checkpoint is for local review and contains no publishing workflow. There are no installers.

## Build and preview

Use the standard Godot 4.7.2 editor and its matching `web_nothreads_release.zip` template. The builder uses the current committed Git revision, not uncommitted changes. Choose a new output directory for each build.

```sh
python3 tools/build-pages.py --godot /path/to/godot \
  --template /path/to/web_nothreads_release.zip --output builds/web
python3 -m http.server 8000 --bind 127.0.0.1 --directory builds
```

Open `http://localhost:8000/web/`. Service workers require HTTPS or localhost. The first download includes the engine and game pack. The service worker caches these resources and the landing page for later visits, including offline play once the cache is complete. A new game-pack version can require a new download.

The site includes a compact playable source archive. Editable artwork, audio masters and authoring tools remain in Git and are linked at the exact build commit rather than copied into the size-limited Pages site. Downloads from a private repository require GitHub access. If distributing the game publicly, also make its corresponding source accessible to players under the project license.

## Saves and storage

Godot stores manual saves and autosaves in IndexedDB. They survive reloads and normal browser restarts on the same origin and browser profile. Game updates do not clear IndexedDB. The complete Web edition retains the save directory used by v0.9.2.

Use **Menu → Browser storage**:

- **Keep browser data** requests persistent storage. The browser may decline; the game displays the outcome.
- **Export save backup** downloads a checksummed JSON file.
- **Import save backup** validates its size, checksum and campaign state before loading. Invalid imports leave existing saves intact. Current progress is preserved in a separate `before-import` slot.

Clearing site data, private browsing and storage eviction can remove saves and cached resources. Persistent storage reduces eviction risk; it does not prevent deliberate deletion. Export a backup before changing browsers, devices, domains or site data. There is no cloud save account or cross-device synchronization.

## Current game hosting

GitHub Pages is retired. Use the current `main` branch of [pakbaz/Night-Nine](https://github.com/pakbaz/Night-Nine) and its `PUBLISHING.md` to build and deploy the current game to Cloudflare Pages.

This checkpoint exporter retains the historical compact source archive and 1 GiB local output budget. It does not split large files for Cloudflare's per-file limit; its output is for local preview, not direct Cloudflare upload. The current release builder performs that splitting and keeps source archives outside the deployed site.

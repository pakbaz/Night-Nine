# Publish Night Nine on GitHub Pages

Night Nine is a web game, published on GitHub Pages. There are no installers.

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

## Deploy

The `Publish Night Nine to GitHub Pages` workflow is manual. It checks the source, exports the Web build and uploads only the static website and not the editable masters. The builder refuses a site at or above the 1 GiB Pages size limit.

The current test build is about **712 MiB total**. Loading the playable game uses about **377 MiB** on a cold visit. GitHub documents a **soft** limit of **100 GB of Pages bandwidth per month**, not a guaranteed allowance. That is roughly **270 cold game loads per month** if no one downloads the optional source archive, or about **144** if each visitor also downloads its roughly 334 MiB compact source ZIP. Browser caching can reduce repeat traffic after it has cached the game pack, but the browser check could not confirm offline behavior in this build. Treat these figures as planning estimates, not a traffic guarantee.

Downloads from the website, including the optional `source.zip`, count as Pages traffic. Cloning the public repository or downloading an archive directly from its GitHub repository page uses GitHub's repository service rather than the Pages site's bandwidth. It still transfers a sizable source tree. Put the game pack on a CDN or another host if expected traffic approaches the Pages soft limit.

In the repository, select **Settings → Pages → Build and deployment → GitHub Actions**. Then run the Pages workflow for the desired committed revision.

Keep the repository private until publication is approved. GitHub Pages from private repositories requires a supported account plan, and the website is normally public even when its repository is private. Do not enable public deployment as a side effect of pushing source.

# Publish Night Nine on Cloudflare Pages

Night Nine is a static web game. The release target is Cloudflare Pages on the free plan. There are no installers, Pages Functions or Workers.

## Build and preview

Use the standard Godot 4.7.2 editor and its matching `web_nothreads_release.zip` template. The builder uses the current committed Git revision, not uncommitted changes. Choose a new output directory for each build.

```sh
python3 tools/build-pages.py --godot /path/to/godot \
  --template /path/to/web_nothreads_release.zip --output builds/web \
  --source-archive builds/source.zip
python3 -m http.server 8000 --bind 127.0.0.1 --directory builds
```

Open `http://localhost:8000/web/`. Service workers require HTTPS or localhost. The first download includes the engine and game pack. The service worker caches these resources and the landing page for later visits, including offline play once the cache is complete. A new game-pack version can require a new download.

`build-pages.py` splits `play.pck` and `play.wasm` into immutable parts no larger than 24 MiB, writes `chunks.json`, installs the browser loader, patches the service worker and runs `tools/check-site.py`. The check also enforces a 5,000-file release limit and verifies every part and whole-file hash.

The website does not contain `source.zip`. The builder writes that matching source archive next to the site, at `builds/source.zip` in the example. The landing page links to the exact GitHub commit archive. Downloads from a private repository require GitHub access. If distributing the game publicly, make its corresponding source accessible under the project license.

Use `--archive builds/Night-Nine-web.zip` to also make a portable copy of the static site. It contains the chunked browser game, not an embedded source checkout. Its README links to the matching source URL.

## Saves and storage

Godot stores manual saves and autosaves in IndexedDB. They survive reloads and normal browser restarts on the same origin and browser profile. Game updates do not clear IndexedDB. The complete Web edition retains the save directory used by v0.9.2.

Use **Menu → Browser storage**:

- **Keep browser data** requests persistent storage. The browser may decline; the game displays the outcome.
- **Export save backup** downloads a checksummed JSON file.
- **Import save backup** validates its size, checksum and campaign state before loading. Invalid imports leave existing saves intact. Current progress is preserved in a separate `before-import` slot.

Clearing site data, private browsing and storage eviction can remove saves and cached resources. Persistent storage reduces eviction risk; it does not prevent deliberate deletion. Export a backup before changing browsers, devices, domains or site data. There is no cloud save account or cross-device synchronization.

## Cloudflare Pages deploy

Cloudflare Pages free-plan limits verified on 2026-11-20 are **25 MiB per file** and **20,000 files per site**. This project keeps every deployed file at or below 24 MiB and no more than 5,000 files. Direct upload does not use Cloudflare build minutes. Static hosting needs no Pages Functions.

Create the `night-nine` Pages project manually when publication is approved, then direct-upload the checked site:

```sh
python3 tools/check-site.py builds/web
npx wrangler pages deploy builds/web --project-name night-nine
```

Do not run Wrangler until the user approves deployment. Wrangler login and project creation are deliberately outside the build.

## Legacy GitHub Pages workflow

`.github/workflows/pages.yml` remains as a manual legacy path. It builds and checks the same chunked site, uploads `source.zip` as a workflow artifact, and can attach it to an existing GitHub Release when a `release_tag` input is supplied. It still deploys the site to GitHub Pages, so do not run it for the Cloudflare release.

Keep the repository private until publication is approved. Do not enable or deploy either public host as a side effect of pushing source.

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

For a plain local HTTP server, open `http://localhost:8000/web/play.html`. The Cloudflare landing page links directly to `/play`, avoiding its `.html` redirect. Portable ZIPs retain the `.html` link for simple HTTP servers. Service workers require HTTPS or localhost. The first download includes the engine and game pack. The service worker caches these resources and the landing page for later visits, including offline play once the cache is complete. A new game-pack version can require a new download.

The loading screen shows download progress and plays **Mysterious Take 1** during the first successful load in that browser. The music starts on its own and fades out over 3 seconds when the download reaches 95%. If the browser blocks sound, the music starts on the first tap, click, or key press, unless the download has already reached 95%. The track stays silent on later visits, including game updates. Clearing site data resets this preference. The original MP3 is `site/loading-screen-music.mp3`; it loads separately from the game pack.

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

## Cloudflare Pages review deployment

Cloudflare Pages free-plan limits verified on 2026-11-20 are **25 MiB per file** and **20,000 files per site**. This project keeps every deployed file at or below 24 MiB and no more than 5,000 files. Direct upload does not use Cloudflare build minutes. Static hosting needs no Pages Functions.

The automated deployment is configured in `.github/workflows/cloudflare-pages.yml`. Every relevant push to `main` runs the voice-pipeline and campaign tests and build checks, then uploads only `builds/web` to the Cloudflare `review` branch. A stable version tag such as `v1.0.0` runs the same checks and deploys to Cloudflare's `main` production branch. Prerelease tags do not deploy production. The workflow does not publish `source.zip`, editor caches, test output, screenshots, logs or other development artifacts. The stable review URL is:

```text
https://review.night-nine.pages.dev
```

The `night-nine` project uses `main` as its production branch. Push a stable version tag in `v1.MAJOR.MINOR.PATCH` form to deploy production automatically; regular pushes to `main` update only the review URL. The public repository has both required Actions secrets. For a new repository:

1. Add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` as repository Actions secrets. Use a Cloudflare API token scoped to **Cloudflare Pages: Edit** for the selected account; do not use the broad Wrangler OAuth token. Missing secrets cause the workflow to report that deployment was skipped.
2. Push a game, art, site, asset, media-credit, license or deployment-workflow change to `main` to refresh the review site. Push a stable `v1.MAJOR.MINOR.PATCH` tag to run the production deployment.

The workflow builds from the checked-out Git commit, downloads the official Godot 4.7.2 editor and matching template, verifies their SHA-512 hashes, runs the campaign test suite and site integrity and size checks, then uploads the browser package. The approved character voices and storybook narration are enabled. The review deployment does not make the game release-ready.

When both campaign and storybook voice playback gates are closed, the builder removes the staged replacement-voice directory from its temporary export snapshot. This keeps unapproved recordings out of the web download without changing the source checkout or voice manifests. With playback approved and enabled, the normal export retains the required runtime recordings.

To build and upload manually after configuring Wrangler authentication:

```sh
python3 tools/check-site.py builds/web
npx wrangler@4.166.0 pages deploy builds/web --project-name night-nine --branch review
```

The portable ZIP and `source.zip` are optional local artifacts and are not uploaded to Pages. The site builder exports a committed Git snapshot and excludes local `tmp/`, `builds/`, engine caches, account data and debug reports.

## GitHub Pages retirement

Cloudflare Pages is the only game host. GitHub Pages is disabled for `pakbaz/Night-Nine`, and the legacy publishing workflow and its checkpoint-generation template have been removed. GitHub continues to host the public source repository and run the Cloudflare workflow. Historical tags remain unchanged.

Browser saves belong to their original site address. Saves from the retired GitHub Pages address do not automatically transfer to Cloudflare; import an existing exported backup through **Menu → Browser storage**. No browser saves or caches are deleted by this hosting change.

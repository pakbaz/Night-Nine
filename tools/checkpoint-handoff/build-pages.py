#!/usr/bin/env python3
"""Build an offline-capable Pages game and compact source from one Git commit."""
import argparse
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


SOURCE_PATHS = ("game", "art", "site", "tools/build-pages.py",
                "README.md", "PUBLISHING.md", "LICENSE", "MEDIA.md")


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def prepare_offline_cache(site):
    worker = site / "play.service.worker.js"
    text = worker.read_text()
    text, count = re.subn(r"const CACHE_PREFIX = '[^']*';",
                         "const CACHE_PREFIX = 'night-nine:' + self.registration.scope + ':';", text)
    if count != 1 or "const FULL_CACHE = " not in text:
        raise ValueError("Unexpected Godot service worker; cannot configure the offline cache.")
    text = text.replace("const FULL_CACHE = ",
                        "CACHED_FILES.push('./', 'index.html', 'cover.jpg', 'LICENSE.txt', "
                        "'MEDIA.txt', 'THIRD-PARTY.txt');\nconst FULL_CACHE = ", 1)
    text = text.replace("cache.put(event.request, response.clone());",
                        "event.waitUntil(cache.put(event.request, response.clone()));")
    worker.write_text(text)


def build(repo, output, godot, template, source_url, archive_path):
    if not (repo / "game/content/checkpoint.json").is_file():
        raise ValueError("Run this command from the public Night Nine release repository.")
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    if archive_path and archive_path.exists():
        raise FileExistsError(f"Choose a new archive: {archive_path}")
    if archive_path and archive_path.is_relative_to(output):
        raise ValueError("Choose an archive path outside the website directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".night-nine-web-", dir=output.parent) as directory:
        temp = Path(directory)
        site = temp / "site"
        site.mkdir()
        # Keep editable masters in Git, not in the size-limited Pages artifact.
        run("git", "-C", repo, "archive", "--format=zip", "--prefix=Night-Nine/",
            "--output", site / "source.zip", "HEAD", *SOURCE_PATHS)
        with zipfile.ZipFile(site / "source.zip") as archive:
            archive.extractall(temp)
        snapshot = temp / "Night-Nine"
        game = snapshot / "game"
        if template:
            target = snapshot / ".tools/templates"
            target.mkdir(parents=True)
            shutil.copyfile(template, target / "web_nothreads_release.zip")
            preset = game / "export_presets.cfg"
            before, web = preset.read_text().split('name="Web"', 1)
            web = re.sub('^custom_template/release=".*"$',
                         'custom_template/release="../.tools/templates/web_nothreads_release.zip"', web, flags=re.M)
            preset.write_text(before + 'name="Web"' + web)
        for operation, args in [("import", ["--editor", "--import", "--quit"]),
                                ("export", ["--export-release", "Web", site / "play.html"])]:
            log = temp / f"{operation}.log"
            run(godot, "--headless", "--path", game, "--log-file", log, *args)
            for line in log.read_text(errors="replace").splitlines():
                if line.startswith(("ERROR:", "SCRIPT ERROR:")):
                    raise RuntimeError(line)
        core = [site / ("play." + ext) for ext in ("html", "js", "wasm", "pck")]
        if not all(p.is_file() and p.stat().st_size for p in core):
            raise RuntimeError("Incomplete Godot Web export.")
        size = sum(p.stat().st_size for p in core) / 2**20
        version = re.search(r'^config/version="(\d+\.\d+\.\d+)', (game / "project.godot").read_text(), re.M).group(1)
        if not source_url:
            github = os.environ.get("GITHUB_REPOSITORY")
            if not github:
                remote = subprocess.check_output(["git", "-C", str(repo), "remote", "get-url", "origin"], text=True).strip()
                match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", remote)
                if not match:
                    raise ValueError("Set --source-url to the matching complete source download.")
                github = match.group(1)
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            source_url = f"https://github.com/{github}/archive/{commit}.zip"
        page = (snapshot / "site/index.html").read_text().replace("@@SIZE@@", str(round(size))).replace("@@RELEASE@@", "")
        (site / "index.html").write_text(page.replace("@@EDITABLE_SOURCE@@", html.escape(source_url, quote=True)))
        shutil.copyfile(snapshot / "art/night-nine.jpg", site / "cover.jpg")
        shutil.copyfile(snapshot / "LICENSE", site / "LICENSE.txt")
        shutil.copyfile(snapshot / "MEDIA.md", site / "MEDIA.txt")
        shutil.copyfile(game / "LICENSES.txt", site / "THIRD-PARTY.txt")
        (site / ".nojekyll").touch()
        prepare_offline_cache(site)
        if sum(p.stat().st_size for p in site.iterdir() if p.is_file()) >= 1024**3:
            raise ValueError("The Pages site exceeds the 1 GiB site limit.")
        if archive_path:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=archive_path.parent) as zip_dir:
                packaged = Path(zip_dir) / archive_path.name
                with zipfile.ZipFile(packaged, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
                    for item in sorted(site.iterdir()):
                        archive.write(item, "Night-Nine/" + item.name)
                    archive.writestr("README.txt",
                        f"Night Nine {version} for desktop web browsers\n\n"
                        "Extract the archive. In the folder containing Night-Nine, run:\n\n"
                        "    python3 -m http.server 8000 --bind 127.0.0.1\n\n"
                        "On Windows you can use py in place of python3. Open http://localhost:8000/Night-Nine/ "
                        "and select Play in browser. Keep the same site address to continue your saved game.\n\n"
                        "The game caches resources after loading. Browser saves stay on the same origin. "
                        "Use Menu > Browser storage to export/import backups or request persistent storage.\n\n"
                        f"Complete source and masters: {source_url}\n"
                        "You can also open the compact Godot checkout in Night-Nine/source.zip.\n")
                with zipfile.ZipFile(packaged) as archive:
                    if archive.testzip():
                        raise RuntimeError("The portable browser archive failed its integrity check.")
                packaged.rename(archive_path)
        site.rename(output)
        print(f"Play at index.html over HTTP. First load is about {size:.1f} MiB. Output: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("builds/web"))
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--template", type=Path, help="Official web_nothreads_release.zip for Godot 4.7.2.")
    parser.add_argument("--source-url", help="Download URL for the matching full source archive with editable masters.")
    parser.add_argument("--archive", type=Path, help="Also create a portable ZIP of the static site.")
    options = parser.parse_args()
    build(Path(__file__).resolve().parents[1], options.output.resolve(), options.godot,
          options.template.resolve() if options.template else None, options.source_url,
          options.archive.resolve() if options.archive else None)

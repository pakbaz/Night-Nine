#!/usr/bin/env python3
"""Build a static Pages site and its matching source from one public release commit."""
import argparse
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def build(repo, output, godot, template, source_url):
    if not (repo / "game/content/checkpoint.json").is_file():
        raise ValueError("Run this command from the public Night Nine release repository.")
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".night-nine-web-", dir=output.parent) as directory:
        temp = Path(directory)
        site = temp / "site"
        site.mkdir()
        run("git", "-C", repo, "archive", "--format=zip", "--prefix=Night-Nine/",
            "--output", site / "source.zip", "HEAD")
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
        full_source = f"NightNine-{version}-source.zip"
        if not source_url:
            github = os.environ.get("GITHUB_REPOSITORY")
            source_url = f"https://github.com/{github}/releases/download/v{version}/{full_source}" if github else "../" + full_source
        page = (snapshot / "site/index.html").read_text().replace("@@SIZE@@", str(round(size)))
        (site / "index.html").write_text(page.replace("@@EDITABLE_SOURCE@@", html.escape(source_url, quote=True)))
        shutil.copyfile(snapshot / "art/night-nine.jpg", site / "cover.jpg")
        shutil.copyfile(snapshot / "LICENSE", site / "LICENSE.txt")
        shutil.copyfile(snapshot / "MEDIA.md", site / "MEDIA.txt")
        shutil.copyfile(game / "LICENSES.txt", site / "THIRD-PARTY.txt")
        (site / ".nojekyll").touch()
        site.rename(output)
        print(f"Play at index.html over HTTP. First load is about {size:.1f} MiB. Output: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("builds/web"))
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--template", type=Path, help="Official web_nothreads_release.zip for Godot 4.7.2.")
    parser.add_argument("--source-url", help="Download URL for the matching full source archive with editable masters.")
    options = parser.parse_args()
    build(Path(__file__).resolve().parents[1], options.output.resolve(), options.godot,
          options.template.resolve() if options.template else None, options.source_url)

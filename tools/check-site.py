#!/usr/bin/env python3
"""Validate a chunked Night Nine static site before upload."""
import argparse
import hashlib
import json
from pathlib import Path


MAX_FILE_SIZE = 24 * 1024 * 1024
MAX_FILE_COUNT = 5000
BIG_FILES = ("play.pck", "play.wasm")


def manifest_release(files):
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def check_site(site):
    site = Path(site)
    if not site.is_dir():
        raise ValueError(f"Site directory does not exist: {site}")

    disk_files = sorted(path for path in site.rglob("*") if path.is_file())
    if len(disk_files) > MAX_FILE_COUNT:
        raise ValueError(
            f"Site has {len(disk_files)} files; the release limit is {MAX_FILE_COUNT}.")
    for path in disk_files:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            relative = path.relative_to(site)
            raise ValueError(
                f"{relative} is {size} bytes; every deployed file must be at most 24 MiB.")

    manifest_path = site / "chunks.json"
    if not manifest_path.is_file():
        raise ValueError("Missing chunks.json.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid chunks.json: {error}") from error

    try:
        if manifest["version"] != 1:
            raise ValueError("chunks.json has an unsupported version.")
        entries = manifest["files"]
        if [entry["name"] for entry in entries] != list(BIG_FILES):
            raise ValueError("chunks.json must list play.pck then play.wasm.")
        if manifest["release"] != manifest_release(entries):
            raise ValueError("chunks.json release hash is inconsistent.")

        referenced_parts = set()
        for entry in entries:
            original_name = entry["name"]
            if (site / original_name).exists():
                raise ValueError(f"Unsplit file is still present: {original_name}")
            if not entry["parts"]:
                raise ValueError(f"{original_name} has no parts.")

            whole_hash = hashlib.sha256()
            total_size = 0
            for number, part in enumerate(entry["parts"], 1):
                name = part["name"]
                if name in referenced_parts:
                    raise ValueError(f"Part is listed more than once: {name}")
                referenced_parts.add(name)
                if Path(name).name != name:
                    raise ValueError(f"Invalid part path: {name}")
                extension = "wasm" if original_name.endswith(".wasm") else "part"
                expected_name = (
                    f"{original_name}.{number:04d}.{part['sha256'][:8]}.{extension}")
                if name != expected_name:
                    raise ValueError(
                        f"Part order or hash name is inconsistent: expected {expected_name}.")

                path = site / name
                if not path.is_file():
                    raise ValueError(f"Missing part: {name}")
                actual_size = path.stat().st_size
                if actual_size != part["size"]:
                    raise ValueError(
                        f"Part size mismatch for {name}: expected {part['size']}, got {actual_size}.")
                if actual_size > MAX_FILE_SIZE:
                    raise ValueError(f"Part exceeds 24 MiB: {name}")
                data = path.read_bytes()
                actual_hash = hashlib.sha256(data).hexdigest()
                if actual_hash != part["sha256"]:
                    raise ValueError(f"Part SHA-256 mismatch: {name}")
                whole_hash.update(data)
                total_size += actual_size

            if total_size != entry["size"]:
                raise ValueError(
                    f"Total size mismatch for {original_name}: expected {entry['size']}, got {total_size}.")
            if whole_hash.hexdigest() != entry["sha256"]:
                raise ValueError(f"Whole-file SHA-256 mismatch: {original_name}")

        actual_parts = {
            path.name for path in disk_files
            if path.name.startswith(("play.pck.", "play.wasm."))
            and path.suffix in {".part", ".wasm"}
        }
        extras = actual_parts - referenced_parts
        if extras:
            raise ValueError(f"Unreferenced part file: {sorted(extras)[0]}")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError(f"Invalid chunks.json structure: {error}") from error

    largest = max((path.stat().st_size for path in disk_files), default=0)
    return {"files": len(disk_files), "largest": largest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    options = parser.parse_args()
    try:
        stats = check_site(options.site)
    except ValueError as error:
        parser.exit(1, f"Site check failed: {error}\n")
    print(f"Site check passed: {stats['files']} files; largest is {stats['largest']} bytes.")

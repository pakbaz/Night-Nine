#!/usr/bin/env python3
"""Split the large Godot Web payloads into immutable Cloudflare Pages assets."""
import argparse
import hashlib
import json
from pathlib import Path


MAX_FILE_SIZE = 24 * 1024 * 1024
BIG_FILES = ("play.pck", "play.wasm")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def release_hash(files):
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def part_name(original, number, digest):
    extension = "wasm" if original.endswith(".wasm") else "part"
    return f"{original}.{number:04d}.{digest[:8]}.{extension}"


def split_site(site, chunk_size=MAX_FILE_SIZE):
    site = Path(site)
    if not 0 < chunk_size <= MAX_FILE_SIZE:
        raise ValueError(f"Chunk size must be between 1 byte and {MAX_FILE_SIZE} bytes.")

    files = []
    for original_name in BIG_FILES:
        original = site / original_name
        if not original.is_file():
            raise ValueError(f"Missing large Web export file: {original_name}")

        for stale in site.glob(f"{original_name}.*.part"):
            stale.unlink()
        for stale in site.glob(f"{original_name}.*.wasm"):
            stale.unlink()

        whole_hash = hashlib.sha256()
        parts = []
        total_size = 0
        with original.open("rb") as source:
            number = 1
            while data := source.read(chunk_size):
                digest = sha256_bytes(data)
                name = part_name(original_name, number, digest)
                (site / name).write_bytes(data)
                parts.append({"name": name, "size": len(data), "sha256": digest})
                whole_hash.update(data)
                total_size += len(data)
                number += 1

        if not parts:
            raise ValueError(f"Cannot split empty file: {original_name}")
        files.append({
            "name": original_name,
            "size": total_size,
            "sha256": whole_hash.hexdigest(),
            "parts": parts,
        })
        original.unlink()

    manifest = {"version": 1, "release": release_hash(files), "files": files}
    (site / "chunks.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    options = parser.parse_args()
    result = split_site(options.site)
    count = sum(len(entry["parts"]) for entry in result["files"])
    print(f"Split {len(result['files'])} files into {count} parts.")

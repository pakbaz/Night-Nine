#!/usr/bin/env python3
"""Lay out storybook captions on the music's bar grid from their recorded narration.

Each picture turns on a whole bar. Its captions follow one another with a short
breath between them, and the next picture waits until the last caption has
finished. Run after the narration is recorded and `script_v2.py --apply` has
copied the clip lengths into game/content/narration.json:

    python3 tools/time-storybook.py ch2 ch3 interlude1
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tools/script_v2/base/storybook.json"
MUSIC = ROOT / "game/content/music.json"
NARRATION = ROOT / "game/content/narration.json"
LEAD = .25    # bars from a picture's turn to its first caption
GAP = .6      # seconds between two captions on the same picture
HOLD = 1.4    # seconds a picture stays after its last caption ends
SETTLE = 1    # bars the last picture holds before the book closes


def track_for(music, file):
    tracks = [music.get("title", {}), *music.get("extras", {}).values()]
    for group in music.get("chapters", {}).values():
        tracks.extend(group.values())
    for track in tracks:
        if track.get("file") == file:
            return track
    raise ValueError(f"No measured track for {file}")


def layout(book, lengths, bar_seconds):
    """lengths: narration seconds per panel, in caption order."""
    cursor = float(book["music"].get("bar", 0))
    for index, (panel, seconds) in enumerate(zip(book["panels"], lengths)):
        start = cursor if index == 0 else math.ceil(cursor - 1e-6)
        panel["bar"] = start
        at = start + LEAD
        for line, length in zip(panel["lines"], seconds):
            line["bar"] = round(at, 3)
            line["seconds"] = length
            at += (length + GAP) / bar_seconds
        cursor = at + (HOLD - GAP) / bar_seconds
    book["end_bar"] = math.ceil(cursor - 1e-6) + SETTLE
    return book


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("books", nargs="+")
    args = parser.parse_args()
    base = json.loads(BASE.read_text(encoding="utf-8"))
    music = json.loads(MUSIC.read_text(encoding="utf-8"))
    narration = json.loads(NARRATION.read_text(encoding="utf-8"))
    for name in args.books:
        book = base["books"][name]
        entries = iter(narration["books"][name])
        lengths = []
        for panel in book["panels"]:
            seconds = []
            for line in panel["lines"]:
                entry = next(entries)
                if entry["caption"] != line["text"] or not entry.get("file"):
                    raise ValueError(f"{name}: record the narration first: {line['text']}")
                seconds.append(round(float(entry["seconds"]), 3))
            lengths.append(seconds)
        track = track_for(music, book["music"]["file"])
        layout(book, lengths, 240.0 / float(track["bpm"]))
        bars = len(track.get("bar_loudness", []))
        if bars and book["end_bar"] > bars:
            raise ValueError(f"{name} needs {book['end_bar']} bars but its music has {bars}")
        print(f"{name}: bars {book['music']['bar']}..{book['end_bar']} of {bars or '?'}")
    BASE.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

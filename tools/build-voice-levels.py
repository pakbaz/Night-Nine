#!/usr/bin/env python3
"""Measure every spoken clip the game plays, so the game can match their levels.

The recorded voices come from several ElevenLabs voices and batches, and their
loudness differs by up to 16 dB between two lines of the same conversation
(Steve's takes sit near -28 LUFS, the Archivist's near -16 LUFS). The game
reads this table and plays each clip at one dialogue level (see
_voice_gain_db in game/scripts/campaign.gd); the recordings stay untouched.

Writes game/content/voice-levels.json: for each clip, its integrated loudness
(EBU R128, LUFS), its true peak (dBFS) and the first 16 hex digits of its
SHA-256, so a re-recorded take is caught as stale. Run after recording:

    python3 tools/build-voice-levels.py
"""
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'game'
OUT = GAME / 'content/voice-levels.json'


def clips():
    voice = json.loads((GAME / 'content/voice-manifest.json').read_text())
    narration = json.loads((GAME / 'content/narration.json').read_text())
    found = set()
    for take in voice['takes'].values():
        for record in (take, take.get('fallback') or {}):
            if record.get('file'):
                found.add(record['file'])
    for book in narration['books'].values():
        for clip in book:
            if clip.get('file'):
                found.add(clip['file'])
    return sorted(f for f in found if (GAME / f.removeprefix('res://')).exists())


def measure(res_path):
    path = GAME / res_path.removeprefix('res://')
    out = subprocess.run(['ffmpeg', '-nostats', '-hide_banner', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    summary = out[out.rfind('Summary:'):]
    lufs = float(re.search(r'I:\s+([-0-9.]+) LUFS', summary).group(1))
    peak = float(re.search(r'Peak:\s+([-0-9.]+) dBFS', summary).group(1))
    return res_path, {'lufs': lufs, 'peak': peak, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()[:16]}


def main():
    with ThreadPoolExecutor(8) as pool:
        levels = dict(pool.map(measure, clips()))
    OUT.write_text(json.dumps({'schema': 1, 'method': 'ffmpeg ebur128: integrated loudness (LUFS) and true peak (dBFS)',
                               'clips': levels}, indent=1) + '\n')
    print(f'{len(levels)} clips -> {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()

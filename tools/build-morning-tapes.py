#!/usr/bin/env python3
"""Build the two deterministic Chapter 1 kitchen cassette recordings.

Sunday's Steve clip is cut at the first clear pause after "Nor.": 20 ms RMS
windows, an 8% peak-RMS threshold (never below -56.5 dBFS), and at least
160 ms of quiet after 0.6 seconds. The cut includes that quiet run and a
20 ms fade. The resulting clip must be 0.6 to 1.6 seconds long.
"""

from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "game"
RATE = 48_000
IDENT_SECONDS = 2.5
GAP_SECONDS = 0.12
SATURDAY_IDENT_START = 0.18
SUNDAY_DELAY = 0.35
FADE_SECONDS = 0.02


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def from_res(path: str) -> Path:
    if not path.startswith("res://"):
        raise ValueError(f"Expected a res:// path, got {path}")
    return GAME / path.removeprefix("res://")


def load_mono(path: Path) -> tuple[np.ndarray, int]:
    data, rate = sf.read(path, dtype="float64", always_2d=False)
    if data.ndim != 1:
        raise ValueError(f"{path} must be mono")
    return data, int(rate)


def resample_to_48k(data: np.ndarray, rate: int) -> np.ndarray:
    if rate == RATE:
        return data.copy()
    if RATE % rate != 0:
        raise ValueError(f"Only integer resampling is supported, got {rate} Hz")
    factor = RATE // rate
    source_positions = np.arange(data.size, dtype=np.float64)
    target_positions = np.arange(data.size * factor, dtype=np.float64) / factor
    return np.interp(target_positions, source_positions, data)


def active_bounds(data: np.ndarray) -> tuple[int, int]:
    frame = int(0.02 * RATE)
    usable = data[: data.size // frame * frame]
    rms = np.sqrt(np.mean(usable.reshape(-1, frame) ** 2, axis=1))
    threshold = max(0.0015, float(rms.max()) * 0.08)
    active = np.flatnonzero(rms > threshold)
    if active.size == 0:
        return 0, data.size
    padding = int(0.04 * RATE)
    start = max(0, int(active[0]) * frame - padding)
    end = min(data.size, (int(active[-1]) + 1) * frame + padding)
    return start, end


def trim_voice(data: np.ndarray) -> tuple[np.ndarray, int, int]:
    start, end = active_bounds(data)
    return data[start:end].copy(), start, end


def audible_ident_tail(data: np.ndarray) -> tuple[np.ndarray, int, int, dict]:
    frame = int(0.02 * RATE)
    usable = data[: data.size // frame * frame]
    rms = np.sqrt(np.mean(usable.reshape(-1, frame) ** 2, axis=1))
    threshold = max(0.0015, float(rms.max()) * 0.03)
    active = np.flatnonzero(rms > threshold)
    if active.size == 0:
        raise ValueError("KBWR ident has no audible signal")
    end = min(data.size, (int(active[-1]) + 2) * frame)
    start = max(0, end - round(IDENT_SECONDS * RATE))
    clip = data[start:end].copy()
    return clip, start, end, {
        "seconds": round(clip.size / RATE, 6),
        "source_start": round(start / RATE, 6),
        "source_end": round(end / RATE, 6),
        "method": (
            "Last 2.5 seconds ending one 20 ms window after the final 20 ms RMS "
            "window above max(-56.5 dBFS, 3% of peak RMS)."
        ),
        "threshold_rms": round(threshold, 9),
    }


def cut_sunday_steve(data: np.ndarray) -> tuple[np.ndarray, dict]:
    frame = int(0.02 * RATE)
    usable = data[: data.size // frame * frame]
    rms = np.sqrt(np.mean(usable.reshape(-1, frame) ** 2, axis=1))
    threshold = max(0.0015, float(rms.max()) * 0.08)
    first_frame = int(0.6 / 0.02)
    quiet_frames = int(0.16 / 0.02)
    cut_frame = None
    for index in range(first_frame, rms.size - quiet_frames + 1):
        if np.all(rms[index:index + quiet_frames] <= threshold):
            cut_frame = index + quiet_frames
            break
    if cut_frame is None:
        raise ValueError("No clear pause found after Sunday 'Morning, Nor.'")
    cut = min(data.size, cut_frame * frame)
    seconds = cut / RATE
    if not 0.6 <= seconds <= 1.6:
        raise ValueError(f"Sunday Steve cut is implausible: {seconds:.3f} seconds")
    clip = data[:cut].copy()
    fade = min(int(FADE_SECONDS * RATE), clip.size)
    clip[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=True)
    return clip, {
        "seconds": round(seconds, 6),
        "source_end_frame": cut,
        "method": (
            "First >=160 ms quiet run after 0.6 s, measured in 20 ms RMS windows "
            "below max(-56.5 dBFS, 8% of peak RMS), followed by a 20 ms fade."
        ),
        "threshold_rms": round(threshold, 9),
    }


def pcm16_bytes(data: np.ndarray) -> bytes:
    samples = np.rint(np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
    return samples.tobytes()


def clean_hash(data: np.ndarray) -> str:
    return hashlib.sha256(pcm16_bytes(data)).hexdigest()


def write_wav(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm16_bytes(data))


def cassette_noise(frames: int, seed: int) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(seed))
    white = rng.standard_normal(frames)
    hiss = white * 0.00065
    time = np.arange(frames, dtype=np.float64) / RATE
    room = 0.00035 * np.sin(2.0 * np.pi * 59.7 * time + seed * 0.01)
    room += 0.00022 * np.sin(2.0 * np.pi * 119.4 * time + seed * 0.017)
    return hiss + room


def main() -> None:
    campaign = json.loads((GAME / "content/campaign.json").read_text())
    voices = json.loads((GAME / "content/voice-manifest.json").read_text())["takes"]
    soundscape = json.loads((GAME / "assets/audio/soundscape-manifest.json").read_text())
    lines = campaign["lines"]

    def voice_for(line_or_audio_id: str) -> tuple[str, Path]:
        audio_id = lines.get(line_or_audio_id, {}).get("audio", line_or_audio_id)
        return audio_id, from_res(voices[audio_id]["file"])

    audio_ids = {}
    paths = {}
    for key, line_id in {
        "saturday_autorick": "c1_flat.in.03",
        "sunday_autorick": "c1_flat.sunday.03",
        "nora": "recording.greeting",
        "saturday_steve": "c1_flat.saturday.02",
    }.items():
        audio_ids[key], paths[key] = voice_for(line_id)
    # The Sunday greeting survives only as evidence, not as a second live line.
    frozen = json.loads((ROOT / "assets/audio/elevenlabs-v4-script-v2/approved-overlay.json").read_text())
    sunday_id = "c1_flat.sunday.02"
    take = frozen["campaign"]["takes"][sunday_id]
    audio_ids["sunday_steve"], paths["sunday_steve"] = sunday_id, from_res(take["file"])
    if not take["text"].startswith("Morning, Nor.") or sha256(paths["sunday_steve"]) != take["sha256"]:
        raise ValueError("The approved Sunday evidence performance has changed")
    paths["ident"] = from_res(soundscape["kbwr_ident"]["file"])
    audio_ids["ident"] = "kbwr_ident"

    loaded = {}
    for key, path in paths.items():
        samples, rate = load_mono(path)
        loaded[key] = resample_to_48k(samples, rate)

    ident, ident_start, ident_end, ident_tail = audible_ident_tail(loaded["ident"])
    clips = {"ident": (ident, ident_start, ident_end)}
    for key in ("saturday_autorick", "sunday_autorick", "nora", "saturday_steve"):
        clips[key] = trim_voice(loaded[key])
    sunday_steve, sunday_cut = cut_sunday_steve(loaded["sunday_steve"])
    clips["sunday_steve"] = (sunday_steve, 0, sunday_cut["source_end_frame"])

    tape_specs = {
        "saturday": (
            SATURDAY_IDENT_START,
            1109,
            ["ident", "saturday_autorick", "nora", "saturday_steve"],
            GAME / "assets/audio/effects/tape-saturday.wav",
        ),
        "sunday": (
            SATURDAY_IDENT_START + SUNDAY_DELAY,
            2109,
            ["ident", "sunday_autorick", "nora", "sunday_steve"],
            GAME / "assets/audio/effects/tape-sunday.wav",
        ),
    }
    label_for = {
        "ident": "Ident",
        "saturday_autorick": "AutoRick",
        "sunday_autorick": "AutoRick",
        "nora": "Nora",
        "saturday_steve": "Steve",
        "sunday_steve": "Steve",
    }
    gap_frames = round(GAP_SECONDS * RATE)
    relative_starts = {
        "Ident": 0,
        "AutoRick": clips["ident"][0].size + gap_frames,
    }
    relative_starts["Nora"] = (
        relative_starts["AutoRick"]
        + max(clips["saturday_autorick"][0].size, clips["sunday_autorick"][0].size)
        + gap_frames
    )
    relative_starts["Steve"] = (
        relative_starts["Nora"] + clips["nora"][0].size + gap_frames
    )

    tape_metadata = {}
    output_paths = {}
    for tape_name, (ident_start, seed, order, output_path) in tape_specs.items():
        placements = []
        ident_start_frame = round(ident_start * RATE)
        for key in order:
            clip, source_start, source_end = clips[key]
            start = ident_start_frame + relative_starts[label_for[key]]
            end = start + clip.size
            placements.append((key, clip, start, end, source_start, source_end))
        frames = placements[-1][3] + round(0.16 * RATE)
        mixed = cassette_noise(frames, seed)
        segments = []
        for key, clip, start, end, source_start, source_end in placements:
            mixed[start:end] += clip
            segments.append({
                "label": label_for[key],
                "start": round(start / RATE, 6),
                "end": round(end / RATE, 6),
                "source_audio_id": audio_ids[key],
                "source_file": "res://" + str(paths[key].relative_to(GAME)),
                "source_sha256": sha256(paths[key]),
                "source_start": round(source_start / RATE, 6),
                "source_end": round(source_end / RATE, 6),
                "clean_sha256": clean_hash(clip),
            })
        write_wav(output_path, mixed)
        output_paths[tape_name] = output_path
        tape_metadata[tape_name] = {
            "file": "res://" + str(output_path.relative_to(GAME)),
            "seconds": round(frames / RATE, 6),
            "noise_seed": seed,
            "segments": segments,
        }

    sources = {
        audio_ids[key]: {
            "file": "res://" + str(path.relative_to(GAME)),
            "sha256": sha256(path),
        }
        for key, path in paths.items()
    }
    metadata = {
        "schema": 1,
        "sample_rate": RATE,
        "format": "mono PCM16",
        "sunday_delay_seconds": SUNDAY_DELAY,
        "segment_gap_seconds": GAP_SECONDS,
        "segment_start_schedule_seconds": {
            label: round(start / RATE, 6) for label, start in relative_starts.items()
        },
        "noise": "Seeded low-level kitchen room tone and tape hiss; different seed per day.",
        "ident_tail": ident_tail,
        "sunday_steve_cut": sunday_cut,
        "sources": dict(sorted(sources.items())),
        "outputs": {
            name: {
                "file": "res://" + str(path.relative_to(GAME)),
                "sha256": sha256(path),
            }
            for name, path in output_paths.items()
        },
        "tapes": tape_metadata,
    }
    metadata_path = GAME / "assets/audio/effects/morning-tapes.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "saturday_seconds": tape_metadata["saturday"]["seconds"],
        "sunday_seconds": tape_metadata["sunday"]["seconds"],
        "sunday_steve_seconds": sunday_cut["seconds"],
        "outputs": metadata["outputs"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

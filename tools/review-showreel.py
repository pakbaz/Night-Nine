#!/usr/bin/env python3
"""Measure a recorded showreel's mix and sample its frames for review.

Reports integrated loudness, loudness range and true peak, lists every stretch
of near silence longer than two seconds, and writes a contact sheet of frames.

It also checks the picture for frozen stretches. Godot's Movie Maker keeps
writing frames when the engine skips drawing (a covered or minimized window on
macOS), so a recording can have perfect audio over a still picture. When the
Movie Maker .avi and the recording log sit next to the video, it compares the
frames the engine drew with the frames written (the gap is how long the window
was covered, which is fine when the recorder renders frames itself), and lists
runs of identical frames over four seconds. Clean recordings hold a picture for
about three seconds at most (a card's slow push-in, a storybook's last panel),
so anything longer is worth a look.
"""
import re, subprocess, sys
from pathlib import Path

def main(path, every=6.0):
    path = Path(path)
    out = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    rows = []
    for m in re.finditer(r"t: *([0-9.]+).*?M: *([-0-9.inf]+)", out):
        try: rows.append((float(m.group(1)), max(-90.0, float(m.group(2)))))
        except ValueError: pass
    summary = out[out.rfind("Summary:"):]
    integrated = re.search(r"I: *([-0-9.]+) LUFS", summary).group(1)
    lra = re.search(r"LRA: *([-0-9.]+) LU", summary).group(1)
    peak = re.search(r"Peak: *([-0-9.inf]+) dBFS", summary).group(1)
    duration = rows[-1][0]
    print(f"{path.name}: {duration:.1f} s, integrated {integrated} LUFS, range {lra} LU, true peak {peak} dBFS")
    quiet, start = [], None
    for t, m in rows:
        if m < -38 and start is None: start = t
        if m >= -38 and start is not None:
            if t - start > 2.0: quiet.append((start, t))
            start = None
    if start is not None and duration - start > 2.0: quiet.append((start, duration))
    print("  near-silent stretches over 2 s:", ", ".join(f"{a:.1f}-{b:.1f} s" for a, b in quiet) or "none")
    blocks = " ▁▂▃▄▅▆▇█"
    strip = ""
    for k in range(int(duration)):
        w = [m for t, m in rows if k <= t < k + 1]
        v = max(w) if w else -90
        strip += blocks[max(0, min(8, int((v + 45) / 35 * 8)))]
    print("  loudness, one character per second:")
    for i in range(0, len(strip), 60):
        print(f"  {i:4d}s |{strip[i:i+60]}|")
    check_picture(path)
    sheet = path.with_name(path.stem + "-frames.jpg")
    count = int(duration // every)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vf",
                    f"fps=1/{every},scale=480:300,tile=4x{max(1, (count + 3) // 4)}", "-frames:v", "1", str(sheet)], check=True)
    print("  frames:", sheet)

def check_picture(path, fps=30.0):
    avi = path.with_suffix(".avi")
    log = path.with_suffix(".log")
    if not avi.exists():
        print("  picture check: no Movie Maker .avi next to the video, skipped")
        return
    # Identical pictures give identical MJPEG packets, so hashing the .avi's
    # packets finds frozen frames without decoding. (This does not work on the
    # H.264 .mp4, whose packets differ even when the pictures match.)
    hashes = [line.rsplit(",", 1)[-1].strip() for line in subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(avi), "-map", "0:v", "-c", "copy", "-f", "framemd5", "-"],
        capture_output=True, text=True).stdout.splitlines() if line and not line.startswith("#")]
    runs, start = [], 0
    for i in range(1, len(hashes) + 1):
        if i == len(hashes) or hashes[i] != hashes[start]:
            if (i - start) / fps > 4.0:
                runs.append((start / fps, i / fps))
            start = i
    print("  identical frames over 4 s:", ", ".join(f"{a:.1f}-{b:.1f} s" for a, b in runs) or "none")
    if log.exists():
        drawn = re.search(r"^(\d+) frames at", log.read_text(errors="replace"), re.M)
        if drawn:
            drawn = int(drawn.group(1))
            # The recorder renders those frames itself, so a gap is not a freeze
            # unless the identical-frames line above lists long runs.
            note = "" if drawn >= len(hashes) else f"; the window was covered for about {(len(hashes) - drawn) / fps:.0f} s"
            print(f"  engine drew {drawn} of {len(hashes)} written frames{note}")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)

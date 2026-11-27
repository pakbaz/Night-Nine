#!/usr/bin/env python3
"""Give every score recording a bar grid, and decide which music plays where.

Tempo and per-bar loudness come from assets/audio/soundtrack/tempo.json. Run
with --measure to recompute them from the MP3s (ffmpeg required). Tempos above
120 BPM are counted at half time so that one bar lasts roughly two and a half
to three and a half seconds in every recording. Storybooks, chapter cards and
chapter-ending films are timed in these bars.

Music plan (November 23, 2026):
- By default the first location of each chapter plays that chapter's main
  theme and later locations play its background music (BGM). A chapter with
  one regular location plays its BGM there. The closing film returns to the
  theme at its loudest section, so every recording is heard.
- SCENE_TRACKS chooses by mood where the default does not fit: the quieter
  BGMs score sneaking, suspicion and quiet work, and the driving or melodic
  themes score escapes and emotional peaks.
- The three flashback "nights" keep the Three Nights BGM wherever they sit,
  except the bay itself: the Prologue plays its own BGM variation.
- Bellwether Bay (Tape Anomaly) scores the ninth night that ends Chapter 1.
- The main title scores the live broadcast, the ship rising and the last
  departure. Mysterious Take 2 is reserved for the completion credit film.
  The original Epilogue BGM plays in the epilogue.
  The short Epilogue theme plays once under the end card.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from ending_reward import apply_music as apply_ending_music

ROOT = Path(__file__).resolve().parents[1]
MUSIC = ROOT / 'game/content/music.json'
CAMPAIGN = ROOT / 'game/content/campaign.json'
FILMS = ROOT / 'game/content/films.json'
TEMPO = ROOT / 'assets/audio/soundtrack/tempo.json'
SOURCE = ROOT / 'game/assets/audio/music'
RES = 'res://assets/audio/music/'

EXTRA_TRACKS = {
    'tape_anomaly': {'file': RES + 'tape-anomaly.mp3', 'lufs': -19.2, 'title': 'Bellwether Bay (Tape Anomaly)'},
    'prologue_variation': {'file': RES + 'prologue-bgm-variation.mp3', 'lufs': -15.1,
                           'title': 'Prologue Background Music (Variation)'},
    'ending_reward': {'file': RES + 'epilogue-bgm.mp3', 'lufs': -16.8},
}

# Scenes whose music is chosen by hand. Values: (track key, start bar or None).
# A track key is "Chapter/bgm", "Chapter/theme", "title" or an EXTRA_TRACKS key.
SCENE_TRACKS = {
    'p_bay': ('prologue_variation', None),
    'p_veyr': ('Prologue/bgm', None),
    'p_meeting': ('Prologue/bgm', None),
    # The morning tape test at home, the busy Sunday harbor on the theme, the uneasy ninth night.
    'c1_flat': ('Chapter 1/bgm', None),
    'c1_pier': ('Chapter 1/theme', None),
    'c1_escape': ('tape_anomaly', None),
    # Sparse, low BGMs for sneaking and suspicion; the driving themes for the escapes.
    'c2_aquarium': ('Chapter 2/bgm', None),
    'c2_ship': ('Chapter 2/theme', None),
    'c4_safe': ('Chapter 4/bgm', None),
    'c4_escape': ('Chapter 4/theme', None),
    # The theme carries from the lab to Saren's offer at dawn; the busy BGM scores the workshop.
    'c8_beach': ('Chapter 8/theme', None),
    # The patient BGM through the Gallery and the waking; the luminous theme for the Choir.
    'c9_gallery': ('Chapter 9/bgm', None),
    'c9_wake': ('Chapter 9/bgm', None),
    'c9_choir': ('Chapter 9/theme', None),
    'c10_live': ('title', 4),
    'c10_report': ('title', 4),
    'epilogue': ('Epilogue/bgm', None),
    'one_year': ('Chapter 1/bgm', None),
}
FLASHBACKS = {'p_veyr', 'p_meeting'}

# Departures that carry their own music: (track key, start bar, bars).
# p_bay: the light rises on the Three Nights theme, which then carries the
#        aftermath storybook to the theme's own ending (bars 37 to 52).
# p_meeting: the Meridian signals rise on the theme's climax (bar 40).
# c10_report: the Long Patience rises on the main title's peak.
# epilogue: the lanterns start the Three Nights theme again, and the closing
#        storybook mirrors the aftermath over the same bars.
# one_year: the last departure reprises the main title before the reward film.
DEPARTURES = {
    'p_bay': ('Prologue/theme', 34, 3),
    'p_meeting': ('Prologue/theme', 40, 3),
    'c10_report': ('title', 32, 6),
    'epilogue': ('Prologue/theme', 27, 4),
    'one_year': ('title', 4, 5),
}


def ebur(path):
    out = subprocess.run(['ffmpeg', '-nostats', '-hide_banner', '-i', str(path), '-af', 'ebur128=peak=none', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    rows = []
    for m in re.finditer(r't: *([0-9.]+).*?M: *([-0-9.inf]+)', out):
        try:
            rows.append((float(m.group(1)), max(-70.0, float(m.group(2)))))
        except ValueError:
            pass
    return rows


def measure(names=None):
    sys.path.insert(0, str(ROOT / 'tools'))
    import music_tempo
    data = json.loads(TEMPO.read_text()) if TEMPO.exists() else {'tracks': {}}
    for path in sorted(SOURCE.glob('*.mp3')):
        record = data['tracks'].get(path.name)
        if names is None and record and 'bar_loudness' in record:
            continue
        if record is None or names is not None:
            env = music_tempo.onset_env(str(path))
            bpm = music_tempo.tempo(env)[0][1]
            record = {'detected_bpm': bpm, 'first_beat': round(music_tempo.phase(env, bpm), 3)}
        bpm, beat = half_time(record['detected_bpm']), record['first_beat']
        bar = 240.0 / bpm
        rows = ebur(path)
        loud = []
        t = beat
        while t < rows[-1][0]:
            window = [m for (s, m) in rows if t <= s < t + bar]
            loud.append(round(sum(window) / len(window), 2) if window else -70.0)
            t += bar
        record['bar_loudness'] = loud
        data['tracks'][path.name] = record
        print(path.name, record['detected_bpm'], record['first_beat'], len(loud), 'bars', flush=True)
    data['method'] = ('tools/music_tempo.py: onset envelope (11025 Hz, 256-sample hop), autocorrelation over 60-170 BPM, '
                      'phase by comb sum; bar_loudness is the mean EBU R128 momentary loudness of each bar')
    TEMPO.write_text(json.dumps(data, indent=2) + '\n')


def half_time(bpm):
    bpm = float(bpm)
    while bpm > 120:
        bpm /= 2
    return round(bpm, 3)


def main():
    if '--measure' in sys.argv or not TEMPO.exists():
        measure([] if '--measure' in sys.argv else None)
    tempo = json.loads(TEMPO.read_text())
    if any('bar_loudness' not in tempo['tracks'].get(p.name, {}) for p in SOURCE.glob('*.mp3')):
        measure()
        tempo = json.loads(TEMPO.read_text())
    music = json.loads(MUSIC.read_text())
    films = json.loads(FILMS.read_text())
    scenes = json.loads(CAMPAIGN.read_text())['scenes']

    def tag(track):
        record = tempo['tracks'][Path(track['file']).name]
        track['bpm'] = half_time(record['detected_bpm'])
        track['beat'] = float(record['first_beat'])
        # Mean loudness of each bar, for the score's automatic level riding.
        track['bar_loudness'] = [round(v, 1) for v in record['bar_loudness']]
        return track

    tag(music['title'])
    for group in music['chapters'].values():
        for track in group.values():
            tag(track)
    music['extras'] = {key: tag(dict(value)) for key, value in EXTRA_TRACKS.items()}

    def track(key):
        if key == 'title':
            return music['title']
        if key in music['extras']:
            return music['extras'][key]
        chapter, kind = key.split('/')
        return music['chapters'][chapter][kind]

    def bar_time(t, bar):
        return round(t['beat'] + bar * 240.0 / t['bpm'], 3)

    def entry_bar(t):
        return max(0, round((float(t.get('entry_seconds', 0.0)) - t['beat']) / (240.0 / t['bpm'])))

    # Chapter-ending films use the loudest stretch of their theme, on whole bars.
    for chapter, group in music['chapters'].items():
        theme = group.get('theme')
        if not theme:
            continue
        loud = tempo['tracks'][Path(theme['file']).name]['bar_loudness']
        bar = 240.0 / theme['bpm']
        last = [s for s in scenes if s['chapter'] == chapter]
        film = films.get(last[-1]['id'], {}).get('duration', 8.0) if last else 8.0
        span = max(2, int(-(-max(film, 8.0) // bar)))
        best = max(range(4, max(5, len(loud) - span - 3)), key=lambda k: sum(loud[k:k + span]))
        theme['climax_bar'] = best

    plan = {}
    previous = None
    themed = set()
    # A chapter with a single regular location plays its BGM there; its theme still closes it.
    regular = {}
    for scene in scenes:
        if scene['id'] not in FLASHBACKS:
            regular[scene['chapter']] = regular.get(scene['chapter'], 0) + 1
    for scene in scenes:
        chapter = scene['chapter']
        if scene['id'] in SCENE_TRACKS:
            key, bar = SCENE_TRACKS[scene['id']]
        elif chapter not in music['chapters']:
            previous = chapter
            continue
        elif chapter not in themed and scene['id'] not in FLASHBACKS and 'theme' in music['chapters'][chapter] and regular.get(chapter, 0) > 1:
            key, bar = chapter + '/theme', None
        else:
            key, bar = chapter + '/bgm', None
        if key.endswith('/theme'):
            themed.add(key.split('/')[0])
        source = track(key)
        start = bar_time(source, bar) if bar is not None else (
            bar_time(source, entry_bar(source)) if (key.endswith('/theme') or key == 'title') else 0.0)
        plan[scene['id']] = {'file': source['file'], 'lufs': source['lufs'], 'bpm': source['bpm'], 'beat': source['beat'],
                             'bar_loudness': source['bar_loudness'], 'entry_seconds': start,
                             'role': 'theme' if (key.endswith('/theme') or key == 'title') else 'bgm'}
        previous = chapter
    music['scene_music'] = plan
    music.pop('scene_bgm', None)

    departures = {}
    for scene_id, (key, bar, bars) in DEPARTURES.items():
        source = track(key)
        departures[scene_id] = {'file': source['file'], 'lufs': source['lufs'], 'bpm': source['bpm'],
                                'beat': source['beat'], 'bar': bar, 'bars': bars}
    music['departures'] = departures
    title = music['title']
    music['credits'] = {'file': title['file'], 'lufs': title['lufs'], 'bpm': title['bpm'], 'beat': title['beat'],
                        'entry_seconds': bar_time(title, 4)}
    finale = music['chapters']['Epilogue']['theme']
    music['finale'] = {'file': finale['file'], 'lufs': finale['lufs'], 'bpm': finale['bpm'], 'beat': finale['beat'],
                       'entry_seconds': 0.0, 'loop': False}
    apply_ending_music(music)
    MUSIC.write_text(json.dumps(music, indent=2) + '\n')
    print(json.dumps({'scenes': len(plan), 'departures': list(departures),
                      'climax_bars': {c: g['theme'].get('climax_bar') for c, g in music['chapters'].items() if 'theme' in g}}))


if __name__ == '__main__':
    main()

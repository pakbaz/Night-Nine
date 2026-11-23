#!/usr/bin/env python3
"""Night Nine script revision v2: merge, validate and render.

The revision lives in tools/script_v2/*.json. Each file holds scene edits that
are applied on top of the pristine build-story snapshot in tools/script_v2/base.
Run without arguments to validate and render the reviewable script into
docs/script-v2/. Run with --apply to write the playable content. The output is
never reused as the merge base.

Line references inside an edit:
  "c1_flat.in.02"              keep an existing line (moving it if needed)
  "steve|Text."                a new line
  {"id": ..., "text": ...}      rewrite an existing line (also speaker, delivery, direction, display)
  {"new": "speaker|Text.", ...} a new line with delivery, direction, display or audio
"""
import argparse
import copy
import csv
import hashlib
import json
import re
from pathlib import Path

from ending_reward import apply_music as apply_ending_music
from script_v2_voice_overlay import apply_overlay_to_content_dir

ROOT = Path(__file__).resolve().parents[1]
EDIT_DIR = Path(__file__).with_name('script_v2')
OUT_DIR = ROOT / 'docs' / 'script-v2'
BASE_DIR = Path(__file__).with_name('script_v2') / 'base'
CONTENT_DIR = ROOT / 'game' / 'content'
LIVE = {None, 'live'}
DELIVERIES = {'live', 'narration', 'phone', 'radio', 'intercom', 'broadcast', 'memory', 'voicemail',
              'recorded_playback', 'private_recording'}
TYPES = {'beat', 'choice', 'rows', 'board', 'tape', 'dial', 'compare'}
ALIASES = {'stephen': 'steve', 'iris': 'nora', 'pell': 'dale', 'agnes_original': 'agnes',
           'rook_copy': 'rook', 'lyle_copy': 'lyle'}


def load_edits(edit_dir=EDIT_DIR):
    merged = {'global': {}, 'scenes': {}, 'storybooks': {}}
    for path in sorted(edit_dir.glob('*.json')):
        data = json.loads(path.read_text())
        for key in ('global', 'storybooks'):
            for k, v in data.get(key, {}).items():
                if k in merged[key] and key == 'storybooks':
                    raise ValueError(f'{path.name}: storybook {k} edited twice')
                merged[key][k] = v
        for sid, edit in data.get('scenes', {}).items():
            if sid in merged['scenes']:
                raise ValueError(f'{path.name}: scene {sid} edited twice')
            edit['_file'] = path.name
            merged['scenes'][sid] = edit
    return merged


class Merge:
    def __init__(self, base, edits):
        self.base = base
        self.edits = edits
        self.issues = []
        self.engine = {}
        self.lines = {}
        self.used = {}
        self.origin = {}
        for scene in base['scenes']:
            for group in ('intro', 'outro'):
                for lid in scene[group]:
                    self.origin[lid] = (scene['id'], group)
            for task in scene['tasks']:
                for lid in task['lines']:
                    self.origin[lid] = (scene['id'], task['id'])
        self.counters = {}

    def issue(self, level, where, text):
        self.issues.append((level, where, text))

    def need(self, feature, where):
        self.engine.setdefault(feature, []).append(where)

    def next_id(self, prefix):
        if prefix not in self.counters:
            pattern = re.compile(re.escape(prefix) + r'\.(\d+)$')
            taken = [int(m.group(1)) for lid in self.base['lines'] if (m := pattern.match(lid))]
            self.counters[prefix] = max(taken, default=0)
        self.counters[prefix] += 1
        return f'{prefix}.{self.counters[prefix]:02}'

    def add(self, line, where):
        lid = line['id']
        if lid in self.used:
            self.issue('error', where, f'line {lid} used twice (also in {self.used[lid]})')
        self.used[lid] = where
        self.lines[lid] = line
        return lid

    def new_line(self, lid, spec, where, extra=None):
        if '|' not in spec:
            raise ValueError(f'{where}: expected speaker|text, got {spec!r}')
        speaker, text = spec.split('|', 1)
        line = {'id': lid, 'speaker': speaker.strip(), 'text': text.strip(), 'audio': lid, 'status': 'new'}
        for key in ('delivery', 'direction', 'display', 'audio', 'cue', 'sfx', 'display_text'):
            if extra and extra.get(key):
                line[key] = extra[key]
        if extra and extra.get('reaction'):
            line['reaction'] = extra['reaction']
        return self.add(line, where)

    def resolve(self, ref, prefix, where, scene_id, group, narration=False):
        if isinstance(ref, str) and '|' not in ref:
            if ref not in self.base['lines']:
                self.issue('error', where, f'unknown line {ref}')
                return None
            line = copy.deepcopy(self.base['lines'][ref])
            line['status'] = 'kept'
            if self.origin.get(ref) != (scene_id, group):
                line['status'] = 'moved'
                line['from'] = '/'.join(self.origin.get(ref, ('?', '?')))
            return self.add(line, where)
        if isinstance(ref, str):
            lid = self.next_id(prefix)
            new = self.new_line(lid, ref, where)
            if narration:
                self.lines[new].setdefault('delivery', 'narration')
            return new
        if 'new' in ref:
            lid = self.next_id(prefix)
            new = self.new_line(lid, ref['new'], where, ref)
            if narration:
                self.lines[new].setdefault('delivery', 'narration')
            return new
        lid = ref['id']
        if lid not in self.base['lines']:
            self.issue('error', where, f'unknown line {lid}')
            return None
        line = copy.deepcopy(self.base['lines'][lid])
        changed = False
        for key in ('text', 'speaker', 'delivery', 'direction', 'display', 'cue', 'sfx', 'display_text'):
            if key in ref and ref[key] != line.get(key):
                line[key] = ref[key]
                changed = changed or key in ('text', 'speaker')
        if 'text' in ref and line['audio'].startswith('recording.') and ref.get('audio') is None:
            line['audio'] = lid
        if ref.get('audio'):
            line['audio'] = ref['audio']
        line['status'] = 'revised' if changed else 'kept'
        if self.origin.get(lid) != (scene_id, group):
            line['from'] = '/'.join(self.origin.get(lid, ('?', '?')))
            if not changed:
                line['status'] = 'moved'
        return self.add(line, where)

    def resolve_list(self, refs, prefix, where, scene_id, group, narration=False):
        out = []
        for ref in refs:
            lid = self.resolve(ref, prefix, where, scene_id, group, narration)
            if lid:
                out.append(lid)
        return out

    def task_type(self, task):
        p = task.get('puzzle') or {}
        if task['id'] == 'p_bay.tune':
            return 'dial'
        if p.get('presentation') == 'case_board':
            return 'board'
        if p.get('presentation') == 'tape_alignment':
            return 'tape'
        if p.get('rows'):
            return 'rows'
        if task.get('evidence_labels'):
            return 'compare'
        return 'beat' if len(task['options']) == 1 else 'choice'

    def build_task(self, scene_id, key, edit, base_task):
        tid = f'{scene_id}.{key}'
        where = tid
        task = copy.deepcopy(base_task) if base_task else {
            'id': tid, 'title': '', 'prompt': '', 'options': [], 'answer': 0, 'lines': [], 'note': '',
            'requires': [], 'actor': '', 'kind': 'choice', 'sounds': [], 'hint': '', 'hints': []}
        task['status'] = 'kept' if base_task else 'new'
        edit = edit or {}
        if edit and base_task:
            task['status'] = 'revised'
        base_type = self.task_type(task)
        for field in ('title', 'prompt', 'actor', 'kind', 'goal', 'background', 'difficulty', 'note', 'sounds',
                      'evidence_labels', 'audition_labels', 'art'):
            if field in edit:
                task[field] = edit[field]
        if 'requires' in edit:
            task['requires'] = [f'{scene_id}.{r}' if '.' not in r else r for r in edit['requires']]
        ttype = edit.get('type', base_type)
        task['type'] = ttype
        if ttype not in TYPES:
            self.issue('error', where, f'unknown type {ttype}')
        if 'options' in edit:
            task['options'] = edit['options']
            task['answer'] = edit.get('answer', 0)
        elif 'answer' in edit:
            task['answer'] = edit['answer']
        if 'wrong' in edit:
            task['wrong'] = {str(k): v for k, v in edit['wrong'].items()}
        if ttype in ('beat', 'choice', 'compare') and base_type in ('rows', 'board') and 'rows' not in edit and 'board' not in edit:
            task.pop('puzzle', None)
        if 'rows' in edit:
            puzzle = {'instruction': edit.get('instruction', (task.get('puzzle') or {}).get('instruction', ''))}
            puzzle['rows'] = [{'label': r['label'], 'options': r['options']} for r in edit['rows']]
            puzzle['solution'] = [r['answer'] for r in edit['rows']]
            keep = task.get('puzzle') or {}
            if ttype == 'tape':
                puzzle['presentation'] = 'tape_alignment'
                tape = edit.get('tape')
                if tape:
                    puzzle.update(tape)
                else:
                    for k in ('recording_a', 'recording_b', 'segments', 'recording', 'lead_a', 'lead_b'):
                        if k in keep:
                            puzzle[k] = keep[k]
            task['puzzle'] = puzzle
        elif 'tape' in edit and ttype == 'tape':
            task.setdefault('puzzle', {})['presentation'] = 'tape_alignment'
            task['puzzle'].update(edit['tape'])
        elif 'instruction' in edit and task.get('puzzle') and ttype in ('rows', 'tape', 'dial'):
            task['puzzle']['instruction'] = edit['instruction']
        if 'board' in edit and edit['board'] != 'keep':
            b = edit['board']
            stages = b['stages']
            task['puzzle'] = {'presentation': 'case_board', 'instruction': b['instruction'], 'evidence': b['evidence'],
                              'stages': stages, 'solution': [a for s in stages for a in s['answer']],
                              'rows': [{'label': slot, 'options': s['pieces']} for s in stages for slot in s['slots']]}
            if b.get('wrong_text'):
                task['puzzle']['wrong_text'] = b['wrong_text']
        if 'hints' in edit:
            task['hints'] = edit['hints']
            if task.get('puzzle'):
                task['puzzle']['hints'] = edit['hints']
        task['lead'] = self.resolve_list(edit.get('lead', []), tid + '.lead', where, scene_id, tid)
        if task['lead']:
            self.need('Lead-in conversation that plays when a lead is first opened, before its puzzle', tid)
        if 'lines' in edit:
            task['lines'] = self.resolve_list(edit['lines'], tid, where, scene_id, tid)
        else:
            task['lines'] = self.resolve_list(task['lines'], tid, where, scene_id, tid)
        if edit.get('finding'):
            spec = edit['finding']
            lid = f'{tid}.find'
            fid = self.new_line(lid, spec if isinstance(spec, str) else spec['new'], where,
                                spec if isinstance(spec, dict) else None)
            self.lines[fid].setdefault('delivery', 'narration')
            task['finding'] = fid
            if 'note' not in edit:
                task['note'] = self.lines[fid]['text']
        task['changes'] = edit.get('changes', [])
        task.pop('hint', None)
        return task

    def build_scene(self, scene):
        sid = scene['id']
        edit = self.edits['scenes'].get(sid, {})
        out = copy.deepcopy(scene)
        for field in ('title', 'place', 'when', 'objective', 'objective_steps', 'coach', 'card', 'present', 'next',
                      'chapter', 'departure_art'):
            if field in edit:
                out[field] = edit[field]
        out.setdefault('present', list(scene.get('actors', [])))
        if 'actors' in edit:
            out['actors'] = edit['actors']
        out['context'] = self.resolve_list(edit.get('context', []), f'{sid}.ctx', sid + ' context', sid, 'context', True)
        out['intro'] = self.resolve_list(edit.get('intro', scene['intro']), f'{sid}.in', sid + ' intro', sid, 'intro')
        base_tasks = {t['id'].split('.', 1)[1]: t for t in scene['tasks']}
        task_edits = edit.get('tasks', {})
        order = edit.get('task_order') or [k for k in base_tasks] + [k for k in task_edits if k not in base_tasks]
        tasks = []
        for key in order:
            if task_edits.get(key) == 'DELETE':
                continue
            if key not in base_tasks and key not in task_edits:
                self.issue('error', sid, f'task {key} not found')
                continue
            tasks.append(self.build_task(sid, key, task_edits.get(key), base_tasks.get(key)))
        out['deleted_tasks'] = [f'{sid}.{k}' for k, v in task_edits.items() if v == 'DELETE']
        out['tasks'] = tasks
        talk = []
        for speaker, topics in edit.get('talk', {}).items():
            for number, topic in enumerate(topics, 1):
                topic_id = f'{sid}.talk.{speaker}.{number}'
                after = str(topic.get('after', '')).strip()
                until = str(topic.get('until', '')).strip()
                entry = {
                    'id': topic_id,
                    'speaker': speaker,
                    'topic': str(topic.get('topic', '')).strip(),
                    'after': f'{sid}.{after}' if after and '.' not in after else after,
                    'lines': self.resolve_list(
                        topic.get('lines', []), topic_id, topic_id, sid, topic_id),
                }
                if until:
                    entry['until'] = f'{sid}.{until}' if '.' not in until else until
                talk.append(entry)
        out['talk'] = talk
        out['recap'] = self.resolve_list(edit.get('recap', []), f'{sid}.recap', sid + ' recap', sid, 'recap', True)
        out['outro'] = self.resolve_list(edit.get('outro', scene['outro']), f'{sid}.out', sid + ' outro', sid, 'outro')
        out['changes'] = edit.get('changes', [])
        out['notes'] = edit.get('notes', [])
        out['edited'] = bool(edit)
        return out

    def run(self):
        scenes = [self.build_scene(s) for s in self.base['scenes']]
        missing = set(self.edits['scenes']) - {s['id'] for s in scenes}
        for sid in missing:
            self.issue('error', sid, 'edit names an unknown scene')
        for lid in self.base['lines']:
            if lid not in self.used:
                scene_id = self.origin.get(lid, ('?',))[0]
                deleted = self.edits['scenes'].get(scene_id, {}).get('delete', [])
                if lid in deleted:
                    continue
                self.issue('warning', scene_id, f'line {lid} is no longer used; add it to "delete" if intended')
        cast = dict(self.base['cast'])
        cast.update(self.edits['global'].get('cast_add', {}))
        content = {k: v for k, v in self.base.items() if k not in ('scenes', 'lines', 'cast')}
        content.update(scenes=scenes, lines=self.lines, cast=cast)
        apply_display(content, self.edits['global'].get('display', []))
        content['display_rules'] = self.edits['global'].get('display', [])
        if 'notebook_cases' in self.edits['global']:
            content['notebook_cases'] = self.edits['global']['notebook_cases']
        return content


def apply_display(content, rules):
    order = {s['id']: i for i, s in enumerate(content['scenes'])}
    for i, scene in enumerate(content['scenes']):
        groups = [scene['context'], scene['intro'], scene['recap'], scene['outro']]
        groups += [topic['lines'] for topic in scene.get('talk', [])]
        groups += [t.get('lead', []) + t['lines'] + ([t['finding']] if t.get('finding') else []) for t in scene['tasks']]
        for lid in (lid for g in groups for lid in g):
            line = content['lines'][lid]
            line['scene'] = scene['id']
            if line.get('display'):
                line['display_speaker'] = line['display']
                continue
            line.pop('display_speaker', None)
            for speaker, through, shown in rules:
                if line['speaker'] == speaker and i <= order[through]:
                    line['display_speaker'] = shown
                    break
            line['display'] = line.get('display_speaker') or content['cast'].get(line['speaker'], line['speaker'])
            line['display_speaker'] = line['display']


def visible_text(scene, content):
    """Every string a player can read in this scene, with a label for reports."""
    yield 'title', scene['title']
    yield 'objective', scene.get('objective', '')
    for step in scene.get('objective_steps', []) or []:
        yield 'objective', step if isinstance(step, str) else step.get('text', '')
    yield 'coach', scene.get('coach', '')
    yield 'card', json.dumps(scene.get('card', {}), ensure_ascii=False)
    for topic in scene.get('talk', []):
        yield topic['id'] + '.topic', topic.get('topic', '')
    for t in scene['tasks']:
        for field in ('title', 'goal', 'background', 'prompt', 'note'):
            yield f"{t['id']}.{field}", t.get(field, '')
        for o in t.get('options', []):
            yield f"{t['id']}.option", o
        for w in (t.get('wrong') or {}).values():
            yield f"{t['id']}.wrong", w
        for h in t.get('hints', []):
            yield f"{t['id']}.hint", h
        p = t.get('puzzle') or {}
        yield f"{t['id']}.instruction", p.get('instruction', '')
        for e in p.get('evidence', []):
            yield f"{t['id']}.evidence", e
        for st in p.get('stages', []):
            yield f"{t['id']}.stage", ' / '.join([st['prompt']] + st['slots'] + st['pieces'])
        for r in p.get('rows', []) if not p.get('stages') else []:
            yield f"{t['id']}.row", ' / '.join([r['label']] + r['options'])
        for lab in t.get('evidence_labels', []) + t.get('audition_labels', []):
            yield f"{t['id']}.label", lab
    for g in ('context', 'intro', 'recap', 'outro'):
        for lid in scene[g]:
            line = content['lines'][lid]
            yield lid, line.get('display_text') or line['text']
            yield lid + '.speaker', line.get('display_speaker') or content['cast'].get(line['speaker'], line['speaker'])
    for topic in scene.get('talk', []):
        for lid in topic['lines']:
            line = content['lines'][lid]
            yield lid, line.get('display_text') or line['text']
            yield lid + '.speaker', line.get('display_speaker') or content['cast'].get(line['speaker'], line['speaker'])
    for t in scene['tasks']:
        for lid in t.get('lead', []) + t['lines'] + ([t['finding']] if t.get('finding') else []):
            line = content['lines'][lid]
            yield lid, line.get('display_text') or line['text']
            yield lid + '.speaker', line.get('display_speaker') or content['cast'].get(line['speaker'], line['speaker'])


def validate(content, edits, merge):
    order = {s['id']: i for i, s in enumerate(content['scenes'])}
    cast = content['cast']
    g = edits['global']
    for sid, appearances in g.get('scene_appearances', {}).items():
        if sid not in order:
            merge.issue('error', sid, 'portrait override references an unknown scene')
        for actor, profile in appearances.items():
            if actor not in cast:
                merge.issue('error', sid, f'portrait override references an unknown actor: {actor}')
            if not isinstance(profile, str) or not re.fullmatch(r'[a-z0-9_]+', profile):
                merge.issue('error', sid, f'invalid portrait profile: {profile}')
                continue
            folder = ROOT / 'game/assets/illustrated/cast' / profile
            metadata = folder / 'sprite.json'
            if not metadata.is_file():
                merge.issue('error', sid, f'portrait metadata not found: {profile}')
            else:
                sprite = json.loads(metadata.read_text())
                if not (folder / sprite.get('base', '')).is_file():
                    merge.issue('error', sid, f'portrait image not found: {profile}')
    for scene in content['scenes']:
        sid = scene['id']
        ids = {t['id'] for t in scene['tasks']}
        present = set(scene.get('present', [])) | set(g.get('always_present', []))
        # The scene departs on its own after its last lead, so a topic can only wait for
        # a lead that some other lead requires; that lead can never be solved last.
        needs = {t['id']: set(t.get('requires', [])) for t in scene['tasks']}
        required = set()
        frontier = [r for reqs in needs.values() for r in reqs]
        while frontier:
            task_id = frontier.pop()
            if task_id not in required:
                required.add(task_id)
                frontier.extend(needs.get(task_id, ()))
        for topic in scene.get('talk', []):
            where = topic['id']
            label = str(topic.get('topic', ''))
            speaker = str(topic.get('speaker', ''))
            if not label:
                merge.issue('error', where, 'talk topic is empty')
            elif len(label) > 48:
                merge.issue('error', where, 'talk topic is longer than 48 characters')
            if len(topic.get('lines', [])) < 2:
                merge.issue('error', where, 'talk topic needs at least two lines')
            if topic.get('after') and topic['after'] not in ids:
                merge.issue('error', where, f"talk after names unknown task {topic['after']}")
            elif topic.get('after') and topic['after'] not in required:
                merge.issue('error', where, f"talk after {topic['after']} could be the last lead, so the topic might never be heard")
            if topic.get('until') and topic['until'] not in ids:
                merge.issue('error', where, f"talk until names unknown task {topic['until']}")
            if speaker not in cast:
                merge.issue('error', where, f'unknown talk speaker {speaker}')
            elif speaker not in present:
                merge.issue('error', where, f'talk speaker {speaker} is not present in {sid}')
        for where, art in [(sid, scene.get('departure_art'))] + [(t['id'], t.get('art')) for t in scene['tasks']]:
            if art and not (str(art).startswith('res://') and (ROOT / 'game' / str(art)[6:]).is_file()):
                merge.issue('error', where, f'art file not found: {art}')
        for t in scene['tasks']:
            where = t['id']
            if not scene['edited']:
                continue
            for field in ('goal', 'background', 'prompt'):
                if not str(t.get(field, '')).strip():
                    merge.issue('error', where, f'missing {field}')
            if len(t.get('hints', [])) != 3 or not all(str(h).strip() for h in t['hints']):
                merge.issue('error', where, 'needs exactly three hints')
            if not t.get('finding') and where not in g.get('no_finding', []):
                merge.issue('error', where, 'missing finding narration')
            for r in t['requires']:
                if r not in ids:
                    merge.issue('error', where, f'requires unknown task {r}')
            typ = t['type']
            if typ == 'beat':
                if len(t['options']) != 1:
                    merge.issue('error', where, 'a beat has exactly one option')
            elif typ in ('choice', 'compare'):
                if len(t['options']) < 2 or not 0 <= t['answer'] < len(t['options']):
                    merge.issue('error', where, 'choice needs two or more options and a valid answer')
                missing = [i for i in range(len(t['options'])) if i != t['answer'] and not (t.get('wrong') or {}).get(str(i))]
                if missing:
                    merge.issue('error', where, f'missing wrong-answer feedback for options {missing}')
            if typ in ('rows', 'tape'):
                p = t.get('puzzle') or {}
                for r, a in zip(p.get('rows', []), p.get('solution', [])):
                    if not 0 <= a < len(r['options']) or len(r['options']) < 2:
                        merge.issue('error', where, f"row {r['label']} has an invalid answer")
                if len(p.get('rows', [])) != len(p.get('solution', [])):
                    merge.issue('error', where, 'rows and solution differ in length')
            if typ == 'board':
                p = t.get('puzzle') or {}
                stages = p.get('stages', [])
                if not 1 <= len(stages) <= 3:
                    merge.issue('error', where, 'a board needs one to three stages')
                for n, st in enumerate(stages, 1):
                    slots, pieces, answer = st['slots'], st['pieces'], st['answer']
                    if st['mode'] not in ('order', 'match', 'route'):
                        merge.issue('error', where, f'stage {n} mode')
                    if len(set(slots)) != len(slots):
                        merge.issue('error', where, f'stage {n} repeats a slot')
                    if len(set(pieces)) != len(pieces):
                        merge.issue('error', where, f'stage {n} repeats a piece')
                    if not 1 <= len(slots) <= 5 or len(pieces) < len(slots):
                        merge.issue('error', where, f'stage {n} needs one to five slots and enough pieces')
                    if len(answer) != len(slots) or len(set(answer)) != len(answer) or not all(0 <= a < len(pieces) for a in answer):
                        merge.issue('error', where, f'stage {n} answer does not fit its slots and pieces')
                    if len(pieces) > len(slots):
                        merge.need('Case boards with decoy pieces (more pieces than slots)', f'{where} stage {n}')
                    if not 3 <= len(slots) <= 5:
                        merge.need('Case boards with one, two or more than five slots', f'{where} stage {n}')
        for label, text in visible_text(scene, content):
            for rule in g.get('spoilers', []):
                first = rule.get('from')
                if rule.get('banned') or (first and order[sid] < order[first]):
                    flags = re.IGNORECASE if rule.get('ignore_case') else 0
                    if text and re.search(rule['pattern'], text, flags):
                        if label in rule.get('allow', []):
                            continue
                        merge.issue('error', sid, f"spoiler '{rule['pattern']}' before {first or 'ever'} in {label}: {text[:90]}")
        groups = scene['context'] + scene['intro'] + scene['recap'] + scene['outro'] \
            + [lid for topic in scene.get('talk', []) for lid in topic['lines']] \
            + [lid for t in scene['tasks'] for lid in t.get('lead', []) + t['lines']]
        for lid in groups:
            line = content['lines'][lid]
            if line['speaker'] not in cast:
                merge.issue('error', lid, f"unknown speaker {line['speaker']}")
            if line.get('delivery') not in DELIVERIES | {None}:
                merge.issue('error', lid, f"unknown delivery {line.get('delivery')}")
            if scene['edited'] and line.get('status') in ('new', 'revised', 'moved') and line.get('delivery') in LIVE \
                    and not line['audio'].startswith('recording.') and line['speaker'] not in present:
                merge.issue('warning', lid, f"{line['speaker']} speaks live but is not listed as present in {sid}")
    for case_id, case in content.get('notebook_cases', {}).items():
        tasks = {t['id'] for s in content['scenes'] for t in s['tasks']}
        for clue in case['clues'] + [th['after'] for th in case['theories']]:
            if clue not in tasks:
                merge.issue('error', 'notebook', f'case {case_id} names missing task {clue}')


def voice_for(speaker, casting):
    key = ALIASES.get(speaker, speaker)
    role = casting['roles'].get(key)
    return (role['library_name'], role['voice_id']) if role else ('UNCAST', '')


def storybook_lines(base_books, edits):
    books = {}
    for name, book in base_books['books'].items():
        edit = edits['storybooks'].get(name)
        panels = []
        for n, panel in enumerate(book['panels']):
            texts = [ln['text'] for ln in panel['lines']]
            status = 'kept'
            if edit and n < len(edit['panels']):
                if edit['panels'][n] != texts:
                    texts, status = edit['panels'][n], 'revised'
            panels.append({'image': panel['image'], 'lines': texts, 'status': status})
        if edit and len(edit['panels']) > len(book['panels']):
            for extra in edit['panels'][len(book['panels']):]:
                panels.append({'image': 'NEW PANEL', 'lines': extra, 'status': 'new'})
        books[name] = {'title': (edit or {}).get('title', book.get('title', name)), 'before': book.get('before'),
                       'panels': panels, 'narrator': 'steve'}
    return books


def playable_storybooks(base_books, edits):
    """Keep the authored timing/art while replacing the reviewed caption text."""
    result = copy.deepcopy(base_books)
    for name, edit in edits['storybooks'].items():
        if name not in result['books']:
            raise ValueError(f'unknown storybook {name}')
        book = result['books'][name]
        source_panels = book['panels']
        panels = []
        for index, texts in enumerate(edit['panels']):
            if index >= len(source_panels):
                raise ValueError(f'{name}: new panel {index + 1} needs authored art and timing')
            panel = copy.deepcopy(source_panels[index])
            old_lines = panel.get('lines', [])
            if not old_lines:
                raise ValueError(f'{name}: panel {index + 1} has no timing anchors')
            lines = []
            for line_index, text in enumerate(texts):
                anchor = copy.deepcopy(old_lines[min(line_index, len(old_lines) - 1)])
                anchor['text'] = text
                anchor['narration'] = ''
                anchor['seconds'] = round(2.5 + len(text) / 20.0, 3)
                lines.append(anchor)
            panel['lines'] = lines
            panels.append(panel)
        book['panels'] = panels
        if edit.get('title'):
            book['title'] = edit['title']
    return result


def clean_campaign(content):
    result = copy.deepcopy(content)
    result['version'] = 'campaign-3'
    for key in ('display_rules', 'storybooks'):
        result.pop(key, None)
    for scene in result['scenes']:
        for key in ('status', 'changes', 'edited', 'deleted_tasks', 'notes'):
            scene.pop(key, None)
        for task in scene['tasks']:
            for key in ('status', 'changes'):
                task.pop(key, None)
    for line in result['lines'].values():
        for key in ('status', 'from', 'scene'):
            line.pop(key, None)
    labels = result.setdefault('sound_labels', {})
    for scene in result['scenes']:
        for task in scene['tasks']:
            names = task.get('evidence_labels') or task.get('audition_labels') or []
            for sound, name in zip(task.get('sounds', []), names):
                labels.setdefault(sound, 'Listen: ' + name)
    labels.update({
        'effect.kbwr_ident': 'Listen: Steve’s twelve-second KBWR station ident',
        'effect.harbor_winch': 'Listen: the harbor winch',
        'effect.nora_whistle_flat': 'Listen: the falling two-note whistle',
        'effect.steve_whistle': 'Listen: Steve’s breathy two-note whistle',
    })
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def rebuild_voice_manifest(content, base_manifest):
    required = {}
    for line in content['lines'].values():
        required.setdefault(line['audio'], line)
    old_takes = base_manifest.get('takes', {})
    takes = {}
    for audio_id, line in required.items():
        old = copy.deepcopy(old_takes.get(audio_id, {}))
        if old:
            take = old
        else:
            take = {'id': audio_id, 'speaker': line['speaker'], 'text': line['text'],
                    'status': 'unrecorded', 'file': '', 'sha256': ''}
        recorded_text = str(take.get('text', line['text']))
        take['text_hash'] = text_hash(recorded_text)
        takes[audio_id] = take
    return {'schema': 1, 'enabled': False, 'takes': takes}


def rebuild_narration(storybooks, base_narration):
    books = {}
    for name, book in storybooks['books'].items():
        books[name] = [{'file': '', 'seconds': float(line.get('seconds', 0.0)),
                        'caption': line['text'], 'status': 'unrecorded',
                        'text_hash': text_hash(line['text'])}
                       for panel in book['panels'] for line in panel.get('lines', [])]
    return {'schema': 1, 'enabled': False, 'voice': base_narration.get('voice', ''), 'books': books}


def valid_reference(value, scene_ids, task_ids, line_ids):
    if value in task_ids or value in line_ids:
        return True
    return any(value == scene_id + suffix for scene_id in scene_ids for suffix in ('.in', '.out', '.context', '.recap'))


def filter_illustrated_campaign(data, content, appearances=None):
    result = copy.deepcopy(data)
    appearances = appearances or {}
    portrait_aliases = {'agnes_original': 'agnes', 'lyle_copy': 'lyle', 'rook_copy': 'rook', 'dale': 'pell'}
    scene_ids = {s['id'] for s in content['scenes']}
    task_ids = {t['id'] for s in content['scenes'] for t in s['tasks']}
    line_ids = set(content['lines'])
    replacements = {'c1_pier.whistle.01': 'c1_pier.whistle.02'}
    for scene_id in list(result):
        if scene_id not in scene_ids:
            del result[scene_id]
            continue
        scene = result[scene_id]
        if appearances and scene_id in appearances:
            scene.setdefault('appearances', {}).update(appearances[scene_id])
        merged_appearances = scene.get('appearances', {})
        company = scene.setdefault('company', [])
        content_scene = next(s for s in content['scenes'] if s['id'] == scene_id)
        for topic in content_scene.get('talk', []):
            speaker = topic['speaker']
            profile = merged_appearances.get(speaker, portrait_aliases.get(speaker, speaker))
            folder = ROOT / 'game/assets/illustrated/cast' / profile
            metadata = folder / 'sprite.json'
            if not metadata.is_file():
                continue
            portrait = json.loads(metadata.read_text())
            if (folder / portrait.get('base', '')).is_file() and speaker not in company:
                company.append(speaker)
        for field in ('off_camera_lines',):
            scene[field] = [replacements.get(x, x) for x in scene.get(field, [])
                            if replacements.get(x, x) in line_ids]
            if not scene[field]:
                scene.pop(field, None)
        for creature in scene.get('creatures', []):
            if 'lines' in creature:
                creature['lines'] = [replacements.get(x, x) for x in creature['lines']
                                     if replacements.get(x, x) in line_ids]
        if isinstance(scene.get('cutaway'), dict) and 'lines' in scene['cutaway']:
            scene['cutaway']['lines'] = [x for x in scene['cutaway']['lines'] if x in line_ids]
        inserts = {}
        for key, value in scene.get('inserts', {}).items():
            key = replacements.get(key, key)
            if not valid_reference(key, scene_ids, task_ids, line_ids):
                continue
            if isinstance(value, str):
                value = replacements.get(value, value)
                if not valid_reference(value, scene_ids, task_ids, line_ids):
                    continue
            inserts[key] = value
        if inserts:
            scene['inserts'] = inserts
        else:
            scene.pop('inserts', None)
    return result


def filter_staging(data, content):
    result = copy.deepcopy(data)
    task_ids = {t['id'] for s in content['scenes'] for t in s['tasks']}
    line_ids = set(content['lines'])
    scene_ids = {s['id'] for s in content['scenes']}
    for scene_id in list(result.get('scenes', {})):
        if scene_id not in scene_ids:
            del result['scenes'][scene_id]
            continue
        scene = result['scenes'][scene_id]
        scene['targets'] = {k: v for k, v in scene.get('targets', {}).items() if k in task_ids}
        scene['dialogue_groups'] = [x for x in scene.get('dialogue_groups', [])
                                    if valid_reference(x, scene_ids, task_ids, line_ids)]
    return result


def filter_hotspots(landmarks, floors, content):
    task_ids = {t['id'] for s in content['scenes'] for t in s['tasks']}
    scene_tasks = {s['id']: {t['id'].split('.', 1)[1] for t in s['tasks']} for s in content['scenes']}
    landmarks = copy.deepcopy(landmarks)
    floors = copy.deepcopy(floors)
    for scene_id in list(landmarks):
        landmarks[scene_id] = {k: v for k, v in landmarks[scene_id].items() if k in task_ids}
    landmarks.setdefault('c2_ship', {})['c2_ship.intake'] = [0.55, 0.31, 0.18, 0.25]
    for scene_id, floor in floors.items():
        keys = scene_tasks.get(scene_id, set())
        for field in ('approach', 'landmarks', 'contact'):
            if field in floor:
                floor[field] = {k: v for k, v in floor[field].items() if k in keys}
        if 'listen' in floor:
            floor['listen'] = [k for k in floor['listen'] if k in keys]
    ship = floors['c2_ship']
    ship['approach']['intake'] = [0.62, 0.76]
    ship.pop('landmarks', None)
    ship.setdefault('contact', {})['intake'] = [0.62, 0.45]
    return landmarks, floors


def apply_content(content, books, base_dir, content_dir):
    campaign = clean_campaign(content)
    storybooks = playable_storybooks(json.loads((base_dir / 'storybook.json').read_text()),
                                     {'storybooks': load_edits()['storybooks']})
    write_json(content_dir / 'campaign.json', campaign)
    write_json(content_dir / 'storybook.json', storybooks)
    narration_base = json.loads((base_dir / 'narration.json').read_text())
    write_json(content_dir / 'narration.json', rebuild_narration(storybooks, narration_base))
    voice_base = json.loads((base_dir / 'voice-manifest.json').read_text())
    voice = rebuild_voice_manifest(campaign, voice_base)
    write_json(content_dir / 'voice-manifest.json', voice)
    lipsync = json.loads((base_dir / 'lipsync-manifest.json').read_text())
    lipsync['takes'] = {k: v for k, v in lipsync.get('takes', {}).items() if k in voice['takes']}
    write_json(content_dir / 'lipsync-manifest.json', lipsync)
    illustrated = filter_illustrated_campaign(
        json.loads((base_dir / 'illustrated-campaign.json').read_text()), campaign,
        load_edits()['global'].get('scene_appearances', {}))
    write_json(content_dir / 'illustrated-campaign.json', illustrated)
    staging = filter_staging(json.loads((base_dir / 'staging.json').read_text()), campaign)
    write_json(content_dir / 'staging.json', staging)
    landmarks, floors = filter_hotspots(
        json.loads((base_dir / 'illustrated-landmarks.json').read_text()),
        json.loads((base_dir / 'illustrated-floor.json').read_text()), campaign)
    write_json(content_dir / 'illustrated-landmarks.json', landmarks)
    write_json(content_dir / 'illustrated-floor.json', floors)
    scene_ids = {s['id'] for s in campaign['scenes']}
    films = json.loads((base_dir / 'films.json').read_text())
    write_json(content_dir / 'films.json', {k: v for k, v in films.items() if k in scene_ids})
    music = json.loads((base_dir / 'music.json').read_text())
    for field in ('scene_music', 'departures'):
        music[field] = {k: v for k, v in music.get(field, {}).items() if k in scene_ids}
    apply_ending_music(music)
    write_json(content_dir / 'music.json', music)
    apply_overlay_to_content_dir(content_dir)


def render(content, books, merge, casting, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cast = content['cast']
    lines = content['lines']
    before = {b['before']: (name, b) for name, b in books.items()}
    md = ['# Night Nine: revised script (v2)', '',
          'Generated by `python3 tools/script_v2.py` from `tools/script_v2/*.json` on top of `game/content/campaign.json`. '
          'Do not edit this file by hand.', '',
          'Legend: **NEW** new line, **REV** rewritten, **MOV** moved from another place, unmarked lines are unchanged. '
          '*Italic lines* are narration in the narrating character\'s voice. ✓ marks the correct choice.', '']
    rows = []
    seen_audio = {}
    order = 0

    def say(lid):
        nonlocal order
        line = lines[lid]
        who = line.get('display_speaker') or cast.get(line['speaker'], line['speaker'])
        tag = {'new': ' **NEW**', 'revised': ' **REV**', 'moved': ' **MOV**'}.get(line.get('status'), '')
        delivery = line.get('delivery')
        extra = f' ({delivery})' if delivery not in (None, 'live', 'narration') else ''
        direction = f' [{line["direction"]}]' if line.get('direction') else ''
        if line.get('sfx'):
            direction += f' *(sound: {line["sfx"]})*'
        elif line.get('cue'):
            direction += f' *(sound: {line["cue"]})*'
        text = line.get('display_text') or line['text']
        if line.get('display_text') and line['display_text'] != line['text']:
            text += f' *(spoken: {line["text"]})*'
        order += 1
        voice, vid = voice_for(line['speaker'], casting)
        audio = line['audio']
        if audio.startswith('recording.') and audio in seen_audio:
            plan = 'reuse ' + seen_audio[audio]
        else:
            plan = 'record'
            seen_audio.setdefault(audio, lid)
        rows.append([order, lid, line.get('scene', ''), line['speaker'], who, voice, vid, delivery or 'live',
                     line.get('direction', ''), line['text'], line.get('status', 'kept'), len(line['text']), audio, plan])
        if delivery == 'narration':
            return f'- *{who}: {text}*{tag} `{lid}`'
        return f'- **{who}**{extra}{direction}: {text}{tag} `{lid}`'

    def book(name, b):
        md.extend([f'## Storybook: {b["title"]}', ''])
        for n, panel in enumerate(b['panels'], 1):
            tag = {'revised': ' **REV**', 'new': ' **NEW**'}.get(panel['status'], '')
            for m, text in enumerate(panel['lines'], 1):
                nonlocal_order_row(name, n, m, text, panel['status'])
                md.append(f'- *Steve: {text}*{tag} `book.{name}.{n}.{m}`')
        md.append('')

    def nonlocal_order_row(name, n, m, text, status):
        nonlocal order
        order += 1
        voice, vid = voice_for('steve', casting)
        rows.append([order, f'book.{name}.{n}.{m}', f'storybook:{name}', 'steve', 'Steve Mercer', voice, vid,
                     'narration', '', text, status, len(text), f'book.{name}.{n}.{m}', 'record'])

    for scene in content['scenes']:
        if scene['id'] in before:
            book(*before[scene['id']])
        card = scene.get('card') or {}
        head = card.get('chapter') if isinstance(card.get('chapter'), dict) else None
        md.append(f"## {scene['chapter']}: {scene['title']} (`{scene['id']}`)")
        md.append('')
        meta = [f"**Where:** {scene['place']}"]
        if scene.get('when'):
            meta.append(f"**When:** {scene['when']}")
        if scene.get('present'):
            idx = [x['id'] for x in content['scenes']].index(scene['id'])
            order_ids = [x['id'] for x in content['scenes']]
            def shown(p):
                for speaker, through, label in content.get('display_rules', []):
                    if speaker == p and idx <= order_ids.index(through):
                        return label
                return cast.get(p, p)
            meta.append('**Present:** ' + ', '.join(shown(p) for p in scene['present']))
        md.append(' · '.join(meta))
        if head:
            md.append(f"\n**Chapter card:** {head.get('kicker', '')}, *{head.get('title', '')}*"
                      + (f" · {head['when']}" if head.get('when') else '') + (f" · {head['goal']}" if head.get('goal') else ''))
        md.append(f"\n**Objective:** {scene.get('objective', '')}")
        for step in scene.get('objective_steps', []) or []:
            md.append(f"- then: {step}")
        if scene.get('coach'):
            md.append(f"\n**Coach tip:** {scene['coach']}")
        if scene.get('changes'):
            md.append(f"\n**Revision notes:** {', '.join(scene['changes'])}")
        for note in scene.get('notes', []):
            md.append(f"\n> Implementation: {note}")
        md.append('')
        if scene['intro'] or scene['context']:
            md.append('### Opening')
            md.extend(say(lid) for lid in scene['context'])
            md.extend(say(lid) for lid in scene['intro'])
            md.append('')
        if scene.get('talk'):
            md.append('### Small talk')
            for topic in scene['talk']:
                after = f" · after `{topic['after']}`" if topic.get('after') else ''
                md.append(f"**{topic['topic']}** · {shown(topic['speaker'])}{after}")
                md.extend(say(lid) for lid in topic['lines'])
                md.append('')
        for n, t in enumerate(scene['tasks'], 1):
            tag = {'new': ' **NEW LEAD**', 'revised': ''}.get(t.get('status'), '')
            diff = f" · difficulty {t['difficulty']}" if t.get('difficulty') else ''
            who = f" · played as {cast.get(t['actor'], t['actor'])}" if t.get('actor') else ''
            md.append(f"### Lead {n}: {t['title']} (`{t['id']}`) · {t['type']}{diff}{who}{tag}")
            if t['requires']:
                md.append(f"*Unlocks after:* {', '.join(t['requires'])}")
            if t.get('lead'):
                md.append('\n**When the lead opens:**')
                md.extend(say(lid) for lid in t['lead'])
            for field, label in (('goal', 'Goal'), ('background', 'What Steve knows'), ('prompt', 'Prompt')):
                if t.get(field):
                    md.append(f"\n**{label}:** {t[field]}")
            p = t.get('puzzle') or {}
            if t['type'] in ('choice', 'beat', 'compare'):
                if t.get('evidence_labels'):
                    md.append(f"\n**Recordings:** {' · '.join(t['evidence_labels'])}")
                md.append('')
                for i, o in enumerate(t['options']):
                    if i == t['answer']:
                        md.append(f"- ✓ {o}")
                    else:
                        md.append(f"- {o}. *Wrong:* {(t.get('wrong') or {}).get(str(i), '(no feedback yet)')}")
            if p.get('instruction'):
                md.append(f"\n**Instruction:** {p['instruction']}")
            if t['type'] in ('rows', 'tape'):
                for r, a in zip(p.get('rows', []), p.get('solution', [])):
                    md.append(f"- {r['label']}: " + ' / '.join(('✓ ' if i == a else '') + o for i, o in enumerate(r['options'])))
            if t['type'] == 'board':
                md.append('\n**Case notes:**')
                md.extend(f'{i}. {e}' for i, e in enumerate(p.get('evidence', []), 1))
                for k, st in enumerate(p.get('stages', []), 1):
                    md.append(f"\n**Stage {k} ({st['mode']}):** {st['prompt']}")
                    md.append(f"- Cards: {', '.join(st['pieces'])}")
                    md.append('- Answer: ' + '; '.join(f"{s} → {st['pieces'][a]}" for s, a in zip(st['slots'], st['answer'])))
            if t.get('hints'):
                md.append('\n**Hints:**')
                md.extend(f'{i}. {h}' for i, h in enumerate(t['hints'], 1))
            if t['lines']:
                md.append('\n**On success:**')
                md.extend(say(lid) for lid in t['lines'])
            if t.get('finding'):
                md.append('\n**Finding:**')
                md.append(say(t['finding']))
            if t.get('note') and t.get('finding') and t['note'] != lines[t['finding']]['text']:
                md.append(f"\n**Notebook:** {t['note']}")
            if t.get('changes'):
                md.append(f"\n*Revision notes:* {', '.join(t['changes'])}")
            md.append('')
        if scene.get('deleted_tasks'):
            md.append(f"*Removed leads:* {', '.join(scene['deleted_tasks'])}\n")
        if scene['recap']:
            md.append('### Scene complete')
            md.extend(say(lid) for lid in scene['recap'])
            md.append('')
        if scene['outro']:
            md.append('### Departure')
            md.extend(say(lid) for lid in scene['outro'])
            md.append('')
        if scene.get('next'):
            md.append(f"**Next:** {scene['next']}\n")
    for name, b in books.items():
        if not b.get('before') or b['before'] not in {s['id'] for s in content['scenes']}:
            book(name, b)
    (out_dir / 'script.md').write_text('\n'.join(md).rstrip() + '\n')
    with open(out_dir / 'recording-list.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['order', 'line_id', 'scene', 'speaker_key', 'shown_as', 'voice', 'voice_id', 'delivery', 'direction',
                    'text', 'status', 'characters', 'audio_key', 'plan'])
        w.writerows(rows)
    to_record = [r for r in rows if r[-1] == 'record']
    stats = {'lines_to_record': len(to_record), 'characters_to_record': sum(r[11] for r in to_record),
             'new': sum(r[10] == 'new' for r in rows), 'revised': sum(r[10] == 'revised' for r in rows),
             'moved': sum(r[10] == 'moved' for r in rows), 'kept': sum(r[10] == 'kept' for r in rows),
             'uncast': sorted({r[3] for r in rows if r[5] == 'UNCAST'})}
    return stats


def validate_staging(staging, content, merge):
    """Story paintings must exist and point at real lines; layers and reveals wait for a lead or line of their scene."""
    line_ids = set(content['lines'])
    scenes = {s['id']: s for s in content['scenes']}

    def painting(where, path):
        if not (str(path).startswith('res://') and (ROOT / 'game' / str(path)[6:]).is_file()):
            merge.issue('error', where, f'missing painting {path}')

    for scene_id, scene in staging.items():
        if scene_id not in scenes:
            continue
        for still in scene.get('stills', []):
            painting(scene_id, still.get('file', ''))
            for item in still.get('lines', []):
                if item not in line_ids and not any(line.startswith(item + '.') for line in line_ids):
                    merge.issue('error', scene_id, f'still names unknown line or lead {item}')
        if scene.get('bridge'):
            painting(scene_id, scene['bridge'])
        for path in scene.get('chapter_frames', []):
            painting(scene_id, path)
        cutaway = scene.get('cutaway', {})
        if 'path' in cutaway:
            painting(scene_id, cutaway['path'])
        if 'onboard_task' in cutaway:
            tasks = {t['id'] for t in scenes[scene_id]['tasks']}
            if cutaway.get('after') not in tasks or cutaway['onboard_task'] not in tasks:
                merge.issue('error', scene_id, 'transport cutaway must name its boarding and onboard tasks')
        marks = {t['id'] for t in scenes[scene_id]['tasks']} | {i for i in line_ids if i.startswith(scene_id + '.')}
        for layer in scene.get('layers', []):
            painting(scene_id, layer.get('file', ''))
            if layer.get('wide_file'):
                painting(scene_id, layer['wide_file'])
            for key in ('until', 'after'):
                if layer.get(key) and layer[key] not in marks:
                    merge.issue('error', scene_id, f"layer {key} {layer[key]} is not a lead or line of {scene_id}")
        for who, wait in scene.get('reveal_after', {}).items():
            for item in (wait if isinstance(wait, list) else [wait]):
                if item not in marks:
                    merge.issue('error', scene_id, f"reveal of {who} waits for {item}, which is not a lead or line of {scene_id}")
        for who, wait in scene.get('leave_after', {}).items():
            if wait not in marks:
                merge.issue('error', scene_id, f"departure of {who} waits for {wait}, which is not a lead or line of {scene_id}")


def write_walkthrough(content, path):
    """The answer to every lead, in play order, for players and reviewers who are stuck."""
    cast = content['cast']
    out = ['# Night Nine - campaign walkthrough', '',
           'Spoilers for the entire game. Generated by `python3 tools/script_v2.py --apply` from the '
           'applied script; do not edit by hand.', '']
    for scene in content['scenes']:
        out += [f"## {scene['title']}", '']
        for task in scene['tasks']:
            actor = f" (as {cast.get(task['actor'], task['actor'])})" if task.get('actor') else ''
            puzzle = task.get('puzzle') or {}
            if puzzle.get('presentation') == 'case_board':
                out.append(f"- {task['title']}{actor}")
                for stage in puzzle['stages']:
                    pairs = ' · '.join(f"{slot} → {stage['pieces'][index]}"
                                       for slot, index in zip(stage['slots'], stage['answer']))
                    out.append(f"  - {stage['prompt']} {pairs}")
            elif puzzle.get('rows'):
                out.append(f"- {task['title']}{actor}")
                out.append('  Settings: ' + '; '.join(
                    f"{row['label']}: {row['options'][int(answer)]}"
                    for row, answer in zip(puzzle['rows'], puzzle['solution'])))
            else:
                out.append(f"- {task['title']}: {task['options'][int(task['answer'])]}{actor}")
        out.append('')
    path.write_text('\n'.join(out) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', type=Path, default=BASE_DIR / 'campaign.json')
    parser.add_argument('--storybook', type=Path, default=BASE_DIR / 'storybook.json')
    parser.add_argument('--out', type=Path, default=OUT_DIR)
    parser.add_argument('--apply', action='store_true',
                        help='Write the validated revision and its dependent catalogs to game/content.')
    args = parser.parse_args()
    if not args.base.is_file() or not args.storybook.is_file():
        parser.error('pristine base files are missing; restore tools/script_v2/base/')
    base = json.loads(args.base.read_text())
    edits = load_edits()
    merge = Merge(base, edits)
    content = merge.run()
    validate(content, edits, merge)
    validate_staging(json.loads((BASE_DIR / 'illustrated-campaign.json').read_text()), content, merge)
    casting = json.loads((ROOT / 'docs/voice-casting-2026-11-20.json').read_text())
    books = storybook_lines(json.loads(args.storybook.read_text()), edits)
    stats = render(content, books, merge, casting, args.out)
    content['storybooks'] = books
    (args.out / 'script.json').write_text(json.dumps(content, ensure_ascii=False, indent=1) + '\n')
    report = ['# Script v2 validation report', '', '## Totals', '', json.dumps(stats, ensure_ascii=False), '']
    errors = [i for i in merge.issues if i[0] == 'error']
    warnings = [i for i in merge.issues if i[0] == 'warning']
    report += ['## Errors', ''] + [f'- `{w}`: {t}' for _, w, t in errors] + ['', '## Warnings', '']
    report += [f'- `{w}`: {t}' for _, w, t in warnings] + ['', '## Engine features this script needs', '']
    report += [f'- {feature}: ' + ', '.join(sorted(set(where))) for feature, where in merge.engine.items()]
    (args.out / 'report.md').write_text('\n'.join(report) + '\n')
    print(json.dumps(stats))
    print(f'{len(errors)} errors, {len(warnings)} warnings. See docs/script-v2/report.md')
    for _, w, t in errors[:40]:
        print('ERROR', w, t)
    if args.apply and not errors:
        apply_content(content, books, BASE_DIR, CONTENT_DIR)
        write_walkthrough(content, ROOT / 'docs/campaign-walkthrough.md')
        print('Applied campaign-3 to game/content.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())

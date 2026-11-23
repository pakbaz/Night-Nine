#!/usr/bin/env python3
import copy
import json
import unittest

import script_v2


class ScriptV2StagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = json.loads((script_v2.BASE_DIR / 'campaign.json').read_text())
        merge = script_v2.Merge(base, script_v2.load_edits())
        cls.content = merge.run()
        cls.staging = json.loads((script_v2.BASE_DIR / 'illustrated-campaign.json').read_text())

    def errors(self, change):
        staging = copy.deepcopy(self.staging)
        change(staging)
        merge = script_v2.Merge(json.loads((script_v2.BASE_DIR / 'campaign.json').read_text()), script_v2.load_edits())
        script_v2.validate_staging(staging, self.content, merge)
        return [text for level, _, text in merge.issues if level == 'error']

    def test_current_staging_is_valid(self):
        self.assertEqual(self.errors(lambda staging: None), [])

    def test_every_line_cue_is_a_sound_the_game_has(self):
        sounds = json.loads((script_v2.ROOT / 'game/assets/audio/soundscape-manifest.json').read_text())
        missing = []
        for line_id, line in self.content['lines'].items():
            cue = line.get('cue')
            if not cue:
                continue
            entry = sounds.get(cue, {})
            path = script_v2.ROOT / 'game' / str(entry.get('file', '')).removeprefix('res://')
            if not entry or not path.is_file():
                missing.append(f'{line_id}: {cue}')
        self.assertEqual(missing, [])

    def test_story_moments_have_their_sound(self):
        lines = self.content['lines']
        for line_id, cue in {'c4_escape.fault.01': 'drill_alarm', 'c4_escape.van.01': 'van_jump',
                             'c5_station.out.11': 'earpiece_click', 'c6_iris.out.04': 'pressed_flower',
                             'c6_jail.ctx.02': 'mail_cart'}.items():
            self.assertEqual(lines[line_id].get('cue'), cue, line_id)

    def test_every_move_within_a_chapter_has_a_painted_bridge(self):
        films = json.loads((script_v2.ROOT / 'game/content/films.json').read_text())
        scenes = self.content['scenes']
        bare = []
        for here, after in zip(scenes, scenes[1:]):
            staging = self.staging.get(here['id'], {})
            if here['chapter'] != after['chapter'] or here['id'] in films:
                continue
            if staging.get('bridge') or staging.get('chapter_insert') or staging.get('departure_painting') \
                    or here.get('departure_art') or here['id'] in ('p_bay', 'p_meeting', 'p_veyr', 'c10_live'):
                continue
            bare.append(f"{here['id']} -> {after['id']}")
        self.assertEqual(bare, [])

    def test_missing_painting_is_rejected(self):
        def change(staging):
            staging['c2_ship']['stills'][0]['file'] = 'res://assets/illustrated/campaign/stills/missing.webp'
        self.assertTrue(any('missing.webp' in error for error in self.errors(change)))

    def test_unknown_line_is_rejected(self):
        def change(staging):
            staging['c2_ship']['stills'][0]['lines'] = ['c2_ship.nowhere']
        self.assertTrue(any('c2_ship.nowhere' in error for error in self.errors(change)))

    def test_layer_needs_a_lead_of_its_scene(self):
        def change(staging):
            staging['c2_ship']['layers'][0]['until'] = 'c3_house.crossword'
        self.assertTrue(any('c3_house.crossword' in error for error in self.errors(change)))

    def test_missing_layer_is_rejected(self):
        def change(staging):
            staging['c2_ship']['layers'][1]['file'] = 'res://assets/illustrated/campaign/layers/missing.webp'
        self.assertTrue(any('missing.webp' in error for error in self.errors(change)))

    def test_layer_can_wait_for_a_line_of_its_scene(self):
        def change(staging):
            staging['c2_ship']['layers'][0]['until'] = 'c2_ship.in.01'
        self.assertEqual(self.errors(change), [])

    def test_reveal_needs_a_lead_or_line_of_its_scene(self):
        def change(staging):
            staging['c2_aquarium']['reveal_after']['iris'] = 'c3_house.crossword'
        self.assertTrue(any('c3_house.crossword' in error for error in self.errors(change)))

    def test_balcony_is_a_lockout_not_a_lock_in(self):
        scene = next(s for s in self.content['scenes'] if s['id'] == 'c1_escape')
        lines = {k: v for k, v in self.content['lines'].items() if k.startswith('c1_escape.')}
        text = ' '.join(line['text'].lower() for line in lines.values())
        for phrase in ('deadbolt', 'locked me in', 'apartment'):
            self.assertNotIn(phrase, text)
        self.assertFalse(any(line['speaker'] == 'iris' and 'go.' in line['text'].lower() for line in lines.values()),
                         'Nora locked Steve out; she does not tell him to go')
        self.assertFalse(any('apartment' in step.lower() for step in scene['objective_steps']))
        self.assertIn('balcony door', lines['c1_escape.in.02']['text'].lower())

    def test_nora_does_not_wear_the_raincoat_steve_hung_up(self):
        appearances = script_v2.load_edits()['global']['scene_appearances']
        self.assertNotEqual(appearances['c1_escape']['iris'], 'nora_rain')

    def test_aquarium_walk_paints_each_room_it_passes(self):
        stills = self.staging['c2_aquarium'].get('stills', [])

        def still_for(line_id):
            for still in stills:
                if any(line_id == item or line_id.startswith(item + '.') for item in still['lines']):
                    return still['file']
            return ''
        pump, doors, holding = still_for('c2_aquarium.plan.02'), still_for('c2_aquarium.guard.01'), \
            still_for('c2_aquarium.intercom.01')
        self.assertTrue(all((pump, doors, holding)), 'pump room, service doors and holding room are painted')
        self.assertEqual(len({pump, doors, holding}), 3)


if __name__ == '__main__':
    unittest.main()

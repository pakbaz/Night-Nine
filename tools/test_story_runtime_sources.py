#!/usr/bin/env python3
import json
from pathlib import Path
import unittest

import script_v2

CAST = Path(__file__).resolve().parents[1] / 'game/assets/illustrated/cast'


class StoryRuntimeSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = json.loads((script_v2.BASE_DIR / 'campaign.json').read_text())
        cls.content = script_v2.Merge(base, script_v2.load_edits()).run()
        cls.staging = json.loads((script_v2.BASE_DIR / 'illustrated-campaign.json').read_text())
        cls.storybooks = json.loads((script_v2.BASE_DIR / 'storybook.json').read_text())['books']

    def test_whistle_direction_is_a_runtime_cue_in_source(self):
        lines = self.content['lines']
        self.assertEqual(lines['c1_pier.whistle.02'].get('cue'), 'nora_whistle_flat')
        self.assertEqual(lines['c1_pier.whistle.03'].get('cue'), 'steve_whistle')

    def test_every_wrong_row_can_explain_its_own_evidence(self):
        for scene in self.content['scenes']:
            for task in scene['tasks']:
                if task['type'] != 'rows':
                    continue
                for row, answer in zip(task['puzzle']['rows'], task['puzzle']['solution']):
                    for index, option in enumerate(row['options']):
                        if index == answer:
                            continue
                        with self.subTest(task=task['id'], row=row['label'], choice=option):
                            feedback = row.get('feedback', '')
                            if isinstance(feedback, dict):
                                feedback = feedback.get(str(index), '')
                            elif isinstance(feedback, list):
                                feedback = feedback[index]
                            self.assertTrue(feedback.strip())

    def test_remote_wen_is_not_painted_into_c10_town(self):
        scene = next(scene for scene in self.content['scenes'] if scene['id'] == 'c10_town')
        line_ids = scene['context'] + scene['intro'] + scene['recap'] + scene['outro']
        for task in scene['tasks']:
            line_ids += task.get('lead', []) + task.get('lines', [])
        for topic in scene.get('talk', []):
            line_ids += topic.get('lines', [])
        wen = [self.content['lines'][line_id] for line_id in line_ids
               if self.content['lines'][line_id]['speaker'] == 'wen']
        self.assertTrue(wen)
        self.assertTrue(all(line.get('delivery') == 'radio' for line in wen))
        filtered = script_v2.filter_illustrated_campaign(
            self.staging, self.content, script_v2.load_edits()['global'].get('scene_appearances'))
        self.assertNotIn('wen', filtered['c10_town']['company'])

    def test_live_exit_waits_for_stephens_last_alibi_line(self):
        self.assertEqual(self.staging['c6_iris']['leave_after']['stephen'], 'c6_iris.alibi.02')

    def test_nora_stands_only_when_she_can_move(self):
        gallery = self.staging['c9_gallery']
        self.assertEqual(gallery['reveal_after']['nora'], 'c9_gallery.link.02')
        held = next(layer for layer in gallery['layers'] if 'nora-held' in layer['file'])
        self.assertEqual(held['until'], 'c9_gallery.link.02')

    def test_authored_appearances_are_standing_portraits_the_room_can_place(self):
        appearances = {name for scene in self.staging.values() if isinstance(scene, dict)
                       for name in scene.get('appearances', {}).values()}
        self.assertTrue(appearances)
        for name in sorted(appearances):
            with self.subTest(appearance=name):
                manifest = json.loads((CAST / name / 'sprite.json').read_text())
                self.assertTrue((CAST / name / manifest['base']).is_file())
                width, height = manifest['size']
                foot_x, foot_y = manifest['foot_anchor']
                self.assertTrue(0 < foot_x < width and 0 < foot_y <= height)
                self.assertEqual(len(manifest.get('eye_centers', [])), 2)

    def test_detail_shots_reference_current_live_lines(self):
        for scene_id, scene in self.staging.items():
            for line_id in scene.get('detail_shots', {}):
                self.assertIn(line_id, self.content['lines'], f'{scene_id}: {line_id}')
                self.assertEqual(self.content['lines'][line_id].get('delivery', 'live'), 'live', line_id)
        self.assertIn('c1_pier.in.01', self.staging['c1_pier']['detail_shots'])
        self.assertNotIn('c1_pier.whistle.01', self.staging['c1_pier']['detail_shots'])

    def test_aftermath_caption_times_are_unique_and_leave_room_for_narration(self):
        lines = [line for panel in self.storybooks['aftermath']['panels'] for line in panel['lines']]
        bars = [float(line['bar']) for line in lines]
        self.assertEqual(len(bars), len(set(bars)))
        seconds_per_bar = 3.2
        for current, following in zip(lines, lines[1:]):
            available = (float(following['bar']) - float(current['bar'])) * seconds_per_bar
            self.assertGreaterEqual(available, float(current.get('seconds', 0.0)) + .1,
                                    f"{current['text']} overlaps {following['text']}")


if __name__ == '__main__':
    unittest.main()

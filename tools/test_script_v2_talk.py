#!/usr/bin/env python3
import copy
import json
import unittest

import script_v2


class ScriptV2TalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((script_v2.BASE_DIR / 'campaign.json').read_text())
        cls.edits = script_v2.load_edits()

    def build(self, talk):
        edits = copy.deepcopy(self.edits)
        edits['scenes']['c1_flat']['talk'] = talk
        merge = script_v2.Merge(copy.deepcopy(self.base), edits)
        content = merge.run()
        script_v2.validate(content, edits, merge)
        scene = next(s for s in content['scenes'] if s['id'] == 'c1_flat')
        return content, scene, merge

    def errors(self, talk):
        _, _, merge = self.build(talk)
        return [text for level, where, text in merge.issues
                if level == 'error' and str(where).startswith('c1_flat')]

    def test_valid_talk_builds_topics_lines_and_portrait_company(self):
        content, scene, merge = self.build({
            'iris': [{
                'topic': 'The quiet morning',
                'after': 'saturday',
                'lines': [
                    'iris|The gulls woke before us.',
                    {'new': 'steve|They usually do.', 'direction': 'At the kitchen window'}
                ],
            }]
        })
        self.assertFalse([issue for issue in merge.issues if issue[0] == 'error' and str(issue[1]).startswith('c1_flat')])
        self.assertEqual(scene['talk'], [{
            'id': 'c1_flat.talk.iris.1',
            'speaker': 'iris',
            'topic': 'The quiet morning',
            'after': 'c1_flat.saturday',
            'lines': ['c1_flat.talk.iris.1.01', 'c1_flat.talk.iris.1.02'],
        }])
        first = content['lines']['c1_flat.talk.iris.1.01']
        self.assertEqual(first['display'], 'Nora Reyes')
        self.assertEqual(first['scene'], 'c1_flat')
        self.assertEqual(first.get('delivery', 'live'), 'live')
        second = content['lines']['c1_flat.talk.iris.1.02']
        self.assertEqual(second['direction'], 'At the kitchen window')
        illustrated = script_v2.filter_illustrated_campaign(
            json.loads((script_v2.BASE_DIR / 'illustrated-campaign.json').read_text()), content)
        self.assertIn('iris', illustrated['c1_flat']['company'])

    def test_bad_after_is_rejected(self):
        errors = self.errors({'iris': [{
            'topic': 'The quiet morning', 'after': 'missing',
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('after names unknown task' in error for error in errors))

    def test_after_must_name_a_lead_that_is_never_solved_last(self):
        # The scene departs on its own after the last lead, so such a topic could never be heard.
        errors = self.errors({'iris': [{
            'topic': 'After the last lead', 'after': 'control',
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('could be the last lead' in error for error in errors))
        self.assertFalse(self.errors({'iris': [{
            'topic': 'After an earlier lead', 'after': 'compare',
            'lines': ['iris|One.', 'steve|Two.'],
        }]}))

    def test_until_ends_a_topic_once_its_lead_is_done(self):
        _, scene, _ = self.build({'iris': [{
            'topic': 'Before the call', 'until': 'saturday',
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertEqual(scene['talk'][0]['until'], 'c1_flat.saturday')
        errors = self.errors({'iris': [{
            'topic': 'Before the call', 'until': 'missing',
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('until names unknown task' in error for error in errors))

    def test_long_topic_is_rejected(self):
        errors = self.errors({'iris': [{
            'topic': 'x' * 49,
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('topic is longer than 48 characters' in error for error in errors))

    def test_empty_topic_is_rejected(self):
        errors = self.errors({'iris': [{
            'topic': '   ',
            'lines': ['iris|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('talk topic is empty' in error for error in errors))

    def test_one_line_topic_is_rejected(self):
        errors = self.errors({'iris': [{
            'topic': 'The quiet morning',
            'lines': ['iris|One.'],
        }]})
        self.assertTrue(any('needs at least two lines' in error for error in errors))

    def test_unknown_speaker_is_rejected(self):
        errors = self.errors({'stranger': [{
            'topic': 'The quiet morning',
            'lines': ['steve|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('unknown talk speaker stranger' in error for error in errors))

    def test_speaker_must_be_present(self):
        errors = self.errors({'agnes': [{
            'topic': 'The quiet morning',
            'lines': ['agnes|One.', 'steve|Two.'],
        }]})
        self.assertTrue(any('talk speaker agnes is not present' in error for error in errors))


if __name__ == '__main__':
    unittest.main()

import json
import unittest

import script_v2 as script


class EndgameInvestigations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = script.Merge(json.loads((script.BASE_DIR / 'campaign.json').read_text()),
                               script.load_edits()).run()
        cls.tasks = {t['id']: t for s in content['scenes'] for t in s['tasks']}

    def test_waking_the_family_uses_the_players_tapes(self):
        for person, anchor in [('frank', 'effect.k7blw'), ('helen', 'effect.lullaby')]:
            task = self.tasks['c9_wake.' + person]
            self.assertTrue(task.get('sound_bank'))
            self.assertNotIn('puzzle', task)
            self.assertEqual(task['sounds'][task['answer']], anchor)
            self.assertEqual(len(set(task['sounds'])), len(task['options']))
            self.assertEqual(len(task['clip_captions']), len(task['sounds']))
        self.assertIn('c9_wake.frank', self.tasks['c9_wake.helen']['requires'])

    def test_broadcast_cues_use_timed_return_lamps_and_the_same_answer_as_the_save_model(self):
        for cue in ('first', 'second', 'third'):
            p = self.tasks['c10_live.' + cue]['puzzle']
            self.assertEqual(p['presentation'], 'broadcast_desk')
            self.assertGreaterEqual(len(p['cues']), 2)
            self.assertEqual(len(p['rows']), len(p['solution']))
            self.assertEqual([r['options'][i] for r, i in zip(p['rows'], p['solution'])],
                             [c['send'] for c in p['cues']])
            self.assertTrue(any(c.get('wait', 0) or c.get('monitor') for c in p['cues'][1:]))

    def test_postcredits_signal_is_audible_and_captioned_without_giving_away_the_shape(self):
        task = self.tasks['postcredits.answer']
        self.assertIn('effect.wick', task['sounds'])
        self.assertEqual(len(task['sounds']), len(task['evidence_labels']))
        self.assertEqual(len(task['sounds']), len(task['clip_captions']))
        self.assertNotRegex(task['prompt'], 'joined|climb|long low')


if __name__ == '__main__':
    unittest.main()

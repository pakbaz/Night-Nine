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


if __name__ == '__main__':
    unittest.main()

import copy
import json
import unittest
from pathlib import Path

from ending_reward import apply_music

ROOT = Path(__file__).resolve().parents[1]


class EndingRewardTests(unittest.TestCase):
    def test_reward_is_reserved_and_keeps_the_original_recording(self):
        music = json.loads((ROOT / 'tools/script_v2/base/music.json').read_text())
        original = copy.deepcopy(music['chapters']['Epilogue']['bgm'])
        apply_music(music)
        self.assertEqual(music['credits']['file'], original['file'])
        self.assertFalse(music['credits']['loop'])
        self.assertGreater(music['credits']['entry_seconds'], 40)
        self.assertLess(music['credits']['entry_seconds'] + 56.4, 174.955)
        for section in ('scene_music', 'departures'):
            self.assertTrue(all(cue['file'] != original['file'] for cue in music[section].values()))
        self.assertNotEqual(music['chapters']['Epilogue']['bgm']['file'], original['file'])
        self.assertEqual(music['finale']['file'], 'res://assets/audio/music/epilogue-theme.mp3')

    def test_repeated_generation_keeps_the_same_reward(self):
        music = json.loads((ROOT / 'tools/script_v2/base/music.json').read_text())
        apply_music(music)
        once = copy.deepcopy(music)
        apply_music(music)
        self.assertEqual(music, once)


if __name__ == '__main__':
    unittest.main()

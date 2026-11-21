"""Reserve Mysterious Take 2 for credits and retain the original Epilogue BGM."""
import copy


def apply_music(music):
    chapters = music['chapters']
    extras = music.setdefault('extras', {})
    if 'ending_reward' not in extras:
        extras['ending_reward'] = copy.deepcopy(chapters['Epilogue']['bgm'])
    music['credits'] = {
        'file': 'res://assets/audio/music/credits-mysterious.mp3',
        'lufs': -16.87,
        'entry_seconds': 0.0,
        'loop': False,
    }
    chapters['Epilogue']['bgm'] = copy.deepcopy(extras['ending_reward'])
    for scene, chapter in (('epilogue', 'Epilogue'), ('one_year', 'Chapter 1')):
        replacement = copy.deepcopy(chapters[chapter]['bgm'])
        replacement.update(entry_seconds=0.0, role='bgm')
        music['scene_music'][scene] = replacement

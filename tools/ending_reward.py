"""Keep the supplied Epilogue BGM exclusive to the completion credit film."""
import copy


def apply_music(music):
    chapters = music['chapters']
    extras = music.setdefault('extras', {})
    if 'ending_reward' not in extras:
        extras['ending_reward'] = copy.deepcopy(chapters['Epilogue']['bgm'])
    reward = copy.deepcopy(extras['ending_reward'])
    # Enter on the full arrangement, leaving ample music for the 56-second film.
    reward.update(entry_seconds=round(reward['beat'] + 15 * 240 / reward['bpm'], 3),
                  loop=False)
    music['credits'] = reward
    for scene, chapter in (('epilogue', 'Chapter 10'), ('one_year', 'Chapter 1')):
        replacement = copy.deepcopy(chapters[chapter]['bgm'])
        replacement.update(entry_seconds=0.0, role='bgm')
        music['scene_music'][scene] = replacement
    # Also keep the generic chapter fallback from revealing the reward early.
    music['chapters']['Epilogue']['bgm'] = copy.deepcopy(chapters['Chapter 10']['bgm'])

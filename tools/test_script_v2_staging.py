#!/usr/bin/env python3
import copy
import json
import re
import unittest

import script_v2


def still_for(stills, line_id):
    """The painting the game shows for a line: exact id or group prefix, first match wins."""
    for still in stills:
        if any(line_id == item or line_id.startswith(item + '.') for item in still['lines']):
            return still['file']
    return ''


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
                             'c5_station.out.11': 'earpiece_click', 'c6_iris.out.04': 'pressed_flower'}.items():
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

    def test_departure_needs_a_lead_or_line_of_its_scene(self):
        def change(staging):
            staging['c6_iris']['leave_after']['stephen'] = 'c3_house.crossword'
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
        pump, doors, holding = still_for(stills, 'c2_aquarium.plan.02'), still_for(stills, 'c2_aquarium.guard.01'), \
            still_for(stills, 'c2_aquarium.intercom.01')
        self.assertTrue(all((pump, doors, holding)), 'pump room, service doors and holding room are painted')
        self.assertEqual(len({pump, doors, holding}), 3)

    def test_interlude_wake_is_supported_reversible_and_shown_in_order(self):
        scene = next(s for s in self.content['scenes'] if s['id'] == 'i2_nora')
        self.assertEqual(scene['intro'][:3], ['i2_nora.in.01', 'i2_nora.in.02', 'i2_nora.in.03'])
        self.assertEqual(scene['intro'][-2:], ['i2_nora.in.04', 'i2_nora.in.05'])
        support = self.content['lines']['i2_nora.in.04']['text'].lower()
        complete = self.content['lines']['i2_nora.in.05']['text'].lower()
        self.assertIn('beds did the work', support)
        self.assertIn('breathe alone', support)
        self.assertIn('mirror link active', complete)
        staging = self.staging['i2_nora']
        open_layer = next(layer for layer in staging['layers'] if 'pods-open' in layer['file'])
        self.assertEqual(open_layer.get('after'), 'i2_nora.in.05')

    def ship(self):
        scene = next(s for s in self.content['scenes'] if s['id'] == 'c2_ship')
        return scene, {t['id']: t for t in scene['tasks']}, self.content['lines']

    def test_ship_escorts_are_sent_back_before_the_escape(self):
        scene, tasks, lines = self.ship()
        dismissal = lines[tasks['c2_ship.command']['lead'][-1]]
        self.assertEqual(dismissal['speaker'], 'guard')
        self.assertIn('escorts', dismissal['text'].lower())
        talk = [topic for topic in scene['talk'] if topic['speaker'] in ('iris', 'lyle_copy')]
        self.assertTrue(talk)
        self.assertTrue(all(topic.get('until') == 'c2_ship.command' for topic in talk),
                        'nobody can chat with an escort who has gone back to town')
        self.assertEqual(self.staging['c2_ship'].get('leave_after'),
                         {'iris': 'c2_ship.command', 'lyle_copy': 'c2_ship.command'})

    def test_ship_release_is_noticed_and_steve_is_chased(self):
        _, tasks, lines = self.ship()
        escape = tasks['c2_ship.escape']['lines']
        self.assertTrue(any(lines[i]['speaker'] == 'guard' for i in escape[escape.index('c2_ship.escape.01') + 1:]),
                        'the attendant is caught off guard by the release')
        intake = tasks['c2_ship.intake']
        denial = lines[intake['lead'][0]]
        self.assertEqual((denial['speaker'], denial.get('delivery')), ('saren', 'intercom'))
        before_flood = intake['lead'][:intake['lead'].index('c2_ship.out.01')]
        self.assertTrue(any(lines[i]['speaker'] == 'guard' and 'empty' in lines[i]['text'].lower() for i in before_flood))
        self.assertTrue(any(lines[i]['speaker'] == 'steve' and 'valve' in lines[i]['text'].lower() for i in before_flood),
                        'Steve opens the seawater valve himself before the tunnel floods')
        self.assertTrue(any(lines[i]['speaker'] == 'guard' for i in intake['lines'][1:]),
                        'the attendant chasing Steve meets Admiral')

    def test_ship_escape_is_painted_beat_by_beat(self):
        ship = self.staging['c2_ship']
        stills = ship['stills']
        expected = {'c2_ship.command.02': 'escorts-leave', 'c2_ship.escape.03': 'chair-release',
                    'c2_ship.escape.04': 'attendant-intercom', 'c2_ship.intake.lead.01': 'attendant-turns',
                    'c2_ship.intake.lead.02': 'attendant-turns', 'c2_ship.intake.lead.03': 'valve-alarm',
                    'c2_ship.intake.lead.04': 'valve-alarm', 'c2_ship.out.01': 'flooded-tunnel',
                    'c2_ship.intake.lead.07': 'flooded-tunnel', 'c2_ship.intake.01': 'flooded-tunnel',
                    'c2_ship.intake.02': 'admiral-burst', 'c2_ship.intake.find': 'admiral-rescue'}
        for line_id, name in expected.items():
            self.assertIn(f'c2_ship-{name}.webp', still_for(stills, line_id), line_id)
        _, tasks, _ = self.ship()
        self.assertTrue(tasks['c2_ship.intake'].get('art', '').endswith('c2_ship-flooded-tunnel.webp'))
        layers = {layer['file'].rsplit('/', 1)[-1]: layer for layer in ship['layers']}
        chair = layers['c2_ship-attendant-chair.webp']
        column = layers['c2_ship-attendant-column.webp']
        hatch = layers['c2_ship-hatch-flooding.webp']
        self.assertEqual(chair.get('until'), 'c2_ship.escape')
        self.assertEqual((column.get('after'), column.get('until')), ('c2_ship.escape', 'c2_ship.intake.lead.03'))
        self.assertEqual(hatch.get('after'), 'c2_ship.intake.lead.03')
        self.assertEqual((hatch.get('painted'), hatch.get('walking')), (['steve'], False),
                         'Steve is down the hatch and cannot walk the room')

    def scene(self, sid):
        scene = next(s for s in self.content['scenes'] if s['id'] == sid)
        return scene, {t['id']: t for t in scene['tasks']}, self.content['lines']

    def assert_stills(self, sid, expected):
        stills = self.staging[sid].get('stills', [])
        for line_id, name in expected.items():
            self.assertIn(f'{sid}-{name}.webp', still_for(stills, line_id), line_id)

    def test_choir_lets_steve_go_before_he_walks_and_says_who_followed(self):
        scene, _, lines = self.scene('c9_choir')
        self.assertEqual(scene['intro'], ['c9_choir.in.04', 'c9_choir.in.01', 'c9_choir.in.05', 'c9_choir.in.02',
                                          'c9_choir.in.06', 'c9_choir.in.07', 'c9_choir.in.03'])
        release, arrival = lines['c9_choir.in.06'], lines['c9_choir.in.07']
        self.assertEqual(release['speaker'], 'steve')
        self.assertIn('straps', release['text'].lower(), 'Steve is strapped in the chair until the Choir stops the scan')
        self.assertEqual(arrival['speaker'], 'calder')
        self.assertIn('row nine', arrival['text'].lower(), 'June says how she, Helen, Frank and Nora got down here')
        self.assert_stills('c9_choir', {'c9_choir.in.04': 'rig-broken', 'c9_choir.in.01': 'scan',
                                        'c9_choir.in.05': 'scan', 'c9_choir.in.02': 'stop',
                                        'c9_choir.in.06': 'stop', 'c9_choir.in.07': 'stop'})
        self.assertNotIn('c9_choir.in.02', self.staging['c9_choir'].get('inserts', {}))

    def test_gate_keeps_the_wanted_man_out_of_sight_until_the_truck_is_through(self):
        scene, tasks, lines = self.scene('c7_gate')
        self.assertEqual(scene['actors'], ['stephen', 'pell', 'steve'], 'the chapter opens with someone who may be seen')
        self.assertIn('out of sight', scene['coach'])
        self.assertNotIn('sound desk', scene['coach'], 'the coach must not give away the checkpoint answer')
        self.assertEqual(self.staging['c7_gate'].get('reveal_after', {}).get('steve'), 'c7_gate.badge')
        arrival = lines[tasks['c7_gate.truck']['lead'][0]]['text'].lower()
        self.assertNotIn('television camera', arrival, 'a fugitive never falls into a live shot')
        self.assertIn('inside the fence', arrival)
        self.assert_stills('c7_gate', {line_id: 'under-desk' for line_id in (
            'c7_gate.badge.02', 'c7_gate.badge.03', 'c7_gate.badge.04', 'c7_gate.badge.05', 'c7_gate.badge.01',
            'c7_gate.badge.find')})
        self.assertNotIn('under-desk', still_for(self.staging['c7_gate']['stills'], 'c7_gate.badge.lead.01'),
                         'the hiding place is the answer to the checkpoint puzzle, so it is not shown before')
        talk = {topic['id']: topic for topic in scene['talk']}
        self.assert_stills('c7_gate', {
            'c7_gate.truck.lead.01': 'shaw-truck', 'c7_gate.truck.01': 'shaw-truck',
            'c7_gate.truck.02': 'shaw-truck', 'c7_gate.truck.find': 'shaw-truck',
            'c7_gate.out.06': 'agnes-fog',
        })
        self.assertEqual(self.staging['c7_gate'].get('bridge'),
                         'res://assets/illustrated/campaign/bridges/c7_gate-c7_swap.webp',
                         'Chapter 7 walks from the truck to the sound tent with a dedicated bridge painting')
        self.assert_stills('c7_swap', {
            'c7_swap.map.lead.04': 'monitors', 'c7_swap.map.lead.05': 'monitors',
            'c7_swap.map.lead.06': 'monitors', 'c7_swap.map.01': 'monitors',
        })
        for topic_id in ('c7_gate.talk.rook_copy.1', 'c7_gate.talk.rook_copy.2'):
            self.assertEqual(talk[topic_id].get('until'), 'c7_gate.badge',
                             'Stephen chats with Rook at the outer gate before driving past him')
        for topic_id in ('c7_gate.talk.pell.1', 'c7_gate.talk.pell.2', 'c7_gate.talk.stephen.1'):
            self.assertEqual(talk[topic_id].get('after'), 'c7_gate.badge', 'Steve chats in the fog once he is out')
        for topic_id in ('c7_gate.talk.shaw.1', 'c7_gate.talk.shaw.2'):
            self.assertEqual(talk[topic_id].get('after'), 'c7_gate.truck.02', 'Steve chats with Shaw once they have met')
        self.assertIn('were right under', lines['c7_gate.talk.stephen.3.02']['text'], 'Steve is out from under the desk')

    def test_gallery_aisle_is_guarded_until_nora_has_timed_the_patrol(self):
        floor = json.loads((script_v2.BASE_DIR / 'illustrated-floor.json').read_text())['i2_nora']
        aisle = next(blocker for blocker in floor['blockers'] if blocker['id'] == 'guarded_aisle')
        self.assertEqual(aisle.get('opens_after'), 'i2_nora.patrol')
        xs = [x for x, _ in aisle['polygon']]
        ys = [y for _, y in aisle['polygon']]
        left = [floor['approach'][key][0] for key in ('patrol', 'jobs')] + [floor['spawn']['nora'][0]]
        right = [floor['approach'][key][0] for key in ('pump', 'message')]
        self.assertTrue(max(left) < min(xs) and max(xs) < min(right), 'the guarded aisle lies between the pods and the pump')
        self.assertTrue(min(ys) <= 0.56 and max(ys) >= 0.98, 'the aisle runs the full depth of the floor')
        guard = next(layer for layer in self.staging['i2_nora']['layers'] if 'guard' in layer['file'])
        self.assertEqual(guard.get('until'), 'i2_nora.patrol', 'the guard keeps his lap until Nora has timed it')
        self.assert_stills('i2_nora', {'i2_nora.patrol.lead.01': 'guard-passes', 'i2_nora.patrol.lead.02': 'guard-passes',
                                       'i2_nora.patrol.01': 'crossing', 'i2_nora.patrol.find': 'crossing',
                                       'i2_nora.pump.01': 'hatch-open', 'i2_nora.pump.find': 'hatch-open',
                                       'i2_nora.out.01': 'rows', 'i2_nora.out.02': 'rows',
                                       'i2_nora.out.03': 'row-zero', 'i2_nora.out.04': 'row-zero'})
        scene = next(s for s in self.content['scenes'] if s['id'] == 'i2_nora')
        self.assertEqual([t['id'] for t in scene['tasks']],
                         ['i2_nora.jobs', 'i2_nora.patrol', 'i2_nora.pump', 'i2_nora.message'],
                         'Nora organizes the pods first, lures the guard into the locked wash shaft, then crosses to the pump and intercom')
        self.assert_stills('c6_iris', {'c6_iris.alibi.01': 'bakery-alibi', 'c6_iris.alibi.02': 'bakery-alibi',
                                       'c6_iris.out.09': 'laundry-wake', 'c6_iris.out.10': 'laundry-wake',
                                       'c6_iris.out.12': 'market-clear', 'c6_iris.out.13': 'market-clear'})

    def test_jail_break_and_bakery_goodbye_are_shown_where_they_happen(self):
        self.assert_stills('c6_jail', {'c6_jail.crossword.06': 'back-door', 'c6_jail.out.02': 'bakery',
                                       'c6_jail.out.04': 'bakery', 'c6_jail.out.01': 'bakery',
                                       'c6_jail.out.05': 'bakery', 'c6_jail.out.03': 'bakery',
                                       'c6_jail.out.06': 'posters'})

    def lines_of(self, *scene_ids):
        return {k: v for k, v in self.content['lines'].items() if k.split('.')[0] in scene_ids}

    def test_ship_recap_remembers_the_lockout_and_names_the_painted_hatch(self):
        lines = self.content['lines']
        self.assertIn('locked me out', lines['c2_ship.recap.03']['text'].lower())
        self.assertIn('hatch', lines['c2_ship.intake.lead.03']['text'].lower(),
                      'Steve names the floor hatch the painting shows flooding')

    def test_june_first_hears_both_takes_by_pneumatic_post(self):
        tube = self.content['lines']['c4_escape.tube.01']['text'].lower()
        self.assertIn('heard both', tube)
        for line_id, line in self.lines_of('c4_safe').items():
            if line['speaker'] == 'calder':
                self.assertNotIn('again', line['text'].lower(), f'{line_id}: June has not heard the takes yet')

    def test_rook_holds_moms_tape_long_enough_for_saren_to_copy_it(self):
        lines = self.content['lines']
        taken = lines['c4_safe.in.07']['text'].lower()
        self.assertIn('even mom’s voicemail', taken)
        self.assertIn('handed that one back', taken)
        task = next(task for scene in self.content['scenes'] for task in scene['tasks']
                    if task['id'] == 'c8_beach.second')
        spoken = ' '.join(lines[line_id]['text'].lower() for line_id in task['lines'] + [task['finding']])
        self.assertIn('rook kept this tape for an hour', spoken)
        self.assertNotIn('never took', task['background'].lower())

    def test_no_wanted_posters_before_sunrise_and_steve_hears_june_will_be_scanned(self):
        for line_id, line in self.lines_of('c4_safe', 'c4_escape').items():
            self.assertNotIn('poster', line['text'].lower(), f'{line_id}: the posters go up at sunrise, in chapter 5')
        self.assertIn('june', self.content['lines']['c4_escape.out.02']['text'].lower())

    def test_rook_case_is_the_same_age_every_time_june_mentions_it(self):
        ages = {re.search(r'(\w+) years ago', line['text'].lower()).group(1)
                for line in self.content['lines'].values()
                if line['speaker'] == 'calder' and 'years ago' in line['text'].lower()
                and ('case' in line['text'].lower() or 'owes me' in line['text'].lower())}
        self.assertEqual(ages, {'twenty'})

    def test_shaw_knows_nothing_about_copies_until_the_president_tells_her(self):
        for line_id, line in self.lines_of('c7_gate', 'c7_swap').items():
            if line['speaker'] == 'shaw' and not line_id.startswith('c7_swap.out.'):
                text = line['text'].lower()
                for word in ('copy', 'copies', 'saren', 'prefect', 'ship'):
                    self.assertNotRegex(text, rf'\b{word}\b', f'{line_id}: Shaw is told in the locked room')
        self.assertIn('stephen', self.content['lines']['c7_swap.recap.02']['text'].lower(),
                      'Stephen is a copy at the desk when the tone plays')

    def test_crew_pass_survives_because_saren_will_not_record_a_mistake(self):
        self.assertIn('on the record', self.content['lines']['c8_rig.path.lead.04']['text'].lower())

    def test_frank_claims_nothing_he_did_while_asleep_in_a_pod(self):
        for line_id, line in self.lines_of('c10_station', 'c10_town', 'c10_live').items():
            if line['speaker'] == 'frank':
                self.assertNotRegex(line['text'].lower(), r'yesterday i\b', line_id)

    def test_epilogue_comes_after_the_ship_has_gone(self):
        self.assertIn('at sunrise', self.content['lines']['c10_report.out.06']['text'].lower())
        for line_id, line in self.lines_of('epilogue', 'one_year', 'postcredits').items():
            self.assertNotIn('with the ship', line['text'].lower(), f'{line_id}: the ship left at sunrise')


if __name__ == '__main__':
    unittest.main()

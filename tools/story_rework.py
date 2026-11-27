"""Story arc rework, November 18, 2026.

The game now opens on Steve's backstory and one easy, hands-on scene with his
parents. The two other "nights" move to the places where the story explains
them: Veyr closes the Archivist's interlude, and the Sentinel Point meeting
opens Chapter 8 as Helen's notebook is finally read.

Everything here is text, order and presentation data. Spoken lines keep their
IDs and recordings. Storybook narration is on-screen text until it is recorded.
"""

# Scenes that move, and the scene they now follow or precede.
MOVES = [
    ('p_veyr', 'after', 'i1_archive', 'Interlude 1'),
    ('p_meeting', 'before', 'c8_lab', 'Chapter 8'),
]

# The chapter card shown when a chapter begins. "goal" comes from the
# "Steve wants" line of each chapter in the final plot.
CHAPTERS = {
    'Prologue': {'kicker': 'Prologue', 'title': 'The Bay Is Singing',
                 'goal': 'Frank and Helen Mercer row out to listen to the bay.'},
    'Chapter 1': {'kicker': 'Chapter 1', 'title': 'Good Morning, Sleepyhead',
                  'when': 'Saturday, three in the morning',
                  'goal': 'Steve wants to find out what is wrong with Nora.'},
    'Chapter 2': {'kicker': 'Chapter 2', 'title': 'The Aquarium Is Closed',
                  'when': 'The same night',
                  'goal': 'Steve wants to find the real Nora.'},
    'Chapter 3': {'kicker': 'Chapter 3', 'title': 'Please Prove You Exist',
                  'when': 'The next morning',
                  'goal': 'Steve wants one person to believe him.'},
    'Interlude 1': {'kicker': 'Interlude', 'title': 'The Archivist',
                    'when': 'The same ninth night, under the bay',
                    'goal': 'The keeper of the ship’s records goes about her work. She has a secret.'},
    'Chapter 4': {'kicker': 'Chapter 4', 'title': 'Federal Hospitality',
                  'goal': 'Steve wants to hand the problem to someone in charge.'},
    'Chapter 5': {'kicker': 'Chapter 5', 'title': 'Wanted: Steve Mercer (Two of Him)',
                  'when': 'Six days before the signing',
                  'goal': 'Steve wants to hide, and to find his mother’s notebook before the crew does.'},
    'Chapter 6': {'kicker': 'Chapter 6', 'title': 'Iris',
                  'goal': 'Steve wants to free Calder and learn what the Veyri want.'},
    'Interlude 2': {'kicker': 'Interlude', 'title': 'Nora',
                    'when': 'Inside the Long Patience',
                    'goal': 'Nora wakes up on the ship. Nobody is coming to fix this.'},
    'Chapter 7': {'kicker': 'Chapter 7', 'title': 'The President’s Other Appointment',
                  'when': 'The day of the signing',
                  'goal': 'Steve wants to stop the swap of the President.'},
    'Chapter 8': {'kicker': 'Chapter 8', 'title': 'The Biggest Lie on Earth',
                  'goal': 'Steve wants a way to stop an invasion with no weapon.'},
    'Chapter 9': {'kicker': 'Chapter 9', 'title': 'The Long Patience',
                  'goal': 'Steve wants to wake the sleepers and get the signal into the ship.'},
    'Chapter 10': {'kicker': 'Chapter 10', 'title': 'Good Morning, Bellwether',
                   'when': 'Before sunrise',
                   'goal': 'Steve wants to turn the fleet away.'},
    'Epilogue': {'kicker': 'Epilogue', 'title': 'A Place to Live',
                 'goal': 'The ship is gone. Bellwether wakes up to a different town.'},
    'After the credits': {'kicker': 'After the credits', 'title': 'We Heard the Singing',
                          'goal': ''},
}

# Extra pages for scenes that jump in time. They follow the chapter card when
# the scene also begins a chapter.
CARDS = {
    'p_veyr': {'kicker': 'The Archivist remembers', 'title': 'Veyr, nine hundred years ago',
               'goal': 'Her homeworld’s sun is failing. Forty thousand sleepers are about to leave, and someone has to record what home sounded like.'},
    'p_meeting': {'kicker': 'From Helen’s notebook', 'title': 'Sentinel Point, nine years ago',
                  'goal': 'Dr. Lin Wen reads Helen’s shorthand aloud. She was in that room, and so was Helen.'},
    'one_year': {'kicker': 'One year later', 'title': 'Good Morning', 'goal': 'KBWR, before the morning show.'},
}

# A short line in the status bar on arrival, for the first scenes that teach a tool.
COACH = {
    'p_bay': 'Click the glowing radio to begin. Press I for a list of things to look at.',
    'c1_flat': 'Steve’s tools are Dad’s recorder and his notebook. Click the recorder to begin. Press J to read the notebook.',
    'c1_pier': 'Some leads open a case board. Drag the cards into place, or ask for a hint.',
    'p_veyr': 'This is the Archivist’s memory. Click the recorder on the terrace to begin.',
    'p_meeting': 'You are Helen. Choose each translation carefully.',
}

# Each storybook plays before the scene it names, over one piece of the score.
# Times are bars of that recording, measured in tools/build-music-sync.py.
IMAGES = 'res://assets/illustrated/'
STORYBOOKS = {
    'opening': {
        'title': 'Before the ninth night',
        'before': 'p_bay',
        'music': {'file': 'res://assets/audio/music/prologue-theme.mp3', 'bar': 0},
        'end_bar': 20,
        'panels': [
            {'bar': 0, 'image': IMAGES + 'campaign/rooms/c1_pier.webp', 'from': [0.42, 0.56, 1.0], 'to': [0.56, 0.48, 1.12], 'lines': [
                {'bar': 0.6, 'text': 'Bellwether. A fishing town on the Pacific coast.'},
                {'bar': 2, 'text': 'Six thousand people, one radio station, and a lot of fog.'}]},
            {'bar': 4, 'image': IMAGES + 'campaign/rooms/c10_station.webp', 'from': [0.5, 0.55, 1.14], 'to': [0.6, 0.45, 1.02], 'lines': [
                {'bar': 4.4, 'text': 'I’m Steve Mercer. For years I ran the night shift at KBWR, the town radio station.'},
                {'bar': 6, 'text': 'Nobody hears the night engineer. The night engineer hears everything.'}]},
            {'bar': 8, 'image': IMAGES + 'campaign/stills/book-frank-radio.webp', 'from': [0.35, 0.6, 1.1], 'to': [0.45, 0.55, 1.0], 'lines': [
                {'bar': 8.4, 'text': 'My dad, Frank, taught me how to listen.'},
                {'bar': 9.4, 'text': 'Ham radio, every night. Strangers from all over the world, all of them his friends.'}]},
            {'bar': 11, 'image': IMAGES + 'rooms/meeting.png', 'from': [0.5, 0.45, 1.0], 'to': [0.5, 0.5, 1.12], 'lines': [
                {'bar': 11.4, 'text': 'My mom, Helen, was an interpreter. Government work, rooms with no windows. She never talked about it.'},
                {'bar': 12.8, 'text': 'She could hear what people meant, even when they said something else.'}]},
            {'bar': 14, 'image': IMAGES + 'rooms/bay.png', 'from': [0.5, 0.42, 1.0], 'to': [0.5, 0.5, 1.16], 'lines': [
                {'bar': 14.4, 'text': 'Eighteen months ago, they rowed out into the bay after dark. They said the water was making a sound.'},
                {'bar': 16.4, 'text': 'They asked me to come along.'},
                {'bar': 17.6, 'text': 'I said no. I had a shift.'}]},
        ],
    },
    'aftermath': {
        'title': 'Eighteen months',
        'before': 'c1_flat',
        'music': {'file': 'res://assets/audio/music/prologue-theme.mp3', 'bar': 37, 'continue': True},
        'end_bar': 52,
        'panels': [
            {'bar': 37, 'image': IMAGES + 'campaign/stills/book-aftermath-boat.webp', 'from': [0.56, 0.52, 1.0], 'to': [0.6, 0.5, 1.12], 'lines': [
                {'bar': 37.3, 'text': 'In the morning, their boat drifted back to shore. Empty.'},
                {'bar': 38.7, 'text': 'Dad’s radio was still on.'}]},
            {'bar': 40, 'image': IMAGES + 'campaign/rooms/c1_escape.webp', 'from': [0.55, 0.5, 1.0], 'to': [0.45, 0.5, 1.1], 'lines': [
                {'bar': 40.3, 'text': 'Nobody found them. That was eighteen months ago.'},
                {'bar': 41.6, 'text': 'Most nights I still play Mom’s last voicemail. I don’t know what I’m listening for.'}]},
            {'bar': 43, 'image': IMAGES + 'campaign/wide/c5_station.webp', 'from': [0.5, 0.5, 1.12], 'to': [0.5, 0.45, 1.0], 'lines': [
                {'bar': 43.3, 'text': 'Three weeks ago, a company called Halcyon Media bought KBWR.'},
                {'bar': 44.6, 'text': 'They replaced me with a machine called DJ AutoRick. He reads yesterday’s weather.'}]},
            {'bar': 46, 'image': IMAGES + 'campaign/stills/book-aftermath-nora.webp', 'from': [0.6, 0.42, 1.12], 'to': [0.56, 0.46, 1.0], 'lines': [
                {'bar': 46.3, 'text': 'And then there’s Nora. Nora Reyes runs the aquarium and argues with everybody, me included.'},
                {'bar': 47.7, 'text': 'Now that I’m home in the mornings, I get to hear her say good morning.'}]},
            {'bar': 49, 'image': IMAGES + 'title.webp', 'from': [0.74, 0.4, 1.62], 'to': [0.5, 0.5, 1.0], 'lines': [
                {'bar': 49.3, 'text': 'This is the story of how I started counting nights.'}]},
        ],
    },
    'after': {
        'title': 'After the ninth night',
        'before': 'one_year',
        # The same Three Nights bars that carried "Eighteen months", now over the same places, changed.
        'music': {'file': 'res://assets/audio/music/prologue-theme.mp3', 'bar': 31, 'continue': True},
        'end_bar': 52,
        'panels': [
            {'bar': 31, 'image': IMAGES + 'campaign/rooms/epilogue.webp', 'from': [0.45, 0.5, 1.0], 'to': [0.55, 0.5, 1.12], 'lines': [
                {'bar': 31.3, 'text': 'Before the ship left, the Choir gave the copies one last gift. They don’t need the ninth night anymore.'},
                {'bar': 32.7, 'text': 'More than two hundred of them stayed. Bellwether has a lot of new neighbors with familiar faces.'}]},
            {'bar': 34, 'image': IMAGES + 'campaign/stills/epilogue-new-face.webp', 'from': [0.5, 0.5, 1.0], 'to': [0.46, 0.42, 1.12], 'lines': [
                {'bar': 34.3, 'text': 'Sunday dinner is still at six. Iris comes too.'},
                {'bar': 35.6, 'text': 'Nora hasn’t forgiven her for the kidnapping. She tells her so, and passes her the bread.'}]},
            {'bar': 37, 'image': IMAGES + 'campaign/stills/book-frank-radio.webp', 'from': [0.45, 0.55, 1.0], 'to': [0.35, 0.6, 1.12], 'lines': [
                {'bar': 37.3, 'text': 'Mom and Dad came home. Dad is back on the radio every Thursday.'},
                {'bar': 38.6, 'text': 'There’s a new note on the kitchen table every morning. Most of them are about paint.'}]},
            {'bar': 40, 'image': IMAGES + 'title.webp', 'from': [0.72, 0.46, 1.6], 'to': [0.75, 0.38, 1.72], 'lines': [
                {'bar': 40.3, 'text': 'I don’t play the old voicemail anymore.'},
                {'bar': 41.8, 'text': 'The ring moved from my sock drawer to my cardigan pocket. Nora and I are starting with coffee, and an actual conversation.'}]},
            {'bar': 44, 'image': IMAGES + 'campaign/rooms/one_year.webp', 'from': [0.4, 0.5, 1.12], 'to': [0.55, 0.45, 1.0], 'lines': [
                {'bar': 44.3, 'text': 'KBWR has live hosts again. Two of them.'},
                {'bar': 45.6, 'text': 'Stephen and I still argue about which one of us is the upgrade.'}]},
            {'bar': 47, 'image': IMAGES + 'campaign/stills/book-after-package.webp', 'from': [0.5, 0.5, 1.0], 'to': [0.5, 0.56, 1.14], 'lines': [
                {'bar': 47.3, 'text': 'One year after the ninth night, a package arrived at the station.'},
                {'bar': 48.8, 'text': 'From very, very far away.'}]},
        ],
    },
}


def fit_narration(books, root):
    """Time each storybook to Steve's recorded narration, on the music's bar grid.

    A picture appears on a bar or half bar, Steve starts speaking a quarter of
    a bar later, and the next picture waits for his line to finish. The book
    ends on the first bar line after a short hold on the last picture.
    """
    import copy, json, math
    narration = json.loads((root / 'game/content/narration.json').read_text())['books']
    music = json.loads((root / 'game/content/music.json').read_text())
    tracks = [music['title']] + [t for g in music['chapters'].values() for t in g.values()]
    fitted = copy.deepcopy(books)
    for key, book in fitted.items():
        clips = narration.get(key, [])
        lines = [line for panel in book['panels'] for line in panel['lines']]
        if len(clips) != len(lines):
            continue
        track = next(t for t in tracks if t['file'] == book['music']['file'])
        bar = 240.0 / track['bpm']
        beat = track['beat']
        at = lambda b: beat + b * bar
        bar_of = lambda t: (t - beat) / bar
        cursor = None
        index = 0
        for panel in book['panels']:
            # Pictures change on the beat: whole or half bars, never before the last line ends.
            start = book['music']['bar'] if cursor is None else math.ceil((bar_of(cursor + .3)) * 2 - 1e-6) / 2
            panel['bar'] = start
            speak = at(start) + bar / 4
            for line in panel['lines']:
                clip = clips[index]; index += 1
                line['bar'] = round(bar_of(speak), 3)
                line['narration'] = clip['file']
                line['seconds'] = clip['seconds']
                speak += clip['seconds'] + .35
            cursor = speak
        book['end_bar'] = math.ceil(bar_of(cursor + bar * .75))
    return fitted


def reorder(scenes):
    """Move the flashbacks to the chapters that explain them."""
    by_id = {scene['id']: scene for scene in scenes}
    for scene_id, where, anchor, chapter in MOVES:
        moving = by_id[scene_id]
        scenes.remove(moving)
        moving['chapter'] = chapter
        index = [scene['id'] for scene in scenes].index(anchor)
        scenes.insert(index + 1 if where == 'after' else index, moving)


def _finding(task, prompt, options, answer, hints, note=None, title=None):
    task['prompt'] = prompt
    task['options'] = options
    task['answer'] = answer
    if note:
        task['note'] = note
    if title:
        task['title'] = title
    task['hints'] = [*hints, 'Choose “' + options[answer] + '”.']


def _conversation(task, title, prompt, action, note):
    # The ending is a victory lap. Each visit is one click and its conversation.
    task.update(title=title, prompt=prompt, options=[action], answer=0, note=note)
    task.pop('puzzle', None)
    task['hints'] = ['There is nothing to solve here. Enjoy the visit.'] * 2 + ['Choose “' + action + '”.']


def gentle_text(scenes):
    """Plain-language goals and prompts where players start and finish."""
    by_id = {scene['id']: scene for scene in scenes}
    tasks = {task['id']: task for scene in scenes for task in scene['tasks']}

    by_id['p_bay']['objective'] = 'Help Frank find the strange hum on his radio.'
    tasks['p_bay.tune']['prompt'] = ('Two stations crackle on Frank’s radio: a time signal on one side, a chime on the other. '
                                     'Something hums in between. Drag the dial until both stations fade, switch on Narrow bandwidth, then record.')
    tasks['p_bay.tune']['hints'] = [
        'Drag the dial toward the middle, away from both stations.',
        'The hum sits at 815 kHz. Narrow bandwidth shuts out the stations on either side.',
        'Set the dial to 815 kHz, switch on Narrow bandwidth, then press Record the signal.']
    _finding(tasks['p_bay.message'],
             'Steve stayed ashore for his shift. Helen wants him to hear this too. How can she reach him tonight?',
             ['Leave Steve a voicemail', 'Write it in the boat’s logbook', 'Call Frank’s radio club'], 0,
             ['Steve is at work, far from the boat.', 'Which of these will Steve find without coming out on the water?'],
             note='Helen left Steve a voicemail.', title='Helen’s phone')

    by_id['c1_flat']['objective'] = 'Nora’s “good morning” sounds exactly the same every day. Record it and find out why.'
    _finding(tasks['c1_flat.saturday'],
             'Dad’s recorder was running when Nora said good morning. The reel is labeled SAT. Keep it as evidence.',
             ['Keep the original Saturday reel', 'Record something new over it', 'Copy it to a loose reel with no label'], 0,
             ['Evidence is only useful if you know when it was made.', 'The original reel already has the day written on it.'])
    _finding(tasks['c1_flat.sunday'],
             'Sunday morning. Steve sets the recorder running before Nora walks in, so she says it the way she always does.',
             ['Play Saturday’s tape to her first', 'Record her without saying anything first', 'Say good morning first and wait for her reply'], 1,
             ['Keep the two mornings as alike as possible.', 'If Steve says or plays something first, she might copy him.'])
    _finding(tasks['c1_flat.control'],
             'Maybe the recorder is broken and keeps replaying old sound. Steve tests it: he says “one, two” twice, and a chair squeaks only the second time. The squeak is on the tape. What does that rule out?',
             ['That Nora used the same words twice', 'That the recorder just replays old sound', 'That Steve recognized Nora’s voice'], 1,
             ['The squeak happened only the second time.', 'A recorder stuck replaying old sound would have played the first pass again, without the squeak.'])
    tasks['c1_flat.compare']['prompt'] = 'Line up Saturday and Sunday and listen closely. Two different mornings, or the same recording?'
    by_id['c1_pier']['objective'] = 'Look around the harbor. Is anyone else acting strangely?'
    by_id['c1_dinner']['objective'] = 'Have Sunday dinner with Nora’s family, and listen.'
    by_id['c1_escape']['objective'] = 'Find out what Nora is hiding, then get out of the locked apartment.'

    # The Archivist's memory now sits after the player has used the recorder for hours.
    by_id['p_veyr']['objective'] = 'Record the wind over the city one last time.'
    _finding(tasks['p_veyr.shield'],
             'The wind thumps against the bare microphone. When the Archivist cups it with her hand, the thumping stops. What can do the same job when she lets go?',
             ['Fit the felt sleeve', 'Set the recorder on a folded cloth', 'Lower the volume a little'], 0,
             ['Her hand blocked the wind from hitting the microphone.', 'A soft cover does what her hand did.'])
    levels = tasks['p_veyr.levels']
    levels['prompt'] = 'Every gust pushes the meter toward the red mark. Leave room for the loud parts.'
    levels['puzzle']['instruction'] = ('The loudest gust so far peaked at −3 dB. The next one will be 6 dB louder, which would hit +3 dB, in the red. '
                                       'Choose the smallest change that brings it back down to −3 dB.')
    levels['hints'] = ['The next gust would land 6 dB too high.', 'Turning the gain down by the same amount brings it back to −3 dB.',
                       'Choose −6 dB. A bigger cut also works, but loses more of the quiet sounds.']
    levels['puzzle']['rows'][0]['options'] = ['+6 dB', '0 dB', '−6 dB', '−12 dB']
    _finding(tasks['p_veyr.record'],
             'The ships begin to rise: first the wind, then the engines, then silence where the engines were. How should she record it?',
             ['Record the whole passage, silence included', 'Make a separate reel for each sound', 'Stop the tape during the quiet part'], 0,
             ['Someone who never heard this will want to know how long the silence lasted.', 'Cutting it into pieces loses the time between the sounds.'])

    by_id['p_meeting']['objective'] = 'Translate carefully, so that both sides can admit the truth.'
    _finding(tasks['p_meeting.terms'],
             'The Chinese delegate says “compare our demonstrations.” Translate it without adding anything he did not say.',
             ['You propose a test of which field was stronger', 'You propose discussing what was demonstrated', 'You propose proving the apparatus can work'], 1,
             ['Listen for the verb he actually used.', '“Stronger” and “prove” are promises he never made.'])
    tasks['p_meeting.confess']['prompt'] = 'Each side saw a ring of light on the other side’s screen. Help both delegates say what really happened, one machine at a time.'
    _finding(tasks['p_meeting.record'],
             'Both delegates sign the same public statement. Helen also heard what each one admitted in private. What goes in the notebook she keeps for herself?',
             ['The public statement alone', 'Who said what in private, and the final agreement', 'One admission credited to both sides'], 1,
             ['Someone may read this notebook years from now.', 'A future reader needs to know who said what, and what they all signed.'])

    _conversation(tasks['epilogue.neighbors'], 'The new neighbors',
                  'Lyle and his copy are walking the boys to school together. Pell has Dale’s mailbag and Biscuit’s leash. Gus is waving a green croissant.',
                  'Say good morning to everyone', 'Bellwether kept its new neighbors.')
    _conversation(tasks['epilogue.bait'], 'Two Mrs. Penhallows',
                  'The two Mrs. Penhallows are arguing about bait prices across one counter. By the ferry, Adrian Rook says goodbye to his copy.',
                  'Visit the bait shop, then the ferry', 'Two Agneses, one shop. One Rook stays, one leaves.')
    _conversation(tasks['epilogue.coffee'], 'A new morning',
                  'Mom is calling from the kitchen. There is a new note on the table. Nora is at the door with her coat on.',
                  'Answer Mom, then go with Nora for coffee', 'Steve answered his mother and kept his date with Nora.')
    by_id['one_year']['objective'] = 'Open the package from the fleet, then go live.'
    _finding(tasks['one_year.newwind'],
             'A package arrived from the fleet: a recording of wind through new glass towers. Steve and Stephen are at the microphones.',
             ['Play the new wind, then open the microphones', 'Play the old Veyr recording instead', 'Replay yesterday’s show'], 0,
             ['The package is new. The Veyr reel is nine hundred years old.', 'Let Bellwether hear the fleet’s new home, then talk.'])
    _finding(tasks['postcredits.answer'],
             'At three in the morning a real signal arrives from deep space. Helen knows its shape: the same script as the last page of her notebook, the tones she copied from Wick’s dreams. Which notes should she open?',
             ['Meridian’s lamp schedule', 'Frank’s Thursday-club roster', 'Her transcription of Wick’s dream tones'], 2,
             ['Where did Helen first write down this script?', 'The last page of her notebook came from listening to the bay.'])


def presentation(scenes):
    """Chapter cards, time-jump pages and first-scene tips, keyed by scene."""
    previous = None
    for scene in scenes:
        card = {}
        if scene['chapter'] != previous and scene['chapter'] in CHAPTERS:
            card['chapter'] = dict(CHAPTERS[scene['chapter']])
        if scene['id'] in CARDS:
            card['page'] = dict(CARDS[scene['id']])
        if card:
            scene['card'] = card
        if scene['id'] in COACH:
            scene['coach'] = COACH[scene['id']]
        previous = scene['chapter']


def transcript_pages(scene_id):
    """Storybook narration for the transcript, placed before its scene."""
    out = []
    for key, book in STORYBOOKS.items():
        if book['before'] != scene_id:
            continue
        out += [f"## Storybook - {book['title']}", '', 'Steve narrates over illustrated panels.', '']
        for panel in book['panels']:
            for line in panel['lines']:
                out += [f"*{line['text']}*", '']
    return out

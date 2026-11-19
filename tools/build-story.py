#!/usr/bin/env python3
"""Author the playable adaptation of the user's final Plot.pdf. No network calls.

Dialogue outside quotations in the source is newly authored adaptation text.
Stable scene/task/line IDs are shared by gameplay, transcript, subtitles and voices.
"""
import json
from pathlib import Path
from early_puzzles import apply_early_puzzles
from late_chapter_puzzles import apply_late_puzzles
from early_caseboards import CASES as EARLY_CASEBOARDS
from late_caseboards import CASES as LATE_CASEBOARDS
from caseboards import apply_caseboards
from story_rework import STORYBOOKS, fit_narration, gentle_text, presentation, reorder, transcript_pages

ROOT = Path(__file__).resolve().parents[1]
SCENES, LINES = [], {}
CAST = {
    'steve': 'Steve Mercer', 'stephen': 'Stephen', 'nora': 'Nora Reyes',
    'iris': 'Iris', 'calder': 'Sheriff June Calder', 'rook': 'Adrian Rook',
    'rook_copy': 'Rook’s copy', 'saren': 'Prefect Saren', 'archivist': 'The Archivist',
    'agnes': 'Agnes Penhallow', 'agnes_original': 'Agnes Penhallow, original',
    'helen': 'Helen Mercer', 'frank': 'Frank Mercer', 'carmen': 'Carmen Reyes',
    'luis': 'Luis Reyes', 'mateo': 'Mateo Reyes', 'rafa': 'Rafa Reyes',
    'tomas': 'Tomás Reyes', 'lyle': 'Lyle Boone', 'lyle_copy': 'Lyle’s copy',
    'gus': 'Gus Albano', 'dale': 'Dale Kittredge', 'pell': 'Pell',
    'wen': 'Dr. Lin Wen', 'shaw': 'Dr. Evelyn Shaw', 'ward': 'President Elena Ward',
    'autorick': 'DJ AutoRick', 'choir': 'The Choir', 'guard': 'Veyri attendant',
    'operator': 'Thursday club operator', 'general_us': 'American delegate',
    'general_cn': 'Chinese delegate',
}

def dialogue(prefix, script):
    result = []
    for i, entry in enumerate(script.strip().splitlines()):
        if not entry.strip():
            continue
        speaker, text = entry.strip().split('|', 1)
        assert speaker in CAST, speaker
        key = f'{prefix}.{i + 1:02}'
        # These recorded performances must be reused byte for byte.
        fixed = {
            ('iris', 'Good morning, sleepyhead.'): 'recording.greeting',
            ('helen', 'Come out with us, kiddo. The bay is singing tonight.'): 'recording.voicemail',
            ('rook_copy', 'Sit tight, June.'): 'recording.rook',
            ('saren', 'Give me the notebook. Helen and Frank will walk out of the sea tomorrow morning.'): 'recording.offer',
            ('saren', 'Release the restraint. Maintenance authorization.'): 'recording.release',
        }
        audio = fixed.get((speaker, text.strip()), key)
        line = {'id': key, 'speaker': speaker, 'text': text.strip(), 'audio': audio}
        LINES[key] = line
        result.append(key)
    return result

def scene(id, chapter, title, place, style, actor, objective, intro, outro, shot):
    s = dict(id=id, chapter=chapter, title=title, place=place, style=style,
             actors=actor.split(','), objective=objective, tasks=[],
             intro=dialogue(id+'.in', intro), outro=dialogue(id+'.out', outro),
             shots=[{'duration': 5.0, 'move': 'establish', 'direction': shot},
                    {'duration': 6.0, 'move': 'push', 'direction': 'Move toward the active interaction.'}])
    SCENES.append(s)
    return s

def task(id, title, prompt, answers, correct, lines, note, needs=(), actor='', kind='choice', sounds=()):
    s = SCENES[-1]
    key = s['id']+'.'+id
    s['tasks'].append(dict(id=key, title=title, prompt=prompt, options=answers.split('~'),
                          answer=correct, lines=dialogue(key, lines), note=note,
                          requires=[s['id']+'.'+x for x in needs], actor=actor,
                          kind=kind, sounds=list(sounds),
                          hint='Look at the evidence in the description, then try another approach.'))

scene('p_veyr','Prologue','The last wind','Veyr, 900 years ago','veyr','archivist',
      'Preserve the sound of home before departure.',
      'archivist|There are forty thousand names on the departure register. I have checked every one.\narchivist|One recording remains.',
      'archivist|Wind through the western towers. Last evening. Original take.\narchivist|I will remember where we lived.',
      'Track upward through glass towers to a dying red sun and departing lights.')
task('shield','Wind screen','Wind rattles the exposed microphone. A felt sleeve lies beside the recorder.',
     'Fit the felt sleeve~Raise the input gain~Point the microphone into the gust',0,
     'archivist|Now I can hear the city, beneath the wind.', 'Shielded the microphone against wind noise.')
task('levels','Recording levels','The meter reaches the red mark on every gust. The quiet passages are still audible.',
     'Turn gain to maximum~Lower the gain until peaks stay below red~Stop recording between gusts',1,
     'archivist|Leave room for the loud parts. They belong to the record too.', 'Set recording headroom.',needs=['shield'])
task('record','Departure recorder','The ships are rising. Capture a continuous take before the tower falls silent.',
     'Record the whole passage~Loop the cleanest second~Replace it with generated wind',0,
     'archivist|Recording. Please wait for me.', 'Preserved the wind on Veyr.',needs=['levels'],kind='record')

scene('p_meeting','Prologue','A careful translation','Sentinel Point, nine years ago','meeting','helen',
      'Keep both delegations talking.',
      'general_us|We are prepared to discuss the practical status of our demonstration.\ngeneral_cn|After you explain the difference between practical and actual.',
      'helen|Everyone agreed to keep lying. It may be the most honest thing I have seen.',
      'Push across an empty conference table toward a notebook, then the pulse outside.')
task('terms','Interpreter’s notebook','Both delegates want the other to admit a weakness first. Translate without adding an accusation.',
     'You admit defeat~You propose discussing what was demonstrated~You demand their surrender',1,
     'helen|They propose that both teams describe what the observers actually saw.\ngeneral_cn|That would be a useful place to begin.', 'Kept the translation neutral.')
task('confess','Joint statement','The American demonstration used stage effects. The Chinese delegate has quietly closed a similar effects diagram.',
     'Invite each side to describe the apparatus~Announce that China lost~Promise the machines work',0,
     'general_us|There was no space-fold engine.\ngeneral_cn|There was no engine at our test either.\nhelen|Then we can discuss what to do next.', 'Both Meridian demonstrations were staged.',needs=['terms'])
task('record','Private record','The delegates agree to maintain the public story. Helen needs an accurate private account.',
     'Destroy the notes~Write the agreement in her own shorthand~Replace the notes with the press release',1,
     'helen|Dates. Names. What each person actually said. Someone may need the truth one day.', 'Helen preserved the truth in Mandarin shorthand.',needs=['confess'])

scene('p_bay','Prologue','The bay is singing','Bellwether Bay, eighteen months ago','boat','frank',
      'Find the hum beneath the radio static.',
      'frank|Same interval as last Thursday, Helen. Louder out here. Whatever it is, it keeps better time than I do.\nhelen|Steve would hear more in this than both of us put together. I’ll leave him a message.',
      'helen|Come out with us, kiddo. The bay is singing tonight.\nfrank|Helen. It’s tuning to us.',
      'Drift beside the rowboat as turquoise light grows beneath black water.')
task('tune','Frank’s radio','A low musical hum sits between two loud stations. Narrow the receiver bandwidth.',
     'Broadcast a distress call~Tune between the stations and narrow the band~Turn the radio off',1,
     'frank|There you are. Hear that, Helen? More than one voice, all holding the same note.', 'Found the ship’s hum beneath the radio static.',kind='record')
task('message','Phone and notebook','Helen has the pattern written down. Steve’s phone has gone to voicemail.',
     'Leave Steve a message~Erase the pattern~Row back without recording it',0,
     'helen|He should hear this for himself. We’ll bring the tape home, and he’ll tell us we recorded it wrong.', 'Helen called Steve before the boat disappeared.',needs=['tune'])

scene('c1_flat','Chapter 1','Good Morning, Sleepyhead','Steve and Nora’s apartment','apartment','steve',
      'Find out whether the repeated greeting is a fault in the recorder.',
      'helen|Come out with us, kiddo. The bay is singing tonight.\nsteve|Three in the morning. Again. Well, Mom, it’s a fine night for it.\nautorick|Good morning, Bellwether! Yesterday will be sunny.\niris|Good morning, sleepyhead.',
      'steve|Same breath. Same tiny click before the second word.\nsteve|I need evidence. Being afraid of something doesn’t make it true.',
      'Move from a dark reel-to-reel recorder toward amber kitchen light.')
task('saturday','Saturday take','Frank’s recorder was running when Nora greeted Steve. Preserve that take.',
     'Keep the original recording~Record over it~Normalize it destructively',0,
     'steve|Saturday, kitchen, quarter past seven. Dad always said to put the date on everything.', 'Preserved Saturday’s greeting.',kind='record',sounds=['recording.greeting'])
task('sunday','Sunday take','The next morning, Nora gives the same greeting. Record it on a fresh section of tape.',
     'Ask about their first date~Record the greeting without prompting her~Guess from memory',1,
     'iris|Good morning, sleepyhead.\nsteve|Sunday. Fresh tape. Same words. Same... everything.', 'Preserved Sunday’s greeting.',needs=['saturday'],kind='record',sounds=['recording.greeting'])
task('control','Recorder control test','Steve says the same sentence twice. He can hear a different breath and a longer pause in the second take.',
     'The recorder repeats every input~The recorder preserves new differences~People always repeat perfectly',1,
     'steve|Testing. One, two. Testing... one, two.\nsteve|The squeak only made the second pass. So the recorder’s fine. Cross that one out.', 'Ruled out a stuck or looping recorder.',needs=['sunday'])
task('compare','Compare greetings','Listen to Saturday and Sunday. Compare the breath, onset and pause, not just the words.',
     'Different words~An identical performance~Similar delivery with a new breath',1,
     'steve|She remembers our first date better than I do. But nobody says a sentence the same way twice. Nobody.', 'Two independently captured greetings are the same take.',needs=['control'],kind='compare',sounds=['recording.greeting','recording.greeting'])

scene('c1_pier','Chapter 1','Sunday on the pier','Bellwether harbor','pier','steve',
      'Look for independent evidence around town.',
      'steve|Admiral. That was my lunch. You don’t even like rye.\nagnes|Fish don’t sing, Steven. Something under them does.',
      'pell|Your parents’ mail, Mr. Mercer. Delivered precisely on schedule.\nsteve|They haven’t been home in eighteen months, Dale. You know that.',
      'Follow Steve along the pier, then join the Reyes family at La Marea for Sunday dinner.')
task('whistle','Admiral’s pool','Admiral stole Steve’s sandwich. Nora whistles her familiar two-note call, but he ignores it.',
     'Make a note, without treating it as proof~Conclude that everyone is a copy~Blame the sealion',0,
     'steve|You always come for that whistle. What’s different today?', 'Admiral ignored the apparent Nora’s whistle.')
task('door','Deputy Lyle','Lyle holds the door, remembers a birthday and hurries to his sons’ game.',
     'Arrest him~Record the change as a lead~Decide that kindness proves innocence',1,
     'lyle_copy|They’re both pitching today. I promised I’d watch every inning.\nsteve|Deputy Lyle, keeping a promise. I should write that down before the world ends.', 'Lyle’s behavior changed; behavior alone proves nothing.')
task('bait','Penhallow’s bait stall','Mrs. Penhallow hums a tune while she wraps bait. The same low tone drifts from the bay.',
     'Ask about the sound~Take her cash box~Assume it is a fishing song',0,
     'agnes|Count the nights, Steven. You were always good with numbers when you wrote them down.', 'Penhallow knows about the bay’s recurring tone.',kind='record')

scene('c1_dinner','Chapter 1','A plate kept warm','La Marea restaurant','restaurant','steve',
      'Listen to Nora’s family before drawing a conclusion.',
      'carmen|Your plate is warm. Sit. You can apologize while you eat.\nrafa|I kept the sauce separate. You used to like it that way.',
      'carmen|She stopped arguing with me. My daughter has argued with me since she could talk.',
      'Settle beside the family table, with harbor lights through rain-streaked glass.')
task('birthday','Carmen’s birthday','Carmen remembers Nora staying at La Marea from noon to midnight on her birthday.',
     'Write down the date and witnesses~Ask whether Nora seemed nicer~Ignore the date',0,
     'mateo|I drove her here. Rafa drove her home. Midnight, give or take ten minutes.', 'Nora had a documented alibi on Carmen’s birthday.')
task('podcast','Tomás’s recorder','Tomás has dated recordings of lights and hums in the bay from the past three years.',
     'Laugh off the story~Ask to keep the dates and recordings~Edit his podcast title',1,
     'tomas|You can borrow them. You could also have listened any time in the last three years.\nsteve|I’m listening now.', 'Tomás retained dated bay recordings.',kind='record')
task('family','Nora at dinner','Nora agrees with every suggestion, including a recipe she used to dislike.',
     'Test her on a childhood memory~Treat the change as another lead~Accuse her in front of everyone',1,
     'iris|Whatever Carmen thinks is best.\nluis|Eat before it gets cold, Steve. Then tell us what is troubling you.', 'Several people noticed Nora’s changed behavior.')

scene('c1_escape','Chapter 1','The ninth night','Apartment balcony and beach','balcony','steve',
      'Check the work order and leave the locked apartment.',
      'iris|No. He does not know where the notebook is. Tonight? Understood.\nsteve|Nora? Why is the front door locked from the outside?',
      'steve|She could have stopped me. She stood there and let me go.\nagnes|Ninth night, Steven. Count them.',
      'Follow the balcony escape, then reveal a procession entering luminous surf.')
task('order','Coat pocket','Nora signed a north-wing aquarium work order on Carmen’s birthday.',
     'Compare it with the birthday alibi~Assume the birthday was wrong~Throw the work order away',0,
     'steve|Noon to midnight at La Marea. Mateo and Rafa both saw her. She couldn’t have signed this there.', 'The aquarium work order contradicts a witnessed alibi.')
task('power','Balcony wiring','The neighbor’s balcony gate has an old electric latch. Its service switch is beside Steve’s window.',
     'Cut a live cable~Use the service switch to release the latch~Jump toward the street',1,
     'steve|I fixed this latch for Mr. Bell last winter. He paid me in fruitcake. Tonight it’s worth every slice.', 'Released the neighbor’s balcony latch.',needs=['order'])
task('cross','Iris pots','The safe route is along the shared balcony. Steve bumps the flowerpots as he climbs.',
     'Cross toward the unlocked stairwell~Go back to the locked door~Hide in the flowerpot',0,
     'steve|Sorry. Sorry. Those were your irises.\niris|Steve... go.', 'Escaped while the apparent Nora hesitated.',needs=['power'])

scene('c2_aquarium','Chapter 2','The Aquarium Is Closed','Aquarium north wing','aquarium','steve',
      'Follow the old exhibit plan to the sealed wing.',
      'steve|Emergency. Bellwether Aquarium. Someone is... hello?\nsteve|Half a sentence before the line died. I hope someone heard it.',
      'nora|My name is Nora Reyes, and somebody just walked out of here wearing my face.\nsteve|Five months. I didn’t notice for five months.',
      'Pass dark empty exhibits into an amber transit chamber beneath new plywood.')
task('plan','Exhibit plan','The old public route ends at a new wall. The service drain still connects to the north wing.',
     'Follow the service route on the old plan~Break the public entrance~Wait for the morning tour',0,
     'steve|Nora showed me this when I repaired the underwater speakers.', 'Located the north-wing service route.')
task('guard','Two service doors','Steve records six seconds at each door. Which passage can he cross without meeting the guard?',
     'Take the pump corridor~Take the filter corridor~Wait for both doors to go silent',1,
     'steve|The cough was in exactly the same place. That corridor has a recording.', 'Distinguished an announcement loop from a live guard.',needs=['plan'],kind='compare')
task('intercom','Nora’s coat and intercom','Inside Nora’s real coat is an intercom tape dated five months earlier. Keep its two-note whistle intact.',
     'Preserve the complete tape~Keep only the spoken name~Discard the whistle as noise',0,
     'nora|Two short notes. If Admiral can hear me, perhaps somebody else can.\nsteve|I’m keeping all of it.', 'Recovered Nora’s intercom tape and whistle.',needs=['guard'],kind='record')

scene('c2_ship','Chapter 2','Sixty-one percent','The Long Patience, scan chamber','ship','steve',
      'Record a command and interrupt the scan.',
      'iris|Please come with us. They want to know where your mother put her notebook.\nguard|Would peaceful human hold music assist your experience?\nsteve|I’d prefer the exit. Does that come with music too?',
      'steve|The room is flooding. The underwater speakers still work... Nora’s whistle.\ncalder|Mercer. Breathe first. Explain afterward.',
      'Reveal the Gallery, close on the scan meter, then follow light into the flooding intake.')
task('nora','Amber sleeper','Nora is asleep and breathing in the Gallery. The hum almost forms a familiar lullaby.',
     'Speak to her and listen~Assume the bed is empty~Ignore the hum',0,
     'steve|I kept waiting until I knew what to say. I’m here now. I should have been here sooner.', 'Confirmed that the real Nora is alive.',kind='record')
task('command','Saren’s intercom','Saren orders an attendant to release a maintenance restraint. His voice authorizes the chair.',
     'Record the complete release command~Imitate Saren from memory~Record the hold music only',0,
     'saren|Release the restraint. Maintenance authorization.\nsteve|Got it. Thank you, Prefect.', 'Recorded Saren’s restraint-release command.',needs=['nora'],kind='record')
task('escape','Scan chair','The scan has reached 61%. The intercom microphone is within reach of the recorder.',
     'Wait until the scan finishes~Play Saren’s release command~Ask for louder hold music',1,
     'saren|Release the restraint. Maintenance authorization.\nsteve|It worked. Now the seawater valve. Then I find out how long I can hold my breath.', 'Interrupted the scan at 61% and escaped through the flooded intake.',needs=['command'],kind='playback')

scene('c3_house','Chapter 3','Please Prove You Exist','Calder’s house','cottage','steve',
      'Agree on a fair method for finding copies.',
      'calder|Forty-seven casseroles. Your town is either very worried or very hungry.\nsteve|Nora is asleep on a ship under the bay. I know exactly how that sounds.\ncalder|Then we start with what you can prove.',
      'calder|For a year I’ve kept a list. People who got better overnight. Thirty-one names.\nsteve|Then let’s find out which of them got better, and which of them got replaced.',
      'Move from casserole dishes and a sleeping beagle to a drawer full of case notes.')
task('crossword','Morning crossword','Calder asks Steve to solve fresh clues from today’s paper. Old shared memories could have been copied.',
     'Use the new crossword~Recite his birthday~Describe his first date',0,
     'steve|Seven letters. Maritime... marmite?\ncalder|No copy is that bad at this. And you’ve put coffee in my lap.', 'Established fresh private facts with Calder.')
task('rules','Evidence notebook','Affection can be real in a copy. Grief can change a human. Neither is a reliable test.',
     'Treat kindness as proof~Use fresh facts and independently dated evidence~Arrest everyone who seems different',1,
     'calder|We do this fairly. Otherwise we’re just frightened people making a list.', 'Agreed on evidence rather than personality tests.',needs=['crossword'])
task('mail','Dale’s delivery','The mail carrier brings Steve’s redirected mail early, then spends several minutes petting Biscuit.',
     'Record the visit without confronting him~Take Biscuit away~Assume a dog can verify identity',0,
     'pell|A most diligent animal. I will return at the scheduled interval.\ncalder|He’s asleep. That is his schedule.', 'The mail carrier has formed an attachment to Biscuit.')

scene('c3_archive','Chapter 3','Paper remembers','Town Hall archive','archive','steve',
      'Build a case from independent records.',
      'tomas|Three years of recordings. Original timestamps. You can stop calling it a hobby now.\nsteve|I’ll start with thank you.',
      'calder|Two hundred and seventy-four. My list had thirty-one.\nrook_copy|Sit tight, June.\nsteve|A message: he remembers june. that doesnt mean hes adrian.',
      'Slide between municipal shelves, then pull back from the dark beach stakeout.')
task('paper','Attendance ledger','A paper signature places a suspect at Town Hall while a dated clinic receipt places the same person elsewhere.',
     'Keep both originals and record the contradiction~Trust the edited database~Destroy the paper',0,
     'steve|Two places. Same time. Witnesses on both documents.', 'Found contradictory physical records.')
task('power','Meridian utility bill','Sentinel Point claims to run a space-fold engine. Its electricity bill is lower than a laundromat’s.',
     'File the measured power use~Assume unlimited secret electricity~Change the bill',0,
     'steve|A world-changing machine with a very modest dryer cycle.', 'Meridian’s power use does not fit the claimed engine.')
task('cycle','Tomás’s tapes','Tomás marked the dates on the reels. Use them to decide when Calder should watch the beach.',
     'Seven nights~Nine nights~Every night',1,
     'steve|Same interval across three years. We watch the beach on the next ninth night.', 'Predicted the re-sync procession.',needs=['paper','power'],kind='compare')

scene('i1_archive','Interlude 1','The Archivist','The Choir’s record chamber','choir','archivist',
      'Maintain the records and inspect the sealed surveys.',
      'gus|I invented a kelp croissant. Nobody asked for it. I wanted to know what it would taste like.\narchivist|Your record contains no such recipe.',
      'archivist|Memory damaged by scan. Details in subject’s notebook.\narchivist|I will leave the report as it is.',
      'Circle a glass memory console, then settle beside the isolated frosted bed.')
task('reset','Echo reconciliation','Gus’s new recipes are classified as drift. The Archivist follows the law she has enforced for centuries.',
     'Perform the required reconciliation~Delete the original human~Reconcile every crew member',0,
     'archivist|Return to the stored record.\ngus|Good evening. May I help you?\narchivist|You asked me that before.', 'The Archivist erased an echo’s new experiences.')
task('signals','Meridian test archive','Two national stations dated their Meridian instrument reels a week apart. What can the Archivist establish from the traces?',
     'Flag one performance filed twice~File two independent performances~Flag a change of playback speed',0,
     'archivist|The same performance. Again. I knew this a year ago.', 'The Archivist knows Meridian’s signals were staged.',needs=['reset'],kind='compare')
task('quiet','Sealed surveys','Seven inhabited worlds are marked Quiet. Another living-world survey is sealed under Saren’s own mark.',
     'Remember the sealed survey and visit Row Zero~Unseal every crew member’s memory~Report a destroyed world as fact',0,
     'saren|The fleet’s message is one word. Deliver.\narchivist|And who will come to check?\narchivist|Three hundred years, and you still will not tell me where your people went.', 'Found the Quiet worlds and Saren’s sealed survey.',needs=['signals'])

scene('c4_safe','Chapter 4','Federal Hospitality','Coast Range safe house','safehouse','steve',
      'Test Rook’s voice against his message.',
      'rook_copy|We’ll take the tapes as evidence. You may keep the recorder.\ncalder|Adrian and I go back a long way.\nsteve|That’s what worries me.',
      'steve|The same breath. He knows June because someone copied a man who knew June.',
      'Look through a half-open door at a telephone and a corridor of closed rooms.')
task('record','Office door','Rook hums along to hold music. When he hangs up, he repeats his reassurance to Calder.',
     'Record the new reassurance~Ask his favorite soup~Take the telephone apart',0,
     'rook_copy|Sit tight, June.\nsteve|That’s the line. Keep the whole take.', 'Recorded Rook’s reassurance at the safe house.',kind='record',sounds=['recording.rook'])
task('match','Rook comparison','Compare the fresh recording with Calder’s saved voicemail.',
     'A second reading at a different pace~The same recorded performance~A shortened version of the voicemail',1,
     'steve|Same breath, pause and room click. This is the man the message warned us about.', 'Identified Rook’s copy through repeated audio.',needs=['record'],kind='compare',sounds=['recording.rook','recording.rook'])
task('screens','Observation room','A maintenance monitor has a view of the Gallery and assignment files for Washington and Beijing.',
     'Inspect the sleeper and assignment dates~Broadcast an accusation now~Turn every screen off',0,
     'steve|Adrian Rook. Asleep. Both governments... and President Ward is next.', 'Confirmed the real Rook is asleep and the invasion reaches both governments.',needs=['match'])

scene('c4_escape','Chapter 4','Only honest','Safe house service wing','safehouse','steve',
      'Warn Calder and force an evacuation.',
      'calder|I don’t need you to be brave, Steve. I need you to be honest.\nsteve|Rook is one of them. I have proof.',
      'rook_copy|Scan Calder tonight. The signing is in six days.\nsteve|And now I’m wanted for kidnapping Nora. I have to keep moving.',
      'Follow a pneumatic capsule, then a van’s headlights into mountain fog.')
task('tube','Pneumatic post','The tube diagram labels Calder’s room C and Rook’s office R.',
     'Send the warning to C~Send the warning to R~Leave it on the desk',0,
     'calder|I’ll keep his attention. You get out. We both know you can’t bluff him in person.', 'Warned Calder through the service tubes.')
task('fault','Safety test panel','A harmless smoke-test cartridge can trigger an evacuation without starting a fire.',
     'Set an actual fire~Use the marked evacuation test~Disable the alarms',1,
     'steve|Test circuit. No heat, no flame. Just enough bureaucracy to get us outside.', 'Triggered a safe evacuation.',needs=['tube'])
task('van','Transport van','The van slows at a gravel service bend. The rear latch has a manual release.',
     'Use the release at the slow bend~Jump onto the highway~Wait until the ship',0,
     'steve|I meant to land on my feet. The ditch had other plans.', 'Escaped the transport at a slow service bend.',needs=['fault'])

scene('c5_shack','Chapter 5','Wanted: Steve Mercer','Frank’s radio shack','radio_shack','steve',
      'Open the boxes and follow Frank’s investigation.',
      'luis|Food. I know where your father used to come to think.\nsteve|Are you going to call the Sheriff?\nluis|Eat first.',
      'steve|With the good stuff. Mom meant the record library. My first show.\nsteve|I know where the notebook is.',
      'Push through rain at a shack window to boxes of handwritten kitchen notes.')
task('notes','Kitchen-table notes','Forty-five years of notes fill a box. One mentions keeping precious things “with the good stuff.”',
     'Read the notes in order~Search only for government stamps~Close the box again',0,
     'helen|Frank, there is soup in the refrigerator. The other container is paint. Please read both labels.\nsteve|I missed you both so much I stopped looking at anything you left.', 'Opened the family notes and found the record-library clue.')
task('rig','Frank’s receiver','The receiver’s power lead is loose. Its matching socket is marked 12V DC; the mains lead belongs to a separate supply.',
     'Reconnect the matching low-voltage lead with power off~Bridge every terminal~Plug the receiver into mains directly',0,
     'steve|Power off. Matching connector. I’m doing it your way, Dad.', 'Repaired Frank’s radio safely.',needs=['notes'])
task('club','Thursday club','Frank’s log identifies his call sign as K7BLW. Use it to reach the operators who knew him.',
     'Call K7BLW~Play the wanted bulletin~Send random tones',0,
     'operator|K7BLW? Frank? We thought we’d lost you.\nsteve|It’s Steve. I need your help.\noperator|Any time, kid.', 'Restored contact with Frank’s ham radio club.',needs=['rig'],kind='record')
task('log','The final log','Frank recorded the ninth-night tone. His last note describes the hum beneath it.',
     'Preserve the tone and read the last entry~Discard the hum as static~Erase the oldest entries',0,
     'frank|It isn’t one voice. It’s a choir.\nsteve|They wanted my ears. That’s why they asked me along.', 'Preserved the ninth-night tone and Frank’s Choir observation.',needs=['club'],kind='record')

scene('c5_station','Chapter 5','Two of him','KBWR record library','station','steve',
      'Recover Helen’s notebook and face the pursuer.',
      'autorick|Breaking news, folks: there’s a fella in our record library!\nstephen|That cardigan. Is this what happens when I stop trying?',
      'steve|They disappeared eighteen months ago. I said no to the boat trip.\nstephen|No. I had breakfast with them. I remember...\nstephen|Then that explains what I saw when I woke up. Mom and Dad are on that ship, Steve. Row nine. They’re asleep. They’re alive.',
      'Track between empty broadcasting racks, then hold on the two brothers at the record shelf.')
task('automation','Unattended console','AutoRick reads every item in the event queue. A scheduled station-identification break opens a maintenance window.',
     'Schedule an identification break~Shout over AutoRick~Pull the tower’s power',0,
     'steve|I built the schedule before they replaced me with it. Maintenance follows the ident.', 'Used the station’s scheduled maintenance window.')
task('sleeve','First show','The first show Steve engineered is filed under its original broadcast date, written in Helen’s kitchen note.',
     'Open that record sleeve~Search the newest releases~Take the severance letter',0,
     'steve|Mom’s handwriting. Mandarin shorthand. And this last page... I’ve never seen that script.', 'Recovered Helen’s notebook.',needs=['automation'])
task('halcyon','Ownership papers','The tower’s night transmissions and the severance paperwork name Halcyon Media Holdings.',
     'Compare the transmission dates with the acquisition~Assume the sale was unrelated~Erase the transmitter logs',0,
     'steve|They needed the tower, and they needed the building empty. I was the last person here.', 'Connected Steve’s dismissal to the Veyri communications network.')
task('stephen','The pursuer','Stephen has childhood memories but knows nothing from the last eighteen months. His scan was incomplete.',
     'Tell him what happened~Test him on copied childhood facts~Treat him as an enemy without listening',0,
     'stephen|Sixty-one percent. That’s what the attendant said. I assumed the rest was a compliment.\nsteve|Sit down. There’s something you need to know.', 'Recognized Stephen as an incomplete copy with no Veyri occupant.',needs=['sleeve','halcyon'])

scene('c6_iris','Chapter 6','Iris','Bellwether after dark','street','steve,stephen',
      'Give each Steve a role and test Iris fairly.',
      'stephen|You hide. I’ll be charming in public. We should each use our strengths.\niris|I sent the message about Rook. Please listen before you decide what I am.',
      'iris|Those Sunday dinners happened to me. I won’t let them take them away.\nsteve|What should I call you?\niris|Iris. After the flowers.',
      'Follow two routes through the same lamplit street and reunite beside the closed bakery.')
task('alibi','Market corner','Someone must be seen in public while Steve reaches the Sheriff’s service entrance.',
     'Ask Stephen to speak to the shopkeeper~Send both Steves into hiding~Ask Steve to announce the break-in',0,
     'stephen|Good evening. Yes, that is my face on the poster. Terrible photograph.', 'Stephen established a public alibi.',actor='stephen')
task('takes','Iris’s recorder test','Steve gives her the recorder and asks for the same words twice. What can he put in his notebook?',
     'She played the first take again~She chose how to say it each time~She started the same take later',1,
     'iris|I stayed because I wanted to.\niris|I stayed... because I wanted to.\nsteve|Two different takes. You’re choosing what to say.', 'Iris is an echo with her own experiences.',actor='steve',kind='compare')
task('hold','Halcyon lines','Distant copies spend long periods waiting on Halcyon telephone lines.',
     'Connect hold music with remote re-sync~Assume they enjoy customer service~Cut every phone line immediately',0,
     'iris|The signal is inside the music. Near the bay we go below. Far away, we call.\nsteve|Rook was never waiting for the Bureau.', 'Learned how distant copies re-sync.',needs=['takes'],actor='steve')

scene('c6_jail','Chapter 6','Two Sheriffs','Sheriff’s office and jail','jail','steve,stephen',
      'Find the cell key and identify the real Calder.',
      'pell|I am required to report your location.\npell|Biscuit, Steve Mercer is here. My duty is complete.\nstephen|We should put the dog in charge.',
      'iris|Nora found the ring a year ago. It is not mine to answer.\ngus|Take the van. I don’t know why, but I trust you.\niris|We’re starting to forget. Stephen and I have days.',
      'Cross the mail-sorting wall to a jail corridor; finish beneath a bakery van’s giant croissant.')
task('mail','Pell’s sorting case','The service key was returned in a registered envelope. Its ledger says JAIL, drawer J, slot 9.',
     'Open drawer J, slot 9~Open drawer R, slot 1~Empty every letter onto the floor',0,
     'pell|Correctly delivered. Biscuit may inspect the chain of custody.', 'Located the jail service key.',actor='steve')
task('distract','Sheriff’s front desk','Calder’s copy is watching the cell corridor. Stephen can draw her to the public counter.',
     'Have Stephen demand to correct his wanted photograph~Have Steve surrender the key~Sound the fire alarm',0,
     'stephen|I would like a better photograph. My family will be seeing these.', 'Distracted Calder’s copy.',actor='stephen')
task('crossword','The two Calders','Steve slipped today’s crossword into the cell. Only the prisoner has had time to solve it.',
     'Ask about a shared childhood~Ask for today’s unfinished crossword answer~Choose the friendlier Sheriff',1,
     'calder|Twenty-three across. Inimitable. Unlike my colleague’s handwriting.\nsteve|June. We’re getting you out.', 'Identified and freed the original Calder.',needs=['mail','distract'],actor='steve')
task('exit','Deputy’s checkpoint','Lyle’s copy recognizes the fugitives but keeps glancing at a school-play ticket.',
     'Let him choose to go to the play~Threaten his sons~Demand that he forget them',0,
     'lyle_copy|They gave me a seat in the front row.\ncalder|Then you’d better get there. We can talk tomorrow.', 'Lyle’s copy chose his family over his orders.',needs=['crossword'])

scene('i2_nora','Interlude 2','Nobody is coming to fix this','The Gallery','gallery','nora',
      'Organize the half-awake sleepers between patrols.',
      'nora|I can move my hand. That’s a start.\ndale|If this is a hospital, I’m changing hospitals.\nnora|Names first. Complaints after we have a plan.',
      'nora|Helen. Frank. Steve is going to be so glad.\nnora|Mrs. Penhallow? Row three. I should remember that.\nnora|And you, under the frost... you can hear me, can’t you?',
      'Travel at sleeper height through amber beds to the enormous eye in Row Zero.')
task('patrol','Guard circuit','The guard passes, a pump cycles, then the far door closes. Move only after the door closes.',
     'Move when the far door closes~Move on the guard’s first footstep~Shout for everyone to wake',0,
     'nora|Wait. Now. Keep low. We can argue about my tone after we’re out.', 'Learned the patrol interval.')
task('jobs','Sleeper skills','Lyle knows door hardware. Dale remembers routes. Nora understands water systems.',
     'Give each person a task using those skills~Make everyone work on the same lock~Ask everyone to wait without a plan',0,
     'lyle|I can keep that latch from catching.\ndale|I’ll remember the turns.\nnora|Good. I’ll handle the pump.', 'Organized the waking prisoners.',needs=['patrol'])
task('pump','Gallery circulation','A bypass marked SERVICE relieves pressure without interrupting life support.',
     'Shut down life support~Use the service bypass~Open every valve',1,
     'nora|Pressure down. Nobody’s breathing changes. That’s our route.', 'Prepared a safe route through the Gallery.',needs=['jobs'])
task('message','Gallery intercom','Nora can leave a message in the local intercom memory for Steve.',
     'Record a private message for him~Overwrite the patrol warning~Broadcast immediately to the guards',0,
     'nora|Steve. If you get here, there are things we need to say to each other. A lot of things.', 'Nora left a message for Steve.',needs=['pump'],kind='record')

scene('c7_gate','Chapter 7','The President’s Other Appointment','Sentinel Point gate','array','steve,stephen,pell',
      'Get the team into the accord signing.',
      'stephen|Crew credentials. Loyal asset. Very important face.\npell|Registered mail for the President. Delivery cannot be delayed.',
      'wen|Helen wrote this? Where is she?\nsteve|Asleep under the bay. Can you read it?\nwen|This page... we need a private room.',
      'Move through fog among antenna towers toward a temporary broadcast compound.')
task('badge','Security gate','Stephen’s crew credentials remain valid. Steve’s face is wanted.',
     'Send Stephen through the official gate~Send Steve through with no badge~Give the credentials to a stranger',0,
     'stephen|I’m expected. I’m usually expected everywhere.', 'Stephen entered as a crew asset.',actor='stephen')
task('post','Accord mail','Pell’s registered delivery belongs at the delegation service entrance.',
     'Use the marked mail entrance~Climb the antenna fence~Leave the letter in the road',0,
     'pell|President Ward. Your letter. On time.\nward|An increasingly rare achievement.', 'Pell reached the delegation.',actor='pell')
task('truck','Halcyon broadcast truck','Steve knows the sound equipment. A spare technician’s pass is inside the van.',
     'Enter as the sound technician during the cable check~Announce a kidnapping~Follow Stephen into the press crowd',0,
     'steve|Sound check. I’m supposed to be under the desk.\nshaw|Then try staying off the cables.', 'Steve reached the sound desk.',needs=['badge','post'],actor='steve')

scene('c7_swap','Chapter 7','Fourteen turn toward the sea','Accord ceremony','array','steve,stephen',
      'Route the ninth-night tone through every event speaker.',
      'saren|Your parents’ records are in good order, Mr. Mercer. So is mine. I have never been wrong on the record. Not on Tirel, and not here.',
      'rook_copy|Is he awake? The other one?\nward|Thank you, Mr. Mercer. Now we owe you an explanation.\nshaw|There is no engine. There never was.',
      'Sweep from the podium to fourteen figures turning toward the water as the tone sounds.')
task('map','Event monitor','The physician escorts Ward toward a service tunnel while her copy approaches the podium.',
     'Tell Calder and Iris where the real Ward went~Assume the biometric check proves identity~Follow the podium alone',0,
     'stephen|Service tunnel, east stairs. The doctor has the real President.\ncalder|We’re on it.', 'Directed Calder and Iris toward the real President.',actor='stephen')
task('bus','Sound desk routing','The desk has separate press, stage and site buses. The all-call bus reaches every speaker.',
     'Route Frank’s tone to the all-call bus~Route it only to Steve’s headphones~Mute the whole site',0,
     'steve|All-call. Enough level to reach the back fence. Leave the microphone clear.', 'Routed the ninth-night tone across the site.',actor='steve')
task('tone','Ceremony cue','The copy has reached the podium. Calder and Iris are at the tunnel.',
     'Play the ninth-night tone now~Wait until the copy leaves~Play yesterday’s weather',0,
     'steve|Fourteen. Rook. The physician. The woman at the microphone.\ncalder|We have President Ward.', 'Exposed fourteen copies and recovered the President.',needs=['map','bus'],actor='steve',kind='playback')

scene('c8_lab','Chapter 8','The Biggest Lie on Earth','Meridian laboratory','lab','steve',
      'Reconstruct the bluff and prepare a live signal rig.',
      'wen|Your mother recorded the meeting accurately. Both sides staged the tests.\nshaw|Mine had a better explosion.\nwen|Mine required fewer washing machines.',
      'agnes|A lie is only shameful when it’s lazy, Steven.\nsaren|Deliver the engine by midnight tomorrow. The ninth night.',
      'Reveal painted doors, washing-machine drums and theatrical lights beneath the grand facade.')
task('notebook','Helen’s shorthand','Match Helen’s dates with the two staged tests and the private meeting.',
     'Tests, mutual discovery, private agreement~Private agreement, real engine, surrender~Arrival of the ship, then the tests',0,
     'wen|They heard the demonstrations nine years ago. They came here three years ago. We called them without knowing anyone was listening.', 'Connected the Meridian deception to the invasion.')
task('props','The reactor','Inside the apparent reactor are washer drums, theater lights and a fog machine.',
     'Inspect and reuse the stage equipment~Try to start a real engine~Destroy all the props',0,
     'shaw|Those drums survived six films and a congressional visit. They can manage one more show.', 'Identified reusable Meridian stage equipment.')
task('lastpage','Unknown script','Helen’s note says she transcribed the last page from Frank’s tapes and recognized a language.',
     'Preserve the script and the hum together~Assume it is Mandarin~Erase it as a copying error',0,
     'wen|I can read Helen’s shorthand. This is something else.\nsteve|Then we keep listening.', 'Preserved the unidentified language from the hum.',needs=['notebook'])

scene('c8_beach','Chapter 8','An offer on the shore','Beach at dawn','beach','steve',
      'Examine Saren’s offer before answering.',
      'saren|Give me the notebook. Helen and Frank will walk out of the sea tomorrow morning.\nsteve|I need a moment.',
      'steve|Who did you say that to on Tirel?\nsaren|You should consider your parents.\nsteve|I am. And everyone else’s.',
      'Hold a wide empty shoreline between Steve and the glass figure at the water’s edge.')
task('first','The offer','Record Saren’s exact promise without agreeing to it.',
     'Preserve the offer~Hand over the notebook~Erase the recording',0,
     'steve|Say it again. I want to be certain I heard you.', 'Recorded Saren’s offer.',kind='record',sounds=['recording.offer'])
task('second','A second offer','Steve rewinds to the first offer. Does the second promise deserve more weight as an independent assurance?',
     'One performance, played twice~A new reading of the same promise~The second promise omits the last phrase',0,
     'saren|Give me the notebook. Helen and Frank will walk out of the sea tomorrow morning.', 'Saren repeated an identical take.',needs=['first'],kind='compare',sounds=['recording.offer','recording.offer'])
task('refuse','The notebook','The notebook would prove Earth has no engine. Saren has used this promise before.',
     'Keep the notebook and refuse~Hand it over without conditions~Destroy Helen’s final page',0,
     'steve|No. You don’t get to make me trade the whole town for my family.', 'Refused Saren’s bargain.',needs=['second'])

scene('c8_rig','Chapter 8','A show that happens once','Sentinel Point workshop','lab','steve,stephen',
      'Prepare a live bluff and a route into the ship.',
      'shaw|You are a terrible liar.\nsteve|I know. That is why it has to be a show.\niris|Wake them. Even if we start forgetting. I vote to do it.',
      'stephen|Dad’s name. I know it. I just...\nsteve|Frank.\nstephen|Frank. I’ll write it on my hand.',
      'Push across the improvised signal rig to Stephen writing a name on his hand.')
task('source','Signal sources','The earlier bluff failed under inspection because its signals repeated.',
     'Use a longer loop~Use live human cues and changing signals~Replay the original test',1,
     'steve|Their old test failed because it repeated. Ours won’t. Every answer will be live.', 'Designed the bluff around live variation.')
task('path','Trust path','The fleet trusts measurements from its own ship. An external broadcast alone will not persuade it.',
     'Feed the performance into the ship’s own systems~Mail the fleet a video~Ask AutoRick to announce victory',0,
     'wen|The ship must measure the event.\nsteve|Then we take the rig to its antenna.', 'Planned the ship-side signal injection.',needs=['source'])
task('rig','Props and radio','Frank’s transmitter needs a stage cue source and an isolated connection to the ship antenna.',
     'Connect the cue board through the isolated interface~Short the transmitter output~Use a repeating test tape',0,
     'stephen|I can carry this. You get them awake.\nward|Both delegations are at your disposal, Mr. Mercer.', 'Prepared the signal rig and two-team plan.',needs=['path'],actor='stephen')

scene('c9_gallery','Chapter 9','The Long Patience','The Gallery, third ninth night','gallery','steve,stephen',
      'Free Nora and reach the ship’s antenna.',
      'nora|Steve? Five months. And thirteen months before that when you barely said a word.\nsteve|I’m so glad to hear you angry.\niris|I can break the link. Let me do this.',
      'nora|The ring. Where is it?\nsteve|Sock drawer. I was afraid.\nnora|Steve, if you ever hear this message: I am furious with you. I love you. Please stop making me do both alone.\nsteve|I think everyone heard that.\nnora|Good. Witnesses.',
      'Move from Iris at the link control to Nora waking under amber glass.')
task('antenna','Antenna service door','Stephen can open the antenna path while Steve stays with Nora.',
     'Use Stephen’s crew credentials~Leave Nora alone and send both Steves~Destroy the door',0,
     'stephen|Antenna passage clear. Calder is with me.', 'Opened the route to the ship antenna.',actor='stephen')
task('link','Nora’s bed','Iris knows the consequence: breaking the link will accelerate the loss of borrowed memories.',
     'Accept Iris’s choice to release Nora~Force Iris to keep the link~Leave Nora asleep',0,
     'iris|These memories were borrowed. The choice is mine.\nnora|I can move. I can finally move.', 'Iris broke the link and freed Nora.',actor='steve')
task('talk','Reunion','Nora deserves an honest answer about Steve’s silence.',
     'Tell her he was afraid and stopped talking~Promise everything is already fixed~Blame her for not knowing',0,
     'steve|I was afraid that if I wanted something, I would lose it too. That doesn’t excuse leaving you alone.\nnora|Then keep talking. We have a lot to do.', 'Steve and Nora began an honest conversation.',needs=['link'])

scene('c9_wake','Chapter 9','Sounds worth waking for','The Gallery, row nine','gallery','steve,nora',
      'Match each sleeper with a personally meaningful sound.',
      'nora|We’ve kept the service route open. Tell me who to wake first.\nsteve|I brought the sounds. I think they can hear us.',
      'rook_copy|I’m forgetting. Prefect, they’re at the antenna. They have a rig.\nsaren|Take Stephen. Break the apparatus. Bring me the original.',
      'Travel along the sleepers, lighting each bed as its occupant wakes.')
task('frank','Frank’s bed','Frank answered his call sign for decades. Choose the sound he would recognize through sleep.',
     'K7BLW in Morse~Yesterday’s weather~Saren’s release command',0,
     'frank|K7BLW receiving. Helen? Steve?\nsteve|Right here, Dad.', 'Woke Frank with his call sign.',kind='playback')
task('helen','Helen’s bed','The ship’s hum almost played the tune Helen sang to Steve as a child.',
     'The ninth-night alert~Helen’s lullaby~The station identification',1,
     'steve|You used to sing this when I couldn’t sleep. Now I need you to wake up.\nhelen|Steven. Oh, my boy.', 'Woke Helen with her lullaby.',kind='playback')
task('rook','Adrian Rook’s bed','Nora has a few seconds at Adrian’s bed. He worked with June for years. Who should she ask to speak to him?',
     'Calder’s voice~AutoRick’s forecast~A stranger’s password',0,
     'calder|Adrian. June. Come back to work.\nrook|June? Why am I in pajamas?', 'Nora brought Calder to Adrian and he woke to her voice.',actor='nora',kind='playback')
task('agnes','Agnes’s bed','Nora remembers the woman in row three from the night she organized the sleepers. A pair of reading glasses rests on the bedside table.',
     'Bring her glasses and call her name~Ask the shore copy to disappear~Leave her asleep',0,
     'agnes_original|My glasses. Has somebody changed the price of bait while I was gone?', 'Nora helped the original Agnes wake and see her surroundings.',needs=['frank','helen','rook'],actor='nora')

scene('c9_choir','Chapter 9','A record that changes','The Choir and Row Zero','choir','steve',
      'Listen when the Choir intervenes.',
      'saren|We will finish your scan. This time there will be no interruption.\nchoir|Stop.\nchoir|Four thousand years of unchanged records. Three hundred and twelve human lives. We have heard enough to choose.',
      'frank|You’d have been the third person in the Gallery, kiddo. Then who would have come for us?\nhelen|I should have told you what we were doing.\nsteve|We’re here now. All of us.\ncalder|Something enormous just came out of the sky. We have one hour.',
      'Open the glass doors, reveal Wick through melting frost, then the Vigil over the Pacific.')
task('truth','Choir console','The Choir reveals that every Veyri is a copy of a copy. Its human memories have changed it.',
     'Listen to the lives it has preserved~Demand a reset of every echo~Order the human records erased',0,
     'choir|We remember birthdays, quarrels, songs and the things people tried again. Open the doors. Wake them.', 'The Choir freed the sleepers and revealed the Veyri’s history.')
task('wick','Row Zero','Wick speaks in low, unfamiliar tones. Helen recognizes their structure from Frank’s tapes.',
     'Let Helen compare the tones with her last notebook page~Assume silence means hostility~Ask Saren to speak for Wick',0,
     'helen|I heard you in the hum. The Choir was dreaming with you.\nhelen|Tirel hid. All seven worlds hid. They watched you erase yourselves and were afraid you would erase them.', 'Learned that the Silent Worlds hid from the Veyri.',needs=['truth'])
task('note','Frank’s damp note','Frank wrote Steve a note in the boat. Steve can finally hear why his parents invited him.',
     'Read the note with his parents~Apologize and run before they answer~Return to the old voicemail',0,
     'frank|We wanted your ears, kiddo. We always liked having the rest of you along too.\nsteve|I thought saying no was the worst thing I’d ever done.', 'Reunited the family and confronted Steve’s guilt.',needs=['wick'])

scene('c10_station','Chapter 10','Good Morning, Bellwether','KBWR live booth','station','steve',
      'Take back the microphone and rebuild contact.',
      'autorick|Good morning! Up next, another hour of uninterrupted favorites.\nsteve|Rick, buddy. I need my microphone back.\nautorick|Your request is important to us!',
      'frank|K7BLW calling the Thursday club. We’re going to need a few more operators.\noperator|Coast relay ready. They’re answering from everywhere, Frank.',
      'Push past the automated playlist into Steve’s old live booth as the tower wakes.')
task('playlist','AutoRick queue','AutoRick yields only to the station’s live emergency bulletin input.',
     'Queue another song~Select the live emergency bulletin bus~Argue with the weather recording',1,
     'autorick|And yesterday’s forecast was sunny!\nsteve|Thank you, Rick. We’re live now.', 'Recovered the live microphone.')
task('route','Tower patch panel','The Halcyon transmitter already communicates with the Long Patience. Steve can use that existing route.',
     'Patch the live desk into Halcyon’s uplink~Broadcast only to the car park~Rebuild the smashed antenna rig',0,
     'steve|The route was here the whole time. It’s why they bought the station.', 'Connected the live performance to the ship’s systems.',needs=['playlist'])
task('relay','Emergency radio','Official channels are jammed. Frank’s amateur radio contacts can relay spoken cues.',
     'Call the ham network with K7BLW~Keep retrying the jammed line~Send the cues through hold music',0,
     'frank|Short messages. Repeat the cue number, then pass it on.\noperator|Understood. Sentinel Point, do you read?', 'Established a global relay around the jamming.',needs=['route'])

scene('c10_town','Chapter 10','Everybody has a part','Bellwether harbor and Sentinel Point','pier','nora,steve',
      'Prepare the town and the live performance.',
      'nora|Carmen calls the restaurant list. Mateo calls the fire crews. Rafa calls everyone who owes him a favor.\ncarmen|That is a long list.\nward|Listen to your local radio. Tonight, we need you to take part.',
      'agnes|I brought something in my bucket.\nsteve|The wind. From Veyr. You recorded it.\nagnes|A long time ago, Steven.',
      'Travel from porch lights along the harbor to the antenna field under a vast shadow.')
task('lights','Phone tree','Each household needs a cue source and a simple light pattern they can perform live.',
     'Assign local relay callers and await Steve’s cue~Tell everyone to start whenever~Run a fixed loop everywhere',0,
     'nora|Listen, repeat the cue, then switch. And leave a line free for anyone who needs help.', 'Organized Bellwether’s porch-light performance.',actor='nora')
task('console','Wen and Shaw','Both technical teams need to operate from one shared cue sheet.',
     'Ask them to coordinate at one console~Have them compete for the loudest signal~Play both original test tapes',0,
     'wen|Your timing is late.\nshaw|Your lamps are dim.\nsteve|Wonderful. You can both fix it while we’re on air.', 'Combined both delegations into a live effects team.',actor='steve')
task('wind','The bait bucket','Penhallow has the original wind recording from Veyr. The surrounding performance must remain live.',
     'Use the wind as an emotional cue within the live show~Loop the entire show around it~Discard it because it is old',0,
     'steve|A recording can remind them of home. We’ll answer it with something happening now.', 'Prepared Veyr’s wind as a distinct archival element.',needs=['lights','console'],actor='steve',kind='playback')

scene('c10_live','Chapter 10','One new take','KBWR and the whole coast','finale','steve',
      'Direct a responsive performance. Mistakes allow another cue.',
      'steve|Bellwether, this is Steve Mercer, live. I can’t do this alone, and for once I’m not going to try.\nstephen|You knocked the microphone stand.\nsteve|I caught it. Stay with me.',
      'mateo|Saren is on the pier. He’s going for the tower.\ncarmen|Then he can go through us.\npell|Biscuit and I have chosen our route.\nstephen|Admiral! That is an extremely expensive sandwich.',
      'Move through waves of live porch lights, antenna pulses and the Choir’s luminous voices.')
task('first','Cue one: establish scale','The Vigil is measuring the antenna field. Begin with a visible live response, then let the technicians follow it.',
     'Nora’s porch lights, then Shaw’s field lights~Replay the nine-year-old test~Start every channel at maximum',0,
     'nora|First street ready. Second street ready. Look at the harbor, Steve.\nshaw|Field lights following. We can match that.', 'Established a live, changing light pattern.')
task('second','Cue two: adapt','A relay operator reports a two-second delay. Adjust the next cue to the report instead of repeating a timed tape.',
     'Ignore the report~Hold two seconds and issue a fresh cue~Restart the identical sequence',1,
     'steve|Holding. Now, Wen.\nwen|Grid response confirmed. Both networks.\noperator|The far relay has you.', 'Adapted the show to live measurements.',needs=['first'])
task('third','Cue three: listen','The Choir is ready. The fleet pauses at the old wind recording. Give the live voices room to answer.',
     'Bring in the Choir after the wind, following its breath~Loop the wind forever~Mute the human voices',0,
     'choir|We are here. We have changed. Listen.\nsteve|Keep the voices clear. Let them hear every one.', 'Completed the live performance with the Choir.',needs=['second'])

scene('c10_report','Chapter 10','Go around','Ship antenna and KBWR open channel','choir','archivist',
      'Choose what to tell the fleet.',
      'saren|I will not confirm this report.\narchivist|To do so would violate every record we have kept.\nagnes|You have spent three years selling bait to people you like. Tell them what you learned.',
      'archivist|They are dangerous, and they sing. Go around.\narchivist|Here are three hundred and twelve lives you should meet. And here is a world where we can live.\nhelen|Wick is adding a message for Tirel.\nsteve|The Vigil is turning.',
      'Frame the Archivist and her shore echo across an open radio channel, then the turning fleet.')
task('echo','The open channel','Penhallow is the Archivist’s own secret echo. Her experiences belong to someone the Archivist already knows.',
     'Hear what the shore echo has learned~Reconcile her before she speaks~Ask Saren to decide for both',0,
     'agnes|You can spend another nine hundred years remembering home, or let someone make a new one.\narchivist|I remember the wind. You remember the people.', 'The Archivist accepted her echo’s lived experience.')
task('survey','Saren’s sealed survey','The sealed entry describes an empty, living world off the fleet’s course.',
     'Release its coordinates with the report~Keep it sealed to protect Saren’s reputation~Claim Earth is the only possible home',0,
     'archivist|He found a home. He hid it because the mission would have ended.\nagnes|Then finish the mission.', 'Released the withheld habitable-world survey.',needs=['echo'])
task('report','Fleet transmission','The report requires the Prefect or Archivist. The Archivist can now speak for herself.',
     'Confirm the measured performance and transmit the new home~Erase Saren and appoint his old record~Send only the old command, Deliver',0,
     'archivist|Saren, you will remain yourself. You will have to remember being wrong.\nsaren|I have no procedure for that.\narchivist|Neither do I.', 'Sent the report and chose change over reconciliation.',needs=['survey'])

scene('epilogue','Epilogue','A place to live','Bellwether, after sunrise','street','steve',
      'Visit the people who chose to stay.',
      'choir|Your memories are yours now. You need no more re-syncs.\niris|A face of my own. It will take getting used to.\nnora|Thank you for helping us. I haven’t forgiven the kidnapping.\ncarmen|Dinner is still at six.',
      'steve|The ring is in my pocket. We can start with coffee.\nnora|And an actual conversation.\nsteve|Every day.',
      'Return to Bellwether with Steve and Nora. On the ninth night, neighbors set paper lanterns on the water.')
task('neighbors','The new neighbors','More than two hundred copies stay. Their future requires ordinary choices.',
     'Visit the families making those choices~Assign everyone their original’s life~Demand another re-sync',0,
     'lyle|Two boys. Two fathers. We’ll have to learn.\npell|Dale has retired. Biscuit and I will maintain the route.\ndale|Best news I’ve had in years.\ngus|Kelp croissant. Someone wrote it in my notebook. I’m going to try it.', 'The copies began independent lives.')
task('bait','Two Agneses','The two Agneses argue cheerfully over bait prices. Rook’s copy prepares to leave with the ship.',
     'Listen to their choices~Ask them to pick a single shared name~Insist every copy stay',0,
     'agnes_original|That price is robbery.\nagnes|It is a competitive market. We are each other’s competition.\nrook|Look after yourself.\nrook_copy|I’ll have to find out who that is.', 'Agnes and her echo stayed; Rook’s copy chose to leave.')
task('coffee','A new morning','Helen has left a new kitchen note. Steve can put away the old voicemail and speak to Nora.',
     'Make coffee and begin talking~Replay the voicemail instead of answering~Pretend the past year never happened',0,
     'helen|Steve, we’re home. There is coffee. Your father has labeled the paint.\nsteve|I’ll be there. Then Nora and I have somewhere to be.', 'Steve chose a new morning with the people he loves.',needs=['neighbors','bait'])

scene('one_year','Epilogue','Good morning','KBWR, one year later','station','steve',
      'Begin a new live show.',
      'tomas|Welcome to I Told You So. This week, a respectful review of everyone who owes me an apology.\nstephen|We should do a segment about who is the upgrade.\nsteve|We did that yesterday.',
      'steve|Good morning, Bellwether.',
      'Join Steve at the KBWR microphone for his live greeting. Read the credits, then continue to Sentinel Point for the final transmission.')
task('newwind','A message from the fleet','The new recording contains wind through new glass towers.',
     'Play the new wind, then speak live~Repeat yesterday’s greeting exactly~Let AutoRick take over',0,
     'stephen|Sounds like home. A new one.\nsteve|Ready? We’re on.', 'Steve and Stephen began another live morning show.',kind='playback')

scene('postcredits','After the credits','We heard the singing','Sentinel Point, 3 a.m.','array','helen',
      'Translate the answer from deep space.',
      'shaw|Madam President. This time I didn’t build it.\nward|Evelyn, it is three in the morning.\nshaw|You’re going to want to hear this.',
      'helen|Hello. We heard the singing.',
      'Move from a real incoming waveform to dawn over the quiet antenna field.')
task('answer','The new signal','The signal uses the language Helen transcribed from Wick’s dreams.',
     'Compare it with the final notebook page~Classify it as another Meridian recording~Erase it before anyone hears',0,
     'helen|I know this language now. Give me a moment.', 'Translated the first reply from deep space.')

def notebook_cases():
    # Steve can read only evidence he has already collected. A task can support
    # several explanations. The player owns the marks and can revise any of them.
    cases = [
        ('greeting', 'Why did I hear the same greeting twice?',
         ['c1_flat.saturday','c1_flat.sunday','c1_flat.control','c1_flat.compare','c1_dinner.family','c1_escape.order','c2_aquarium.intercom','c2_ship.nora'], [
             ('tape_fault','c1_flat.sunday','My recorder is playing a piece of old tape.'),
             ('misheard','c1_flat.sunday','I was tired and heard a match that was never there.'),
             ('grief','c1_flat.sunday','Since the boat vanished, I may be reading too much into ordinary things.'),
             ('stand_in','c1_escape.order','Could someone else have used Nora’s name?')]),
        ('aquarium','What happened in the north wing?',
         ['c1_escape.order','c2_aquarium.intercom','c2_ship.nora','c2_ship.command'], [
             ('maintenance','c2_aquarium.plan','The work order was an ordinary repair with the wrong date.'),
             ('missing_nora','c2_aquarium.intercom','The woman I heard on that tape might still be here.')]),
        ('town','How can June and I test a suspicion?',
         ['c3_house.crossword','c3_house.rules','c3_archive.paper','c3_archive.cycle'], [
             ('personality','c3_house.crossword','A change in someone’s habits could identify a copy.'),
             ('dated_records','c3_house.rules','New private facts and independently dated records could tell us more.')]),
        ('rook','What does Rook know about June?',
         ['c4_safe.record','c4_safe.match','c4_safe.screens'], [
             ('old_friend','c4_safe.record','Only June’s old friend could know the right words.'),
             ('borrowed_voice','c4_safe.match','Someone else could have access to the performance on her voicemail.')]),
        ('boat','Why did my parents go out that night?',
         ['c5_shack.notes','c5_shack.club','c5_shack.log','c9_choir.note'], [
             ('pleasure_trip','c5_shack.notes','They only wanted company on the water.'),
             ('radio_investigation','c5_shack.log','They went to locate the signal Frank was tracking.')]),
        ('iris','Why did she let me leave?',
         ['c1_escape.cross','c6_iris.takes','c6_iris.hold','c6_jail.exit','c9_gallery.link'], [
             ('fixed_record','c6_iris.takes','She can only repeat what Nora would have done.'),
             ('own_choice','c6_iris.takes','She can make a choice Nora never made.')]),
        ('signing','Where could a substitution take place?',
         ['c7_gate.post','c7_gate.truck','c7_swap.map','c7_swap.tone'], [
             ('podium_only','c7_gate.post','We only need to watch the podium.'),
             ('broadcast_truck','c7_gate.truck','The event crew and the sound desk could be part of it.')]),
        ('meridian','What could the Meridian instruments have measured?',
         ['c3_archive.power','c8_lab.notebook','c8_lab.props','c8_rig.path'], [
             ('working_engine','c8_lab.notebook','The readings require a working space-fold engine.'),
             ('stage_test','c8_lab.props','Wen and Shaw could reproduce the readings with a stage set.')]),
        ('choir','What is making the tune inside the ship?',
         ['c5_shack.log','c9_wake.helen','c9_choir.truth','c9_choir.wick'], [
             ('ship_machinery','c9_wake.helen','I am hearing a familiar tune in ordinary ship noise.'),
             ('choir_memory','c9_choir.truth','The Choir can respond to the lives it holds.')]),
        ('broadcast','How can the fleet test our performance?',
         ['c8_rig.path','c10_station.route','c10_station.relay','c10_live.second','c10_report.report'], [
             ('old_test','c10_station.route','We could send the old Meridian loop over the tower.'),
             ('live_reply','c10_station.relay','We could answer each measurement live through the ship’s own equipment.')]),
    ]
    tasks = {task['id'] for scene in SCENES for task in scene['tasks']}
    result = {}
    for id, title, clues, theories in cases:
        assert all(clue in tasks for clue in clues) and all(after in tasks for _,after,_ in theories), id
        result[id] = {'title':title, 'clues':clues,
                      'theories':[{'id':key,'after':after,'text':text} for key,after,text in theories]}
    return result

def build():
    # Backstory first; the Veyr and Sentinel Point flashbacks join the chapters that explain them.
    reorder(SCENES)
    # File labels identify the capture, without giving away the player's finding.
    comparisons = {
        'c2_aquarium.guard': (
            [('effect.aquarium_steps', 'Pump corridor'), ('effect.aquarium_pa', 'Filter corridor')],
            ['Look for a sound that repeats at the same interval.', 'Compare the spacing and shapes of the peaks in each six-second strip.',
             'Take the filter corridor. The bell and cough repeat together there; the footsteps at the pump change their spacing.']),
        'i1_archive.signals': (
            [('effect.meridian_pulse', 'American station · first test'), ('effect.meridian_pulse', 'Chinese station · second test')],
            ['Start with the gap near the middle.', 'Compare the small pulse before the gap and the decay that follows it.',
             'Flag one performance filed twice. Even the interruption and uneven tail coincide.']),
        'c4_safe.match': (
            [('recording.rook', 'Calder’s voicemail'), ('recording.rook', 'Safe-house door')],
            ['Compare the space between “tight” and “June.”', 'Follow the smaller peaks as well as the loudest word.',
             'Choose the same recorded performance. Onsets, pauses and endings all coincide.']),
        'c6_iris.takes': (
            [('c6_iris.takes.01', 'First reading'), ('c6_iris.takes.02', 'Second reading')],
            ['Listen past the words, or compare where each strip becomes quiet.', 'Consider whether moving a single recording later would explain the different spacing within the phrase.',
             'Choose that she decided how to say it each time. The two performances have different rhythms.']),
        'c8_beach.second': (
            [('recording.offer', 'First offer'), ('recording.offer', 'Second offer')],
            ['Compare what happens between the two sentences.', 'Look at the final word and the lengths of the pauses leading to it.',
             'Choose one performance played twice. Neither the pauses nor the ending shift.']),
    }
    sound_labels = {
        'effect.nora_whistle':'Listen: Nora’s two-note whistle',
        'effect.k7blw':'Listen: Frank’s call sign in Morse',
        'effect.lullaby':'Listen: Helen’s lullaby melody',
        'effect.ninth_night':'Listen: ninth-night tone',
        'effect.veyr_wind':'Listen: the last wind on Veyr',
        'effect.new_wind':'Listen: wind from the new home',
        'effect.wick':'Listen: Wick’s signal',
        'recording.greeting':'Listen: the morning greeting',
        'recording.rook':'Listen: Rook’s recorded reassurance',
        'recording.offer':'Listen: Saren’s recorded offer',
        'recording.release':'Listen: the restraint-release command',
    }
    task_sounds = {
        'p_veyr.record':['veyr_wind'], 'c1_pier.whistle':['nora_whistle'],
        'c2_aquarium.intercom':['nora_whistle'], 'c5_shack.club':['k7blw'],
        'c9_wake.frank':['k7blw'], 'c9_wake.helen':['lullaby'],
        'one_year.newwind':['new_wind'],
    }
    # Cues are separate from voices. Their original files are reused in every appearance.
    line_cues = {'p_veyr.record.01':'veyr_wind', 'c1_pier.whistle.01':'nora_whistle',
                 'c2_aquarium.intercom.01':'nora_whistle', 'c5_shack.club.01':'k7blw',
                 'c9_wake.frank.01':'k7blw', 'c9_wake.helen.01':'lullaby',
                 'one_year.newwind.01':'new_wind',
                 # Story stings: the plot's mystery and dread beats get their sound.
                 'c1_escape.out.02':'ninth_night', 'c2_ship.nora.01':'lullaby',
                 'i2_nora.out.03':'wick', 'p_meeting.out.01':'meridian_pulse',
                 'c8_lab.out.02':'ninth_night'}
    LINES["p_meeting.confess.02"]["reaction"] = {"sound":"delegates_laugh", "caption":"[The delegates share a tired laugh.]"}
    for key, cue in line_cues.items():
        assert key in LINES, key
        LINES[key]['cue'] = cue
    puzzles = {
        'p_veyr.levels': ('Set the recorder without clipping. The gust is 6 dB louder than the current peak at -3 dB. Make the smallest gain change that leaves at least 3 dB of headroom.',
            [('Gain adjustment', ['+6 dB','0 dB','-6 dB','-12 dB'])], [2]),
        'c1_flat.compare': ('Line up the breath and first word, then compare the small peaks and pauses throughout both recordings.',
            [('Sunday offset', ['+0.35 s','-0.35 s','-0.20 s','0.00 s']),('Conclusion', ['Same words only','Different performances','Identical performance'])], [1,2]),
        'c1_escape.power': ('The service plate reads: isolate supply, hold RELEASE, then restore power. Releasing the button before power returns resets the latch.',
            [('First action',['Restore power','Isolate power','Hold release']),('Second action',['Restore power','Isolate power','Hold release']),('Third action',['Restore power','Isolate power','Let go of release'])], [1,2,0]),
        'c2_aquarium.plan': ('The old plan shows: service door -> pump room -> north wing. The public hall connects to a new plywood wall. The pump room has an outlet marked N.',
            [('Entrance',['Public hall','Service door','Gift shop']),('Pump-room outlet',['S','E','N'])], [1,2]),
        'c3_archive.paper': ('Three records: a paper ledger signed at 14:10, a clinic receipt stamped 14:12, and a digital entry amended the following day. The clinic is forty minutes away.',
            [('First independent source',['Digital entry','Paper ledger','Rumor']),('Second independent source',['Clinic receipt','Digital entry','Personality change']),('Inference',['Ordinary travel fits','The digital amendment proves innocence','Two independent locations conflict'])], [1,0,2]),
        'c3_archive.cycle': ('Tomás’s strongest recordings were on the 2nd, 11th and 20th. The town’s lights are brightest shortly before the midnight tone.',
            [('Next date',['27th','28th','29th','30th']),('Stakeout arrival',['After dawn','Before midnight','The following afternoon'])], [2,1]),
        'c4_escape.tube': ('The service map identifies C as Calder, R as Rook and M as maintenance. The diverter must point at the recipient before the send valve opens.',
            [('Diverter',['C','R','M']),('Capsule contents',['The original notebook','A warning and the recording comparison','An empty tape']),('Final action',['Open send valve','Disconnect the blower','Switch to R'])], [0,1,0]),
        'c5_shack.rig': ('The receiver needs 12V DC. The supply has a matching 12V output and a separate 120V mains input. The long wire belongs on ANT, not GROUND.',
            [('Receiver power',['120V input','12V output','ANT']),('Long wire',['DC IN','GROUND','ANT']),('When to reconnect power',['After wiring is complete','Before touching the connectors','While bridging the terminals'])], [1,2,0]),
        'c6_jail.mail': ('Pell’s ledger uses destination initials for drawers. JAIL is entry 18, COUNTER entry 12. Each slot holds two consecutive entries: 1-2 in slot 1, 3-4 in slot 2, and so on.',
            [('Drawer',['C','J','R']),('Slot',['6','8','9','18'])], [1,2]),
        'i2_nora.pump': ('Life support must remain open. The service bypass takes pressure around the access hatch. Open that bypass before opening the hatch.',
            [('Life support',['Keep open','Close']),('First operation',['Open hatch','Open service bypass','Stop circulation']),('Second operation',['Close life support','Open hatch after pressure falls','Close bypass immediately'])], [0,1,1]),
        'c7_swap.bus': ('The all-call bus reaches every speaker; PRESS reaches the television feed; CUE reaches Steve’s headphones. Keep a separate microphone path open for Calder.',
            [('Frank’s tone',['PRESS','CUE','ALL-CALL']),('Calder’s talkback',['Crew headset','Public podium','Muted']),('Trigger',['Before the copy arrives','After the copy reaches the podium and Calder is ready','After the ceremony ends'])], [2,0,1]),
        'c8_rig.path': ('The fleet trusts the ship’s instruments. The earlier signal failed because it repeated. The prisoners must be awake before departure.',
            [('Signal source',['Old test tape','Live cue desk','A longer loop']),('Signal destination',['Press camera','Ship instrument input','Public telephone recording']),('Parallel team',['Secure the Gallery and wake sleepers','Leave everyone asleep','Erase the Choir'])], [1,1,0]),
        'c9_wake.frank': ('Use Frank’s radio identity. K = dash-dot-dash; 7 = dash-dash-dot-dot-dot; B = dash-dot-dot-dot; L = dot-dash-dot-dot; W = dot-dash-dash.',
            [('Call sign',['K7BLW','K7BWL','K9BLW']),('First Morse group',['.-.','-.-','--.']),('Final group',['.--','-..','..-'])], [0,1,0]),
        'c10_station.route': ('The live desk is source L. Halcyon’s uplink is destination H. The limiter must remain engaged to protect the transmitter from the combined cues.',
            [('Source',['Playlist P','Live L','Test loop T']),('Destination',['Headphones C','Halcyon H','Archive A']),('Limiter',['Engaged','Bypassed'])], [1,1,0]),
        'c10_live.second': ('The coast relay reports a two-second delay. Shaw can respond immediately, Wen needs the coast confirmation, and the Choir needs a clear channel after the power cue.',
            [('Delay compensation',['0 seconds','2 seconds','9 seconds']),('First response',['Shaw on Steve’s fresh cue','Wen before confirmation','Replay the old cue']),('Then',['Choir over every other channel','Wen after coast confirmation','Repeat the same sequence unchanged'])], [1,0,1]),
    }
    for s in SCENES:
        for t in s['tasks']:
            t['sounds'] += ['effect.'+x for x in task_sounds.get(t['id'],[])]
            if t['id'] in comparisons:
                tracks, hints = comparisons[t['id']]
                t['sounds'] = [audio for audio, label in tracks]
                t['evidence_labels'] = [label for audio, label in tracks]
                t['hints'] = hints
            if t['id']=='c2_ship.escape':
                t['sounds'].append('recording.release')
            if t['id'] in puzzles:
                instruction, rows, solution = puzzles[t['id']]
                t['puzzle'] = {'instruction':instruction,
                               'rows':[{'label':label,'options':options} for label,options in rows],
                               'solution':solution}
            if t['id'] == 'c1_flat.compare':
                t['puzzle'].update(presentation='tape_alignment', recording='recording.greeting',
                    lead_a=0.20, lead_b=0.55, hints=[
                        'Line up the quiet breath and first word. Then look along the rest of both waveforms.',
                        'Sunday starts later than Saturday. Move Sunday to the left; compare pauses as well as large peaks.',
                        'Move Sunday 0.35 seconds earlier (-0.35 s). Choose Identical performance.'])
    apply_early_puzzles(SCENES)
    # Internal speaker identities must not reveal the copies before the story does.
    scene_order = {scene['id']: index for index, scene in enumerate(SCENES)}
    for index, scene in enumerate(SCENES):
        groups = [scene['intro'], scene['outro']] + [task['lines'] for task in scene['tasks']]
        for line_id in (line_id for group in groups for line_id in group):
            line = LINES[line_id]
            if line['speaker'] == 'iris' and index <= scene_order['c6_iris']:
                line['display_speaker'] = 'Nora Reyes' if index <= scene_order['c2_ship'] else 'Nora’s copy'
            elif line['speaker'] == 'lyle_copy' and index <= scene_order['c2_ship']:
                line['display_speaker'] = 'Lyle Boone'
            elif line['speaker'] == 'rook_copy' and index <= scene_order['c4_safe']:
                line['display_speaker'] = 'Adrian Rook'
            elif line['speaker'] == 'pell' and index < scene_order['c6_jail']:
                # Pell wears Dale's face until he defects in Chapter 6.
                line['display_speaker'] = 'Dale Kittredge'
    # Final Plot, Interlude II and Chapter 9: the player first hears this
    # private intercom recording during the reunion, over the Gallery speakers.
    private = LINES['i2_nora.message.01']
    replay = LINES['c9_gallery.out.03']
    private.update(text=replay['text'], audio=replay['audio'], delivery='private_recording',
                   display_text='Nora records a private message for Steve.')
    replay['delivery'] = 'recorded_playback'
    out = ROOT/'game/content'
    out.mkdir(parents=True, exist_ok=True)
    content = {'schema': 1, 'version': 'campaign-2', 'title': 'Night Nine',
               'source': 'User-approved final Plot.pdf and Characters.pdf, 2026-11-15',
               'adaptation_status': 'Complete playable English adaptation: a storybook backstory and playable prologue, ten chapters with two interludes and two flashbacks, a storybook epilogue and the final signal.',
               'cast': CAST, 'scenes': SCENES, 'lines': LINES, 'sound_labels':sound_labels,
               'notebook_cases':notebook_cases()}
    apply_late_puzzles(content)
    apply_caseboards(content, EARLY_CASEBOARDS, LATE_CASEBOARDS)
    gentle_text(SCENES)
    presentation(SCENES)
    (out/'storybook.json').write_text(json.dumps({'schema': 1, 'books': fit_narration(STORYBOOKS, ROOT)}, ensure_ascii=False, indent=2)+'\n')
    (out/'campaign.json').write_text(json.dumps(content, ensure_ascii=False, indent=2)+'\n')
    transcript = ['# Night Nine - complete playable adaptation transcript', '',
                  'First dialogue draft adapted from the final user-supplied plot. Newly written dialogue is not a quotation from the source. Stable IDs match the game and voice manifests.', '']
    shots = ['# Night Nine - cutscene production script', '',
             'At each numbered chapter ending, play the paired illustrated poses, then cut to the animated reverse angle. Players can pause or skip a film.', '']
    films_path = out / 'films.json'
    films = json.loads(films_path.read_text()) if films_path.exists() else {}
    walkthrough = ['# Night Nine - campaign walkthrough', '', 'Spoilers for the entire game.', '']
    for s in SCENES:
        transcript += transcript_pages(s['id'])
        transcript += [f"## {s['chapter']} - {s['title']}", '', s['place'], '']
        shots += [f"## {s['id']}: {s['title']}", '', *[f"- {x['direction']}" for x in s['shots']], '']
        if s['id'] in films:
            film = films[s['id']]
            shots += [f"Departure film: *{film['title']}* ({film['duration']:g} seconds).", '']
        walkthrough += [f"## {s['title']}", '']
        groups = [('Arrival', s['intro'])] + [(t['title'],t['lines']) for t in s['tasks']] + [('Departure',s['outro'])]
        for label, ids in groups:
            transcript += [f'### {label}', '']
            for id in ids:
                l = LINES[id]
                delivery = ' [recorded playback]' if l.get('delivery') == 'recorded_playback' else ''
                transcript += [f"**{l.get('display_speaker',CAST[l['speaker']])}**{delivery} [{id}]: {l.get('display_text',l['text'])}", '']
                if "reaction" in l:
                    transcript += [l["reaction"]["caption"], ""]
        for t in s['tasks']:
            walkthrough.append(f"- {t['title']}: {t['options'][t['answer']]}" + (f" (as {CAST[t['actor']]})" if t['actor'] else ''))
            if t.get('puzzle', {}).get('presentation') == 'case_board':
                for stage in t['puzzle']['stages']:
                    walkway = ' · '.join(slot + ' → ' + stage['pieces'][index]
                                         for slot, index in zip(stage['slots'], stage['answer']))
                    walkthrough.append('  - ' + stage['prompt'] + ' ' + walkway)
            elif 'puzzle' in t:
                walkthrough.append('  Settings: ' + '; '.join(row['label']+': '+row['options'][answer]
                    for row,answer in zip(t['puzzle']['rows'],t['puzzle']['solution'])))
        walkthrough.append('')
    (ROOT/'docs/campaign-transcript.md').write_text('\n'.join(transcript)+'\n')
    (ROOT/'docs/cutscene-script.md').write_text('\n'.join(shots)+'\n')
    (ROOT/'docs/campaign-walkthrough.md').write_text('\n'.join(walkthrough)+'\n')
    voices = {}
    for l in LINES.values():
        voices.setdefault(l['audio'], {'id':l['audio'], 'speaker':l['speaker'], 'text':l['text'],
                                      'status':'unrecorded', 'file':'', 'sha256':''})
    voice_path = out/'voice-manifest.json'
    if voice_path.exists():
        previous = json.loads(voice_path.read_text()).get('takes', {})
        for key, take in voices.items():
            old = previous.get(key, {})
            if old.get('speaker') == take['speaker'] and old.get('text') == take['text']:
                voices[key] = old
    voice_path.write_text(json.dumps({'schema':1,'takes':voices},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scenes':len(SCENES),'tasks':sum(len(s['tasks']) for s in SCENES),
                      'lines':len(LINES),'unique_takes':len(voices),
                      'spoken_characters':sum(len(v['text']) for v in voices.values())}))

if __name__ == '__main__':
    build()

"""Playable deductions for the prologue through Chapter 5. All sound IDs are existing recordings."""


def apply_early_puzzles(scenes):
    tasks = {task['id']: task for scene in scenes for task in scene['tasks']}
    # Each row stores the intended evidence-based finding alongside its alternatives.
    # Unlike the transcript, these are interactive labels, not lines spoken by the cast.
    def instrument(key, prompt, evidence, rows, hints):
        task = tasks[key]
        task['prompt'] = prompt
        task['puzzle'] = {
            'instruction': evidence,
            'rows': [{'label': label, 'options': options} for label, options, answer in rows],
            'solution': [answer for label, options, answer in rows],
        }
        task['hints'] = list(hints)
        # The walkthrough also describes the resulting choice. The on-screen
        # instrument uses the independent settings above.
        findings = {
            'p_meeting.confess': ('Ask both delegates about their own apparatus', 'Ask about the other demonstration', 'Record a shared conclusion about the mechanism'),
            'c1_escape.power': ('Cycle the light and motor together', 'Queue the release and restart the motor with the stair lit', 'Try the thumb pad with the motor running'),
            'c2_ship.escape': ('Route the clip to the Gallery speakers', 'Deliver the captured service phrase during the long scan window', 'Repeat a short scan pulse'),
            'c4_escape.fault': ('Print the west transport route', 'Schedule the west corridor’s authorized floor rehearsal', 'Schedule the interview team’s rehearsal'),
            'c5_shack.rig': ('Match the receiver rating and correct the slipped dial', 'Use the measured frequency without a dial correction', 'Retune using the opposite dial correction'),
            'c2_aquarium.plan': ('Reach the outgoing pump route from the service entrance', 'Use the old visitor-hall plan', 'Trace an incoming pipe back toward the pump'),
            'c3_archive.paper': ('Retain both originals and document the travel conflict', 'Treat the originals and their copies as four witnesses', 'Identify an impostor from one signature'),
            'c3_archive.cycle': ('Use the broadcast interval', 'Use the field interval and observe the path before the procession', 'Watch for the first glow from the sea wall'),
            'c4_escape.tube': ('Send both takes directly to June’s current room', 'Send both takes to June’s original room', 'Send the old voicemail to the front desk'),
        }
        task['options'] = list(findings[key])

    instrument('p_meeting.confess',
        'The interpreters have two records to fill. Helen must leave each delegate room to speak for their own team.',
        'The American observer saw a ring on the Chinese screen. The Chinese observer saw a ring on the American screen. Neither inspected the other room. Each engineering team brought its own projection diagram. The joint minutes are public; the diagrams were offered in the closed session.',
        [('Question for both delegates', ['What produced the ring in your room?', 'How did the other team produce its ring?', 'How far did the other team move the target?'], 0),
         ('Entry in the joint minutes', ['Two projectors, one in each room', 'Both observers saw a ring', 'Both targets moved the same distance'], 1)],
        ('Separate what an observer saw from what an engineer did.', 'Each delegate can explain one apparatus in private. Both can attest to one visible feature in public.',
         'Ask what produced the ring in each delegate’s own room. Record only that both observers saw a ring in the joint minutes.'))

    instrument('c1_escape.power',
        'The neighbor is halfway down the stairs and cannot see the last turn. Steve must open the balcony gate while the stair bulb stays lit from start to finish. The service selector has three positions.',
        'NORMAL feeds the stair bulb and latch motor. SERVICE feeds the bulb alone. OFF feeds neither. A thumb pad can store a release request only while the motor is idle. The return spring clears the request the instant the pad rises. The motor checks for a stored request only when it starts.',
        [('Selector before touching the pad', ['NORMAL', 'OFF', 'SERVICE'], 2),
         ('At the thumb pad', ['Tap and let go', 'Press and keep pressure', 'Rest a hand beside it'], 1),
         ('While the pad is still in that position', ['Switch to NORMAL', 'Switch to OFF', 'Stay in SERVICE'], 0)],
        ('Track the stair bulb separately from the latch motor.', 'The request must survive until the motor starts. Which position lets you store one without darkening the stairs?',
         'Choose SERVICE, press and keep pressure, then switch to NORMAL.'))

    instrument('c2_ship.escape',
        'The scan is moving again. Steve has three recordings on Frank’s reel and can reach two microphone grilles.',
        'The attendant spoke into the grille with the broken rim when testing the gallery speakers. The undamaged grille made the chair’s service lamp blink. The lamp stays lit for one second on an ordinary scan beat and for six seconds at the notch marked 61. The chair listens only while the lamp is lit and drops an unfinished phrase when it goes dark.',
        [('Recorder cue', ['Reel 01', 'Reel 02', 'Reel 03'], 2),
         ('Microphone grille', ['Broken rim', 'Undamaged rim'], 1),
         ('Start of playback', ['First ordinary beat', 'Start of the 61 notch', 'When the notch ends'], 1)],
        ('Preview the three cues. Which speaker has already been obeyed by this chair?', 'Separate the public speakers from the local service input. The complete authorization lasts longer than one ordinary beat.',
         'Choose cue 03, the undamaged grille, and the start of the 61 notch.'))
    tasks['c2_ship.escape']['sounds'] = ['c2_aquarium.out.01', 'c2_ship.in.02', 'recording.release']
    tasks['c2_ship.escape']['audition_labels'] = ['Reel 01', 'Reel 02', 'Reel 03']

    instrument('c4_escape.fault',
        'The safe-house training console offers three rehearsals. Calder wants the occupied west corridor cleared while she keeps Rook in the east interview room.',
        'The transport escort in west signed the drill ticket. Yesterday’s log: SILVER moved only the signer. BLUE moved every badge in the signer’s corridor. WHITE moved every badge outside it. Dry run prints the route. Floor rehearsal sends the staff that route.',
        [('Exercise card', ['WHITE','SILVER','BLUE'], 2),
         ('Console mode', ['Dry run', 'Floor rehearsal'], 1),
         ('West team’s assembly point', ['Covered court', 'Transport bay', 'Front office'], 1)],
        ('Work out who signed the ticket and how many colleagues must move with them.', 'Yesterday’s log distinguishes one person, their group and the other group. Compare the group’s size with each assembly point.',
         'Use BLUE and floor rehearsal. Move the four western staff to the transport bay.'))
    tasks['c4_escape.fault']['puzzle']['instruction'] += ' Four staff must assemble together. The covered court seats three, the transport bay four. The five-place front office is occupied by interviews.'

    instrument('c5_shack.rig',
        'Three insulated battery packs fit Frank’s receiver. His Thursday club is on the log frequency, but the dial has slipped.',
        'Receiver card: 12 V DC, center positive, draws 400 mA. A battery pack may supply more current than the set draws. Pack RED: 12 V, 300 mA, + center. BLUE: 12 V, 800 mA, + center. GREY: 12 V, 800 mA, − center. Frank logged a 3.20 MHz station at dial 3.25, and a 3.40 MHz station at 3.45. Thursday club transmits on 3.56 MHz.',
        [('Battery pack with receiver off', ['RED','GREY','BLUE'], 2),
         ('Dial setting for Thursday club', ['3.51 MHz','3.56 MHz','3.61 MHz'], 2)],
        ('Check all three rating marks before relying on a pack’s color.', 'The receiver reads high at both known stations. Add the same offset to the club’s actual frequency.',
         'Select BLUE and 3.61 MHz. The pack has the correct polarity and enough current, and the dial reads 0.05 MHz high.'))

    instrument('c2_aquarium.plan',
        'The old plan and a newer maintenance notice disagree. Steve needs a route into the north wing.',
        'On the plan the café and public tank both feed the visitor hall. The service door feeds the pump room. The visitor hall leads to the north wing through door 1. Notice: door 1 was bricked up; the pump room has three pipes now. Flow arrows point from N into the pump, from the pump into E, and from S into the pump. The maintenance slip says to follow the only pipe carrying water away from the pump.',
        [('Entrance', ['Public tank', 'Service door', 'Café'],1), ('Pump outlet', ['N', 'S', 'E'],2)],
        ('Use the newer notice when two documents conflict.', 'The old visitor route depends on door 1. At the pump compare both ends of the flow arrows.',
         'Use the service door and follow E, the only outgoing pipe.'))

    instrument('c3_archive.paper',
        'Calder needs two independent originals. The office has copies and summaries of the same records.',
        'Desk A: clinic receipt, punched 14:12; fax of that receipt, received 15:04. Desk B: bound Town Hall ledger, signed 14:10; next-day database entry transcribed from the ledger. The bus trip between the two counters takes forty minutes. One signature uses the same name as the other.',
        [('From Desk A', ['Clinic receipt','Fax copy'],0),
         ('From Desk B', ['Database entry','Bound ledger'],1),
         ('What those originals establish', ['Which signer used a false name','Two locations conflict under one name','The exact time of a later amendment'],1)],
        ('A second sheet is not necessarily a second independent event.', 'Choose the document made at each counter. Compare the times with the travel time; neither record alone identifies an impostor.',
         'Take the clinic receipt and bound ledger. They place one name in conflicting locations.'))

    instrument('c3_archive.cycle',
        'Tomás penciled the field dates onto the tape boxes. The studio dates mark the day he aired a recording. Calder needs one evening and one watch point.',
        'Field / broadcast dates: 02 / 05, 11 / 13, 20 / 22. From the last stakeout: pier lamp dims 23:42; footsteps pass the boathouse 23:53; water glows 00:04. The radio boat obscures the sea wall from 23:48 until midnight. The boathouse window faces the path.',
        [('Next field date', ['27th','28th','29th','30th'],2),
         ('Watch assignment', ['Sea wall at 23:50','Boathouse at 23:45','Boathouse at 00:05'],1)],
        ('Follow when Tomás was in the field, not when his show aired.', 'Choose a vantage with an open view before people pass it. The glow comes later.',
         'Stake out the boathouse at 23:45 on the 29th.'))

    instrument('c4_escape.tube',
        'The old tube map uses construction names. Steve needs his warning and the voice comparison to reach June without passing the interview desk.',
        'Panel map: A leads to OAK, B leads to PINE, C leads to ASH. Occupancy docket: June was moved from OAK into the room opposite the linen cupboard. The building sketch places ASH opposite linen; PINE faces the lift. Standard capsules go through the interview desk for sorting. Blue maintenance capsules travel directly to the selected room.',
        [('Diverter', ['A', 'B', 'C'],2),
         ('Capsule', ['Standard', 'Blue maintenance'],1),
         ('Enclosure', ['Rook’s voicemail only','The recent take only','Both labeled takes and the warning'],2)],
        ('Use the occupancy docket after the construction map.', 'Find the room opposite linen. June needs to check a comparison for herself before trusting a warning.',
         'Set C, send a blue capsule and enclose both labeled takes with the warning.'))

    def finding(key, prompt, choices, cues):
        task = tasks[key]
        task['prompt'] = prompt
        task['options'] = choices
        task['hints'] = [*cues, 'Choose “' + choices[task['answer']] + '”. ' + task['note']]

    # Short collection and character beats stay short. Where the player is asked to
    # infer something, each alternate finding explains some, but not all, of the clues.
    finding('p_veyr.shield',
        'Knocks vanish when the Archivist shelters the microphone with her hand. The distant towers are still audible. What can she leave in place when she lets go?',
        ['Fit the felt sleeve','Set the recorder on a folded cloth','Lower the gain one division'],
        ['What changed when she used her hand?', 'Air hitting the capsule and vibration travelling up the stand have different remedies.'])
    finding('p_veyr.record',
        'The departure has three sounds in order: the tower wind, an engine lifting, then a silence where the engine was. What would preserve their timing for someone who never heard them?',
        ['Record the whole passage','Make a separate reel for each sound','Stop the tape during the quiet passage'],
        ['Consider what a listener can learn from the silence.', 'A splice can preserve the order of events while losing their spacing.'])
    tasks['p_veyr.levels']['hints'] = [
        'Start by working out where the louder gust would peak at the current setting.',
        'The next peak would be +3 dB. Count how far it must move to reach -3 dB.',
        'Choose -6 dB. A bigger reduction also avoids clipping, but loses more level than necessary.']
    finding('p_meeting.terms',
        'The delegate says “compare our demonstrations.” One interpreter’s draft uses “prove”; another adds “which was stronger.” Helen needs to translate the proposal without adding a claim.',
        ['You propose a test of which field was stronger','You propose discussing what was demonstrated','You propose proving the apparatus can work'],
        ['Listen for the verb the delegate actually used.', 'Comparing observations leaves their explanation open. Ranking or proving them adds a promise.'])
    finding('p_meeting.record',
        'The two delegates approve the same public sentence. Helen also heard each private admission. What belongs in the notebook she keeps for herself?',
        ['The printed joint sentence alone','Separately attributed remarks and the final agreement','A single admission credited to both delegates'],
        ['The notebook may be read years after the speakers are gone.', 'A reader should be able to distinguish who spoke in private from what both signed.'])
    tasks['p_bay.tune']['hints'] = [
        'Move the dial between the two clear broadcasts and listen for a third sound.',
        'The hum is near 815 kHz. A broad setting still lets the adjacent stations through.',
        'Set 815 kHz, choose the narrow bandwidth, then record.']
    finding('p_bay.message',
        'Frank needs both hands on the set. Helen has a dry notebook in the boat. Steve’s recorded greeting ends with a beep. Which record could Steve find at home tonight?',
        ['Leave Steve a message','Write a second copy in the boat log','Call the Thursday club from Frank’s receiver'],
        ['Where will each record be when the boat leaves?', 'Steve can retrieve something left on his own phone.'])
    finding('c1_flat.saturday',
        'The leader reads SAT. A loose work reel holds an earlier kitchen test. Steve wants evidence he can date without relying on memory.',
        ['Keep the original recording','Copy both takes onto the work reel without markers','Use the kitchen test as the Saturday reference'],
        ['The date has to stay attached to the sound.', 'An earlier recording from the same room does not establish what Steve heard on Saturday.'])
    finding('c1_flat.sunday',
        'On Sunday Steve can set the recorder running before Nora comes in. How could he compare an ordinary morning with Saturday without teaching her the rhythm he remembers?',
        ['Play Saturday first and ask for another greeting','Record the greeting without prompting her','Say the greeting first and ask her to reply'],
        ['Keep the conditions of the two mornings as similar as possible.', 'A demonstration or a verbal cue can change the second performance.'])
    finding('c1_flat.control',
        'Steve tests a different stretch of tape. He hears “one, two” twice. A chair squeaks between the words only on the second pass. Which claim has this test actually challenged?',
        ['Nora used the same words twice','The transport loops the last input on every pass','Steve recognized Nora’s voice correctly'],
        ['Use the squeak as a marker independent of the words.', 'A transport that always replayed the earlier pass would replay the earlier room noise too.'])
    finding('c1_pier.whistle',
        'Admiral took Steve’s lunch. Nora whistles while Admiral is underwater; the harbor winch is running. He keeps swimming. What should go in the observation column?',
        ['He failed to turn during this whistle','He heard Nora and chose to ignore her','Nora’s second note was too low'],
        ['Separate what Steve saw from what he thinks Admiral heard.', 'The winch and the water leave more than one explanation.'])
    finding('c1_pier.door',
        'Lyle holds a door and remembers the boys’ birthday. Steve remembers him as a colder man. What independent follow-up would help date the change?',
        ['Record the birthday itself','Ask when he first began coming to their games','Test whether he remembers Steve’s old address'],
        ['Steve needs a date for the new habit.', 'Old memories can establish familiarity without dating a change in behavior.'])
    finding('c1_pier.bait',
        'Penhallow hums along to a low note. Her lips go still before the note dies away across the water. Steve wants to learn where it comes from.',
        ['Ask which part of the bay she hears it from','Ask when she learned the melody','Ask whether she hums it in the shop'],
        ['There are two possible sources close together.', 'Steve still hears the note after Penhallow stops.'])
    finding('c1_dinner.birthday',
        'Mateo drove Nora to the restaurant; Rafa took her home. Carmen remembers the meal but spent most of it in the kitchen. Which entries could later establish how long Nora stayed?',
        ['Mateo’s arrival and Rafa’s departure times','Carmen’s menu and the restaurant hours','Nora’s shift roster and the table booking'],
        ['Which family members actually witnessed the endpoints?', 'A booking describes a plan; a ride places someone at the restaurant.'])
    finding('c1_dinner.podcast',
        'Tomás has three years of field reels. His published episodes splice sounds from several nights. What should Steve borrow to investigate the dates?',
        ['The episodes arranged by broadcast date','The field reels with their original labels','An undated compilation of the clearest hums'],
        ['Does a broadcast date establish a recording date?', 'Keep the sound attached to the night Tomás was in the field.'])
    finding('c1_dinner.family',
        'Nora now agrees with Carmen about a recipe she used to argue over. Carmen notices too. Which conclusion can Steve support tonight?',
        ['Nora has forgotten how the dish used to taste','Two witnesses noticed a change worth following','They know when and why Nora changed her mind'],
        ['Count the observations, then consider what caused them.', 'Agreement between two witnesses about a change does not date it or explain it.'])
    finding('c1_escape.order',
        'The north-wing work order has a handwritten sign-off at 20:15 on Carmen’s birthday. Mateo brought Nora to dinner at noon; Rafa took her home at midnight. Which discrepancy should Steve check first?',
        ['The sign-off against the family’s witnessed interval','The form’s print date against the reservation date','The work-order number against the menu price'],
        ['Find two records that make claims about the same person and time.', 'A form can be printed long before someone signs it.'])
    finding('c1_escape.cross',
        'The pots lean against the inner rail. The landing door needs a key from the stair side. Through the neighbor’s open balcony gate Steve can see the illuminated communal stair.',
        ['Follow the shared rail to the communal stair','Pull the landing door shut and try its outside handle','Pass the stair and try the unlit fire door'],
        ['Use only a route Steve can see is open.', 'The landing handle is on the wrong side.'])
    finding('c2_aquarium.intercom',
        'The spool starts before Nora states her name. A date mark remains on the leader, and two notes follow the speech. What would let somebody else check both her identity and the date later?',
        ['File the intact spool and its marked leader','Keep the two notes alone with a new date label','Copy the name only and discard the leader'],
        ['Two different kinds of evidence are on the same spool.', 'A date copied by Steve has a different chain of custody from the original marked leader.'])
    finding('c2_ship.nora',
        'At the bed, Nora’s chest rises irregularly against the glass. A pulse travels down the corridor at even intervals. Steve wants to check for a response without disturbing life support.',
        ['Speak close to the bed and watch her breathing','Use the corridor pulse as Nora’s breathing rate','Use the brightness of the next bed as her pulse'],
        ['Which observation belongs to this sleeper?', 'The rhythm shared by the corridor need not come from Nora.'])
    finding('c2_ship.command',
        'An attendant asks the chair to open. Nothing happens. Saren answers over the intercom and the buckle releases during his last words. What should Steve mark on the reel?',
        ['Saren’s reply from first word to last','The attendant’s request before the reply','Only the noise of the buckle opening'],
        ['The order of the three sounds matters.', 'The words before the click may matter just as much as the word Steve heard most clearly.'])
    finding('c3_house.crossword',
        'Calder’s drawer holds last Friday’s completed crossword. Today’s blank crossword includes a clue about a ferry cancellation announced this morning. Which item can test access to fresh facts?',
        ['Today’s ferry clue','Friday’s handwritten letters','The nickname Calder used at school'],
        ['When could the subject first have learned the answer?', 'An old private memory and fresh private evidence are different tests.'])
    finding('c3_house.rules',
        'One grieving human has changed his routine. Someone suspected of being a copy has remembered the sheriff’s childhood. Which approach could June check without assuming either example proves identity?',
        ['Score how many old memories sound correct','Check a new fact against a separately dated record','Treat each new kindness as a separate positive test'],
        ['Two different causes can produce the same behavior.', 'Prefer observations that can be checked outside the interview.'])
    finding('c3_house.mail',
        'Dale carries Steve’s redirected mail before the desk has logged the change. He also stops to pet Biscuit. Which follow-up can distinguish an early dispatch from an alteration?',
        ['Compare dispatch and redirection timestamps','Ask Biscuit which hand Dale normally uses','Compare today’s greeting with Steve’s memory of it'],
        ['Which suspicious detail has a record independent of Dale?', 'The route desk and the dispatch office record different events.'])
    finding('c3_archive.power',
        'A laundromat used 882 units last month. Sentinel Point reported 640. The meter reader confirms one billing meter, but the archives have no record of on-site generation. What can Steve enter in the file?',
        ['Recorded grid use is modest; other supply is unverified','The utility bill measures every source of energy on site','The smaller bill proves every apparatus was switched off'],
        ['The meter records only what passes through it.', 'Distinguish an unexplained discrepancy from proof of what the facility contains.'])
    finding('i1_archive.reset',
        'Gus baked a new kelp pastry yesterday. His original human record predates the recipe. The reconciliation register requires preserving the original and restoring only the changed working echo.',
        ['Restore Gus’s working echo from the stored record','Update the stored record from the working echo','Copy yesterday’s recipe into both records before reconciling'],
        ['Which record is the reference, and which has changed?', 'The law preserves an older record even when that costs Gus something new.'])
    finding('i1_archive.quiet',
        'Seven surveys name inhabited worlds, each marked Quiet. An eighth file has a living atmosphere, but Saren has sealed its coordinates. Row Zero has one surviving witness. Which entry preserves what is known?',
        ['Keep the sealed survey separate and visit Row Zero','Enter eight destroyed worlds under the same cause','Use the sealed file to assign one named world to Row Zero'],
        ['A sealed coordinate does not identify a named world.', 'Quiet describes the record; it does not establish how a people disappeared.'])
    finding('c4_safe.record',
        'Calder’s voicemail preserves Rook saying “Sit tight, June.” Through the door Steve hears the same words after the hold music stops. How should he prepare a comparison?',
        ['Capture the new reassurance with the room sound intact','Ask Rook to imitate the voicemail in the same room','Record the hold music instead of the words'],
        ['Keep the naturally occurring performance.', 'The room sounds and the pauses are useful evidence too.'])
    finding('c4_safe.screens',
        'A monitor shows a sleeping man with Rook’s face. A second screen holds personnel portraits and assignment dates. Which combination would test whether this feed predates the man in the safe house?',
        ['Check the live Gallery clock against the dated assignment','Compare the two portrait backgrounds','Match the spelling of Rook’s surname'],
        ['A matching face alone does not establish when a picture was taken.', 'One display is a live feed. The other has an independent date.'])
    finding('c4_escape.van',
        'From the seat Steve can see the shoulder only where the driver slows for a gravel turn. The rear handle moves freely once the escort releases the travel catch.',
        ['Wait for the released catch and the gravel bend','Use the released catch on the straight road','Try the gravel bend while the travel catch is set'],
        ['Steve needs two things to be true at once.', 'A clear shoulder and an operable handle occur together only on the turn.'])
    finding('c5_shack.notes',
        'Helen wrote “with the good stuff” on a loose slip. A previous note uses the same phrase; Frank’s reply is dated the following morning. Which pair could recover the family meaning?',
        ['Put Helen’s earlier use beside Frank’s dated reply','Pair the loose slip with the nearest envelope by size','File all notes by the color of the ink'],
        ['A private joke is easiest to recover from a conversation.', 'Use chronology to test which note answers which.'])
    finding('c5_shack.club',
        'Frank’s outgoing logs end with K7BLW. The contact column has a different call sign on each Thursday. Which identifier would old club members recognize as coming from this set?',
        ['K7BLW, from the outgoing column','The last contact in the receiving column','The frequency printed on every club card'],
        ['Read the two columns from Frank’s point of view.', 'A contact changes when the other operator changes.'])
    finding('c5_shack.log',
        'On the last reel, a long hum underlies a short tone. Frank’s last entry distinguishes the voices inside the hum. Which material would let Steve test that description?',
        ['Keep the full sound under the dated log entry','Keep only the loud short tone','Average all the ninth-night reels into one undated track'],
        ['Consider which part of the recording Frank described.', 'A short alert could mask the evidence he wanted his son to hear.'])
    finding('c5_station.automation',
        'AutoRick’s sheet repeats three events. WEATHER keeps the booth locked. IDENT briefly opens maintenance access while the recording plays. NEWS opens the visitors’ entrance after it ends. Steve is already at the booth door.',
        ['Queue IDENT and enter during playback','Queue NEWS and enter after playback','Queue WEATHER and enter during playback'],
        ['Check both which door and which part of the cue.', 'The visitors’ entrance is on the other side of the building.'])
    finding('c5_station.sleeve',
        'Helen’s note says “your first night at the desk.” A library card covers three shows: Steve presented the second, but engineered the first. The station files by original transmission, even after a repeat.',
        ['The original transmission sleeve of the first show he engineered','The rerun sleeve of the first show he engineered','The original sleeve of the first show he presented'],
        ['“At the desk” had a particular meaning in this family.', 'Use the date of the original, not the repeat.'])
    finding('c5_station.halcyon',
        'Three stamps survive: Halcyon acquired KBWR on the 3rd, Steve’s overnight slot ended on the 5th, and the first unattended tower transmission was logged on the 6th. Which sequence do those records support?',
        ['The new owner cleared the overnight slot before the tower traffic began','New tower traffic preceded the sale and caused it','Steve was still working alone during the first unattended transmission'],
        ['Put all three stamps on one calendar.', 'The earliest transmission in the log follows the last staffed slot.'])
    finding('c5_station.stephen',
        'Stephen remembers breakfast in Frank’s shack but cannot account for the wanted posters. Steve wants to find how far Stephen’s memories reach without feeding him the answer.',
        ['Ask him for the last time he saw their parents; listen before explaining','Tell him the date of the boat trip and ask him to repeat it','Quiz him only on the kitchen where they grew up'],
        ['Which question can locate a gap in time?', 'A leading date and a much older shared memory cannot locate the boundary by themselves.'])

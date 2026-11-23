# Night Nine script v2: changes and audit

Written 2026-11-20 for milestone M1. The source of truth is `tools/script_v2/*.json`. The readable script is `docs/script-v2/script.md`. How the tool works is in `docs/script-v2/README.md`.

## (a) Summary

- The revision covers all 34 scenes and 101 leads: 88 puzzles and 13 non-graded beats. 39 are settings rows, 23 case boards, 17 choices, 7 listening compares, one tape alignment and one dial.
- Every lead has a goal, a "What Steve knows" background, a prompt and three hints. 79 leads open with a short lead-in conversation. The rest follow straight on from the scene opening or the previous lead.
- 99 leads end with a finding narration that says what the result means. The two exceptions are the last beat of the game and the post-credits puzzle, where the next line is the payoff.
- 32 scenes end with a recap narration that sums up the scene and points at the next place. The last two short scenes go straight to their payoff.
- Chapter 1 now starts from an ordinary job. Steve wants to save Mom's voicemail to a fresh tape, so he times Dad's old recorder against his own 12-second station ident on two mornings. Nora's good morning happens to be on both tapes, and it lines up breath for breath.
- Wrong answers explain themselves in Steve's (or the playing character's) voice and never name the right option. Case boards have their own miss line.
- This audit rewrote all 88 third hints. Before the audit every hint 3 stated the answer. Now hint 3 names the deciding fact or the last step, and the player still makes the final choice.
- The audit fixed 38 further continuity, staging and wording problems (section e) and added coach tips to 9 scenes.
- Five questions need a structural decision (section f). The most important one: with no hint that gives the answer, the engine needs a separate way out for a stuck player.
- The validator reports **0 errors and 0 warnings**. 873 lines need recording (66,444 characters), and nothing is recorded yet.

## (b) Chapter by chapter

### Prologue: The bay is singing (`p_bay`)
The storybook "Before the ninth night" introduces Bellwether, Steve, Frank the radio ham and Helen the interpreter, and the boat trip Steve said no to. The player then plays Frank on the boat, eighteen months ago. Frank tunes his radio to the hum hidden between two stations (`p_bay.tune`, a dial puzzle). Helen picks where to hold her phone so Steve's voicemail carries the hum (`p_bay.message`). Frank's log entries are the findings, and they time the night. The scene ends on the voicemail Steve will replay for eighteen months. The storybook "Eighteen months" covers the empty boat, the job loss to Halcyon's AutoRick, and Nora, who "argues with everybody" but lately has been endlessly patient.

### Chapter 1: Good Morning, Sleepyhead (`c1_flat`, `c1_pier`, `c1_dinner`, `c1_escape`)
Saturday the 20th, 3 a.m.: Steve plays Mom's voicemail, hears the tape wearing thin, and decides to copy it once Dad's slow old recorder proves it runs true. The test is his own 12-second KBWR ident at 7:15. He records it on Saturday (`c1_flat.saturday`) and again on Sunday under the same conditions (`c1_flat.sunday`). Lining the two tapes up (`c1_flat.compare`) shows the recorder is fine, and also that Nora's good morning, caught by accident on both tapes, is identical. He crosses the boring explanation off his notebook list with a squeak test (`c1_flat.control`). On Sunday afternoon at the harbor, with crab boats in, June Calder in the fish-shed line and Agnes Penhallow at her stall, Steve sets up a fair whistle test for Admiral (`c1_pier.whistle`), dates Deputy Lyle's sudden change of heart (`c1_pier.door`) and traces the low note to the water (`c1_pier.bait`). At Sunday dinner Carmen's photo strip pins Nora's birthday evening (`c1_dinner.birthday`), her brothers bracket when she stopped arguing (`c1_dinner.family`), and Tomás's field reels show the hum comes every nine nights, which makes tonight the next one (`c1_dinner.podcast`). At home a work order falls out of Nora's raincoat. Steve uses his dinner notes to prove she could not have signed it (`c1_escape.order`), overhears her call about a notebook, gets out through his neighbor Mr. Bell's gate (`c1_escape.power`), and Nora lets him go on the balcony (`c1_escape.cross`). At midnight on the beach the town walks into the water, and Mrs. Penhallow says "Ninth night, Steven."

### Chapter 2: The Aquarium Is Closed (`c2_aquarium`, `c2_ship`)
Steve's 911 call about the procession breaks up. The work order names one place: the sealed north wing of Nora's aquarium. He finds the way in from the exhibit plan Nora once showed him (`c2_aquarium.plan`), picks the corridor that only plays a loop (`c2_aquarium.guard`), and finds Nora's real fleece and an intercom spool. The board (`c2_aquarium.intercom`) turns its May 29 date into "five months" and separates her rising whistle from the falling one Admiral ignored. Her copy and Lyle catch him. On the ship the attendant explains that the scan reads the oldest memories first. Steve tapes the Prefect's release command (`c2_ship.command`), plays it back at the 61 notch to get out of the chair (`c2_ship.escape`), finds the real Nora breathing on her own (`c2_ship.nora`), and in the flooding intake picks Nora's spool so Admiral comes for him (`c2_ship.intake`). June Calder finds him on the beach at dawn.

### Chapter 3: Please Prove You Exist (`c3_house`, `c3_archive`)
Friday the 26th, four days later, which is how long a copy body takes to grow. Carmen brings casserole number forty-eight and mentions she saw a cheerful Steve at the market that morning. To prove which Steve is in her kitchen, June asks about something the scan never reached: his 911 call, which her kitchen machine recorded (`c3_house.crossword`). Steve then helps June sort her list of 31 names into feelings and dated evidence (`c3_house.rules`) and works out that Lyle passed his whereabouts to Dale the mail carrier (`c3_house.mail`). In the Town Hall archive Walt Prior's permit puts one name in two cities on one afternoon (`c3_archive.paper`). Mrs. Penhallow turns up with herring wrapped in a Meridian article, June explains Sentinel Point, and the meter rolls show it uses less power than a laundromat (`c3_archive.power`). Tomás's dated boxes give the next ninth night, the window and the time for a stakeout (`c3_archive.cycle`). The stakeout plays on screen: 274 people walk into the surf, Nora's good coat turns back at the waterline, Mrs. Penhallow watches from the boathouse steps, June calls Adrian Rook, and an anonymous lowercase text warns them.

### Interlude 1: The Archivist (`i1_archive`, `p_veyr`)
The same ninth night under the bay. The Archivist defines an echo and reconciles Gus the baker, writing his kelp croissant into the witness ledger (`i1_archive.reset`). She compares the two Meridian test reels and files a shared pulse under two different lamp shows, without saying what she thinks it means (`i1_archive.signals`). The fleet's one-word message, "Deliver", leads her to the seven Quiet worlds, Tirel and the Prefect's sealed survey (`i1_archive.quiet`). She leaves her report on Helen as "memory damaged" and admits privately that it is not. Then she replays her own memory of Veyr: she sets the recording level (`p_veyr.levels`) and records the departure, silence included (`p_veyr.record`).

### Chapter 4: Federal Hospitality (`c4_safe`, `c4_escape`)
Rook takes Steve and June to a safe house and keeps asking about Helen's notebook. Steve records Rook's hourly "Sit tight, June" through the office door with the room sound kept (`c4_safe.record`), shows it is the same recorded take as June's voicemail (`c4_safe.match`), and reads Rook's monitor wall: the real Rook asleep in bed 41B, Walt Prior on a placements list, and an empty bed for President Ward (`c4_safe.screens`). Separated from June, he sends her the proof through the old pneumatic tubes (`c4_escape.tube`). Her recorded reply tells him to run. A drill console gets the west corridor moved by van (`c4_escape.fault`), and he jumps out on the gravel bend (`c4_escape.van`). The stolen radio says he is wanted for Nora's abduction, Calder will be scanned tonight, and the signing is in six days.

### Chapter 5: Wanted: Steve Mercer (`c5_shack`, `c5_station`)
Steve hides in Dad's radio shack. Luis Reyes brings food and does not call the Sheriff. The kitchen-table notes decode the family phrase "with the good stuff" as the KBWR record library (`c5_shack.notes`). Steve repairs Frank's receiver (`c5_shack.rig`) and signs on with K7BLW (`c5_shack.club`). Gull, Marsh and Cedar answer even though it is not Thursday. Frank's last reel turns out to be a choir (`c5_shack.log`). That night at KBWR he queues WEATHER and then his own ident to open the library door (`c5_station.automation`), finds "my first night at the desk" in the blue sleeve (`c5_station.sleeve`), and learns Halcyon sent him home every ninth night (`c5_station.halcyon`). He also meets the man with his face and maps where his memory stops (`c5_station.stephen`). Stephen names himself, hears about the boat for the first time, and remembers Row nine.

### Chapter 6: Iris (`c6_iris`, `c6_jail`)
AutoRick broadcasts the manhunt. A lowercase text asks Steve to the pier at 8:10. Stephen gives the town a face at Gus's wanted poster at exactly that minute (`c6_iris.alibi`). Steve tests the stranger with the recorder, and her two takes differ (`c6_iris.takes`). She shows how distant copies stay in step on Halcyon hold music, taped at the minute the bay lit up (`c6_iris.hold`). She says Saren wants the notebook and the President, and that the President's physician scanned her, and she chooses the name Iris. At noon there are two Sheriffs. Pell admits who he is and helps find the cell key in his sorting case (`c6_jail.mail`). Stephen contests his own poster to pull the deputy away (`c6_jail.distract`), and one circled crossword square proves which June is real (`c6_jail.crossword`). Lyle's copy chooses his son's school play over his orders (`c6_jail.exit`). Gus lends the croissant van, Iris answers about the ring, and she warns that she and Stephen have days.

### Interlude 2: Nobody is coming to fix this (`i2_nora`)
The real Nora wakes in the Gallery because Iris stopped re-syncing. She counts the guard's lap (`i2_nora.patrol`), gives Lyle and Dale the jobs they are already good at (`i2_nora.jobs`), and uses her aquarium knowledge to drop the return pressure without starving the beds (`i2_nora.pump`). She leaves a message for Steve in the slot that waits for PLAY (`i2_nora.message`). She sits with Helen and Frank in row nine, notes Mrs. Penhallow asleep in row three, and something under the frost in Row Zero opens one eye.

### Chapter 7: The President's Other Appointment (`c7_gate`, `c7_swap`)
At Sentinel Point, Stephen drives the Halcyon truck through the blue window while Steve hides under the sound desk, and Rook's copy waves them through (`c7_gate.badge`). Pell delivers registered mail into Ward's own hand at 11:54 and notes a fresh bandage on her left wrist (`c7_gate.post`). Evelyn Shaw introduces herself, and Steve proves the back fence hears the desk (`c7_gate.truck`). Saren speaks to Steve for the first time and mentions Tirel. The bandage tells the real Ward from the copy made before it and traces her to the service tunnel (`c7_swap.map`). Steve routes Dad's ninth-night tone to every site speaker but not the national feed (`c7_swap.bus`) and times it so June and Iris already have Ward (`c7_swap.tone`). Fourteen people turn toward the sea, Iris holds on through the pull, and Rook's copy asks if "the other one" is awake. In a locked room Ward, Lin Wen and Shaw tell Steve there is no engine.

### Chapter 8: The Biggest Lie on Earth (`p_meeting`, `c8_lab`, `c8_beach`, `c8_rig`)
The flashback puts the player in Helen's chair nine years ago. She translates the Chinese delegate's word for "performance" exactly (`p_meeting.terms`) and asks the question that lets each side confess about its own machine (`p_meeting.confess`). Back in the present, Wen and Steve put Helen's loose pages in order and see that the fleet came because of a broadcast show (`c8_lab.notebook`). Shaw's film log shows which effects share one cue (`c8_lab.props`), and Helen's last page matches Frank's Reel 11, a language nobody can read (`c8_lab.lastpage`). Mrs. Penhallow appears by the reactor, and Saren gives his ultimatum on every screen. At dawn Saren plays Mom's voice, which Steve proves was cut from his own voicemail (`c8_beach.second`), and Steve keeps the notebook (`c8_beach.refuse`). At the workshop Iris and Stephen vote for the plan. The team finds the one live feed and its jack (`c8_rig.source`), the only receipt the fleet would trust (`c8_rig.path`) and the one clean coupler (`c8_rig.rig`). Stephen forgets Frank's name and writes it on his hand.

### Chapter 9: The Long Patience (`c9_gallery`, `c9_wake`, `c9_choir`)
The attendant offers the visitors a scan, and Steve remembers that ends with a flood. Nora is awake and furious. Iris breaks her link knowing the cost (`c9_gallery.link`), and Steve answers for the thirteen months (`c9_gallery.talk`). Stephen goes for the antenna only when June sees the lamp (`c9_gallery.antenna`). Nora's Slot B message plays on every speaker. In row nine Frank wakes to his call sign in Morse (`c9_wake.frank`) and Helen to her lullaby, the tune in the ship's hum (`c9_wake.helen`). June wakes Adrian Rook (`c9_wake.rook`), and the woman in row three turns out to have been asleep for three years, which raises the question of who sells bait on the pier (`c9_wake.agnes`). Rook's copy betrays them, the rig is smashed and Steve goes back in the chair. The Choir stops the scan. Steve plays it his season of tapes to show one record that changed (`c9_choir.truth`). Wick wakes, Helen follows its phrase (`c9_choir.wick`), Frank gives Steve his note from the boat (`c9_choir.note`), and the Vigil arrives.

### Chapter 10: Good Morning, Bellwether (`c10_station`, `c10_town`, `c10_live`, `c10_report`)
With the rig in pieces, Steve uses the KBWR tower that has talked to the ship for a year. He beats AutoRick's queue (`c10_station.playlist`), recalls from the rig which jack is live and which return the fleet trusts (`c10_station.route`), and lets Frank's club find the one operator who can see Sentinel Point (`c10_station.relay`). Mrs. Penhallow walks into the booth with the wind of Veyr in her bait bucket and admits she is part of the ship's record keeper. Nora runs the phone tree (`c10_town.lights`), Wen and Shaw share one cue sheet (`c10_town.console`), and Steve places the Choir's live answer after the old recording (`c10_town.wind`). The live show runs three cues (`c10_live.first`, `c10_live.second`, `c10_live.third`). Saren threatens on air, the town blocks the pier and Admiral takes his crystal. On the open channel the Archivist admits why she lied about the notebook, takes her echo as witness (`c10_report.echo`), opens Saren's sealed survey (`c10_report.survey`) and builds the report (`c10_report.report`). The fleet goes around, and the ship rises at sunrise.

### Epilogue, one year later, after the credits (`epilogue`, `one_year`, `postcredits`)
The Choir steadies the copies who stay. Three beats visit the new neighbors, the two Mrs. Penhallows and Rook's goodbye, then coffee with Nora and Mom's new kitchen note. The closing storybook no longer repeats the epilogue jokes. One year later a recording of new wind arrives and Steve says good morning live. After the credits Helen recognizes the shape of a real signal from deep space and translates it.

## (c) Disposition of every plan item

Status: **applied** (done as written or with the critic's fix), **adapted** (the intent is met in a different way, noted), **deferred** (needs engine, voice or test work in a later milestone).

### C01 to C37

| Item | Where it landed | Status | Note |
| --- | --- | --- | --- |
| C01 wrong answers teach | `wrong` on every choice and compare; `wrong_text` on every board; all hints | applied, engine deferred | Hint 3 goes further than planned and never gives the answer. Panel feedback, disabled option and auto hint are M2 engine work. |
| C02 goal on boards, coach tips | `goal` on all 101 leads; coach on c1_pier, c1_dinner, c1_escape, c2_aquarium, c2_ship, i1_archive, c6_iris, i2_nora, c7_gate, c9_wake | applied, engine deferred | Actor switching and the coach card are M2. |
| C03 Tomás's field dates | c1_dinner.podcast (24 Sep, 3, 12 Oct, next 21 Oct); c3_archive.cycle (recorded 3, 12, 21 Oct; aired 4, 15, 23) | applied | Uses the critic's calendar: Chapter 1's Sunday is the 21st, a field night. |
| C04 jack meanings | c8_rig.source finding; c10_station.route; c10_station.relay; c10_live.second "Booth" | applied | Route is a recall puzzle. Relay uses Gull, Marsh, Cedar. |
| C05 faster hook, notebook control | c1_flat intro in.05 to in.08; saturday, sunday, compare, control | adapted | The recorder runs because Steve is testing it to save Mom's tape. Saturday stays a simple choice, not a beat. Control options now match the notebook theories. |
| C06 Admiral, whistle, Lyle, Agnes | c1_pier.ctx, in.01, whistle, door, bait, bait.01 | applied | Bait uses the critic's stage. Lyle task asks "Since when?". |
| C07 photo strip, family, podcast | c1_dinner.birthday, family, podcast, in.01 | adapted | Family became a bracket of dated last arguments, using the storybook's "argues with everybody". |
| C08 escape restructure | c1_escape ctx, order, power, cross; objective steps | applied | Intro is hanging up the wet raincoat. Cross is a beat with the new lines. |
| C09 nine-night count, hum under voicemail | p_bay.in.01, message, message.01; c1_pier.bait.lead.01 | adapted | Steve's "something under her voice" line moved to the pier, where he hears the same note. |
| C10 aquarium goal, five months | c2_aquarium objective, intro, intercom | adapted | 911 call stays at the opening, because Chapter 3's identity test uses its exact words. |
| C11 ship order, oldest memories, Admiral | c2_ship.in.07, command, escape, nora, intake | applied | Display rule shows "Nora's copy" on the ship. |
| C12 prove you exist, rules, mail | c3_house.crossword, rules, mail | adapted | The test is the 911 call on June's machine (fresh private fact), not June's first words. The coffee spill comes after. |
| C13 Meridian, stakeout, Rook, text | c3_archive.power lead, out.04 to out.12, out.03 display_text | applied | Meridian arrives through Agnes's newspaper and June. |
| C14 gate | c7_gate.badge, post, truck, outro | adapted | No new gate_guard voice. Rook's copy works the gate (he runs the liaison in the plot). |
| C15 tone, bandage swap, engine demand | c7_swap ctx, map, bus, tone, outro | adapted | The tone is explained from the processions and Frank's tape, not Mrs. Penhallow. c1_pier.bait was not added to the signing case. |
| C16 Mom's cut voicemail | c8_beach.second, refuse, intro, out.01 | applied | Splice is made from the new Helen take. |
| C17 capture, Choir, Wick | c9_choir intro, truth, wick; c10_station.in.04 | adapted | The truth board uses Steve's own tapes (good morning, Rook, Iris). |
| C18 Agnes reveal | c10_town intro in.04 to in.09; wind; outro | applied | Echoes the Veyr line word for word. |
| C19 Saren on air, cues | c10_live in.02, in.03, second, third, outro | applied | Third cue uses the critic's numbers. |
| C20 good stuff | c5_shack.notes, out.01 | applied | |
| C21 van, charge, Ward stakes | c4_escape.van, out.01, out.02; c4_safe.screens | adapted | Van is a rows puzzle with two "slowing" calls (critic). |
| C22 cut copied order stages | all listed boards | applied | c8_lab.notebook keeps a real order stage; its evidence is now shuffled so the order is deduced. |
| C23 emotional beats | c9_gallery.link, talk; c9_choir.note; c10_town.console; c9_wake.rook; plus c5_shack.club, p_veyr.record, c8_beach.refuse, one_year.newwind | applied | Button style is M2. |
| C24 relapse, reunion first, initials | c9_gallery.in.01, out.06, antenna; c9_wake.agnes, rook.01 | applied | Initials O.T. and M.V. (critic). |
| C25 recognition puzzles | c9_wake.helen; c8_lab.lastpage; c9_choir.wick; postcredits.answer | applied | Wick's phrase is given in hertz, as at the lab. |
| C26 echoes, Tirel, Vigil | i1_archive in.03, reset, signals, quiet, out.01, out.02 | adapted | out.02 stays spoiler safe until Chapter 7. |
| C27 levels | p_veyr.levels, record.02; shield removed | applied | |
| C28 two Calders, handwriting | c6_jail in.04, mail.02, crossword, exit; c6_iris.in.02; c4_safe.match.01; c1_dinner.in.05 | adapted | The no-capitals habit is planted by Tomás at dinner, not a fridge note. |
| C29 hold music, notebook motive | c6_iris.hold, hold.04; alibi | applied | Calls are now taped at 00:04 (audit fix). |
| C30 Stephen's name, timing puzzles | c5_station intro, stephen, automation, halcyon, out.02 | adapted | Halcyon became the early-nights pattern. Automation uses the critic's three rows. |
| C31 AutoRick board | c10_station.playlist | applied | AutoRick's line is the board's wrong_text. |
| C32 Agnes ambiguity, survey | c10_report.echo, survey, report | applied | |
| C33 lab reconstruction | c8_lab.in.01, notebook, props, out; c8_rig intro, path, source, rig | adapted | Mrs. Penhallow is in the lab in person (plot), not a memory. |
| C34 Helen's word | p_meeting.terms, confess, record cut | applied | Pinyin on screen (critic). |
| C35 closing storybook | storybook "after" panels 2 to 4 | applied | |
| C36 AutoRick manhunt, Chapter 9 threat | c6_iris.in.03 to in.05; c9_gallery.in.04 to in.06 | applied | Flood line given to Steve (critic). |
| C37 locked leads, i2 prompts | i2_nora.patrol, pump | applied, UI deferred | Locked-lead text and progress counter are M2. |

### Critic's corrections

| Item | Where it landed | Status | Note |
| --- | --- | --- | --- |
| C12 with C11: crossword logic | c3_house.crossword | adapted | Asks about the newest memory (Sunday's 911 call) and checks it against June's own recording. |
| C11: intake labels, flat duplicate | c2_ship.intake; c2_aquarium.intercom evidence 3 | applied | |
| C04: route recall, neutral relay names | c10_station.route; c8_rig.source finding; c5_shack.club.05 | applied | |
| C30: automation timing | c5_station.automation | applied | |
| C28: mail.02 gives away the crossing | c6_jail.mail.02 | applied | The crossing is in the mail finding by design (Steve circled it himself); row 2 is the deduction. |
| C34: no CJK font | p_meeting.terms.lead.01 display_text | applied | |
| C06: wrong bait stage | c1_pier.bait | applied | |
| C19: third cue ambiguity | c10_live.third | applied | |
| C16: Tirel line | c8_beach.out.01 | applied | |
| C25: post-credits gap, Wick text matching | postcredits.answer; c9_choir.wick | applied | |
| C10: intercom states answers | c2_aquarium.intercom | applied | |
| C24: initials match real sleepers | c9_wake.agnes | applied | |
| C02: prompts as goals | `goal` field everywhere | applied | |
| C14/C15: wrist | c7_gate.post.03, post.04; c7_swap.map evidence 1, 3 | applied | |
| C03 with C05/C10: weekday | c1_flat when, card; c1_pier, c1_dinner, c1_escape when | applied | |
| C21: van copies evidence | c4_escape.van | adapted | Rows, not a board. |
| C11: nora board repeats itself | c2_ship.nora | applied | One stage. |
| C05 to C36: delivery tags, voice pass | validator delivery list; recording-list.csv | deferred | Caption styles are M2. Recording is M8 after approval. |
| C36: Stephen cannot remember the flood | c9_gallery.in.05, in.06 | applied | |
| C13: sea wall view | c3_archive.out.09 | applied | Boathouse steps. |
| C01: wrong text on boards | `wrong_text` on all boards | applied | |

### Missing from the plan

| Item | Where it landed | Status | Note |
| --- | --- | --- | --- |
| Saren's move to the ship | c10_live.out.10 | applied | |
| Notebook notes spoil the copy | c1_escape.order note, c1_escape.cross note | applied | |
| Why the Archivist lied | c10_report.in.04 | applied | |
| Lullaby reaction in Chapter 2 | c2_ship.nora.lead.02; payoff c9_wake.helen.lead.02 | applied | |
| Staging and new speakers | `present` lists; no gate_guard | applied | Audit added Agnes to c1_escape, Calder to c2_ship, Frank to c10_live, and lists for one_year and postcredits. Engine actor lists come with `--apply`. |
| Tests for new solution arrays | `game/tests` | deferred | M2. |

## (d) The user's requests and where they are met

| Request | Where |
| --- | --- |
| Steve stumbles on the identical greeting while doing something ordinary | c1_flat intro in.05 to in.08 (saving Mom's tape, timing the recorder), c1_flat.saturday and sunday lines (Nora's greeting caught in passing), c1_flat.compare.02 and .03 (he notices only while checking the ident), c1_flat.recap. |
| The harbor visit has real background | c1_pier.ctx.01 to .04 (crab boats, the winch, the fish-shed line with June, Agnes's stall, Nora's Sunday visits to Admiral), plus the whistle and bait backgrounds and the Lyle apology lead-in. |
| Finding narration after each solved puzzle | `finding` on 99 of 101 leads. |
| Recap narration when a scene is cleared | `recap` on 32 of 34 scenes; most recaps end by pointing at the next place or the next problem. |
| Lead-in, background and goal on every puzzle | `lead` on 79 leads, `background` and `goal` on all 101 (the validator enforces the last two). |
| Three hints that never give the answer | All 88 puzzles. Rewritten in this audit; hint 3 names the deciding fact, not the option. |
| No spoilers before their scene | Spoiler rules in `00-global.json` (validator), plus this audit's display rules for the Prefect and for the sleeping Mrs. Penhallow. |
| Challenging but fair | Difficulty 2 to 3 for most puzzles, decoy cards on 14 board stages, wrong answers that fail for a stated reason. Every fact a puzzle needs is planted earlier and kept in the notebook. |
| Leads come from relationships and town roles | Carmen's camera, the brothers' arguments, Tomás's podcast, June's 911 machine and list, Dale's mail round, the Town Hall clerk's ledger, Luis and Frank's club, Gus's poster, Pell's sorting case, Lyle's son's play, Frank's call sign, Nora's phone tree. |

## (e) Fixed during this audit

Hints (every chapter):
- Hint 3 rewritten so it no longer states the answer, on all 88 puzzles: p_bay.tune, message; c1_flat.saturday, sunday, compare, control; c1_pier.whistle, door, bait; c1_dinner.birthday, family, podcast; c1_escape.order, power; c2_aquarium.plan, guard, intercom; c2_ship.command, escape, nora, intake; c3_house.crossword, rules, mail; c3_archive.paper, power, cycle; i1_archive.reset, signals, quiet; p_veyr.levels; c4_safe.record, match, screens; c4_escape.tube, fault, van; c5_shack.notes, rig, log; c5_station.automation, sleeve, halcyon, stephen; c6_iris.alibi, takes, hold; c6_jail.mail, distract, crossword, exit; i2_nora.patrol, jobs, pump, message; c7_gate.badge, post, truck; c7_swap.map, bus, tone; p_meeting.terms, confess; c8_lab.notebook, props, lastpage; c8_beach.second; c8_rig.source, path, rig; c9_gallery.antenna; c9_wake.frank, helen, agnes; c9_choir.truth, wick; c10_station.playlist, route, relay; c10_town.lights, wind; c10_live.first, second, third; c10_report.echo, survey, report; postcredits.answer.
- Hint 2 rewritten because it gave the answer or was wrong: p_bay.tune (gave 815 kHz), c2_ship.intake, c3_house.crossword (said the 911 call was the newest thing before the chair; it was not), c5_station.halcyon, p_veyr.levels, c10_live.second.
- c1_flat.sunday hint 3: "Copy every detail" broke the "copy" spoiler rule; rewritten.

Prologue and Chapter 1:
- c1_flat.control options 1 and 2 now match the notebook theories (tired, reading too much since the boat); wrong feedback 1 and 2 and the finding rewritten to match.
- c1_flat.in.01: Mom's voicemail now has delivery `recorded_playback`, because Helen is not in the room.
- c1_pier.ctx.01 and ctx.04 (new): harbor background, and June introduced at the fish shed before the bait board relies on her. The two Admiral lines are now ctx.02 and ctx.03.
- c1_dinner.birthday: stray trailing periods removed from the options.
- c1_dinner.family.lead.05: Mateo now says he coaches the Little League games, which sets up "Mateo's coaching book" in Chapter 3.
- c1_dinner.recap.01: the change is dated "between the end of May and the first Sunday in June", matching the finding and the May 29 tape.
- c1_escape.ctx.02: the raincoat no longer hangs on a hook that Steve then hangs it on, and no longer claims she was in the car all evening.
- c1_escape.order.01: "She couldn't have signed this there" became "She couldn't have been in the north wing."
- c1_escape.power.lead.01 (new): Steve names the way out before the settings puzzle.
- c1_escape present: Agnes added (she speaks on the beach).
- Coach tips added to c1_dinner (first settings rows) and c1_escape (look things up in the notebook).

Chapter 2:
- c2_ship.recap.03: no longer says the copy "let me go" when she had just walked him to the chair.
- c2_ship.escape.01: delivery `recorded_playback`; the Prefect's voice comes from Dad's recorder.
- c2_ship present: Calder added (she speaks on the beach).
- Display rule: the Prefect is shown as "The Prefect" through c3_archive. Steve does not hear the name Saren until Iris says it in Chapter 6.
- Coach tips added to c2_aquarium and c2_ship.

Chapter 3 and Interlude 1:
- c3_house.mail wrong feedback for Biscuit: no longer refers to "Thursday", which made no sense for a Monday delivery.
- c3_archive.power.lead.05: "next week the President flies in" was wrong on Friday the 26th; now "on November seventh".
- c3_archive.cycle background: no longer hands over the last loud date, so the dated box labels matter.
- Coach tip added to i1_archive.

Chapter 4:
- c4_escape.tube: the tube room ASH renamed ALDER (instruction and hint) so it does not collide with the Ash jack in Chapters 8 and 10.

Chapter 5:
- c5_shack.club.05 and club background: the Thursday club now answers on a Friday for a stated reason ("none of us ever really switch off").
- c5_station.ctx.02: the ident no longer plays "every hour on the hour", which clashed with the 7:15 ident in Chapter 1.

Chapter 6 and Interlude 2:
- c6_iris place: "Bellwether after dark" clashed with Monday morning; now "Bellwether, the market and the pier".
- c6_iris.hold: Iris could not have taped two calls at 23:53 while walking in the procession. Background, prompt, evidence labels, hold.03 and the finding now place the calls at 00:04, after she turned back, when the water lit up.
- c6_iris.hold.05: adds that the President's own physician scanned her, which c7_swap.map's background relies on.
- c6_jail.crossword hint 3 points at the notebook entry by name.
- Coach tips added to c6_iris and i2_nora.

Chapter 7:
- c7_gate.post.03, post.04, c7_gate.recap.02 and c7_swap.map evidence 1: "Ward signed the accord at 11:54" clashed with the 11:58 ceremony. Now she signs for Pell's letter at 11:54, the burn is on her left wrist from the accord folder, and Pell says the time aloud.
- c7_swap.recap.02 (new): Iris is a copy too. The recap says how she held on through the tone, so the player is not left asking why she did not turn.
- c7_swap.map wrong_text: "wearing the wrong wrist" reworded.
- Coach tip added to c7_gate.

Chapter 8:
- p_meeting.confess.lead.01 (new): Helen's lead-in before the joint statement.
- c8_lab.notebook: case notes reordered so the order stage is deduced, not copied (C22's own rule).
- c8_lab notes: art note for Helen's last page.

Chapter 9:
- Display rule: the sleeping Mrs. Penhallow is "Mrs. Penhallow, row three" through c9_wake. The old label "Agnes Penhallow, original" gave away the Chapter 10 secret one scene early.
- c9_gallery.out.03: direction says the message plays from every speaker, which the next two lines depend on.
- Coach tip added to c9_wake.

Chapter 10 and after:
- c10_town.in.07: Steve links Mrs. Penhallow to "the records officer Iris told me about" (c6_iris.hold.04) instead of guessing.
- c10_town.in.09 (new): Agnes says what Veyr was. No human had named Veyr to Steve, yet later prompts used it.
- c10_town.recap.01: reworded ("part of the ship's record keeper, the part that stayed ashore").
- c10_live.second.lead.01 and c10_live.third.lead.01 (new) lead-ins; Frank added to c10_live present.
- c10_live.third wrong feedback for 54 no longer names the right beat.
- c10_report.survey background: "Ten nights ago" was wrong; the last ninth night was nine nights ago. It also says why she now has the key.
- one_year and postcredits: `present` lists now include everyone who speaks.

Follow-up review (story walkthrough, same day), details in `docs/story-walkthrough.md`:
- i1_archive.reset case note 2: Gus's first kelp tray is now "eight days ago, on Monday", matching June's list in c3_house.rules.
- c8_rig.path.03 and the c8_rig note: Rook's copy reports the team's location without forgetting; by the script's rule he only starts to forget in Chapter 9.
- c9_choir.truth lead line, prompt, background, hint 3 and note: Steve presents his notebook list, not a reel, because Rook kept his tapes in Chapter 4.
- c4_safe.in.07 (new narration) and c8_beach.second background and prompt: Mom's voicemail cassette stayed in Steve's pocket when Rook took the evidence tapes.
- Dad's recorder is a cassette recorder throughout: c2_ship.escape cues renamed Cue 01 to 03 (options, labels, hint, background), c2_ship.intake options, labels, prompt and background, c2_ship coach, c9_wake.frank background. Other characters' reels and spools keep their names.

## (f) Needs a structural decision

1. **No way out after hint 3.** C01 planned "Show answer" as the third hint. The user asked for hints that never give the answer, so hint 3 now stops one step short. Recommendation: in M2, add a separate "Show answer" button that appears only after hint 3 has been read and two more misses, asks for confirmation, and is not counted as a hint. No task changes.
2. **Settings rows have no specific miss line.** The tool stores `wrong_text` for boards only, so 39 rows puzzles, one tape and one dial fall back to a generic line. Recommendation: let `script_v2.py` accept `wrong_text` on rows, tape and dial tasks, show it in the panel, then write one line per puzzle in a follow-up pass.
3. **Answer position.** In choices and compares the answer is the first or second option in 21 of 24 tasks. Players can learn that. Recommendation: the engine shuffles option order on display and checks by option text, so no answer index changes. The alternative is to reorder options in the edit files, which changes answer indexes and needs sign-off from the engine agent.
4. **"What Steve knows" for other characters.** The background label is fixed, but some leads are played as the Archivist (i1_archive, p_veyr, c10_report), Helen (p_meeting, postcredits), Nora (i2_nora and some Chapter 9 and 10 leads) or Stephen. Recommendation: the engine labels it "What <actor> knows", using the task actor, or the scene's point of view when there is no actor. A `pov` field per scene would make this explicit.
5. **Chapter 1 opening beats.** C05 wanted c1_flat.saturday as a non-graded beat. It is now a three-option tutorial choice that teaches how wrong-answer feedback works, and c1_flat.sunday is similar. Recommendation: keep both as choices. Converting them to beats would change option counts.

Not structural, but worth knowing:
- Dad's recorder wording (cassette, reel, spool) was settled in the follow-up review: it is a cassette recorder throughout; see section (e).
- Difficulty peaks at 4 only once (c2_ship.escape). The plan wanted 4s in Chapters 5 and 10. The ratings are labels only; raise them if playtesting agrees.

## (g) Engine requirements the script relies on

From `docs/script-v2/report.md`:
- **Lead-in conversation** that plays when a lead is first opened, before its puzzle, on 79 leads (full list in report.md).
- **Case boards with decoy pieces** (more pieces than slots): c1_dinner.podcast stage 2, c1_escape.order stages 1 and 3, c1_pier.bait, c2_aquarium.intercom, c2_ship.command stage 2, c3_archive.power, c4_safe.screens, c5_station.sleeve, c5_station.stephen, c6_iris.alibi stage 1, c9_choir.truth, i1_archive.quiet, i1_archive.reset.
- **Case boards with one, two or more than five slots**: c1_dinner.podcast stage 2, c1_escape.order stage 1.

Also relied on (release plan M2 and the edit fields):
- Finding narration after each solved lead; recap narration when a scene is cleared, then the move to the next place.
- Wrong answers show their reason in the panel; the missed option is disabled; hint 1 is offered after two misses. Board `wrong_text` shows on a failed check.
- Goal and background on every puzzle panel and board; hint buttons say "Hint 1 of 3".
- Beats use one Continue button. Locked leads say what unlocks them.
- Coach tip card per scene, shown until the first lead is solved.
- Delivery styles change the caption look: narration, phone, radio, intercom, broadcast, memory, voicemail, recorded_playback, private_recording. These must not be treated as evidence audio.
- Line-level `display` labels (for example "Steve Mercer?", "June at the desk") and `display_text` (pinyin, lowercase texts).
- Display rules by scene from `00-global.json`.
- Multi-step objectives (`objective_steps` in c1_escape).
- Actor switching for leads with an `actor`.
- Text-only playback: no recording means the subtitle stays for a time based on its length, and a click or key continues.

## (h) Art needs

From the scene notes in `script.json`. Match the painted style of the existing rooms and inserts. Store new inserts in `game/assets/illustrated/campaign/inserts/`.

| Priority | Scene | What it must show | Used in |
| --- | --- | --- | --- |
| Recommended | c1_dinner | Carmen's birthday photo strip pinned by the register: three snapshots of Nora stamped 20:04, 20:15 (holding the kitchen check) and 20:29. | c1_dinner.birthday; reused in c1_escape.order |
| Recommended | c1_escape | The rain-soaked work order: Bellwether Aquarium letterhead, NORTH WING, signed N. Reyes, wall-clock time 20:30, dated on Carmen's birthday. | c1_escape.order |
| Recommended | c3_archive | Stakeout from the boathouse window at midnight: townspeople walking down the path into glowing surf, a woman in a good wool coat turning back at the waterline, a small old woman on the boathouse steps. | c3_archive departure |
| Recommended | c8_lab | Helen's last notebook page: three pencil strokes, the second joined to the first and climbing, a gap, then one long stroke lower than both; margin note "repeats after the low note". | c8_lab.lastpage; reused in c9_choir.wick and postcredits.answer |
| Optional | c1_pier | Admiral hauling out beside Steve, matching inserts/c1_pier.webp. | c1_pier.whistle |
| Optional | c3_house | June's list, "People who got better overnight", thirty-one names in her handwriting, Lyle Boone near the top. | c3_house.rules |
| Optional | i1_archive | The windowless meeting room seen through frost, or the p_meeting painting behind a memory filter. | i1_archive departure |
| Optional | c6_jail | Gus's bakery van with a giant croissant on its roof, at the loading door. | c6_jail departure |
| Optional | i2_nora | Row Zero: one enormous eye open under cracked frost. | i2_nora departure |
| Hotspot only | c2_ship | A hotspot and approach point on the flooded intake grille in the existing painting. No new picture. | c2_ship.intake |

New sound assets are listed in the scene notes too: effect.kbwr_ident (c1_flat), effect.harbor_winch, effect.nora_whistle_flat, effect.steve_whistle (c1_pier), effect.hum_first_reel and effect.hum_last_reel (c5_shack), effect.halcyon_hold_seattle and effect.halcyon_hold_denver (c6_iris), effect.wick_high_ending (c8_lab), recording.saren_splice (c8_beach), and the faint hum mixed under recording.voicemail (p_bay).

## (i) November 22 revision: Chapters 4 to 7

A playthrough to Chapter 7 found gaps a player would notice. Each fix changes the script edit files and staging only; puzzle answers are unchanged except where a time moved.

| What a player asked | What the story now says | Where |
| --- | --- | --- |
| How did Steve get into a van, and away from the agents? | The safe house is in the hills above the bay. Rook books Steve a 5 a.m. van to Bellwether "for processing". House rules send a protected witness out in his own van in any alarm, so the BLUE drill puts him in it six hours early. He jumps on the gravel bend, keeps the escort's radio, hears the roadblocks and dogs, and walks down the creek bed to Dad's shack. | `c4_safe` outro, `c4_escape` (context, drill, van, recap, outro), `c5_shack` context |
| How did the two Steves meet, and why is Stephen on his side? | Stephen woke in a tank on Friday the 26th with a crew pass, an earpiece and orders from Saren. He was the man at the market, watched June's house, followed Steve to the shack twice and overheard "the station library". At KBWR he stays hidden until Steve has the notebook. When Saren calls the earpiece, Stephen lies for Steve. He keeps reporting "north" every night. | `c5_station` (lead, outro), `c6_iris` context, staging `reveal_after` |
| Iris becoming Iris | After naming herself she shows the pressed iris from the balcony, the first thing she kept for herself, says she has hidden in the otter house since Tuesday, and says her name again, differently. | `c6_iris` outro |
| The Sheriff's office made no sense | The scene is at four in the afternoon, matching the painting's light. June's copy is out on the harbor and is heard only on the front-desk radio. Steve comes in under the parcels in Pell's mail cart, on Iris's tip. The circled crossword square proves who is in cell two. Stephen sends June's copy to the north jetty. Gus and Iris stay outside. All jail times are 12-hour afternoon times. | `c6_iris` recap, `c6_jail` (context, leads, recap), staging |
| How did they reach the President? | They plan on Tuesday in Gus's bakery: nobody official can be called, because the FBI's man is Rook's copy. June writes to the President and Pell delivers it into her hand. June and Iris walk in with Gus's catering passes. In the tunnel Ward reads June's letter and asks to meet Steve. | `c7_gate` intro and recap, `c7_swap` context and `tone` |

New story paintings show the drill, the jump, the watcher on the path, the two Steves face to face, the earpiece lie, the pressed iris, the mail cart, the bakery plan and the bakers at the gate. The shack-to-station bridge now shows Steve alone, with Stephen waiting by the station. New sounds (cue): `drill_alarm`, `van_jump`, `earpiece_click`, `pressed_flower`, `mail_cart`; masters and prompts in `assets/audio/story-effects/`.

## (j) November 23 revision: Chapters 5 and 6, Interlude 2

A second playthrough found plot holes in the middle of the story. The fixes change the script edit files, staging and two small engine hooks: a body can leave after a set line (`leave_after`), and a talk topic can close once a task is done (`until`).

| What a player asked | What the story now says | Where |
| --- | --- | --- |
| How does Steve know about his copy so early? | Carmen's sighting of a cheerful Steve at the market (Chapter 3) is the only hint. At KBWR Steve recognizes Stephen as that man before Stephen says a word. | `c5_station` (`stephen` lead, recap) |
| Why are there no copies of Helen and Frank? | Helen's scan was damaged, so her copy would not know where the notebook is, and the town had already buried them when the empty boat came back. They are kept asleep so the notebook still has an owner the crew can ask. | `c5_station` outro |
| How did two Steves run into Iris? | They don't. Stephen is the decoy at Gus's bread window at 8:10 and leaves by the alley. Steve meets Iris alone at the pier. The market task cannot start until the alibi is solved. | `c6_iris` (staging, `takes` requires `alibi`) |
| Isn't Stephen hunted too? | Stephen is the hunter in the crew's eyes, and the posters hunt Steve's face, so Stephen shows his face only on purpose, as the decoy. | `c6_iris`, `c7_gate` |
| June's copy never appears, so how does she leave? | Once Iris says "Steve didn't take me" at the market, the search ends. June's copy and Lyle's copy are on the harbor calling the boats in, heard only on the desk radio. Steve walks in alone. By dark the posters say "fled federal custody" and June's copy knows who opened cell two. | `c6_jail` (rewritten) |
| Why doesn't the deputy report Steve? | Lyle's copy never sees him. The school-play choice and the front-desk and checkpoint leads are removed. | `c6_jail` |
| How did Nora get out of her pod? | On Sunday night the crew took Iris below to be reset and left her on a laundry cart in the Gallery. She set a slow, reversible wake on Nora, Lyle Boone and Dale, timed to finish Monday night, then rode out with the wash. In the interlude the glass stays shut until all three breathe alone; the panel reads MIRROR LINK ACTIVE. | `c6_iris` outro, `i2_nora` |

31 new or reworded lines are recorded (ElevenLabs v4, checked by local transcripts). No new paintings: the existing pressed-flower, Gallery, pod and market stills now play with the lines that describe them.

## (k) November 23 revision: action scenes, held characters and a whole-story pass

A third playthrough asked for three things. Action scenes should be shown, not only told. A person who is strapped down, hidden or guarded should not walk around freely. Nobody should walk through walls, pillars or props. A review of the whole script then found small mismatches between chapters. The fixes change the script edit files, staging, the floor maps and four small engine hooks:

- A person named in `reveal_after` is not in the scene until that task or line. The name menu greys them out, Q skips them, and a saved game that had them selected opens with someone who is present.
- A floor blocker can wait for a story event (`after`). A person painted in by a story layer takes up floor only once the story puts them there.
- A story layer also paints over the floor's cut-outs, so a person painted beside a prop stays whole when walkers pass in front of it.
- A talk topic's `after` can name a line as well as a task, so small talk opens once two people have met.

| What a player asked | What the story now says | Where |
| --- | --- | --- |
| People walk through walls, pillars and props. | Every walking floor was checked against its painting. The ship's column base, the archive lamp stand, the lab crates and the epilogue planter now block walkers. The floor is trimmed in front of the safe-house door leaf and behind the gate cage. Approach points and Pell's mark that sat inside props have moved, and the safe-house recorder is reached from open floor. | `illustrated-floor.json` (24 rooms) |
| How does Steve get out of the scan chair with someone watching? | Nora's copy and Lyle go back up to town, and the attendant stays at the chair. Steve plays the Prefect's recorded order into the grille at the notch marked sixty-one, and the buckle opens. The attendant never asked for a release, so they turn to argue with the speaker column. Steve creeps out along the front of the room, because the attendant at the column blocks the way behind it. Saren says "Look at the chair", and the attendant finds it empty and raises the alarm. Steve opens the intake valve in the floor, the sea floods the tunnel, and Admiral surges up in front of the attendant wading after him. | `c2_ship` (staging, floor blocker `ship_attendant`, three layers, seven stills, repainted room) |
| Steve stands in front of the gate guard, but his face is on every poster. | Steve rides through under the sound desk while Stephen drives. He is off the floor and can't be picked until the badge check is done. Inside the fence he climbs out. Only then can he chat with Pell, and with Shaw once she has introduced herself. | `c7_gate` (staging `reveal_after`, talk `after`, still `c7_gate-under-desk`) |
| Nora walks straight past the guard. | A Veyri guard walks his lap through the Gallery. The aisle to the pumps and the intercom is in his sight, so Nora stays on the pod side until she has timed him. Once he is through the far door, the aisle opens and he is gone from the room. | `i2_nora` (floor `guarded_aisle`, layer `i2_nora-guard`, two stills) |
| The jailbreak is only told. | Pell holds the back door while June's copy pulls up out front. Gus hands over the van behind his bakery. The new posters go up at dusk. Once they are out the back, the closing lines stay outside: the finding and the first recap line keep the back-door picture, and the rest of the recap moves to the bakery. | `c6_jail` (three stills) |
| How do June, Helen, Frank and Nora get into the Choir chamber? | When the Choir says "Stop", the straps open, the crew let go of Stephen and Saren steps back. June: "We followed you down from row nine. Nobody stopped us. The whole crew had stopped to listen." | `c9_choir.in.06`, `c9_choir.in.07`, three stills |
| How did Saren get Mom's voicemail to splice it? | Rook took every tape at the safe house, even the voicemail, and handed that one back an hour later: "Not evidence." On the beach Steve works it out: "Rook kept this tape for an hour at the safe house. Long enough to copy it." | `c4_safe.in.07`, `c8_beach.second.03` |
| June asked Steve to play the recording again, with Rook's agents in the hall. | Now she stops him: "Not here, Mercer. Not with Adrian's agents in the hall." | `c4_safe.match.02` |
| Why doesn't Steve go back for June after the jump? | "They'll scan June tonight, because she stayed behind for me. I can't get back up that hill alone." | `c4_escape.out.02` |
| How does Shaw know about the copies before the locked room? | She doesn't. The press-van warning is now Stephen's line. Shaw learns everything in the locked room. | `c7_swap.bus.lead.04` |
| The tone pulls at copies, so why doesn't Stephen walk to the sea? | "Beside me, Stephen gripped the desk with both hands and did not turn." | `c7_swap.recap.02` |
| Why does Stephen's crew pass still open the antenna passage? | "Cancelling it would put Saren's mistake on the record." | `c8_rig.path.lead.04` |
| Who sent signal three while Frank was asleep? | "The club sent signal three yesterday, without me." | `c10_station.relay.lead.01` |
| Rook's copy is "going with the ship", but the ship has gone. | He is "leaving town today". The bait-shop finding says the same. | `epilogue.talk.rook_copy.1.01`, `epilogue.bait.find` |
| When was June's case with Rook? | Twenty years ago, in Chapters 3, 4 and 9. | `c3_archive.out.11` |

28 new or reworded lines are recorded (ElevenLabs v4, checked by local transcripts). The transcript checker now treats "cancelling" and "canceling" as the same word. `c8_beach.second.find` keeps its first wording and its human-approved take; the new fact is a separate line, `c8_beach.second.03`. 21 pictures are new or repainted: the ship room, three ship layers and seven ship stills, the Gallery guard layer and two Gallery stills, and stills for the jail (three), the gate (one) and the Choir (three).

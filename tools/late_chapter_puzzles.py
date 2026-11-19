"""Player-facing clues for the second half of Night Nine's illustrated campaign."""


def apply_late_puzzles(content):
    tasks = {task["id"]: task for scene in content["scenes"] for task in scene["tasks"]}

    def choice(key, evidence, options, answer, hints, note=None):
        task = tasks[key]
        assert len(options) >= 2 and 0 <= answer < len(options) and len(hints) == 3
        task.update(prompt=evidence, options=options, answer=answer, hints=hints)
        task.pop("puzzle", None)
        if note:
            task["note"] = note

    def board(key, evidence, instruction, rows, hints, note=None):
        task = tasks[key]
        assert len(hints) == 3
        task.update(prompt=evidence, hints=hints)
        task["puzzle"] = {
            "instruction": instruction,
            "rows": [{"label": label, "options": options} for label, options, answer in rows],
            "solution": [options.index(answer) for label, options, answer in rows],
        }
        if note:
            task["note"] = note

    choice("c6_iris.alibi",
           "Steve’s appointment is at 8:10. Stephen has three chances for someone else to remember seeing him. Which one puts his face in public at the same time?",
           ["Buy flowers from the unattended stall at 8:10", "Ask the baker to correct the wanted poster during her 8:10 window sale", "Sign for the 8:20 bread delivery beside the poster"], 1,
           ["A timestamp and a face can come from different sources.", "Who can personally vouch for a face at 8:10?", "Talk to the baker during the window sale. She will see Stephen while Steve is at his appointment."])
    # The two independently voiced readings and their waveform comparison already
    # give players a fair experiment. Keep their original takes and listening hints.
    choice("c6_iris.hold",
           "Iris marks three calls on the café receipt. At 9:00 two people dial different Halcyon offices. Both stay through the same hold tune and hang up at the same bar. A caller who reaches a clerk hangs up early. Which timing should Steve compare with the procession at the bay?",
           ["Minutes each clerk spends speaking", "Time between dial tone and pickup", "The shared passage in the hold tune"], 2,
           ["Look at what the two long calls have in common.", "Different offices and waiting times leave one sound in common.", "Compare the shared passage in the hold tune with the bay schedule. The two listeners hang up at the same musical bar."])
    board("c6_jail.mail",
          "Pell has a carbon dated today. DESTINATION / ITEM reads ‘Jail / returned key.’ In the register, the jail’s last three numbers are 14 (signed), 18 (returned), 19 (signed). The drawer tabs read Counter, Returns, Jail. Pell filed by destination. Drawer slots hold pairs starting with 1 and 2.",
          "Find today's return in Pell's case.", [
              ("Drawer", ["Counter", "Returns", "Jail"], "Jail"),
              ("Slot", ["7", "9", "10", "18"], "9")],
          ["Separate the destination from the parcel status.", "Use the returned entry in the jail register. Two consecutive numbers share a slot.", "Find the jail drawer, slot 9. Entries 17 and 18 share it."],
          "Pell kept the key in Jail, slot 9. On June’s folded crossword Steve pencilled a circle round the crossing of 23 Across and 8 Down before he passed it through the slot.")
    choice("c6_jail.distract",
           "The desk book lists three appointments at noon. Stephen looks exactly like the man on the town poster. Which clerk would need him standing at the public counter for the entire appointment?",
           ["Lost property, to identify a coat over the intercom", "Records, for a new likeness on a contested poster", "Mail, to sign a collection slip at the side hatch"], 1,
           ["Stephen needs a reason to stay in view.", "A signature or a description can be taken elsewhere.", "Ask Records to correct the wanted photograph. The clerk needs Stephen's face in front of her."])
    board("c6_jail.crossword",
          "Both Calders have the town edition. Only one received Steve’s marked copy after the cell door closed. His pocket grid reads ‘23 Across: beyond imitation (10), I _ I _ I _ A _ L _’. The down headings over its first, second and last blanks are 3, 8 and 12. Radio or paper? The guard can hear the radio; June can slip back a square of paper.",
          "Use Steve’s notebook entry for Pell’s sorting case. Ask for the marked crossing, then check the handwritten reply.", [
              ("Crossing to ask for", ["17 Across / 8 Down", "23 Across / 3 Down", "23 Across / 8 Down"], "23 Across / 8 Down"),
              ("Accept the slip with", ["An M circled", "A T circled", "An A circled"], "An M circled")],
          ["Retrieve the private mark from the entry for Pell’s sorting case. The public crossword alone proves little.",
           "Solve 23 Across, then count its letters from the left for the crossing.",
           "Ask for 23 Across / 8 Down and accept the circled M. INIMITABLE has M as its fourth letter."])
    choice("c6_jail.exit",
           "Lyle’s copy has written ‘Front row, two boys’ beside tonight’s duty roster. His partner has already signed the relief line. The school ticket says ‘Admit one’. June waits for Steve to speak.",
           ["Offer to keep the ticket safe until the morning", "Tell him his relief has signed and let him decide where to go", "Ask if June can take his seat and tell him how the boys did"], 1,
           ["Read his ticket alongside the duty roster.", "A relief officer is already present. Who has a seat?", "Tell Lyle his relief has signed. Give him the choice to go see his sons."])

    board("i2_nora.patrol",
          "Nora scratches times against the bed rail. On the first lap: boots at 02, pump at 05, door at 08, boots again at 14. The guard can see the aisle until the door shuts. It takes four counts to cross. On the next lap the boots arrive at 14.",
          "Use the next lap and allow all four counts for the crossing.", [
              ("Step out at count", ["17", "20", "23"], "20"),
              ("Reach cover at count", ["21", "24", "27"], "24")],
          ["Find the length of a whole lap using the boots.", "The door closed six counts after the boots. Add four more for the crossing.", "Leave at 20 and reach cover at 24, before the next boots at 26."])
    choice("i2_nora.jobs",
           "Nora asks for volunteers. Lyle has kept two doors from jamming. Dale can repeat all five turns with his eyes shut. Nora has sketched where the blue water crosses the return pipe. Which rota leaves someone at each job they have practised?",
           ["Dale at the latch, Nora on directions, Lyle at the gauge", "Nora at the latch, Lyle on directions, Dale at the gauge", "Lyle at the latch, Dale on directions, Nora at the gauge"], 2,
           ["Read the three volunteers’ own observations.", "Start with Dale. Who would you trust to lead the return trip?", "Give Lyle the latch, Dale the turns and Nora the gauge."],
           "Lyle minded the latch. Dale remembered the turns. Nora traced circulation through the Gallery.")
    board("i2_nora.pump",
          "Nora copies the readings from the three service trials. Amber: bed flow 4, hatch pressure 7. Blue: bed flow 4, hatch pressure 2. White: bed flow 1, hatch pressure 2. The handwritten limits are bed flow at least 3 and hatch pressure below 3.",
          "Set the service branch. Decide which reading gives Nora clearance to open the hatch.", [
              ("Branch", ["Amber", "White", "Blue"], "Blue"),
              ("Clearance on both gauges", ["Beds 1 / hatch 2", "Beds 4 / hatch 2", "Beds 4 / hatch 7"], "Beds 4 / hatch 2")],
          ["A low reading on the hatch alone cannot tell you about the beds.", "Amber keeps bed flow up. White relieves pressure. Test the remaining branch against both limits.", "Choose Blue and wait for beds 4 / hatch 2."])
    choice("i2_nora.message",
           "Three slots on the Gallery intercom: A plays in every bed now, B keeps one message by this bed until someone presses PLAY, C clears itself when Dale changes the watch. Steve may arrive on another watch. Where can Nora leave her words?",
           ["Slot C", "Slot A", "Slot B"], 2,
           ["Who should hear the message, and when?", "Nora needs it to survive a change of watch.", "Use slot B. Only a visitor at this bed can start playback."])

    choice("c7_gate.badge",
           "Pell’s list has a red dot for delivery staff, a blue stripe for contracted crew and a gold seal for signatories. The gate board gives times: red 11:20, blue 11:40, gold noon. Stephen’s card has a stripe; its printed face is his. Which appointment is his?",
           ["11:20, deliveries", "Noon, delegation", "11:40, contracted crew"], 2,
           ["Look at the mark on Stephen’s card.", "Only one appointment shares his crew stripe.", "Use the blue 11:40 appointment."])
    choice("c7_gate.post",
           "Pell’s envelope needs Ward’s own signature and a counterfoil he can take back. The press desk stamps copies. The delegation clerk brings the signer to the hatch. The stage manager signs receipts for scenery.",
           ["Leave both sheets at the press desk", "Keep the counterfoil at the delegation hatch for Ward", "Take the stage manager’s receipt back to the post office"], 1,
           ["Pell needs two things from one delivery.", "Whose signature belongs on the returning half?", "Use the delegation hatch and keep Ward’s signed counterfoil."])
    choice("c7_gate.truck",
           "A sound check failed at the back fence. Steve’s docket reads ‘return meter required’. Cameras show a local monitor, the stage van has lamps, and the Halcyon truck has a return strip still showing the fence. Where can he verify the repair?",
           ["Camera monitor", "Stage van", "Halcyon truck"], 2,
           ["Who can see what the far end received?", "A local monitor can look good when the far end hears nothing.", "Use the return strip in the Halcyon truck."])
    choice("c7_swap.map",
           "Pell saw Ward sign before the ceremony. At 11:56 the physician and a patient pass a camera with a chipped east-stair tile. At 11:57 someone in Ward’s coat reaches the podium. A lift log puts all lifts on the west side until noon. Which route should Calder check for the patient?",
           ["Service tunnel at the east stairs", "West lift from the press gallery", "Podium gangway from the public gate"], 0,
           ["Follow the last sighting of the patient.", "Use the tile to place the camera; the coat can travel separately.", "Follow the service tunnel to the east stairs. That is the physician’s last verified route."])
    board("c7_swap.bus",
          "Steve writes down everyone who heard each test. Amber: lectern and press van. Blue: lectern, back fence and service steps. Green: back fence and service steps. Calder tries the return. Copper: Steve, Iris and the lectern. Slate: Steve and Iris. Pearl: Steve alone.",
          "Sound the tone for the people standing at the lectern, fence and steps. The press van feeds the TV audience and must stay on ceremony audio. Calder’s reply is for Steve and Iris alone.", [
              ("Tone send", ["Amber", "Green", "Blue"], "Blue"),
              ("Recovery-team return", ["Slate", "Pearl", "Copper"], "Slate")],
          ["Trace the tone and Calder’s reply separately.", "Green misses one group by the stage. Copper would put Calder on the lectern speaker.", "Use Blue for the three groups in the grounds and Slate for Steve and Iris. Neither goes to the press van."])
    choice("c7_swap.tone",
           "Steve marks two events: Ward’s double at the lectern (11:58:10), Calder and Iris with the patient (11:58:14). The public feed closes at 11:58:18. The tone takes two seconds. Which start gives Calder time to reach the real Ward and keeps the whole tone on air?",
           ["11:58:11", "11:58:15", "11:58:17"], 1,
           ["Mark the first moment when both teams are in place.", "The two-second tone must finish by :18.", "Start at :15. The recovery team is in place, and the tone ends at :17."])

    choice("c8_lab.notebook",
           "Helen’s undated slips read ‘our demonstration’, ‘their demonstration: our broken beat again’ and ‘both teams at one table’. Her date index puts the table after both tests. In the margin by the broken beat she wrote ‘heard this before’. What order belongs in the notebook?",
           ["Their test, our test, table", "Our test, their test, table", "Our test, table, their test"], 1,
           ["Start with the slip the date index places last.", "Helen recognized a blemish on the second slip.", "File our test first, their test second and the table last."])
    choice("c8_lab.props",
           "Shaw rolls the film and Wen reads the old test sheet. At the apparent surge, three drum strikes coincide with three lamp flashes. The fog keeps drifting after the meter drops. Which two crew members need the same cue?",
           ["Drums and lamps", "Lamps and fog", "Fog and drums"], 0,
           ["Find two effects with separate, matching starts.", "The fog outlasts the meter. Count the other two effects.", "Cue the drums with the lamps. Their three starts coincide."])
    board("c8_lab.lastpage",
          "Helen drew three strokes from Frank’s hydrophone tape. Stroke two touches the first and climbs higher. A space follows, then the longest stroke falls below both. Wen can read the notes in the margin; she has no translation for the marks themselves.",
          "Audition Frank’s three reels or use their listening captions. Label the reel and decide what Steve can file as evidence.", [
              ("Reel to keep with Helen’s page", ["Reel 07", "Reel 11", "Reel 14"], "Reel 11"),
              ("Notebook finding", ["A match in rhythm and pitch", "A word-for-word translation", "A match in the reel length alone"], "A match in rhythm and pitch")],
          ["Compare where the ink strokes touch and where Helen lifted her pencil.", "The first two sounds run together. Listen for the lower, longer note after the space.", "File reel 11 with the page. The lengths and pitches match; Wen still needs a translation."],
          "Helen’s last page matches reel 11 of Frank’s hydrophone tape: two joined notes rise, then a longer low note follows a space. The words remain unknown.")
    last_page = tasks["c8_lab.lastpage"]
    last_page.update(
        sounds=["effect.ninth_night", "effect.wick", "effect.meridian_pulse"],
        evidence_labels=["Reel 07 · one steady note", "Reel 11 · two rising notes together, gap, long lower note", "Reel 14 · five separate notes, the third cut short"])
    choice("c8_beach.first",
           "Steve has the recorder running when Saren names a price and offers a date for their release. Three takes fit the reel. Which pair would let Steve compare the promise itself?",
           ["Record Saren’s offer and his next answer to a different question", "Record the offer, then have Steve read it back", "Keep the first take and ask Saren to repeat the whole offer"], 2,
           ["Keep the speaker and the requested words constant.", "A second voice or a fresh question changes the experiment.", "Keep the first take and ask Saren for the same words a second time."])
    choice("c8_beach.refuse",
           "Steve has two matching takes of the promise. He has received a date, no independent word from his parents, and no way to recover the notebook once he gives it up. What can he honestly say when he answers Saren?",
           ["Two takes establish two independent guarantees", "He has one assurance and will keep the notebook", "The matching takes prove his parents have already left the ship"], 1,
           ["Separate what the promise says from how often Steve heard it.", "The same performance cannot supply independent confirmation.", "Keep the notebook. Steve has heard one assurance twice."])
    choice("c8_rig.source",
           "Wen tries three control feeds. On A the flare lands one beat late even when Shaw changes the cue. On B it follows Shaw early on one trial and late on the next, exactly when she moves her hand. On C the flare leads her change by a beat. Which feed can answer a cue the fleet has never seen?",
           ["Feed A", "Feed B", "Feed C"], 1,
           ["A changing sequence can still be a recording.", "See which output follows an unexpected change in Shaw’s hand.", "Take feed B. It follows both of Shaw’s changes."])
    board("c8_rig.path",
          "Wen’s paper trial has three receipts. Dock signed ‘camera saw lamps’. Mast signed ‘ship measured lamps’. Shore signed ‘ship received crew’s numbers’. The fleet asks for its own measured return. On the team sheet Stephen can open the antenna passage; Nora has already found an occupied row and a route out.",
          "Choose a receipt the fleet can verify and assign two simultaneous jobs.", [
              ("Measurement receipt", ["Dock", "Mast", "Shore"], "Mast"),
              ("Stephen’s assignment", ["Gallery beds", "Antenna passage", "Shore camera"], "Antenna passage"),
              ("Other team", ["Bring sleepers through the Gallery", "Wait for the camera receipt", "Read shore figures to the ship"], "Bring sleepers through the Gallery")],
          ["Read who took the measurement, not just who received the page.", "Only one receipt has the ship as observer. The other job follows the occupied beds.", "Choose Mast, send Stephen to the antenna passage, and bring the sleepers through the Gallery."],
          "The fleet accepted measurements from its own ship. A camera picture or a set of figures delivered from shore could not replace a ship reading.")
    choice("c8_rig.rig",
           "The crew tests three couplers on a dummy meter. A passes the cue outward and returns the stage hum. B blocks the hum and the cue. C passes the outward cue and keeps the return meter still. Stephen needs the stage cue at the antenna and the stage hum off its return.",
           ["Coupler B", "Coupler C", "Coupler A"], 1,
           ["Read each coupler in both directions.", "Eliminate the one that blocks the cue and the one that returns the hum.", "Use C. The cue passes outward and the return stays still."])

    choice("c9_gallery.antenna",
           "A painted emblem appears on each side of the gallery door. The inner pad accepts a crew pass. Calder’s visitor slip is stamped observation deck only. Steve promised Nora he would stay within earshot. Who takes the inner pad?",
           ["Stephen, with the crew pass", "Calder, with the visitor slip", "Steve, with Stephen’s pass"], 0,
           ["Consider the pass and the person Nora needs beside her.", "The observation deck and antenna passage have different marks.", "Stephen takes the crew pass to the antenna. Steve stays beside Nora."])
    choice("c9_gallery.link",
           "Nora can blink but cannot move her hands. Iris is holding the release and has asked to use it. Her memory gauge drops when she eases it open. Steve can tell her what he sees and stay with them both. Whose decision is he waiting for?",
           ["Iris’s, after she sees the gauge", "Nora’s, after she can take the handle", "Stephen’s, after he opens the antenna door"], 0,
           ["Look at who is holding the release.", "Iris has already told Steve how she wants to use it.", "Tell Iris what the gauge shows, then accept her decision to release Nora."])
    choice("c9_gallery.talk",
           "Nora has counted five months here and thirteen months of silence before it. Steve can answer for the part that began at home. What should he start with?",
           ["Why he stopped talking before she was taken", "Why Iris chose to break the link today", "Why his parents invited him on the boat"], 0,
           ["Nora has named two different absences.", "Which absence came from a choice Steve made?", "Answer for the thirteen months of silence at home."])
    board("c9_wake.frank",
          "Nora finds three call cards: K7BWL, K7BLW and K9BLW. Frank’s bed mic catches five groups: −·− / −−··· / −··· / ·−·· / ·−−. The desk key lists K −·−, B −···, L ·−··, W ·−−, 7 −−···, 9 −−−−·. A scratched playback head can lose the last group; the operator asks for that group separately.",
          "Identify Frank's card and its last group. The Thursday club recording is beside the bed.", [
              ("Card", ["K7BWL", "K9BLW", "K7BLW"], "K7BLW"),
              ("Final group to repeat", ["·−··", "·−−", "−···"], "·−−")],
          ["Compare the second group to distinguish the two digits.", "The fourth group has four strokes and the fifth has three.", "Select K7BLW and repeat ·−−, the W."])
    choice("c9_wake.helen",
           "In the margin beside Helen’s bed, Frank pencilled the tune Steve used to fall asleep to: home note, up, higher still, then back through the first rise. One box holds the six-note family melody. The other sleeves hold Frank’s five Morse groups and a single warning tone.",
           ["Five-group radio identification", "Single sustained warning", "Six-note family melody"], 2,
           ["Frank used the radio card for himself.", "Look for a contour a parent could sing.", "Play the six-note family melody for Helen."])
    choice("c9_wake.rook",
           "Calder’s old voicemail contains Adrian’s own reassurance to her. The safe-house recording used the very same performance. Nora wants to try a cue that can change if Adrian stirs. June is at the bed; the two old clips are on Steve’s reel.",
           ["Play the safe-house clip, then its voicemail match", "Ask June to address Adrian and wait for his response", "Play Adrian’s voicemail and ask June to mouth the words"], 1,
           ["Who speaks on the two recordings?", "Nora has someone at the bed who can answer Adrian now.", "Ask June to speak to him in person."])
    choice("c9_wake.agnes",
           "Nora’s row-three list has three objects: a crew ledger labelled A.R., a glasses case with a tiny bait-shop price sticker, and a pair of gloves stitched H.M. The woman is squinting at Nora’s name badge. Which object should Nora put in her hand?",
           ["The crew ledger", "The stitched gloves", "The stickered glasses case"], 2,
           ["Combine what the woman is trying to do with what Nora recalls of row three.", "The price sticker connects the case to the bait-shop owner.", "Give Agnes the glasses case and call her name."])
    choice("c9_choir.truth",
           "A miner’s first account in the Choir ends ‘nobody came’. Years later she recorded the names of the people who found her. Her voice and archive number match in both entries. What evidence of change can Steve ask the Choir to play?",
           ["The first entry twice at different levels", "Both entries in the order she gave them", "Her archive number spoken by two different clerks"], 1,
           ["Look for something that changed during one life.", "The archive number identifies the witness. Her two accounts show what she learned.", "Play the earlier account and then her later account."])
    choice("c9_choir.wick",
           "Wick sings two joined tones. The second climbs. After a break, a lower tone follows. Helen has her notebook, Frank’s call card and the timetable from the bay. Which can she place on the music stand to follow Wick into the next phrase?",
           ["The final page Helen made from Frank’s hydrophone tape", "Frank’s radio call card from the Thursday club", "The bay’s ninth-night procession timetable"], 0,
           ["Recall the gap Helen marked at Meridian.", "Choose the page that records the contour as well as the spacing.", "Use Helen’s final page. This is the pattern she heard in Frank’s hydrophone recording."])
    choice("c9_choir.note",
           "The damp fold reads ‘kiddo’, ‘boat’ and ‘bring your ears’. Helen’s notes are in shorthand. Frank calls Steve ‘kiddo’ on air. Steve wants the rest of the invitation in its writer’s own voice.",
           ["Ask Helen to translate the note", "Ask June to compare signatures", "Open it with Frank and let him finish"], 2,
           ["Read the greeting as well as the invitation.", "Who uses that greeting for Steve?", "Open it with Frank. These are the words he meant Steve to hear."])

    choice("c10_station.playlist",
           "AutoRick’s log from the last outage has three entries. Traffic: queued after the song. Ident: opened the engineer’s maintenance door and kept the song on air. Bulletin: gave the microphone to the duty host until sign-off. Steve wants to talk to the town and still hear their answer.",
           ["Book the traffic slot", "Sign the bulletin as duty host", "Use the ident to open maintenance"], 1,
           ["Getting inside the booth and getting on air are separate jobs.", "Check what the audience heard during the last ident.", "Sign the bulletin as duty host. That entry put the microphone on air until sign-off."])
    board("c10_station.route",
          "Wen puts the patch tests on paper. Sources: Birch changed on Shaw’s hand signal; Elm repeated the last song; Ash carried a steady check note. Returns: A gave a booth echo; B gave a shore camera picture; C gave a measurement signed aboard the Long Patience. The tower ceiling is 8 divisions. Two cues together peak at 11. The pad trims 2; the limiter caps at 8.",
          "Patch a fresh performance, choose the return the fleet can verify, and keep both cues within the tower ceiling.", [
              ("Source jack", ["Elm", "Ash", "Birch"], "Birch"),
              ("Accepted return", ["Return C", "Return A", "Return B"], "Return C"),
              ("Level stage", ["Pad only", "Straight through", "Limiter in"], "Limiter in")],
          ["Work from the three slips separately: source, observer and peak level.",
           "Use the rig team’s finding about who must measure the show. An 11-division peak through the pad still reaches 9.",
           "Patch Birch to Return C with the limiter in. Shaw changed Birch live, the ship signed C, and the limiter holds the peak at 8."],
          "Birch followed Shaw live. Return C carried the ship’s own measurement. Wen kept the limiter on for the combined cues.")
    choice("c10_station.relay",
           "Frank sends ‘cue four’ once. The official line returns yesterday’s cue three. The club operator at Sentinel repeats four and gives a new wind reading on request. A second club operator repeats four but cannot hear Steve’s follow-up. Who should acknowledge tonight’s changing cues first?",
           ["The official operator", "The second club operator", "The Sentinel operator"], 2,
           ["Confirm that the path works in both directions.", "One operator can answer a new question.", "Call the Sentinel operator through Frank’s club. They repeated four and answered the wind check."])
    board("c10_town.lights",
          "Nora has two street captains and one spare phone. Pier can see Orchard's lamps. Orchard faces inland and cannot see Pier. Both can hear KBWR. If every phone stays on the show, nobody can call the fire crew.",
          "Arrange a visible handoff: one street leads, the other answers what it sees. Keep emergency calls possible.", [
              ("First street", ["Pier", "Orchard"], "Orchard"),
              ("Spare phone", ["Keep free for the fire crew", "Join both captains in a show call"], "Keep free for the fire crew")],
          ["Draw an arrow from the lamps toward the captain who can see them.", "Orchard can hear Steve; Pier can see Orchard. Only the spare phone remains.", "Start with Orchard and keep the spare phone free for the fire crew."],
          "Orchard starts on KBWR. Pier can see Orchard and answers its lamps. Nora keeps the spare phone free for the fire crew.")
    choice("c10_town.console",
           "Shaw’s stage lamps show when the harbor response arrives. Wen’s grid crew can raise load on the next beat. If they follow independent wall clocks, Wen sometimes fires first. Which mark belongs on the common cue sheet?",
           ["Wen follows Shaw’s observed lamp mark", "Both teams start on their wall clocks", "Shaw follows Wen’s predicted load time"], 0,
           ["The desired order starts with something seen at the harbor.", "Wen needs a mark that corrects for the harbor’s actual response.", "Have Wen follow Shaw’s observed mark."],
           "Shaw takes the visible field cue. Wen waits for confirmation before she raises the live grid response.")
    choice("c10_town.wind",
           "Agnes has one spool from Veyr. It has a pencil tail mark after the last gust. The Choir can answer Steve from aboard the ship. He wants listeners to hear both home as it was and a voice answering them now. What cue should he mark on the spool?",
           ["Restart the spool at the tail", "Open the Choir’s return after the last gust", "Record the Choir on the leader for every replay"], 1,
           ["Find the point where the old recording has finished speaking.", "Keep the Choir free to choose its own answer.", "Open the Choir’s return at the tail mark, after the last gust."],
           "Agnes marked the tail of the original wind from Veyr. The Choir has an open return for its live answer.")
    board("c10_live.first",
          "Steve is live with three slips. ORCHARD: relay heard the call, no lamps yet. PIER: last rehearsal left two lamps glowing. FIELD: Shaw has a hand on the follower bank. From his desk Steve can see both streets. He needs evidence of a reply made during this broadcast.",
          "Use the phone tree Nora prepared. Cue one street and choose the observation that releases Shaw’s bank.", [
              ("Call first", ["Pier", "Orchard", "Sentinel field"], "Orchard"),
              ("Release Shaw on", ["Two Pier lamps already glowing", "Orchard’s first flash alone", "A new Pier flash after Orchard changes"], "A new Pier flash after Orchard changes")],
          ["Look in the notebook for Nora’s sightline between the streets. A lamp already on tells Steve very little.",
           "Only one captain can see the other street. Shaw needs proof that the second street saw the first change.",
           "Call Orchard. Release Shaw when a fresh Pier flash follows Orchard’s change. The two old Pier lights are left over from rehearsal."])
    board("c10_live.second",
          "Frank logged three returns on Steve’s beat clock. Test at 10 with the coast connected: Birch 10, Reed 12, Bell 12. Test at 20 with the coast unplugged: Birch 20, Reed silent, Bell 22. Test at 31, coast reconnected: Birch 31, Reed 33, Bell 33. Cue four leaves at 40.",
          "Arm the coast return. When its fresh reply arrives, Shaw uses that beat for the field lamps. Wen needs two consecutive beats on the same supply. The crew needs the supply back at the start of beat 45. Hold if the coast stays silent.", [
              ("Coast return fader", ["Bell", "Birch", "Reed"], "Reed"),
              ("Reserve for Wen", ["Beats 42 and 43", "Beats 44 and 45", "Beats 43 and 44"], "Beats 43 and 44")],
          ["Cover the first and last tests. Which return changed when Frank unplugged the coast?",
           "Use the connected runs to find the delay. Cross out the beat Shaw needs and the beat already booked by the crew.",
           "Arm Reed. Its expected reply at 42 is Shaw’s beat. Reserve 43 and 44 for Wen. If Reed stays silent, hold the cue."])
    choice("c10_live.third",
           "The master cue sheet has three marks. At 48 Wen confirms the grid. At 50 Agnes reaches the final gust; Steve can still hear it through 52. At 53 the Choir draws breath on the return. Where can Steve open the vocal channel and preserve its first word?",
           ["At 48, mixed under Wen’s confirmation", "At 50, with the gust still playing", "At the Choir’s intake at 53"], 2,
           ["Use the marks the people at the console can hear.", "Check the tail Agnes marked, then listen for a live entrance.", "Open on the intake at 53. Wen has confirmed and the wind has ended."])

    choice("c10_report.echo",
           "The two Agneses remember the last wind on Veyr. Only one can list the boat owners who took bait on credit during Bellwether’s bad winter. The Archivist needs a witness to what happened on shore. Whom should she invite?",
           ["The Archivist with her departure register", "Penhallow with the bait ledger", "Either one reading the old wind log"], 1,
           ["A shared memory predates the shore assignment.", "Look for an experience acquired during three years in town.", "Hear Penhallow’s bait ledger and her memories of those customers."])
    board("c10_report.survey",
          "Saren sealed three slips. Reef 6: water and air, beacon answers every inquiry. Sound 4: air, no liquid water, silent. Reach 2: water and air, three unoccupied-ground surveys on separate visits. The fleet needs a living world with evidence of room to settle.",
          "Choose which surveyed world to disclose and what makes its claim to empty ground the strongest.", [
              ("Survey", ["Sound 4", "Reach 2", "Reef 6"], "Reach 2"),
              ("Evidence for ground clear", ["The channel was quiet once", "An automated beacon replied", "Separate visits found no settlements"], "Separate visits found no settlements")],
          ["A silent receiver alone tells you little about who lives there.", "Require both a living environment and repeated observations on the ground.", "Disclose Reach 2 and attach the three independent surveys of unoccupied ground."])
    choice("c10_report.report",
           "The fleet asks for two signed attachments: evidence of the danger at Earth, and coordinates for another living world. Steve has the camera film and the ship’s own live measurement. The Archivist has the newly opened survey. Which packet can she stand behind?",
           ["Ship measurement and the Reach 2 survey", "Shore camera film and Reach 2’s quiet-channel log", "Ship measurement and Reef 6’s beacon acknowledgment"], 0,
           ["Use one result from Wen’s patch and one from Saren’s survey.", "The fleet accepted its own ship as observer. Which world has repeated settlement surveys?", "Send the ship’s live measurement and the Reach 2 survey."])

    # The ending is a coda. Small recognitions leave time for the conversations.
    choice("epilogue.neighbors",
           "A chalkboard outside the café has a blank for tomorrow’s mail round. Dale left his retirement card beneath it. Pell’s bag is under the bench and Biscuit waits at the gate. Who should Steve ask about the first delivery?",
           ["Dale, at his retirement breakfast", "Pell, beside his bag", "Lyle, on his way to the school"], 1,
           ["Look for the person starting a shift.", "Dale’s card and Pell’s bag tell different stories.", "Visit Pell and Biscuit for the morning route."])
    choice("epilogue.bait",
           "Two chalked prices face one another across the bait counter. By the ferry, Rook and his copy share one boarding ticket between them. Steve has space for one line under each visit. What did he actually see?",
           ["One stall closing; two seats on the ferry", "Two prices at the shop; one traveler at the ferry", "Two stalls merging; two travelers staying ashore"], 1,
           ["Count the prices, then count the tickets.", "Look for what each person chose for themself.", "Record the two competing prices and the one traveler."])
    choice("epilogue.coffee",
           "In the kitchen, yesterday’s voicemail is still cued to play. A new note has a coffee ring across Dad’s freshly labelled paint tin. Nora is standing by the door with her coat. Steve can answer his mother and still keep whom he promised to meet.",
           ["Ask Nora to sit through the old voicemail", "Ring the station for a replay of yesterday", "Answer Mom, then go with Nora for coffee"], 2,
           ["Look around the kitchen Steve is in today.", "He can answer one person and keep his plans with another.", "Answer Mom, then go for coffee with Nora."])
    choice("one_year.newwind",
           "A package from the fleet carries a fresh date and the glass towers of its new home. The Veyr spool already has Agnes’s old tail mark. Steve and Stephen are at the live microphones. How can they let Bellwether hear where the fleet is today?",
           ["Play the new arrival, then open the brothers’ microphones", "Start the old Veyr spool at its tail mark", "Replay yesterday’s show over the arrival"], 0,
           ["Check the place and date on the package.", "The old spool preserves the home the fleet left.", "Play the new wind, then let Steve and Stephen speak live."])
    choice("postcredits.answer",
           "At three in the morning the receiver catches a low voice. Helen traces the first signs: rise without a break, space, then a longer fall. One reference in her notes came from listening rather than translation. Which should she open before she tries to answer?",
           ["Meridian’s lamp schedule", "Frank’s Thursday-club roster", "Her transcription of Wick’s dream tones"], 2,
           ["Follow the contour back to its first appearance.", "Think of the page Helen compared with the hydrophone tape.", "Open the transcription of Wick’s dream tones and compare the incoming phrase."])

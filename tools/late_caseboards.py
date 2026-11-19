"""Investigation boards for the second half of Night Nine.

Answer indices refer to the pieces as authored. Shared receipts and exhibits
stay on the desk throughout the successive deductions in each case.
"""


def stage(mode, prompt, slots, pieces, answer):
    return dict(mode=mode, prompt=prompt, slots=slots.split("|"),
                pieces=pieces.split("|"), answer=answer)


def order(prompt, pieces, answer):
    return stage("order", prompt, "|".join(
        ["First", "Second", "Third", "Fourth", "Fifth"][:len(answer)]), pieces, answer)


def match(prompt, slots, pieces, answer):
    return stage("match", prompt, slots, pieces, answer)


def route(prompt, slots, pieces, answer):
    return stage("route", prompt, slots, pieces, answer)


def case(intro, evidence, *stages, hints):
    return dict(intro=intro, evidence=evidence, stages=list(stages), hints=hints)


CASES = {
    "c6_iris.alibi": case(
        "The poster shows Steve’s face. Stephen can give the town a true sighting of that face, if the time holds up.",
        [
            "Gus sets the oven clock four minutes fast. The bus clock is two minutes slow. The florist sets hers by the radio.",
            "Three slips: BREAD 08:14, BUS 08:05, FLOWERS 08:12. Steve’s appointment begins at 08:10 by the radio.",
            "The bus driver stamped the fare card through a slot. The florist called back a telephone order. At the bread window Gus corrected a smudge on the poster while his customer stood beside it.",
            "Iris has three envelopes: JUST BEFORE, DURING and JUST AFTER. Only the middle envelope needs a witness to a face.",
        ],
        match("Correct each slip to the radio clock.", "Bread|Bus|Flowers",
              "08:12|08:10|08:07", [1, 2, 0]),
        order("Pin the three envelopes in the order of the actual transactions.",
              "Bread window|Bus fare|Florist call", [1, 0, 2]),
        match("Label what a stranger could actually testify to at each stop.", "Bus|Bread window|Florist",
              "Voice on a phone|Face beside likeness|Fare card present", [2, 1, 0]),
        hints=["Use the radio as the common clock.", "Subtract four at the bakery and add two on the bus. Ask whether each witness saw a face.",
               "The bus reads 08:07, the window 08:10, and the flowers 08:12 in radio time. Gus can compare a face with the poster."]),
    "c6_jail.distract": case(
        "The desk copy can send a deputy away for only one appointment. Plan a distraction Stephen can sustain without ever entering the cell corridor.",
        [
            "Three brass tickets: 41 is paid in coins, 42 needs a likeness checked, 43 is a form already signed. The slot accepts paper only; a cashier is behind frosted glass.",
            "The likeness clerk has to compare the applicant in person with the public poster. No part of that examination can happen by telephone.",
            "The noon stamp is accurate. The front-counter register opens two minutes before noon and closes four minutes after. The deputy leaves the records desk one minute after the register opens, and returns one minute before it closes.",
            "Steve needs two complete minutes in the empty corridor. He must start strictly after the deputy leaves and finish strictly before she returns. Choose whole-minute marks.",
        ],
        match("Send each ticket to the only desk that can finish it.", "41|42|43",
              "Document slot|Likeness counter|Cashier", [2, 1, 0]),
        order("Reconstruct the four marks on the duty strip.", "Deputy returns|Register opens|Register closes|Deputy leaves",
              [1, 3, 0, 2]),
        match("Write the duty times on Steve’s pass.", "Deputy leaves|Steve starts|Steve finishes|Deputy returns",
              "12:02|12:03|11:59|12:00", [2, 3, 0, 1]),
        hints=["First distinguish a paper transaction from somebody checking a face.", "The register is open from 11:58 to 12:04. The deputy’s absence is shorter.",
               "The deputy leaves at 11:59 and returns at 12:03. Stephen stays at ticket 42 while Steve uses noon to 12:02."]),
    "c6_jail.exit": case(
        "Lyle is still on duty at the checkpoint. June wants to show him that he can leave of his own accord. Sort the evening papers before the van comes.",
        [
            "Three signatures have been rubbed off. The embossed star appears only on duty records. The school uses perforated stock. Gus writes on the waxy back of a bread order.",
            "The perforated stub says ADMIT ONE / FRONT ROW. Two boys’ names are pencilled in the margin. The waxed slip promises a bakery van at the loading door.",
            "Relief signs at 18:24. The school doors close at 18:40. A walk from the jail takes 18 minutes. Bus A leaves at 18:29 and takes 9 minutes; bus B leaves at 18:26 and takes 15 minutes.",
            "House practice: check that cover is signed before inviting a deputy to hand over. The signed RELIEF line covers the post. The time on the school stub is a firm last entry. Only after Lyle elects to leave can June collect the group at the loading door.",
        ],
        match("Return the torn slips to their owners.", "Perforated stock|Star embossing|Waxed slip",
              "Gus|Duty desk|School", [2, 1, 0]),
        match("If Lyle leaves as soon as his relief signs, work out his school-door arrival for each route.", "Walk the whole way|Wait for bus A|Wait for bus B",
              "18:41|18:42|18:38", [1, 2, 0]),
        order("Lay out June’s handover so Lyle keeps control of his decision.",
              "Lyle chooses whether to leave|Read the relief signature|Meet the van|Offer him the stub", [1, 3, 0, 2]),
        hints=["Feel the edges of the three slips.", "A school stub admits one person; it cannot release someone from duty. Use the departure time of each bus, or start walking when the relief signs.",
               "The walk arrives at 18:42, A at 18:38 and B at 18:41. Check cover, offer Lyle the stub, wait for his choice, then meet the van."]),
    "i2_nora.jobs": case(
        "Three sleepers, one trip along an aisle they can cross only between patrols. Nora must fit each person’s knowledge to the route.",
        [
            "Lyle left two fresh wedge marks on a sticking hatch. Dale can recite the turn sequence without opening his eyes. Nora drew the lines in the return-water circuit.",
            "Nora’s pencil map: from the beds the striped aisle ends at the sticking hatch. Beyond the hatch a fork has lost its arrows. Each branch ends in a gauge cabinet.",
            "Dale’s memory: at the fork the nearer turn led straight back to the beds. The other turn ended at the gauge beside a cold return pipe.",
            "At the right cabinet, the upper dial belongs to the empty wash line. The lower dial is stamped RETURN. Nobody has opened a pipe yet.",
        ],
        match("Set the first person responsible for each job.", "Keep an exit available|Guide the party at the fork|Read the working circuit",
              "Dale|Nora|Lyle", [2, 0, 1]),
        route("Trace the walk from bed to the instrument Nora needs.", "Aisle end|Next landmark|Turn to take|Final instrument",
              "Far branch|Lower dial|Sticking hatch|Unmarked fork", [2, 3, 0, 1]),
        match("Log what each sleeper could check on this trip.", "Lyle|Nora|Dale",
              "Which circuit the gauge reads|Which branch returns home|Whether the hatch stays open", [2, 0, 1]),
        hints=["Each skill came from something Nora personally observed.", "The hatch comes before the fork. The nearer turn takes everyone back.",
               "Lyle wedges the hatch, Dale takes the far branch, and Nora reads the lower RETURN gauge."]),
    "c7_gate.badge": case(
        "One familiar face, two people, three ways through the gate. Reconstruct access for the venue before Stephen presents his crew pass.",
        [
            "Gate card: red dot at 11:20, blue stripe twenty minutes later, gold seal twenty minutes after blue.",
            "The tray with the earliest window takes individual deliveries. The last window admits accord signatories. A Halcyon crew pass is valid in the only remaining window.",
            "Pell’s satchel holds a counterfoil. Stephen’s pass has a strip of blue thread. Ward’s folder has a raised seal. Steve has no credential of his own and travels with the sound truck.",
            "Use the right clock: the gate runs on event time. The wristwatch Stephen borrowed is five minutes fast.",
        ],
        match("Identify each mark from the time and purpose of its window.", "Mail delivery|Contracted crew|Signatory",
              "Gold seal|Red dot|Blue stripe", [1, 2, 0]),
        order("Place the credential holders in admission order. Steve is already in the sound truck.", "Stephen|Pell|Ward", [1, 0, 2]),
        match("Write the correct reading of Stephen’s wristwatch at each gate opening.", "Red|Blue|Gold",
              "11:45|12:05|11:25", [2, 0, 1]),
        hints=["Use one event clock for all three badges.", "The crew window is between the mail and the signatories; a fast watch reads later.",
               "Pell enters at 11:20, Stephen at 11:40 and Ward at noon. Add five minutes for each watch reading."]),
    "c7_gate.post": case(
        "Pell wants Ward’s signature on an original and proof of delivery for his bag. Follow one envelope through three very similar hatches.",
        [
            "The press desk keeps a photocopier and a publicity stamp. The delegation clerk can call Ward to the hatch. The stage manager signs only on behalf of the venue.",
            "Pell must compare the still-sealed cover to his bag log before the clerk opens it. The outside bears the dispatch number. Inside are the white petition and its yellow carbon, still clipped together.",
            "Ward presses through both sheets when she signs the white one. Then the clerk files the white sheet with the delegation. Pell takes the matching yellow impression back.",
            "A returned receipt needs two independent matches: the dispatch number against the bag log and the impression against the white original. A publicity stamp supplies neither.",
        ],
        match("Label the authority behind each desk.", "Stage door|Press office|Delegation hatch",
              "Publicity only|Can summon the signer|Venue only", [2, 0, 1]),
        order("Handle the papers without losing the carbon impression.",
              "Separate the sheets|Match dispatch to bag|File the signed original|Ask Ward to sign the clipped set", [1, 3, 0, 2]),
        match("Reconstruct where each piece of evidence belongs.", "Pell’s outgoing log|Delegation file|Pell’s return pouch",
              "Yellow impression|Dispatch number|White original", [1, 2, 0]),
        hints=["A clerk may bring a signer to the desk. A clerk’s own signature has a different meaning.",
               "The carbon must remain under the original during the signature; the bag number is visible before opening.",
               "Match the dispatch, get Ward’s signature on both layers, separate them, file white and take yellow."]),
    "c7_swap.map": case(
        "A coat, a patient and a service lift appear in the fog. Calder wants a route to the woman Pell actually saw, using evidence with a time and place.",
        [
            "Pell watched Ward sign with a bandaged left wrist at 11:54. The physician supported a bandaged patient under camera E at 11:56. The camera at the podium recorded a coat at 11:57 but never saw its wearer’s wrist.",
            "Map legend: camera E looks down on a chipped stair tile. The west stair has an intact tile. There is only one door at the bottom of the chipped stairs, into the service tunnel.",
            "At 11:55 the service lift logged an empty trip. A red lamp indicates the door opened; the weight trace stayed at zero throughout.",
            "On Calder’s overlay, mark the last identified person, the route confirmed by a second observation, and the public sighting that cannot establish identity.",
        ],
        match("Match each record to the strongest fact it supports.", "Pell’s counterfoil|Podium camera|Lift trace|Camera E",
              "An empty trip occurred|A coat reached the lectern|Ward signed in person|Bandaged patient went downstairs", [2, 1, 0, 3]),
        order("Arrange the independent observations by time.", "Podium coat|Empty lift|Chipped tile|Bandaged signer", [3, 1, 2, 0]),
        route("Walk Calder from the last identified Ward to the search area.", "Start|Follow this person|Take this stair|Search beyond it",
              "Service tunnel|Physician with patient|Signature hatch|East stair", [2, 1, 3, 0]),
        hints=["Distinguish identifying a person from identifying a coat.", "Pell and camera E both saw a bandaged wrist. Only the east stair has a chipped tile.",
               "Follow Ward from the hatch with the physician down the east stair into the service tunnel. The lift carried nobody."]),
    "c8_lab.notebook": case(
        "Wen can read Helen’s notes, but the pages have come loose. Use a production fault to date the demonstrations and work out what the meeting could establish.",
        [
            "Scrap H reads ‘our demonstration’. Its strip shows two strikes, a missing beat and a lamp flare. Helen sealed the join with her thumbprint. Wen has Helen’s authenticated print on their correspondence.",
            "Scrap W reads ‘their demonstration’. It has the same missing beat and a different lamp flare. Wen remembers receiving a copy of H before her team made its demonstration.",
            "The table minutes quote both demonstrations and show both teams’ signatures. An unsigned invitation asks the teams to bring both strips to that meeting; the invitation was issued after both demonstrations.",
            "Helen distinguishes an observation from an inference: the two recorded lamp patterns differ; the missing beat recurs; the number of actual engines is never measured on either strip.",
        ],
        order("Date the four scraps from the evidence on the desk.", "Meeting minutes|Wen’s demonstration|Invitation|Helen’s demonstration", [3, 1, 2, 0]),
        match("For each comparison, choose what a reader can establish.", "Lamp flares|Missing drum beat|Working engines",
              "No measurement|Different lamp patterns|Shared production fault", [1, 2, 0]),
        match("Match each search question to the item that can answer it.", "Which team made H?|Did W follow H?|Did both teams formally meet?",
              "Both signatures|Wen’s account of receipt|Helen’s authenticated print", [2, 1, 0]),
        hints=["A quotation cannot predate the material it quotes.","Wen received H before making W. The invitation calls for two finished strips.",
               "Date H, W, invitation, minutes. Treat the missing beat as a shared fault and the differing flares as a real difference."]),
    "c8_rig.source": case(
        "An old film can look live on a single trial. Shaw changes her cue twice while Wen isolates three possible sources.",
        [
            "Shaw cues at beat 4 on trial one and beat 7 on trial two. On A, the flare comes at beat 5 both times. On B, it comes at 4 and 7. On C, it comes at 4 and 4.",
            "Shaw had made the rehearsal film on beat 4 and left it looping. Wen’s automatic lamp tester is fixed at beat 5. The hand-controlled feed has no fixed beat.",
            "Three covered jacks go to the meter. Birch connects to the feed that stayed at 5, Elm to the one that followed both cues, Ash to the rehearsal loop.",
            "Verification card: commit your prediction before drawing a fresh beat; let Shaw give the new cue without announcing it to Wen; afterwards, compare the return with the written cue.",
        ],
        match("Identify the source behind each letter.", "A|B|C", "Rehearsal film|Fixed tester|Shaw’s hand", [1, 2, 0]),
        match("Mark each jack with the source letter you would receive.", "Ash|Birch|Elm", "C|B|A", [0, 2, 1]),
        order("Use a third trial to challenge the apparent live source.", "Compare cue and return|Write what each source predicts|Shaw gives the cue|Draw a fresh beat", [1, 3, 2, 0]),
        hints=["One trial cannot distinguish B and C. Use the changed cue.",
               "Ask what stayed at 5, what stayed at 4, and what moved along with Shaw. Trace those patterns to the jacks.",
               "A is the tester on Birch, B is Shaw on Elm, and C is the film on Ash. Predict before drawing the surprise cue."]),
    "c8_rig.rig": case(
        "The prop table gives Wen three couplers with identical plugs. Qualify one on a dummy meter before letting Stephen carry it toward the antenna.",
        [
            "Signal direction: Shaw makes the cue at the prop console; the selected coupler sits between that console and the dummy load. The return meter reads what leaks back toward the console.",
            "With the output connected, A and C pass Shaw’s cue. B passes nothing. With the output isolated, a stage hum still shows up on the return through A. The return through B or C stays still.",
            "A usable coupler must pass the outward cue and keep local hum out of its return. A dead outward line can still look excellent if all you watch is a quiet return.",
            "For the acceptance run, first write down the uncabled baseline. Then push a surprise cue through the dummy. Pull the output plug while the local hum keeps playing. Sign only after both comparisons.",
        ],
        match("Give each coupler its diagnosis.", "A|B|C", "Isolated and passes cue|Leaks stage hum|Blocks the cue", [1, 2, 0]),
        route("Follow a deliberate stage cue along the bench and back to the observer.", "Origin|Interface|Test load|Leak check",
              "Return meter|Dummy load|Prop console|Coupler C", [2, 3, 1, 0]),
        order("Arrange the acceptance slips so a silent dead line cannot pass.", "Isolate output; leave hum on|Sign the run|Record uncabled baseline|Send surprise cue", [2, 3, 0, 1]),
        hints=["Check the outward and return paths separately.","B and C both have a clean return. Only one passes Shaw’s cue.",
               "Use C between the console and dummy load. Take a baseline, send the cue, then isolate the output and check local hum before signing."]),
    "c9_gallery.antenna": case(
        "Two teams need opposite sides of the Gallery door. Use the permits and the corridor sketch to divide the work without leaving Nora alone.",
        [
            "Stephen has the only crew pass. Calder’s visitor slip admits its holder to the observation deck. On the deck she can see the inner pad, but the slip cannot operate it.",
            "The inside pad is reachable from the crew lane. The status lamp is around the bend, visible from the deck only. It stays dark until the crew pass is accepted.",
            "Steve promised to remain by Nora’s bed. Iris needs a clear place at the release beside that bed. The portable rig needs a bearer in the crew lane.",
            "Calder’s plan uses one radio call from the deck after the status lamp changes and before Stephen departs toward the antenna; nobody should call success on a dark lamp.",
        ],
        match("Assign people to the marks where they can do useful work.", "Carry rig to crew pad|Watch the status lamp|Keep promise at bed|Reach the release",
              "Iris|Steve|Stephen|Calder", [2, 3, 1, 0]),
        match("Mark the evidence of access you could obtain at each station.", "Crew pad|Observation deck|Nora’s bedside",
              "Can witness lamp change|Can speak to Nora in person|Can present crew credential", [2, 0, 1]),
        order("Signal passage to the antenna without a premature all-clear.", "Calder calls confirmation|Stephen presents pass|Stephen departs the door|Lamp turns on", [1, 3, 0, 2]),
        hints=["Separate permission to watch from permission to open.","Only Stephen can satisfy the pad. Only the deck offers a clear view of the lamp.",
               "Stephen presents the pass; the lamp changes; Calder calls; Stephen goes on. Steve and Iris stay with Nora."]),
    "c9_wake.agnes": case(
        "Nora does not want to hand a half-awake stranger another sleeper’s belongings. Reconstruct row three’s displaced trays from the tags.",
        [
            "The tray numbers slid off in one piece. From left to right the bed marks are III-1, III-2, III-3. The middle bed’s resident has been squinting at Nora.",
            "Three belongings: a ledger stamped A.R.; a glasses case with a crooked price sticker; gloves with the initials H.M. Only the glasses case bears a shop sticker.",
            "The inventory says ‘A.R. left of the shopkeeper; H.M. right of the shopkeeper.’ Nora’s earlier list places Mrs. Penhallow in row three and identifies her as the bait seller.",
            "Nora’s return procedure: reconstruct the row before checking the shop sticker against the ledger entry. Offer the case without putting the glasses on anyone; wait for the owner to recognise it.",
        ],
        match("Return the objects to the three numbered trays.", "III-1|III-2|III-3", "H.M. gloves|Glasses case|A.R. ledger", [2, 1, 0]),
        match("For each fact, identify the independent detail that supports it.", "Bed order|Owner’s trade|Immediate difficulty",
              "Entry on Nora’s list|Left/right inventory|Squinting at Nora", [1, 0, 2]),
        order("Return the item and leave recognition to its owner.", "Wait for recognition|Check the sticker|Reconstruct the row|Offer the closed case", [2, 1, 3, 0]),
        hints=["Place the shopkeeper between the two initialled objects.", "A price sticker suggests a shop; Nora’s earlier list connects that shop with Agnes.",
               "A.R. is on the left, Agnes in the middle, H.M. on the right. After checking the sticker, offer the case and wait for her."]),
    "c9_choir.truth": case(
        "The Choir must decide whether two apparently contradictory entries can both belong to the same person. Reconstruct the record before asking anyone to erase a memory.",
        [
            "Entry T-41 ends ‘nobody came’. Entry T-41b names the people who found the speaker. The voiceprint and archive number agree across both entries.",
            "T-41 was sealed at the collapse. The names on T-41b appear on a rescue roll signed after the collapse. A later interviewer quoted both entries side by side.",
            "The first speaker could report only what she knew when the tunnel went dark. The later speaker knew who had searched. The rescue roll lists names but contains no account of being trapped.",
            "The Choir wants four dates preserved without editing earlier testimony: the collapse account, the rescue, the later naming of rescuers, and the interview using both.",
        ],
        order("Put the archive leaves into a chronology that permits both accounts.", "Later interview|Rescue roll|Names given by survivor|Entry at collapse", [3, 1, 2, 0]),
        match("Give each piece of evidence the question it can answer.", "Same speaker?|Did someone search?|What did she know in the tunnel?",
              "Her first testimony|Voiceprint and number|Signed rescue roll", [1, 2, 0]),
        match("Caption three copies for the restored record.", "T-41|T-41b|Later interview",
              "Knowledge after rescue|Knowledge at collapse|Both accounts considered", [1, 0, 2]),
        hints=["A person’s experience can change between recordings.","The rescue roll comes after the collapse and before the survivor can name her rescuers.",
               "Keep collapse, rescue, naming and interview in that order. The record number connects the voices, and each account keeps its own date."]),
    "c10_station.playlist": case(
        "The desk has a live mic, a running playlist and a maintenance latch. AutoRick’s outage slips have lost their headings. Reconstruct what each command actually did.",
        [
            "At 06:01 the song continued and the maintenance latch clicked. At 06:03 a traffic card went into a queue and stayed there until the song ended. At 06:05 the song dropped and a human voice appeared immediately.",
            "The three slips are IDENT, TRAFFIC, BULLETIN. Only the bulletin has spaces for the duty host’s signature and the live-air start time. The ident requests a maintenance check.",
            "The desk clock was two minutes ahead of the outage logger throughout. The three events above are logger times. Steve writes the desk times on his reconstruction.",
            "House practice: establish who is taking responsibility before you sign. Only the signed bulletin permits the live handover; check the on-air return after opening the mic.",
        ],
        match("Reattach the headers to the three events.", "06:01 logger|06:03 logger|06:05 logger", "Traffic|Bulletin|Ident", [2, 0, 1]),
        match("Convert the desk timestamps back onto the correct slips.", "Traffic|Bulletin|Ident", "06:07|06:05|06:03", [1, 0, 2]),
        order("Recover the broadcast without confusing a maintenance opening with airtime.",
              "Check the on-air return|Sign the bulletin|Declare the duty host|Take the live microphone", [2, 1, 3, 0]),
        hints=["Use the audio return and the latch as separate observations.",
               "The logger runs two minutes behind the desk. Only the 06:05 logger event displaced the song immediately.",
               "The slips read Ident, Traffic, Bulletin. On the desk they are 06:03, 06:05 and 06:07. Name the host, sign, go live, then check the return."]),
    "c10_station.relay": case(
        "Frank has three replies to a fresh cue. A fast echo can sound convincing. Work out which operator can actually observe Sentinel Point and pass back a new report.",
        [
            "Frank sent THREE yesterday and FOUR today. Alpha immediately returned THREE. Birch returned FOUR and supplied a fresh local wind reading when asked. Cedar returned FOUR but transmitted the very same wind phrase when asked a second question.",
            "Yesterday’s official circuit was logged under Alpha. The Thursday club has two volunteers: only one is physically at Sentinel Point. The distant volunteer can repeat a cue but cannot see the field.",
            "Frank chooses another surprise observation beyond the spoken number: after Birch classifies the gust, Shaw will signal a lamp change. The operator must describe the changed lamp before Frank passes the cue to the coast.",
            "On the relay strip the coast must acknowledge the cue before inland clubs repeat it onward. A returning acknowledgement is addressed to Frank; it should never be mistaken for a second outbound cue.",
        ],
        match("Label the strongest result from each reply.", "Alpha|Cedar|Birch", "Current cue, stale observation|Current cue and fresh local observation|Yesterday’s cue", [2, 0, 1]),
        route("Trace a verified instruction out from the booth.", "Origin|Field witness|First relay|Next relay",
              "Inland clubs|Frank at KBWR|Coastal operator|Birch at Sentinel", [1, 3, 2, 0]),
        order("Establish that your field witness sees the new state before the coast relays it.", "Coast receives verified cue|Coast acknowledges|Birch describes new lamp|Shaw changes lamp", [3, 2, 0, 1]),
        hints=["Matching FOUR is necessary, but it cannot identify someone standing at the field.",
               "Two respondents know FOUR. Only Birch answers a different question with new local evidence.",
               "Use Birch to observe Shaw’s change; send that verified cue to the coast, wait for acknowledgement, then let the inland clubs repeat it."]),
    "c10_report.report": case(
        "The fleet will act on a report signed aboard its own ship. Agnes asks you to separate what the fleet can verify from what the Archivist wants the fleet to understand.",
        [
            "The fleet accepts measurements from the Long Patience itself. A camera saw the lights on Earth; an onboard instrument independently measured the live changes. Only one of those records meets the fleet’s rule.",
            "Saren sealed three charts. Reef 6 answers a beacon hailing its residents. Sound 4 has air but no liquid water. Reach 2 has both and three separate surveys of unoccupied ground. A destination must support life and have evidence that nobody already lives there.",
            "The Choir’s ledger holds 312 lived human accounts. The instrument strip proves a measurement; the survey gives a destination; neither contains those lives. The report can offer an introduction as well as a course change.",
            "A fleet transmission requires the Prefect or the Archivist. The dispatch form locks its attachment field until someone logs the Prefect’s decision. Saren refuses. The ship logs attachments before its authorised signer confirms the packet, and the fleet can answer only after confirmation.",
        ],
        match("Classify the three sealed sites before picking a chart.", "Reef 6|Reach 2|Sound 4", "Missing water|Living, surveyed empty|Already inhabited", [2, 1, 0]),
        match("Attach the source the receiver can use for each claim.", "Measured danger|A habitable destination|People worth meeting",
              "Choir ledger|Long Patience instrument|Reach 2 survey", [1, 2, 0]),
        order("Finish the transmission after Saren declines to sign.", "The Vigil can reply|Archivist confirms packet|Log the evidence and survey|Record the Prefect’s refusal", [3, 2, 1, 0]),
        hints=["Apply both destination conditions; breathable air alone will not do.",
               "The fleet trusts its scout’s instrument. The Choir can introduce people but cannot establish a world’s occupancy.",
               "Attach the onboard measurement, Reach 2 survey and Choir accounts. After Saren refuses, log the attachments and let the Archivist confirm."]),
}

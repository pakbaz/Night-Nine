#!/usr/bin/env python3
import json
import unittest

import script_v2


class NarrativeContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = json.loads((script_v2.BASE_DIR / "campaign.json").read_text())
        cls.edits = script_v2.load_edits()
        cls.merge = script_v2.Merge(base, cls.edits)
        cls.content = cls.merge.run()
        script_v2.validate(cls.content, cls.edits, cls.merge)
        cls.scenes = {scene["id"]: scene for scene in cls.content["scenes"]}
        cls.lines = cls.content["lines"]

    def text(self, line_ids):
        return " ".join(self.lines[line_id]["text"] for line_id in line_ids)

    def task(self, scene_id, task_id):
        return next(task for task in self.scenes[scene_id]["tasks"]
                    if task["id"] == f"{scene_id}.{task_id}")

    def scene_text(self, scene_id):
        scene = self.scenes[scene_id]
        line_ids = list(scene.get("context", [])) + list(scene.get("intro", []))
        for topic in scene.get("talk", []):
            line_ids += topic["lines"]
        for task in scene["tasks"]:
            line_ids += task.get("lead", []) + task.get("lines", [])
            if task.get("finding"):
                line_ids.append(task["finding"])
        line_ids += scene.get("recap", []) + scene.get("outro", [])
        return self.text(line_ids)

    def test_compiled_narrative_validates(self):
        errors = [issue for issue in self.merge.issues if issue[0] == "error"]
        self.assertEqual(errors, [])

    def test_scan_index_is_not_copy_completeness(self):
        ship = self.scene_text("c2_ship")
        station = self.scene_text("c5_station")
        choir = self.scene_text("c9_choir")
        self.assertIn("memory index", ship)
        self.assertIn("Binding runs separately", ship)
        self.assertIn("Last stable binding", station)
        self.assertNotIn("Sixty-one percent of me", ship + station)
        self.assertIn("it wasn’t erasing them", choir)

    def test_nora_alibi_uses_stolen_credentials(self):
        order = self.task("c1_escape", "order")
        order_text = " ".join([
            order["goal"], order["background"], order["prompt"],
            self.text(order["lead"] + order["lines"] + [order["finding"]]),
        ])
        self.assertIn("staff credential", order_text)
        self.assertIn("same minute", order_text)
        self.assertNotIn("could have signed", order_text)

    def test_the_chair_does_not_announce_final_progress_before_the_escape(self):
        intro = self.text(self.scenes["c2_ship"]["intro"]).lower()
        self.assertNotIn("sixty-one percent", intro)
        self.assertIn("fifty-nine", self.text(self.task("c2_ship", "escape")["lead"]).lower())

    def test_nora_distinguishes_the_silence_from_the_time_in_the_gallery(self):
        recap = self.text(self.scenes["i2_nora"]["recap"])
        self.assertNotIn("quiet for eighteen months", recap)
        self.assertIn("thirteen months", recap)

    def test_paper_evidence_and_mail_source_are_legally_specific(self):
        house = self.scene_text("c3_house")
        archive = self.scene_text("c3_archive")
        self.assertIn("sworn hearing transcript", house)
        self.assertIn("private car-to-station handset", house)
        self.assertIn("May third", archive)
        self.assertIn("clerk’s stamp", archive)

    def test_lyles_game_attendance_is_not_proof_of_replacement(self):
        case = self.task("c3_house", "rules")
        evidence = self.text(case["lead"] + [case["finding"]])
        self.assertIn("clinic", evidence)
        self.assertIn("citation", evidence)
        self.assertIn("same minute", evidence)
        self.assertNotIn("sign-in book", self.lines[case["finding"]]["text"])

    def test_calendar_and_room_order_stay_consistent(self):
        aftermath = self.edits["storybooks"]["aftermath"]["panels"]
        aftermath_text = " ".join(line for panel in aftermath for line in panel)
        self.assertIn("Three weeks ago", aftermath_text)
        self.assertIn("dubbed her phone voicemail onto a cassette", aftermath_text)
        self.assertIn("two afternoons later", self.scene_text("c4_safe"))
        self.assertIn("control room", self.scene_text("c5_station"))
        self.assertIn("five weeks ago", self.task("c5_station", "halcyon")["background"])

    def test_helen_leaves_the_message_before_frank_logs_it(self):
        phone = self.task("p_bay", "message")
        self.assertIn("p_bay.out.01", phone["lines"])
        self.assertIn("Eleven-twenty", self.lines[phone["finding"]]["text"])
        self.assertNotIn("p_bay.out.01", self.scenes["p_bay"]["outro"])

    def test_breakfast_opens_with_one_live_greeting_and_coffee(self):
        kitchen = self.scenes["c1_flat"]
        first = [self.lines[i] for i in kitchen["context"] + kitchen["intro"]]
        self.assertEqual([(line["speaker"], line["text"]) for line in first[:3]], [
            ("iris", "Good morning, sleepyhead."),
            ("steve", "Morning, Nor."),
            ("iris", "Coffee’s on the stove. I made it strong, the way you like it."),
        ])
        self.assertEqual(self.scene_text("c1_flat").count("Morning, Nor."), 1)
        self.assertNotIn("three in the morning", kitchen["card"]["chapter"]["when"].lower())
        self.assertTrue(any(not topic["after"] for topic in kitchen["talk"] if topic["speaker"] == "iris"))

    def test_helen_is_on_the_optional_recorder_not_the_critical_path(self):
        kitchen = self.scenes["c1_flat"]
        recorder = self.task("c1_flat", "control")
        self.assertIn("c1_flat.in.01", recorder.get("optional_playback", {}).get("lines", []))
        mandatory = kitchen["context"] + kitchen["intro"] + kitchen["outro"]
        for task in kitchen["tasks"]:
            mandatory += task["lead"] + task["lines"]
        self.assertNotIn("c1_flat.in.01", mandatory)
        self.assertNotIn("Three in the morning.", self.text(mandatory))

    def test_resync_wake_and_missing_companions_are_explained(self):
        self.assertIn("boathouse phone rang once", self.scene_text("c3_archive"))
        iris = self.scene_text("c6_iris")
        self.assertIn("re-sync window passed", iris)
        self.assertIn("escorted you below later", iris)
        self.assertIn("Monday, November fifth", self.scene_text("i2_nora"))
        wake_context = self.text(self.scenes["c9_wake"]["context"])
        self.assertIn("Iris stayed", wake_context)
        self.assertIn("Pell and Biscuit", wake_context)

    def test_voicemail_copy_wind_dub_and_ferry_are_physical(self):
        self.assertIn("personal copy Rook made", self.scene_text("c8_beach"))
        town = self.scene_text("c10_town")
        self.assertIn("Shore dub from the original take", town)
        self.assertIn("shore phone", town)
        live_recap = self.text(self.scenes["c10_live"]["recap"])
        self.assertIn("wind was a dub", live_recap)
        self.assertIn("answered it live", live_recap)
        self.assertNotIn("None of it recorded", live_recap)
        bait = self.task("epilogue", "bait")
        self.assertIn("morning ferry", self.lines[bait["finding"]]["text"])
        self.assertIn("already gone", self.lines[bait["finding"]]["text"])

    def test_smaller_cross_chapter_cues_remain_unambiguous(self):
        self.assertIn("personally circled", self.task("c6_jail", "crossword")["prompt"])
        self.assertIn("bait bucket", self.scene_text("c7_gate"))
        self.assertNotIn("old woman was walking a dog", self.scene_text("c7_gate"))
        self.assertIn("bait bucket", self.scene_text("c8_lab"))
        relay = self.task("c10_station", "relay")
        relay_text = " ".join([relay["background"], self.text(relay["lead"]),
                              self.lines[relay["finding"]]["text"]])
        self.assertIn("test signal", relay_text)
        self.assertNotIn("cue four today", relay_text)
        self.assertIn("Pier and Orchard", self.text(self.scenes["c10_town"]["recap"]))


if __name__ == "__main__":
    unittest.main()

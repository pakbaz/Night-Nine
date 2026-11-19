import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("milestones", ROOT / "tools/build-milestone-repo.py")
milestones = importlib.util.module_from_spec(spec)
spec.loader.exec_module(milestones)


def read_entry(files, name):
    value = files[name]
    return value.read_text() if isinstance(value, Path) else value.decode()


def resources(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from resources(item)
    elif isinstance(value, list):
        for item in value:
            yield from resources(item)
    elif isinstance(value, str) and value.startswith("res://"):
        yield value


class ReleasePackagingTests(unittest.TestCase):
    def test_complete_release_contains_runtime_dependencies(self):
        files, meta = milestones.make_snapshot(10, True)
        self.assertEqual(meta["scenes"], 34)
        for name in ("game/content/storybook.json", "game/ui/storybook.gd", "game/ui/title_card.gd"):
            self.assertTrue(name in files, name)
        for name in files:
            if Path(name).suffix in {".gd", ".tscn", ".tres"}:
                for resource in re.findall(r'"(res://[^"%\n]+\.(?:gd|gdshader|tscn|tres|wav))"', read_entry(files, name)):
                    with self.subTest(script=name, resource=resource):
                        self.assertTrue("game/" + resource[6:] in files, resource)
        for name in ("storybook", "music"):
            for resource in resources(json.loads(read_entry(files, f"game/content/{name}.json"))):
                with self.subTest(catalog=name, resource=resource):
                    self.assertTrue("game/" + resource[6:] in files, resource)
        for scene in ("p_bay", "p_veyr", "p_meeting"):
            self.assertIn(f"game/assets/audio/ambience-prologue/{scene}.ogg", files)

    def test_checkpoint_catalogs_only_include_reachable_story(self):
        for stage in (0, 3, 7, 8):
            with self.subTest(stage=stage):
                files, _ = milestones.make_snapshot(stage, True)
                scenes = json.loads(read_entry(files, "game/content/campaign.json"))["scenes"]
                scene_ids = {scene["id"] for scene in scenes}
                books = json.loads(read_entry(files, "game/content/storybook.json"))["books"]
                self.assertIn("opening", books)
                self.assertEqual("aftermath" in books, "c1_flat" in scene_ids)
                self.assertNotIn("after", books)
                self.assertEqual("p_veyr" in scene_ids, stage >= 3)
                self.assertEqual("p_meeting" in scene_ids, stage >= 8)
                music = json.loads(read_entry(files, "game/content/music.json"))
                for catalog in ("scene_music", "departures"):
                    self.assertLessEqual(music[catalog].keys(), scene_ids)
                for catalog in (books, music):
                    for resource in resources(catalog):
                        self.assertTrue("game/" + resource[6:] in files, resource)


class WindowsPackagingTests(unittest.TestCase):
    def test_rebuild_uses_one_current_copy_of_each_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("tools", "game/content", "builds/windows"):
                (root / folder).mkdir(parents=True)
            for name in ("package-windows.py", "desktop_notices.py"):
                shutil.copyfile(ROOT / "tools" / name, root / "tools" / name)
            (root / "game/project.godot").write_text('config/version="0.9.2"\n')
            (root / "game/content/voice-manifest.json").write_text('{"takes": {}}')
            for name in ("LICENSE", "MEDIA.md"):
                (root / name).write_text("current " + name)
            (root / "game/LICENSES.txt").write_text("current dependency notices")
            (root / "builds/windows/NightNine.exe").write_bytes(b"packaging fixture")
            for name in ("LICENSE", "MEDIA.md", "LICENSES.txt", "README.txt", "SOURCE.txt"):
                (root / "builds/windows" / name).write_text("previous release")
            subprocess.run([sys.executable, root / "tools/package-windows.py"],
                           check=True, capture_output=True)
            with zipfile.ZipFile(root / "builds/NightNine-0.9.2-Windows-x64.zip") as archive:
                self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
                self.assertIn(b"NightNine-0.9.2-source.zip", archive.read("NightNine/SOURCE.txt"))
                self.assertEqual(archive.read("NightNine/LICENSES.txt"), b"current dependency notices")


if __name__ == "__main__":
    unittest.main()

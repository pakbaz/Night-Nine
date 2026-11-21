import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("milestones", ROOT / "tools/build-milestone-repo.py")
milestones = importlib.util.module_from_spec(spec)
spec.loader.exec_module(milestones)


def load_tool(name, filename):
    tool_spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    tool = importlib.util.module_from_spec(tool_spec)
    tool_spec.loader.exec_module(tool)
    return tool


split_site = load_tool("split_site", "split-site.py")
check_site = load_tool("check_site", "check-site.py")
build_pages = load_tool("build_pages", "build-pages.py")


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
    def test_web_export_omits_voice_staging_only_while_both_playback_gates_are_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            game = Path(directory) / "game"
            content = game / "content"
            staged = game / "assets/audio/voices/elevenlabs-v4-script-v2"
            historic = game / "assets/audio/voices/recording.greeting.wav"
            content.mkdir(parents=True)
            staged.mkdir(parents=True)
            (content / "voice-manifest.json").write_text(json.dumps({"enabled": False}))
            (content / "narration.json").write_text(json.dumps({"enabled": False}))
            (staged / "take.wav").write_bytes(b"unapproved")
            historic.parent.mkdir(parents=True, exist_ok=True)
            historic.write_bytes(b"historic")

            build_pages.prune_unapproved_voice_assets(game)

            self.assertFalse(staged.exists())
            self.assertTrue(historic.exists())

            staged.mkdir()
            (staged / "take.wav").write_bytes(b"approved")
            (content / "voice-manifest.json").write_text(json.dumps({"enabled": True}))
            build_pages.prune_unapproved_voice_assets(game)
            self.assertTrue((staged / "take.wav").exists())

    def test_split_files_reassemble_exactly_with_bounded_parts(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            originals = {
                "play.pck": (b"pack-data-" * (3 * 1024 * 1024)) + b"end",
                "play.wasm": (b"\0asm-test-" * (2 * 1024 * 1024)) + b"end",
            }
            for name, data in originals.items():
                (site / name).write_bytes(data)

            manifest = split_site.split_site(site)

            for file_entry in manifest["files"]:
                rebuilt = b"".join((site / part["name"]).read_bytes()
                                   for part in file_entry["parts"])
                self.assertEqual(originals[file_entry["name"]], rebuilt)
                self.assertEqual(file_entry["sha256"], split_site.sha256_bytes(rebuilt))
                self.assertTrue(all(part["size"] <= split_site.MAX_FILE_SIZE
                                    for part in file_entry["parts"]))
                self.assertFalse((site / file_entry["name"]).exists())
            check_site.check_site(site)

    def test_check_site_rejects_25_mib_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            (site / "too-large.bin").write_bytes(b"\0" * (25 * 1024 * 1024))
            with self.assertRaisesRegex(ValueError, "too-large.bin.*24 MiB"):
                check_site.check_site(site)

    def test_check_site_rejects_missing_part(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            (site / "play.pck").write_bytes(b"pck")
            (site / "play.wasm").write_bytes(b"wasm")
            manifest = split_site.split_site(site, chunk_size=2)
            (site / manifest["files"][0]["parts"][0]["name"]).unlink()
            with self.assertRaisesRegex(ValueError, "Missing part"):
                check_site.check_site(site)

    def test_check_site_rejects_corrupted_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            (site / "play.pck").write_bytes(b"pck")
            (site / "play.wasm").write_bytes(b"wasm")
            split_site.split_site(site, chunk_size=2)
            (site / "chunks.json").write_text("{broken")
            with self.assertRaisesRegex(ValueError, "chunks.json"):
                check_site.check_site(site)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the browser loader test.")
    def test_browser_loader_verifies_and_retries_parts(self):
        result = subprocess.run(["node", ROOT / "tools/test_chunk_loader.mjs"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_post_processed_html_loads_chunk_loader_before_engine(self):
        source = '<script src="play.js"></script>'
        result = build_pages.inject_chunk_loader(source)
        self.assertIn('<script src="night-nine-loader.js"></script>', result)
        self.assertLess(result.index("night-nine-loader.js"), result.index("play.js"))

    def test_offline_worker_caches_shell_but_not_unsplit_payloads(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            worker = site / "play.service.worker.js"
            worker.write_text(
                "const CACHE_VERSION = 'export';\n"
                "const CACHE_PREFIX = 'old';\n"
                "const CACHED_FILES = [\"play.html\",\"play.js\"];\n"
                "const CACHEABLE_FILES = [\"play.wasm\",\"play.pck\"];\n"
                "const FULL_CACHE = CACHED_FILES.concat(CACHEABLE_FILES);\n"
                "cache.put(event.request, response.clone());\n")
            (site / "chunks.json").write_text('{"release":"test"}')
            (site / "night-nine-loader.js").write_text("loader")
            build_pages.prepare_offline_cache(site)
            result = worker.read_text()
            self.assertRegex(result, r"const CACHE_VERSION = 'export\\|nn-[0-9a-f]{16}';")
            self.assertIn("const CACHEABLE_FILES = [];", result)
            self.assertIn("'chunks.json', 'night-nine-loader.js'", result)
            self.assertNotIn('["play.wasm","play.pck"]', result)

    def test_complete_release_contains_runtime_dependencies(self):
        files, meta = milestones.make_snapshot(10, False)
        self.assertEqual(meta["scenes"], 34)
        self.assertFalse(".github/workflows/pages.yml" in files,
                         "Checkpoints must not recreate the retired hosting workflow.")
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
        for name in files:
            if name.startswith("game/") and Path(name).suffix in milestones.MEDIA_EXT:
                self.assertTrue(name + ".import" in files, name)

    def test_checkpoint_catalogs_only_include_reachable_story(self):
        for stage in (0, 3, 7, 8):
            with self.subTest(stage=stage):
                files, _ = milestones.make_snapshot(stage, False)
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

    def test_snapshot_keeps_script_v2_dialogue_and_reward_dependencies(self):
        files, _ = milestones.make_snapshot(10, False)
        campaign = json.loads(read_entry(files, "game/content/campaign.json"))
        for scene in campaign["scenes"]:
            for line_id in scene.get("recap", []):
                self.assertTrue(line_id in campaign["lines"], line_id)
            for task in scene["tasks"]:
                for line_id in task.get("lead", []):
                    self.assertTrue(line_id in campaign["lines"], line_id)
                if task.get("finding"):
                    self.assertTrue(task["finding"] in campaign["lines"], task["finding"])
            for resource in resources(scene):
                self.assertTrue("game/" + resource[6:] in files, resource)
        for name in ("home-at-last", "family-radio", "bellwether-together"):
            self.assertTrue(f"game/assets/illustrated/campaign/rewards/{name}.webp" in files, name)
        narration = json.loads(read_entry(files, "game/content/narration.json"))
        for resource in resources(narration):
            self.assertTrue("game/" + resource[6:] in files, resource)

    def test_snapshot_preserves_disabled_voice_gate_and_identity_metadata(self):
        original_read = milestones.read

        def disabled_manifest(path):
            data = original_read(path)
            if Path(path).name == "voice-manifest.json":
                data["enabled"] = False
            return data

        with patch.object(milestones, "read", side_effect=disabled_manifest):
            files, _ = milestones.make_snapshot(10, False)
            voice = json.loads(read_entry(files, "game/content/voice-manifest.json"))
            self.assertIs(voice.get("enabled"), False)
            source = original_read(milestones.GAME / "content/voice-manifest.json")
            for take_id, take in voice["takes"].items():
                for field in ("voice_id", "text_hash", "status", "listening_reviewed"):
                    if field in source["takes"][take_id]:
                        self.assertEqual(take.get(field), source["takes"][take_id][field])
            with self.assertRaisesRegex(RuntimeError, "Voice playback is not approved"):
                milestones.make_snapshot(10, True)



if __name__ == "__main__":
    unittest.main()

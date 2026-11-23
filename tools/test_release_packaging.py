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
from urllib.parse import urljoin
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


def write_offline_worker(site):
    worker = site / "play.service.worker.js"
    worker.write_text(
        "const CACHE_VERSION = 'export';\n"
        "const CACHE_PREFIX = 'old';\n"
        "const CACHED_FILES = [\"play.html\",\"play.js\"];\n"
        "const CACHEABLE_FILES = [\"play.wasm\",\"play.pck\"];\n"
        "const FULL_CACHE = CACHED_FILES.concat(CACHEABLE_FILES);\n"
        "function remember(event, cache, response) {\n"
        "  cache.put(event.request, response.clone());\n"
        "}\n"
        "async function cachedNavigation(event, cache) {\n"
        "  const isNavigate = event.request.mode === 'navigate';\n"
        "  let cached = await cache.match(event.request);\n"
        "  if (cached != null) {\n"
        "    return cached;\n"
        "  }\n"
        "  return null;\n"
        "}\n")
    (site / "chunks.json").write_text('{"release":"test"}')
    (site / "night-nine-loader.js").write_text("loader")
    (site / "loading-screen-music.mp3").write_bytes(b"take-one")
    return worker


class ReleasePackagingTests(unittest.TestCase):
    def test_cutaway_without_room_is_valid(self):
        files, _ = milestones.make_snapshot(10, False)
        directions = json.loads(read_entry(files, "game/content/illustrated-campaign.json"))
        self.assertIn("c4_escape", directions)
        self.assertNotIn("room", directions["c4_escape"]["cutaway"])

    def test_play_button_uses_the_cloudflare_route_without_a_redirect(self):
        landing = (ROOT / "site/index.html").read_text()
        link = re.search(r'<a class="play" href="([^"]+)">', landing)
        self.assertIsNotNone(link)
        self.assertEqual(urljoin("https://night-nine.test/", link.group(1)),
                         "https://night-nine.test/play")

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

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the web audio test.")
    def test_web_audio_position_follows_the_audible_sound(self):
        fixture = ROOT / "tools/fixtures/web-audio"
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "play.js").write_text("const GodotAudio={" + (fixture / "sample-node.js").read_text() + "};")
            build_pages.patch_web_audio_position(site)
            result = subprocess.run(["node", "--input-type=module", "-e", r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
const library = fs.readFileSync(process.argv[1], 'utf8');
const near = (actual, expected, what) => assert.ok(Math.abs(actual - expected) < 1e-9, `${what}: ${actual} != ${expected}`);
const started = [];
const ctx = { currentTime: 3, sampleRate: 48000, baseLatency: 0.01, outputLatency: 0.04,
	createBufferSource: () => ({ playbackRate: { value: 1 }, connect() {}, disconnect() {}, stop() {},
		start(when, offset) { started.push(offset); }, addEventListener() {}, removeEventListener() {} }) };
globalThis.AudioWorkletNode = class { constructor() { this.port = { postMessage() {} }; }
	get parameters() { return { get: () => ({ setValueAtTime() {} }) }; } connect() {} disconnect() {} };
globalThis.GodotRuntime = { error: (e) => { throw e; } };
globalThis.GodotAudio = new Function(library + '; return GodotAudio;')();
Object.assign(GodotAudio, {
	ctx, sampleNodes: new Map(), audioPositionWorkletNodes: [], audioPositionWorkletPromise: Promise.resolve(),
	Sample: { getSample: () => ({ sampleRate: 48000, loopMode: 'disabled', getAudioBuffer: () => ({}) }) },
	Bus: { getBus: () => ({}) },
	SampleNodeBus: { create: () => ({ setVolume() {}, getInputNode: () => ({}), clear() {} }) },
	deleteSampleNode: (id) => GodotAudio.sampleNodes.delete(id),
});
const voice = GodotAudio.SampleNode.create({ id: 'a', streamObjectId: 's', busIndex: 0 }, { offset: 0, start: true });
near(voice.getPlaybackPosition(), 0, 'before the first block');
await Promise.resolve(); await Promise.resolve();
// Audible from the first block: the clock minus the output latency, with no hold at zero.
ctx.currentTime = 3.1; near(voice.getPlaybackPosition(), 0.05, 'a tenth of a second in');
ctx.currentTime = 4; near(voice.getPlaybackPosition(), 0.95, 'one second in');
// Pausing holds the position; resuming continues from it instead of restarting the clip.
GodotAudio.SampleNode.pauseSampleNode('a', true);
ctx.currentTime = 6; near(voice.getPlaybackPosition(), 0.95, 'held while paused');
GodotAudio.SampleNode.pauseSampleNode('a', false);
near(started.at(-1), 0.95, 'resumed source starts where the listener was');
ctx.currentTime = 6.5; near(voice.getPlaybackPosition(), 1.4, 'continues after resuming');
// A clip with an offset and a pitch scale.
const music = GodotAudio.SampleNode.create({ id: 'b', streamObjectId: 's', busIndex: 0 }, { offset: 2, pitchScale: 2, start: true });
await Promise.resolve(); await Promise.resolve();
ctx.currentTime = 6.75; near(music.getPlaybackPosition(), 2 + 0.2 * 2, 'offset and pitch');
""", str(site / "play.js")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_web_audio_patch_refuses_an_unexpected_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "play.js").write_text("const GodotAudio={};")
            with self.assertRaisesRegex(ValueError, "Unexpected Godot web audio"):
                build_pages.patch_web_audio_position(site)

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
            worker = write_offline_worker(site)
            build_pages.prepare_offline_cache(site)
            result = worker.read_text()
            self.assertRegex(result, r"const CACHE_VERSION = 'export\\|nn-[0-9a-f]{16}';")
            self.assertIn("const CACHEABLE_FILES = [];", result)
            self.assertIn("'chunks.json', 'night-nine-loader.js'", result)
            self.assertIn("'loading-screen-music.mp3'", result)
            self.assertNotIn('["play.wasm","play.pck"]', result)
            first_version = re.search(r"const CACHE_VERSION = '[^']+';", result).group()
            (site / "loading-screen-music.mp3").write_bytes(b"replacement-take")
            build_pages.prepare_offline_cache(site)
            next_version = re.search(r"const CACHE_VERSION = '[^']+';", worker.read_text()).group()
            self.assertNotEqual(first_version, next_version, "Refresh offline audio when the loading theme changes.")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the service worker test.")
    def test_cached_navigation_handles_clean_and_redirected_html_routes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            worker = write_offline_worker(site)
            build_pages.prepare_offline_cache(site)
            result = subprocess.run(["node", "--input-type=module", "-e", """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const context = {
    URL, Response,
    self: {registration: {scope: 'https://night-nine.test/game/'}},
    cache: {
        async match(request) {
            const url = new URL(request.url || request);
            if (!url.pathname.endsWith('/play.html')) return undefined;
            const response = new Response('<html>Night Nine</html>', {
                headers: {'Content-Type': 'text/html'}, status: 200,
            });
            Object.defineProperty(response, 'redirected', {value: true});
            return response;
        },
    },
};
vm.createContext(context);
vm.runInContext(readFileSync(process.argv[1], 'utf8'), context);
for (const path of ['play.html', 'play']) {
    context.event = {request: {url: 'https://night-nine.test/game/' + path, mode: 'navigate'}};
    const response = await vm.runInContext('cachedNavigation(event, cache)', context);
    assert.ok(response, `Serve cached ${path} without needing the network`);
    assert.equal(response.redirected, false, 'Manual navigations cannot use followed redirect responses');
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Content-Type'), 'text/html');
    assert.equal(await response.text(), '<html>Night Nine</html>');
}
""", str(worker)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_release_contains_runtime_dependencies(self):
        files, meta = milestones.make_snapshot(10, False)
        self.assertEqual(meta["scenes"], 34)
        self.assertFalse(".github/workflows/pages.yml" in files,
                         "Checkpoints must not recreate the retired hosting workflow.")
        splash = re.search(r'^boot_splash/image="res://([^"]+)"',
                           read_entry(files, "game/project.godot"), re.M)
        self.assertIsNotNone(splash, "Keep the game's branded boot splash.")
        self.assertIn("game/" + splash.group(1), files)
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

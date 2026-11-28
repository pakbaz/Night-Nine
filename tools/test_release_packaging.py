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
    shutil.copyfile(ROOT / "tools/fixtures/service-worker/play.service.worker.js", worker)
    (site / "chunks.json").write_text('{"release":"test"}')
    (site / "night-nine-loader.js").write_text("loader")
    (site / "loading-screen-music.mp3").write_bytes(b"take-one")
    return worker


# Plays a built service worker in Node: a site that can publish a new release or go
# offline, the browser's caches, and the install, activate and fetch events.
WORKER_HARNESS = r"""
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const scope = 'https://night-nine.test/game/';
const at = (path) => new URL(path, scope).href;
let online = true;
let release = '';
const publish = (name) => { release = name; };
// Pages answers play.html by redirecting to the clean /play address.
async function network(request) {
    if (!online) {
        throw new TypeError('Failed to fetch');
    }
    let path = new URL(request.url || request, scope).pathname.slice(new URL(scope).pathname.length);
    const redirected = path === 'play.html';
    if (redirected) {
        path = 'play';
    }
    const page = path === '' || path === 'play' || path.endsWith('.html');
    const body = path === 'chunks.json' ? JSON.stringify({release}) : `${path || 'index'} ${release}`;
    const response = new Response(body, {status: 200, headers: {'Content-Type': page ? 'text/html' : 'text/plain'}});
    if (redirected) {
        Object.defineProperty(response, 'redirected', {value: true});
    }
    return response;
}
const copy = (response) => {
    const twin = response.clone();
    if (response.redirected) {
        Object.defineProperty(twin, 'redirected', {value: true});
    }
    return twin;
};
class FakeCache {
    entries = new Map();
    async match(request) {
        const response = this.entries.get(at(request.url || request));
        return response ? copy(response) : undefined;
    }
    async put(request, response) {
        this.entries.set(at(request.url || request), response);
    }
    async addAll(paths) {
        for (const path of paths) {
            await this.put(path, await network(at(path)));
        }
    }
}
const storage = new Map();
const caches = {
    async open(name) {
        if (!storage.has(name)) {
            storage.set(name, new FakeCache());
        }
        return storage.get(name);
    },
    async keys() { return [...storage.keys()]; },
    async delete(name) { return storage.delete(name); },
    async match(request) {
        for (const cache of storage.values()) {
            const response = await cache.match(request);
            if (response) {
                return response;
            }
        }
        return undefined;
    },
};
const listeners = {};
const worker = {skippedWaiting: false, claimed: false};
const self = {
    registration: {scope, navigationPreload: {enable: async () => {}}},
    origin: new URL(scope).origin,
    addEventListener: (type, listener) => { listeners[type] = listener; },
    fetch: network,
    skipWaiting: async () => { worker.skippedWaiting = true; },
    clients: {claim: async () => { worker.claimed = true; }, get: async () => undefined, matchAll: async () => []},
};
vm.runInContext(readFileSync(process.argv[1], 'utf8'),
    vm.createContext({self, caches, fetch: network, URL, Response, Headers, console}));
async function lifecycle(type) {
    const pending = [];
    listeners[type]({waitUntil: (promise) => pending.push(promise)});
    await Promise.all(pending);
}
// A page load when navigate is true; otherwise a file the game page asks for.
async function visit(path, navigate = false) {
    const pending = [];
    let answer;
    listeners.fetch({
        request: {url: at(path), mode: navigate ? 'navigate' : 'cors', referrer: navigate ? '' : at('play')},
        preloadResponse: Promise.resolve(undefined),
        respondWith: (promise) => { answer = promise; },
        waitUntil: (promise) => pending.push(promise),
    });
    assert.ok(answer, `The worker answers ${path}`);
    const response = await answer;
    await Promise.all(pending);
    return response;
}
"""


def run_worker(test, worker, scenario):
    result = subprocess.run(["node", "--input-type=module", "-e", WORKER_HARNESS + scenario, str(worker)],
                            capture_output=True, text=True)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ReleasePackagingTests(unittest.TestCase):
    def test_cutaway_without_room_is_valid(self):
        files, _ = milestones.make_snapshot(10, False)
        directions = json.loads(read_entry(files, "game/content/illustrated-campaign.json"))
        self.assertIn("c4_escape", directions)
        self.assertNotIn("room", directions["c4_escape"]["cutaway"])

    def test_play_button_uses_the_cloudflare_route_without_a_redirect(self):
        landing = (ROOT / "site/index.html").read_text()
        link = re.search(r'<a class="play" href="([^"]+)"', landing)
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
        result = build_pages.inject_chunk_loader(source, "abc123")
        self.assertIn('<script src="night-nine-loader.js" data-release="abc123"></script>', result)
        self.assertLess(result.index("night-nine-loader.js"), result.index("play.js"))

    def test_landing_and_game_pages_name_the_release_for_the_loading_music(self):
        # The loading music plays again whenever a release must be downloaded again.
        landing = (ROOT / "site/index.html").read_text()
        self.assertIn('data-release="@@RELEASE@@"', landing)
        self.assertIn("link.dataset.release", landing)

    def test_offline_worker_caches_shell_but_not_unsplit_payloads(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            worker = write_offline_worker(site)
            build_pages.prepare_offline_cache(site)
            result = worker.read_text()
            self.assertRegex(result, r"const CACHE_VERSION = '1795778690\|4653383\|nn-[0-9a-f]{16}';")
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
            run_worker(self, worker, """
publish('first');
await lifecycle('install');
await lifecycle('activate');
online = false;
for (const path of ['play.html', 'play']) {
    const response = await visit(path, true);
    assert.equal(response.redirected, false, 'Manual navigations cannot use followed redirect responses');
    assert.equal(response.status, 200, `Open ${path} from the cache without the network`);
    assert.equal(response.headers.get('Content-Type'), 'text/html');
    assert.equal(await response.text(), 'play first');
}
""")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the service worker test.")
    def test_returning_player_gets_the_release_on_the_server(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            worker = write_offline_worker(site)
            build_pages.prepare_offline_cache(site)
            run_worker(self, worker, """
publish('first');
await lifecycle('install');
await lifecycle('activate');
publish('second');
const manifest = await (await visit('chunks.json')).json();
assert.equal(manifest.release, 'second', 'A returning player gets the chunk list on the server, not the cached one');
assert.equal(await (await visit('night-nine-loader.js')).text(), 'night-nine-loader.js second');
assert.equal(await (await visit('play.js')).text(), 'play.js second');
assert.equal(await (await visit('play', true)).text(), 'play second');
online = false;
const offline = await (await visit('chunks.json')).json();
assert.equal(offline.release, 'second', 'Offline, the game uses the chunk list it last saw online');
assert.equal((await visit('play', true)).status, 200, 'The game page still opens offline');
""")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the service worker test.")
    def test_new_release_takes_over_open_pages(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            site = Path(directory)
            worker = write_offline_worker(site)
            build_pages.prepare_offline_cache(site)
            run_worker(self, worker, """
publish('second');
await lifecycle('install');
assert.ok(worker.skippedWaiting, 'A new release does not wait until every open tab is closed');
await lifecycle('activate');
assert.ok(worker.claimed, 'The new worker takes over open pages, so Retry or a reload gets the new release');
""")

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
        for asset in (
            "game/assets/illustrated/campaign/walk/iris_gallery-idle.webp",
            "game/assets/illustrated/cast/iris_gallery/iris_gallery.webp",
            "game/assets/illustrated/campaign/walk/rook_pajamas-idle.webp",
            "game/assets/illustrated/cast/rook_pajamas/rook_pajamas.webp",
            "game/assets/illustrated/campaign/stills/c9_wake-rook-wakes.webp",
            "game/assets/illustrated/campaign/stills/c9_choir-wick-rises.webp",
            "game/assets/illustrated/campaign/stills/c10_report-departure.webp",
        ):
            self.assertIn(asset, files, asset)
        for name in files:
            if name.startswith("game/") and Path(name).suffix in milestones.MEDIA_EXT:
                self.assertTrue(name + ".import" in files, name)

    def test_checkpoint_catalogs_only_include_reachable_story(self):
        for stage in (0, 3, 7, 8):
            with self.subTest(stage=stage):
                files, _ = milestones.make_snapshot(stage, False)
                scenes = json.loads(read_entry(files, "game/content/campaign.json"))["scenes"]
                scene_ids = {scene["id"] for scene in scenes}
                people = json.loads(read_entry(files, "game/content/scene-people.json"))
                self.assertLessEqual(people.keys(), scene_ids)
                for scene in people.values():
                    for appearance, *_ in scene.get("figures", {}).values():
                        sprite = f"game/assets/illustrated/campaign/walk/{appearance}-idle.webp"
                        self.assertIn(sprite, files)
                        self.assertIn(sprite+".import", files)
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

    def test_first_chapter_keeps_the_walk_in_optional_recorder_and_small_talk(self):
        files, _ = milestones.make_snapshot(1, False)
        campaign = json.loads(read_entry(files, "game/content/campaign.json"))
        voices = json.loads(read_entry(files, "game/content/voice-manifest.json"))["takes"]
        self.assertTrue("game/assets/illustrated/campaign/walk/nora.webp" in files)
        for scene in campaign["scenes"]:
            optional = [i for t in scene["tasks"] for i in t.get("optional_playback", {}).get("lines", [])]
            topics = [i for topic in scene["talk"] for i in topic["lines"]]
            for line_id in optional + topics + scene["context"]:
                self.assertTrue(line_id in campaign["lines"], line_id)
                take = voices[campaign["lines"][line_id]["audio"]]
                self.assertTrue("game/" + take["file"][6:] in files, line_id)

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

// Runs site/night-nine-loader.js against fake browser APIs. Usage: node tools/test_chunk_loader.mjs
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../site/night-nine-loader.js', import.meta.url), 'utf8');
const good = new Uint8Array(4096).map((_, index) => index % 251);
const bad = good.map((value) => value ^ 0xff);
const digest = createHash('sha256').update(good).digest('hex');
const partName = `play.wasm.0001.${digest.slice(0, 8)}.wasm`;
const manifest = {
	version: 1,
	release: 'test-release',
	files: [{name: 'play.wasm', size: good.length, sha256: digest,
		parts: [{name: partName, size: good.length, sha256: digest}]}],
};

async function makeManifest(parts) {
	const entries = parts.map(([name, bytes]) => ({
		name, size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'),
	}));
	return {
		version: 1,
		release: 'test-release',
		files: [{name: 'play.wasm', size: entries.reduce((sum, part) => sum + part.size, 0),
			sha256: '', parts: entries}],
	};
}

function browser(serve, {storage = new Map(), play = async () => {}, chunks = manifest} = {}) {
	const requests = [];
	const stored = new Map();
	const listeners = new Map();
	const observers = [];
	const created = [];
	const warnings = [];
	function element(tagName) {
		const events = new Map();
		const node = {
			tagName, style: {}, textContent: '', children: [], isConnected: true,
			paused: true, playCalls: 0, currentTime: 0, volumes: [],
			get volume() { return this.volumes.at(-1); },
			set volume(value) { this.volumes.push(value); },
			async play() {
				this.playCalls += 1;
				await play();
				this.paused = false;
			},
			pause() { this.paused = true; },
			append(...children) { this.children.push(...children); },
			remove() { this.isConnected = false; },
			setAttribute() {},
			addEventListener(name, callback) { events.set(name, callback); },
			click() { events.get('click')?.(); },
			replaceChildren() { this.children = []; },
		};
		created.push(node);
		return node;
	}
	const body = element('body');
	const progress = {
		style: {},
		value: 0,
		max: 0,
		removeAttribute(name) {
			delete this[name];
		},
	};
	const status = element('div');
	status.style.visibility = 'hidden';
	status.parentNode = body;
	const notice = element('div');
	notice.style.display = 'none';
	const label = {textContent: '', style: {}};
	const document = {
		baseURI: 'https://night-nine.test/play.html',
		body,
		getElementById(id) {
			if (id === 'status-progress') return progress;
			if (id === 'status') return status.isConnected ? status : null;
			if (id === 'status-notice') return notice;
			if (id === 'status-progress-label') return label;
			return created.find((node) => node.id === id && node.isConnected) || null;
		},
		createElement: element,
	};
	const cache = {
		match: async (url) => stored.get(String(url)),
		put: async (url, response) => stored.set(String(url), response),
		delete: async (url) => stored.delete(String(url)),
	};
	const window = {
		localStorage: {
			getItem: (key) => storage.get(key) ?? null,
			setItem: (key, value) => storage.set(key, value),
		},
		addEventListener(name, callback) {
			if (!listeners.has(name)) listeners.set(name, new Set());
			listeners.get(name).add(callback);
		},
		removeEventListener(name, callback) { listeners.get(name)?.delete(callback); },
		fetch: async (input, init = {}) => {
			const url = new URL(String(input));
			const name = url.pathname.split('/').pop();
			requests.push({name, cache: init.cache});
			if (name === 'chunks.json') {
				return new Response(JSON.stringify(chunks));
			}
			return new Response(await serve(name, init.cache));
		},
	};
	const context = {
		window, URL, Response, Request, Uint8Array, Map, Set, Array, Promise, Error, String,
		setTimeout: (callback) => setTimeout(callback, 0),
		clearTimeout: (timer) => clearTimeout(timer),
		crypto: globalThis.crypto,
		caches: {keys: async () => [], delete: async () => true, open: async () => cache},
		location: {origin: 'https://night-nine.test', pathname: '/play.html', reload() {}},
		document,
		console: {warn: (...args) => warnings.push(args)},
		MutationObserver: class {
			constructor(callback) { this.callback = callback; observers.push(this); }
			observe(target, options) { this.target = target; this.options = options; }
			disconnect() { this.target = null; }
		},
	};
	vm.runInNewContext(source, context);
	return {
		fetch: window.fetch, requests, progress, label, created, storage, warnings, document,
		gesture() {
			for (const callback of [...(listeners.get('pointerdown') || [])]) callback();
		},
		finish() {
			status.remove();
			for (const observer of observers) {
				if (observer.target === body && observer.options.childList) observer.callback();
			}
		},
	};
}

const settle = () => new Promise(setImmediate);

async function load(serve) {
	const page = browser(serve);
	const response = await page.fetch('https://night-nine.test/play.wasm');
	return {bytes: new Uint8Array(await response.arrayBuffer()), requests: page.requests};
}

const tests = {
	async 'assembles verified parts'() {
		const {bytes} = await load(() => good);
		assert.deepEqual(bytes, good);
	},
	async 'retries bypass a corrupt copy in the browser HTTP cache'() {
		// A revalidated request can return the same bad cached bytes; only a reload reaches the network.
		const {bytes, requests} = await load((name, mode) => (mode === 'reload' ? good : bad));
		assert.deepEqual(bytes, good);
		assert.deepEqual(requests.filter((item) => item.name === partName).map((item) => item.cache),
			['no-cache', 'reload']);
	},
	async 'gives up after three corrupt responses'() {
		await assert.rejects(load(() => bad), /failed after 3 attempts: SHA-256 mismatch/);
	},
	async 'shows loading percentage and creates loading music'() {
		const page = browser(() => good);
		await page.fetch('https://night-nine.test/play.wasm');
		assert.equal(page.progress.value, 4096);
		assert.equal(page.progress.max, 4096);
		assert.equal(page.label.textContent, '100%');
		assert.ok(page.created.some((element) => element.tagName === 'audio'));
	},
	async 'stops music when Godot removes the loading screen and keeps later visits silent'() {
		const page = browser(() => good);
		await settle();
		const audio = page.created.find((element) => element.tagName === 'audio');
		assert.equal(audio.src, 'https://night-nine.test/loading-screen-music.mp3');
		assert.equal(audio.paused, false);
		page.finish();
		assert.equal(audio.paused, true);
		assert.equal(page.storage.size, 1);
		const revisit = browser(() => good, {storage: page.storage});
		await revisit.fetch('https://night-nine.test/play.wasm');
		assert.equal(revisit.label.textContent, '100%');
		assert.ok(!revisit.created.some((element) => element.tagName === 'audio'));
	},
	async 'starts blocked music on the first page gesture without showing a button'() {
		let allowed = false;
		const page = browser(() => good, {play: async () => {
			if (!allowed) throw Object.assign(new Error('Gesture required'), {name: 'NotAllowedError'});
		}});
		await settle();
		const audio = page.created.find((element) => element.tagName === 'audio');
		assert.equal(audio.paused, true);
		assert.ok(!page.created.some((element) => element.tagName === 'button'));
		allowed = true;
		page.gesture();
		await settle();
		assert.equal(audio.paused, false);
		page.finish();
		assert.equal(audio.paused, true);
	},
	async 'fades the music out gradually when loading reaches 95 percent'() {
		const first = new Uint8Array(94).fill(1);
		const second = new Uint8Array(1).fill(2);
		const last = new Uint8Array(5).fill(3);
		const chunks = await makeManifest([['a.wasm', first], ['b.wasm', second], ['c.wasm', last]]);
		const gates = new Map(['b.wasm', 'c.wasm'].map((name) => {
			let open;
			const gate = new Promise((resolve) => { open = resolve; });
			return [name, {gate, open}];
		}));
		const bytes = {'a.wasm': first, 'b.wasm': second, 'c.wasm': last};
		const page = browser(async (name) => {
			await gates.get(name)?.gate;
			return bytes[name];
		}, {chunks});
		const loading = page.fetch('https://night-nine.test/play.wasm');
		const audio = page.created.find((element) => element.tagName === 'audio');
		await new Promise((resolve) => setTimeout(resolve, 20));
		assert.equal(page.label.textContent, '94%');
		assert.equal(audio.paused, false);
		assert.equal(audio.volume, 0.35);
		gates.get('b.wasm').open();
		await new Promise((resolve) => setTimeout(resolve, 200));
		assert.equal(page.label.textContent, '95%');
		assert.equal(audio.paused, true);
		const fade = audio.volumes.slice(audio.volumes.indexOf(0.35) + 1);
		assert.ok(fade.length >= 10, 'Lower the volume in steps instead of cutting the music');
		assert.ok(fade.every((volume, index) => volume < (fade[index - 1] ?? 0.35)));
		assert.equal(fade.at(-1), 0);
		page.gesture();
		await settle();
		assert.equal(audio.playCalls, 1);
		assert.equal(audio.paused, true);
		gates.get('c.wasm').open();
		await loading;
		assert.equal(page.storage.size, 0, 'The first visit completes only when Godot opens');
	},
	async 'lets an active fade finish when Godot removes the loading screen'() {
		const page = browser(() => good);
		await page.fetch('https://night-nine.test/play.wasm');
		const audio = page.created.find((element) => element.tagName === 'audio');
		page.finish();
		assert.equal(audio.paused, false, 'Do not cut the music while it fades');
		assert.equal(page.storage.size, 1);
		await new Promise((resolve) => setTimeout(resolve, 200));
		assert.equal(audio.paused, true);
		assert.equal(audio.volume, 0);
	},
	async 'a gesture after 95 percent does not start blocked music'() {
		const page = browser(() => good, {play: async () => {
			throw Object.assign(new Error('Gesture required'), {name: 'NotAllowedError'});
		}});
		await page.fetch('https://night-nine.test/play.wasm');
		await settle();
		const audio = page.created.find((element) => element.tagName === 'audio');
		page.gesture();
		await settle();
		assert.equal(audio.playCalls, 1);
	},
	async 'a late autoplay rejection cannot restart music over the intro'() {
		let reject;
		const page = browser(() => good, {play: () => new Promise((_, fail) => { reject = fail; })});
		const audio = page.created.find((element) => element.tagName === 'audio');
		page.finish();
		reject(Object.assign(new Error('Gesture required'), {name: 'NotAllowedError'}));
		await settle();
		page.gesture();
		await settle();
		assert.equal(audio.playCalls, 1);
		assert.equal(audio.paused, true);
	},
	async 'failed downloads stop music without consuming the first completed visit'() {
		const page = browser(() => bad);
		await assert.rejects(page.fetch('https://night-nine.test/play.wasm'), /failed after 3 attempts/);
		await new Promise((resolve) => setTimeout(resolve, 10));
		const audio = page.created.find((element) => element.tagName === 'audio');
		assert.equal(audio.paused, true);
		assert.equal(page.storage.size, 0);
	},
};

let failed = 0;
for (const [name, test] of Object.entries(tests)) {
	try {
		await test();
		console.log(`ok - ${name}`);
	} catch (error) {
		failed += 1;
		console.log(`not ok - ${name}\n${error.stack}`);
	}
}
process.exit(failed ? 1 : 0);

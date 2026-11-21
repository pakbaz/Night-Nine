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

function browser(serve) {
	const requests = [];
	const stored = new Map();
	const cache = {
		match: async (url) => stored.get(String(url)),
		put: async (url, response) => stored.set(String(url), response),
		delete: async (url) => stored.delete(String(url)),
	};
	const window = {
		fetch: async (input, init = {}) => {
			const url = new URL(String(input));
			const name = url.pathname.split('/').pop();
			requests.push({name, cache: init.cache});
			if (name === 'chunks.json') {
				return new Response(JSON.stringify(manifest));
			}
			return new Response(serve(name, init.cache));
		},
	};
	const context = {
		window, URL, Response, Request, Uint8Array, Map, Set, Array, Promise, Error, String,
		setTimeout: (callback) => setTimeout(callback, 0),
		crypto: globalThis.crypto,
		caches: {keys: async () => [], delete: async () => true, open: async () => cache},
		location: {origin: 'https://night-nine.test', pathname: '/play.html', reload() {}},
		document: {baseURI: 'https://night-nine.test/play.html', getElementById: () => null},
	};
	vm.runInNewContext(source, context);
	return {fetch: window.fetch, requests};
}

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

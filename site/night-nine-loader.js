(function () {
	'use strict';

	const nativeFetch = window.fetch.bind(window);
	const bigFiles = new Set(['play.pck', 'play.wasm']);
	const cachePrefix = `night-nine-parts:${location.origin}${location.pathname.replace(/[^/]*$/, '')}:`;
	const assemblies = new Map();
	let manifestPromise;
	let cachePromise;
	let progressTotal = 0;
	const progressByFile = new Map();

	function sleep(milliseconds) {
		return new Promise((resolve) => setTimeout(resolve, milliseconds));
	}

	function hex(buffer) {
		return Array.from(new Uint8Array(buffer), (value) => value.toString(16).padStart(2, '0')).join('');
	}

	async function sha256(bytes) {
		return hex(await crypto.subtle.digest('SHA-256', bytes));
	}

	function updateProgress(name, loaded) {
		progressByFile.set(name, loaded);
		const progress = document.getElementById('status-progress');
		const status = document.getElementById('status');
		if (!progress || !status || !progressTotal) {
			return;
		}
		status.style.visibility = 'visible';
		progress.style.display = 'block';
		progress.max = progressTotal;
		progress.value = Array.from(progressByFile.values()).reduce((sum, value) => sum + value, 0);
	}

	function showFailure(error) {
		const status = document.getElementById('status');
		const progress = document.getElementById('status-progress');
		const notice = document.getElementById('status-notice');
		if (!status || !notice) {
			return;
		}
		const message = error instanceof Error ? error.message : String(error);
		status.style.visibility = 'visible';
		if (progress) {
			progress.style.display = 'none';
		}
		notice.style.display = 'block';
		notice.replaceChildren();
		const text = document.createElement('div');
		text.textContent = `Night Nine could not verify its game files. ${message}`;
		const retry = document.createElement('button');
		retry.type = 'button';
		retry.textContent = 'Retry';
		retry.style.cssText = 'margin-top:1rem;padding:.65rem 1.2rem;font:inherit;cursor:pointer';
		retry.addEventListener('click', () => location.reload());
		notice.append(text, retry);
	}

	async function loadManifest() {
		const response = await nativeFetch(new URL('chunks.json', document.baseURI), {cache: 'no-cache'});
		if (!response.ok) {
			throw new Error(`chunks.json returned HTTP ${response.status}.`);
		}
		const manifest = await response.json();
		if (manifest.version !== 1 || !manifest.release || !Array.isArray(manifest.files)) {
			throw new Error('chunks.json is invalid.');
		}
		progressTotal = manifest.files.reduce((sum, entry) => sum + entry.size, 0);
		return manifest;
	}

	async function openReleaseCache(manifest) {
		const name = cachePrefix + manifest.release;
		const keys = await caches.keys();
		await Promise.all(keys
			.filter((key) => key.startsWith(cachePrefix) && key !== name)
			.map((key) => caches.delete(key)));
		return caches.open(name);
	}

	async function fetchPart(cache, part) {
		const url = new URL(part.name, document.baseURI);
		let lastError;
		for (let attempt = 1; attempt <= 3; attempt += 1) {
			try {
				let response = await cache.match(url);
				const cached = Boolean(response);
				if (!response) {
					// A retry must skip a bad copy in the browser HTTP cache.
					response = await nativeFetch(url, {cache: attempt === 1 ? 'no-cache' : 'reload'});
				}
				if (!response.ok) {
					throw new Error(`HTTP ${response.status}`);
				}
				const bytes = new Uint8Array(await response.arrayBuffer());
				if (bytes.byteLength !== part.size) {
					throw new Error(`expected ${part.size} bytes, received ${bytes.byteLength}`);
				}
				const digest = await sha256(bytes);
				if (digest !== part.sha256) {
					throw new Error('SHA-256 mismatch');
				}
				if (!cached) {
					await cache.put(url, new Response(bytes, {
						headers: {
							'Content-Length': String(part.size),
							'Content-Type': part.name.endsWith('.wasm')
								? 'application/wasm' : 'application/octet-stream',
						},
					}));
				}
				return bytes;
			} catch (error) {
				lastError = error;
				await cache.delete(url);
				if (attempt < 3) {
					await sleep(250 * (2 ** (attempt - 1)));
				}
			}
		}
		throw new Error(`${part.name} failed after 3 attempts: ${lastError.message || lastError}`);
	}

	async function assemble(entry, manifest) {
		if (!cachePromise) {
			cachePromise = openReleaseCache(manifest);
		}
		const cache = await cachePromise;
		const output = new Uint8Array(entry.size);
		const offsets = [];
		let offset = 0;
		for (const part of entry.parts) {
			offsets.push(offset);
			offset += part.size;
		}
		if (offset !== entry.size) {
			throw new Error(`${entry.name} has an inconsistent chunk manifest.`);
		}

		let next = 0;
		let loaded = 0;
		const workers = Array.from({length: Math.min(4, entry.parts.length)}, async () => {
			while (next < entry.parts.length) {
				const index = next;
				next += 1;
				const bytes = await fetchPart(cache, entry.parts[index]);
				output.set(bytes, offsets[index]);
				loaded += bytes.byteLength;
				updateProgress(entry.name, loaded);
			}
		});
		await Promise.all(workers);
		return new Response(output, {
			status: 200,
			headers: {
				'Content-Length': String(entry.size),
				'Content-Type': entry.name.endsWith('.wasm')
					? 'application/wasm' : 'application/octet-stream',
			},
		});
	}

	window.fetch = async function (input, init) {
		const requestUrl = new URL(input instanceof Request ? input.url : input, document.baseURI);
		const name = requestUrl.pathname.split('/').pop();
		if (requestUrl.origin !== location.origin || !bigFiles.has(name)) {
			return nativeFetch(input, init);
		}
		try {
			if (!manifestPromise) {
				manifestPromise = loadManifest();
			}
			const manifest = await manifestPromise;
			const entry = manifest.files.find((item) => item.name === name);
			if (!entry) {
				throw new Error(`${name} is missing from chunks.json.`);
			}
			if (!assemblies.has(name)) {
				assemblies.set(name, assemble(entry, manifest));
			}
			const response = await assemblies.get(name);
			return response.clone();
		} catch (error) {
			setTimeout(() => showFailure(error), 0);
			throw error;
		}
	};

	window.NightNineChunks = {showFailure};
}());

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
	const firstLoadKey = `night-nine:loaded:${new URL('.', document.baseURI).pathname}`;
	let loadingActive = true;
	let loadingMusic;
	let musicPending = false;
	let musicClosed = false;
	let fadeTimer;
	let loadingObserver;
	const musicVolume = 0.35;
	const fadeStartPercent = 95;
	const fadeSteps = 30;
	const fadeStepMilliseconds = 100;

	function ensureProgressLabel() {
		let label = document.getElementById('status-progress-label');
		if (!label) {
			label = document.createElement('div');
			label.id = 'status-progress-label';
			label.setAttribute?.('aria-live', 'polite');
			label.style.cssText =
				'position:absolute;left:0;right:0;bottom:calc(10% - 2rem);' +
				'text-align:center;color:#f6dcac;font:700 1rem/1.2 system-ui,sans-serif;' +
				'text-shadow:0 1px 3px #000;pointer-events:none;';
			const status = document.getElementById('status');
			status?.append(label);
		}
		return label;
	}

	function updateProgressLabel() {
		const label = ensureProgressLabel();
		const loaded = Array.from(progressByFile.values()).reduce((sum, value) => sum + value, 0);
		const percent = progressTotal ? Math.min(100, Math.max(0, Math.floor(loaded / progressTotal * 100))) : 0;
		label.textContent = `${percent}%`;
		if (percent >= fadeStartPercent) {
			fadeOutLoadingMusic();
		}
	}

	function clearMusicRetry() {
		window.removeEventListener('pointerdown', startLoadingMusic);
		window.removeEventListener('keydown', startLoadingMusic);
	}

	function fadeOutLoadingMusic() {
		if (musicClosed) {
			return;
		}
		musicClosed = true;
		clearMusicRetry();
		if (!loadingMusic || loadingMusic.paused) {
			loadingMusic?.pause();
			return;
		}
		let step = 0;
		const lowerVolume = () => {
			step += 1;
			const remaining = 1 - step / fadeSteps;
			// A squared curve sounds even to the ear; a linear one drops off at the end.
			loadingMusic.volume = musicVolume * remaining * remaining;
			if (step < fadeSteps) {
				fadeTimer = setTimeout(lowerVolume, fadeStepMilliseconds);
			} else {
				fadeTimer = null;
				loadingMusic.pause();
			}
		};
		fadeTimer = setTimeout(lowerVolume, fadeStepMilliseconds);
	}

	function stopLoadingMusic() {
		loadingActive = false;
		musicClosed = true;
		clearMusicRetry();
		clearTimeout(fadeTimer);
		fadeTimer = null;
		loadingObserver?.disconnect();
		if (loadingMusic) {
			loadingMusic.pause();
			loadingMusic.currentTime = 0;
			loadingMusic.remove();
		}
	}

	function finishLoading() {
		if (!loadingActive) {
			return;
		}
		try {
			window.localStorage.setItem(firstLoadKey, '1');
		} catch (error) {
			console.warn('Night Nine could not remember the completed first load.', error);
		}
		if (fadeTimer) {
			// Godot can block the page near 100%; let the fade end smoothly instead of cutting it.
			loadingActive = false;
			loadingObserver?.disconnect();
			return;
		}
		stopLoadingMusic();
	}

	function isFirstLoad() {
		try {
			return window.localStorage.getItem(firstLoadKey) !== '1';
		} catch (error) {
			console.warn('Night Nine loading music is disabled because browser storage is unavailable.', error);
			return false;
		}
	}

	// The landing page starts the music inside its Play click, where browsers allow
	// sound, and opens this page in place. Take that music over instead of a new copy.
	function launchMusic() {
		try {
			const host = window.parent;
			if (!host || host === window) {
				return null;
			}
			const music = host.nightNineLaunchMusic;
			host.nightNineLaunchMusic = null;
			return music && typeof music.play === 'function' ? music : null;
		} catch (error) {
			return null;
		}
	}

	function startLoadingMusic() {
		if (!loadingActive || musicClosed || musicPending) {
			return;
		}
		if (!loadingMusic) {
			loadingMusic = launchMusic();
		}
		if (!loadingMusic) {
			loadingMusic = document.createElement('audio');
			loadingMusic.src = new URL('loading-screen-music.mp3', document.baseURI).href;
			loadingMusic.loop = true;
			loadingMusic.preload = 'auto';
			loadingMusic.volume = musicVolume;
			loadingMusic.setAttribute('aria-hidden', 'true');
			document.body.append(loadingMusic);
		}
		musicPending = true;
		loadingMusic.play().then(() => {
			musicPending = false;
			if (!loadingActive || (musicClosed && !fadeTimer)) {
				loadingMusic.pause();
			}
			clearMusicRetry();
		}).catch((error) => {
			musicPending = false;
			if (!loadingActive || musicClosed) {
				return;
			}
			if (error.name !== 'NotAllowedError') {
				console.warn('Night Nine could not play the loading music.', error);
				clearMusicRetry();
				return;
			}
			// Browsers can block sound until the first tap, click, or key press.
			window.addEventListener('pointerdown', startLoadingMusic, {once: true});
			window.addEventListener('keydown', startLoadingMusic, {once: true});
		});
	}

	if (document.getElementById('status') && isFirstLoad()) {
		startLoadingMusic();
	}
	window.addEventListener('pagehide', stopLoadingMusic, {once: true});
	if (typeof MutationObserver !== 'undefined') {
		loadingObserver = new MutationObserver(() => {
			const status = document.getElementById('status');
			if (!status || status.isConnected === false) {
				finishLoading();
			} else if (document.getElementById('status-notice')?.style.display === 'block') {
				stopLoadingMusic();
			}
		});
		// Godot removes the overlay itself when ready; observe its parent.
		loadingObserver.observe(document.body, {
			childList: true, subtree: true, attributes: true, attributeFilter: ['style'],
		});
	}

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
		updateProgressLabel();
	}

	function showFailure(error) {
		const status = document.getElementById('status');
		const progress = document.getElementById('status-progress');
		const notice = document.getElementById('status-notice');
		stopLoadingMusic();
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
		updateProgressLabel();
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

	window.NightNineChunks = {showFailure, stopLoadingMusic};
}());

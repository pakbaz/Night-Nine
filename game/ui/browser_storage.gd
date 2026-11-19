extends RefCounted

signal backup_selected(text: String)
signal status_changed(message: String)

var bridge: JavaScriptObject
var import_callback: JavaScriptObject
var storage_callback: JavaScriptObject

func _init() -> void:
	JavaScriptBridge.eval("""
		window.nightNineStorage = {
			choosing: false,
			choose(callback, maxBytes) {
				if (this.choosing) return;
				this.choosing = true;
				const input = document.createElement('input');
				input.type = 'file';
				input.accept = '.json,application/json';
				input.hidden = true;
				document.body.appendChild(input);
				const finish = (text, error) => {
					input.remove();
					this.choosing = false;
					callback(text, error);
				};
				input.addEventListener('cancel', () => finish('', 'Import cancelled.'), {once:true});
				input.addEventListener('change', async () => {
					const file = input.files[0];
					if (!file) return finish('', 'Import cancelled.');
					if (file.size > maxBytes) return finish('', 'Save file is too large.');
					try { finish(await file.text(), ''); }
					catch (error) { finish('', 'Could not read the backup: ' + error.message); }
				}, {once:true});
				try { input.click(); }
				catch (error) { finish('', 'Could not open the file picker: ' + error.message); }
			},
			async persist(callback) {
				if (!navigator.storage || !navigator.storage.persist) {
					callback('This browser does not support persistent storage. Export a save backup.');
					return;
				}
				try {
					const kept = await navigator.storage.persisted() || await navigator.storage.persist();
					callback(kept
						? 'Persistent storage is enabled. Clearing site data will still erase saves and cached files.'
						: 'Persistent storage was not granted. Saves and cached files may be evicted; export a backup.');
				} catch (error) {
					callback('Could not request persistent storage: ' + error.message);
				}
			}
		};
	""", true)
	bridge = JavaScriptBridge.get_interface("nightNineStorage")
	import_callback = JavaScriptBridge.create_callback(_selected)
	storage_callback = JavaScriptBridge.create_callback(func(args: Array): status_changed.emit(str(args[0])))

func choose_backup() -> void:
	bridge.choose(import_callback, NightSaves.MAX_BYTES)

func request_persistence() -> void:
	bridge.persist(storage_callback)

func download(text: String) -> void:
	JavaScriptBridge.download_buffer(text.to_utf8_buffer(), "night-nine-save.json", "application/json")

func _selected(args: Array) -> void:
	if not str(args[1]).is_empty():
		status_changed.emit(str(args[1]))
	else:
		backup_selected.emit(str(args[0]))

class_name NightSaves
extends RefCounted
## Checksummed JSON, last-good backup and same-directory atomic replacement.

const MAX_BYTES := 1048576
var root: String
var last_error := ""
var validator: Callable

func _init(save_root: String, state_validator: Callable) -> void:
	root = save_root
	validator = state_validator

func _path(slot: String) -> String:
	var regex := RegEx.new()
	regex.compile("^[a-zA-Z0-9_-]{1,40}$")
	if regex.search(slot) == null:
		return ""
	return root.path_join(slot + ".json")

func write_slot(slot: String, state: Dictionary) -> bool:
	last_error = validator.call(state)
	if not last_error.is_empty():
		return false
	var path: String = _path(slot)
	if path.is_empty():
		last_error = "Invalid save slot."
		return false
	var error: Error = DirAccess.make_dir_recursive_absolute(root)
	if error != OK:
		last_error = "Cannot create save folder: " + error_string(error)
		return false
	var body: String = _encode(state)
	if body.to_utf8_buffer().size() > MAX_BYTES:
		last_error = "Save exceeds the size limit."
		return false
	var temporary: String = path + ".tmp"
	var file := FileAccess.open(temporary, FileAccess.WRITE)
	if file == null:
		last_error = "Cannot open temporary save: " + error_string(FileAccess.get_open_error())
		return false
	file.store_string(body)
	file.flush()
	error = file.get_error()
	file.close()
	if error != OK:
		last_error = "Could not write complete save."
		return false
	# Preserve only a validated previous file, never overwrite a good backup with corruption.
	if FileAccess.file_exists(path):
		var previous: Dictionary = _read_file(path)
		if previous.get("ok", false):
			error = DirAccess.copy_absolute(path, path + ".bak")
			if error != OK:
				last_error = "Cannot preserve previous save."
				return false
	error = DirAccess.rename_absolute(temporary, path)
	if error != OK:
		last_error = "Cannot replace save: " + error_string(error)
		return false
	last_error = ""
	return true

func read_slot(slot: String) -> Dictionary:
	var path: String = _path(slot)
	if path.is_empty():
		return {"ok": false, "error": "Invalid save slot."}
	var result: Dictionary = _read_file(path)
	if result.get("ok", false):
		result["recovered"] = false
		return result
	var backup: Dictionary = _read_file(path + ".bak")
	if backup.get("ok", false):
		backup["recovered"] = true
		return backup
	return result

func export_slot(slot: String) -> Dictionary:
	var result := read_slot(slot)
	if result.get("ok", false):
		result["text"] = _encode(result.state)
	return result

func import_slot(slot: String, text: String) -> bool:
	var result := _decode(text)
	if not result.get("ok", false):
		last_error = result.error
		return false
	return write_slot(slot, result.state)

func _encode(state: Dictionary) -> String:
	var payload := JSON.stringify(state, "", true)
	return JSON.stringify({"format": 1, "sha256": payload.sha256_text(), "payload": payload})

func _read_file(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"ok": false, "error": "Save unavailable."}
	if file.get_length() > MAX_BYTES:
		file.close()
		return {"ok": false, "error": "Save file is too large."}
	var text: String = file.get_as_text()
	file.close()
	return _decode(text)

func _decode(text: String) -> Dictionary:
	if text.to_utf8_buffer().size() > MAX_BYTES:
		return {"ok": false, "error": "Save file is too large."}
	var parser := JSON.new()
	if parser.parse(text) != OK:
		return {"ok": false, "error": "Invalid save JSON."}
	var envelope: Variant = parser.data
	if not envelope is Dictionary or envelope.get("format") != 1:
		return {"ok": false, "error": "Invalid save envelope."}
	var payload: Variant = envelope.get("payload")
	if not payload is String or envelope.get("sha256") != payload.sha256_text():
		return {"ok": false, "error": "Save checksum failed."}
	if parser.parse(payload) != OK:
		return {"ok": false, "error": "Invalid save payload."}
	var candidate: Variant = parser.data
	if not candidate is Dictionary:
		return {"ok": false, "error": "Save payload must be an object."}
	var issue: String = validator.call(candidate)
	if not issue.is_empty():
		return {"ok": false, "error": issue}
	return {"ok": true, "state": candidate}

class_name NightCampaign
extends RefCounted
## Progress is an ordered journal of completed interactions. No consumable quest items.
## Validation replays prerequisites and scene gates before accepting a saved journal.

signal changed
var content: Dictionary
var data: Dictionary
var task_index: Dictionary = {}
var task_scene: Dictionary = {}
const NOTE_LIMIT := 240

func _init() -> void:
	content = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	for i: int in range(content.scenes.size()):
		for task: Dictionary in content.scenes[i].tasks:
			task_index[task.id] = task
			task_scene[task.id] = i
	reset()

func reset() -> void:
	data = {"schema": 2, "game": "night-nine", "content": content.version,
		"scene": 0, "actor": content.scenes[0].actors[0], "done": [],
		"seen": [], "finished": false, "hints": {}, "walk_positions": {},
		"notebook": {"marks": {}, "notes": {}}}
	changed.emit()

func current() -> Dictionary:
	return content.scenes[int(data.scene)]

func available(task_id: String) -> bool:
	if not task_index.has(task_id) or task_scene[task_id] != int(data.scene):
		return false
	var task: Dictionary = task_index[task_id]
	if task_id in data.done:
		return false
	for required: String in task.requires:
		if required not in data.done:
			return false
	return true

func choose(task_id: String, answer: int, puzzle_input: Array = []) -> Dictionary:
	if not available(task_id):
		return {"ok": false, "reason": "Follow the available leads first."}
	var task: Dictionary = task_index[task_id]
	if not task.actor.is_empty() and task.actor != data.actor:
		return {"ok": false, "reason": "Switch to " + content.cast[task.actor] + " for this part."}
	if answer != int(task.answer):
		return {"ok": false, "reason": "That approach does not resolve this lead. Review the evidence or use a hint."}
	if task.has("puzzle") and not _settings_match(puzzle_input,task.puzzle.solution):
		return {"ok": false, "reason": "Those settings do not satisfy the evidence. Check each connection; you can retry safely."}
	data.done.append(task_id)
	changed.emit()
	return {"ok": true, "lines": task.lines}

func _settings_match(values: Array, solution: Array) -> bool:
	# JSON numbers are floats; OptionButton selections are integers.
	# Array equality distinguishes these types even for the same setting.
	if values.size()!=solution.size():
		return false
	for i: int in range(solution.size()):
		if typeof(values[i]) not in [TYPE_INT,TYPE_FLOAT]:
			return false
		if not is_finite(float(values[i])) or float(values[i])!=float(int(solution[i])):
			return false
	return true

func switch_actor(actor: String) -> bool:
	if actor not in current().actors:
		return false
	data.actor = actor
	changed.emit()
	return true

func can_leave() -> bool:
	for task: Dictionary in current().tasks:
		if task.id not in data.done:
			return false
	return true

func advance() -> bool:
	if not can_leave():
		return false
	if int(data.scene) == content.scenes.size() - 1:
		data.finished = true
	else:
		data.scene = int(data.scene) + 1
		data.actor = current().actors[0]
		data.walk_positions = {}
	changed.emit()
	return true

func mark_seen(ids: Array) -> void:
	for id: String in ids:
		if content.lines.has(id) and id not in data.seen:
			data.seen.append(id)

func hint(task_id: String) -> String:
	if not task_index.has(task_id):
		return ""
	var task: Dictionary = task_index[task_id]
	var level := mini(int(data.hints.get(task_id, 0)) + 1, 3)
	data.hints[task_id] = level
	changed.emit()
	if task.has("hints"):
		return str(task.hints[level - 1])
	if task.get("puzzle", {}).has("hints"):
		return str(task.puzzle.hints[level - 1])
	if level == 1:
		return task.puzzle.instruction if task.has("puzzle") else task.prompt
	if level == 2:
		if not task.actor.is_empty() and task.actor != data.actor:
			return "Ask " + content.cast[task.actor] + " to handle this."
		return "What can you verify independently? Preserve evidence and use the tools already available."
	if task.has("puzzle"):
		var answer := ""
		for i: int in range(task.puzzle.rows.size()):
			var row: Dictionary = task.puzzle.rows[i]
			answer += row.label + ": " + row.options[int(task.puzzle.solution[i])] + ". "
		return answer
	return "Try: " + task.options[int(task.answer)]

func restore(candidate: Variant) -> bool:
	if not validate(candidate).is_empty():
		return false
	data = candidate.duplicate(true)
	if not data.has("walk_positions"):
		data.walk_positions = {}
	if not data.has("notebook"):
		data.notebook = {"marks": {}, "notes": {}}
	changed.emit()
	return true

func validate(candidate: Variant) -> String:
	if not candidate is Dictionary or candidate.size() != 9 + int(candidate.has("walk_positions")) + int(candidate.has("notebook")):
		return "Invalid campaign state."
	for key: String in ["schema", "game", "content", "scene", "actor", "done", "seen", "finished", "hints"]:
		if not candidate.has(key):
			return "Missing campaign field."
	if candidate.schema != 2 or candidate.game != "night-nine" or candidate.content != content.version:
		return "Unsupported campaign version."
	if not (candidate.scene is int or candidate.scene is float) or candidate.scene != int(candidate.scene):
		return "Invalid scene index."
	var at := int(candidate.scene)
	if at < 0 or at >= content.scenes.size() or candidate.actor not in content.scenes[at].actors:
		return "Invalid scene or actor."
	var positions: Variant = candidate.get("walk_positions",{})
	if not positions is Dictionary or positions.size()>content.scenes[at].actors.size():
		return "Invalid investigator positions."
	for id: Variant in positions:
		var foot: Variant = positions[id]
		if id not in content.scenes[at].actors or not foot is Array or foot.size()!=3 or not foot[2] is bool:
			return "Invalid investigator position."
		for axis: int in 2:
			var coordinate: Variant = foot[axis]
			if not (coordinate is float or coordinate is int) or not is_finite(coordinate) or coordinate<0.0 or coordinate>1.0:
				return "Invalid investigator coordinate."
	if not candidate.done is Array or candidate.done.size() > task_index.size():
		return "Invalid journal."
	var completed: Dictionary = {}
	for id: Variant in candidate.done:
		if not id is String or not task_index.has(id) or completed.has(id) or int(task_scene[id]) > at:
			return "Invalid completed task."
		for required: String in task_index[id].requires:
			if not completed.has(required):
				return "Task prerequisite missing."
		completed[id] = true
	for i: int in range(at):
		for task: Dictionary in content.scenes[i].tasks:
			if not completed.has(task.id):
				return "Earlier scene is unfinished."
	if not candidate.seen is Array or candidate.seen.size() > content.lines.size():
		return "Invalid transcript history."
	var unique_lines: Dictionary = {}
	for id: Variant in candidate.seen:
		if not id is String or not content.lines.has(id) or unique_lines.has(id):
			return "Unknown or duplicated transcript line."
		unique_lines[id] = true
	if not candidate.finished is bool:
		return "Invalid ending flag."
	if candidate.finished and (at != content.scenes.size()-1 or completed.size() != task_index.size()):
		return "Campaign ending is premature."
	if not candidate.hints is Dictionary or candidate.hints.size() > task_index.size():
		return "Invalid hints."
	for id: Variant in candidate.hints:
		var count: Variant = candidate.hints[id]
		if not id is String or not task_index.has(id) or not (count is int or count is float):
			return "Invalid hint entry."
		if count != int(count) or count < 1 or count > 3:
			return "Invalid hint level."
	if candidate.has("notebook") and not _valid_notebook(candidate.notebook, completed):
		return "Invalid notebook entry."
	return ""

func available_theories(case_id: String, completed: Variant) -> Array:
	var page: Dictionary = content.get("notebook_cases", {}).get(case_id, {})
	var theories: Array = []
	for theory: Dictionary in page.get("theories", []):
		if theory.after in completed:
			theories.append(theory)
	return theories

func mark_theory(case_id: String, id: String, mark: String) -> bool:
	if mark not in ["open", "struck", ""]:
		return false
	for theory: Dictionary in available_theories(case_id, data.done):
		if theory.id == id:
			if mark.is_empty():
				data.notebook.marks.erase(id)
			else:
				data.notebook.marks[id] = mark
			changed.emit()
			return true
	return false

func write_case_note(case_id: String, note: String) -> bool:
	if note.length() > NOTE_LIMIT or available_theories(case_id, data.done).is_empty():
		return false
	if note.strip_edges().is_empty():
		data.notebook.notes.erase(case_id)
	else:
		data.notebook.notes[case_id] = note
	changed.emit()
	return true

func _valid_notebook(book: Variant, completed: Dictionary) -> bool:
	if not book is Dictionary or book.size() != 2 or not book.get("marks") is Dictionary or not book.get("notes") is Dictionary:
		return false
	var marks: Dictionary = {}
	var pages: Dictionary = {}
	for case_id: String in content.get("notebook_cases", {}):
		var theories := available_theories(case_id, completed)
		if not theories.is_empty():
			pages[case_id] = true
		for theory: Dictionary in theories:
			marks[theory.id] = true
	for id: Variant in book.marks:
		if not marks.has(id) or book.marks[id] not in ["open", "struck"]:
			return false
	for id: Variant in book.notes:
		if not pages.has(id) or not book.notes[id] is String or book.notes[id].length() > NOTE_LIMIT:
			return false
	return true

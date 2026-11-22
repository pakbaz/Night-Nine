class_name NightCampaign
extends RefCounted
## Progress is an ordered journal of completed interactions. No consumable quest items.
## Validation replays prerequisites and scene gates before accepting a saved journal.

signal changed
var content: Dictionary
var data: Dictionary
var task_index: Dictionary = {}
var task_scene: Dictionary = {}
var line_scene: Dictionary = {}
const NOTE_LIMIT := 240
## Saves made before the story reorder ("campaign-1") count scenes in this order.
const ORDER_V1 := ["p_veyr", "p_meeting", "p_bay", "c1_flat", "c1_pier", "c1_dinner", "c1_escape", "c2_aquarium", "c2_ship", "c3_house", "c3_archive", "i1_archive", "c4_safe", "c4_escape", "c5_shack", "c5_station", "c6_iris", "c6_jail", "i2_nora", "c7_gate", "c7_swap", "c8_lab", "c8_beach", "c8_rig", "c9_gallery", "c9_wake", "c9_choir", "c10_station", "c10_town", "c10_live", "c10_report", "epilogue", "one_year", "postcredits"]

func _init() -> void:
	content = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	for i: int in range(content.scenes.size()):
		var scene: Dictionary = content.scenes[i]
		for line_group: String in ["context", "intro", "recap", "outro"]:
			for line_id: String in scene.get(line_group, []):
				line_scene[line_id] = i
		for task: Dictionary in scene.tasks:
			task_index[task.id] = task
			task_scene[task.id] = i
			for line_group: String in ["lead", "lines"]:
				for line_id: String in task.get(line_group, []):
					line_scene[line_id] = i
			var finding: String = task.get("finding", "")
			if not finding.is_empty():
				line_scene[finding] = i
	reset()

func reset() -> void:
	data = {"schema": 2, "game": "night-nine", "content": content.version,
		"scene": 0, "scene_id": content.scenes[0].id, "chapter": content.scenes[0].chapter,
		"actor": content.scenes[0].actors[0], "done": [],
		"seen": [], "finished": false, "hints": {}, "walk_positions": {},
		"notebook": {"marks": {}, "notes": {}}, "case_boards": {},
		"misses": {}, "post_hint_misses": {}, "missed_options": {}, "revealed": []}
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
		record_miss(task_id, answer)
		return {"ok": false, "reason": str(task.get("wrong", {}).get(str(answer),
			"That approach does not resolve this lead. Review the evidence or use a hint.")),
			"offer_hint": int(data.misses.get(task_id, 0)) >= 2 and int(data.hints.get(task_id, 0)) == 0,
			"offer_answer": answer_available(task_id)}
	if task.has("puzzle") and not _settings_match(puzzle_input,task.puzzle.solution):
		record_miss(task_id)
		return {"ok": false, "reason": "Those settings do not satisfy the evidence. Check each connection; you can retry safely.",
			"offer_hint": int(data.misses.get(task_id, 0)) >= 2 and int(data.hints.get(task_id, 0)) == 0,
			"offer_answer": answer_available(task_id)}
	data.done.append(task_id)
	data.case_boards.erase(task_id)
	for field: String in ["misses", "post_hint_misses", "missed_options"]:
		data[field].erase(task_id)
	changed.emit()
	return {"ok": true, "lines": task.lines, "finding": str(task.get("finding", ""))}

func record_miss(task_id: String, option: int = -1) -> void:
	if not task_index.has(task_id):
		return
	data.misses[task_id] = int(data.misses.get(task_id, 0)) + 1
	if option >= 0:
		var options: Array = data.missed_options.get(task_id, [])
		if option not in options:
			options.append(option)
		data.missed_options[task_id] = options
	if int(data.hints.get(task_id, 0)) >= 3:
		data.post_hint_misses[task_id] = int(data.post_hint_misses.get(task_id, 0)) + 1
	changed.emit()

func unseen_lead(task_id: String) -> Array:
	var pending: Array = []
	if not task_index.has(task_id):
		return pending
	for id: String in task_index[task_id].get("lead", []):
		if id not in data.seen:
			pending.append(id)
	return pending

func perspective_name(task_id: String) -> String:
	if not task_index.has(task_id):
		return "Steve"
	var task: Dictionary = task_index[task_id]
	var role: String = task.get("actor", "")
	if role.is_empty():
		var scene: Dictionary = content.scenes[int(task_scene[task_id])]
		if not scene.get("actors", []).is_empty():
			role = str(scene.actors[0])
	return str(content.get("cast", {}).get(role, "Steve"))

func lock_reason(task_id: String) -> String:
	if not task_index.has(task_id):
		return ""
	var labels: Array[String] = []
	for required: String in task_index[task_id].requires:
		if required in data.done:
			continue
		var prerequisite: Dictionary = task_index.get(required, {})
		labels.append("“" + str(prerequisite.get("card", prerequisite.get("title", required))) + "”")
	if labels.is_empty():
		return ""
	return "Solve " + " and ".join(labels) + " first"

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

## One entry per settings row: true where the chosen value matches the solution.
func settings_marks(task_id: String, values: Array) -> Array[bool]:
	var marks: Array[bool] = []
	if not task_index.has(task_id):
		return marks
	var solution: Array = task_index[task_id].get("puzzle", {}).get("solution", [])
	for i: int in solution.size():
		var value: Variant = values[i] if i < values.size() else null
		marks.append(typeof(value) in [TYPE_INT, TYPE_FLOAT] and is_finite(float(value)) and float(value) == float(int(solution[i])))
	return marks

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
	data.misses = {}
	data.post_hint_misses = {}
	data.missed_options = {}
	data.scene_id = current().id
	data.chapter = current().chapter
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
	if level == 3:
		data.post_hint_misses[task_id] = 0
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

func hint_label(task_id: String) -> String:
	return "Hint %d of 3" % mini(int(data.hints.get(task_id, 0)) + 1, 3)

func answer_available(task_id: String) -> bool:
	return task_index.has(task_id) and int(data.hints.get(task_id, 0)) >= 3 \
		and int(data.post_hint_misses.get(task_id, 0)) >= 2

func reveal_answer(task_id: String) -> bool:
	if not answer_available(task_id):
		return false
	if task_id not in data.revealed:
		data.revealed.append(task_id)
		changed.emit()
	return true

func answer_text(task_id: String) -> String:
	if not task_index.has(task_id):
		return ""
	var task: Dictionary = task_index[task_id]
	var puzzle: Dictionary = task.get("puzzle", {})
	if puzzle.get("presentation", "") == "case_board":
		var parts: Array[String] = []
		for stage: Dictionary in puzzle.get("stages", []):
			for i: int in stage.answer.size():
				parts.append(str(stage.slots[i]) + ": " + str(stage.pieces[int(stage.answer[i])]))
		return "Answer: " + "; ".join(parts)
	if puzzle.has("rows"):
		var rows: Array[String] = []
		for i: int in puzzle.rows.size():
			rows.append(str(puzzle.rows[i].label) + ": " + str(puzzle.rows[i].options[int(puzzle.solution[i])]))
		return "Answer: " + "; ".join(rows)
	return "Answer: " + str(task.options[int(task.answer)])

## Carry a campaign-1 save into the new order. A player in the old three-night
## prologue starts at the bay. Later players keep their place; flashbacks they
## have not reached in the new order are simply played again when they arrive.
func migrate(candidate: Variant) -> Variant:
	if not candidate is Dictionary or candidate.get("schema") != 2 or candidate.get("game") != "night-nine":
		return candidate
	var source_version: String = str(candidate.get("content", ""))
	if source_version == str(content.version):
		return candidate
	if source_version not in ["campaign-1", "campaign-2"]:
		return candidate
	var order: Array = []
	for scene: Dictionary in content.scenes:
		order.append(scene.id)
	var target := -1
	var requested_id: String = "" if source_version == "campaign-1" else str(candidate.get("scene_id", ""))
	if not requested_id.is_empty():
		target = order.find(requested_id)
	var old: Variant = candidate.get("scene")
	if target < 0 and (old is int or old is float) and old == int(old):
		var old_index := int(old)
		if source_version == "campaign-1" and old_index >= 0 and old_index < ORDER_V1.size():
			target = 0 if old_index < 3 else order.find(ORDER_V1[old_index])
		elif old_index >= 0 and old_index < content.scenes.size():
			target = old_index
	if target < 0:
		var chapter: String = str(candidate.get("chapter", ""))
		for i: int in content.scenes.size():
			if content.scenes[i].chapter == chapter:
				target = i
				break
	if target < 0:
		target = 0
	var moved: Dictionary = {
		"schema": 2, "game": "night-nine", "content": content.version,
		"scene": target, "scene_id": content.scenes[target].id, "chapter": content.scenes[target].chapter,
		"actor": candidate.get("actor", content.scenes[target].actors[0]), "done": [],
		"seen": [], "finished": false, "hints": {}, "walk_positions": {},
		"notebook": {"marks": {}, "notes": {}}, "case_boards": {},
		"misses": {}, "post_hint_misses": {}, "missed_options": {}, "revealed": []
	}
	var done: Array = []
	if candidate.get("done") is Array:
		for id: Variant in candidate.done:
			if id is String and task_index.has(id) and int(task_scene[id]) <= target and id not in done:
				var ready := true
				for required: String in task_index[id].requires:
					ready = ready and required in done
				if ready:
					done.append(id)
	moved.done = done
	var seen: Array = []
	if candidate.get("seen") is Array:
		for id: Variant in candidate.seen:
			if id is String and content.lines.has(id) and int(line_scene.get(id, target)) <= target and id not in seen:
				seen.append(id)
	moved.seen = seen
	var hints: Dictionary = {}
	if candidate.get("hints") is Dictionary:
		for id: Variant in candidate.hints:
			var level: Variant = candidate.hints[id]
			if id is String and task_index.has(id) and int(task_scene[id]) <= target \
				and (level is int or level is float) and level == int(level) and level >= 1 and level <= 3:
				hints[id] = int(level)
	moved.hints = hints
	if moved.get("actor") not in content.scenes[target].actors:
		moved.actor = content.scenes[target].actors[0]
	if requested_id == content.scenes[target].id and candidate.get("walk_positions") is Dictionary:
		moved.walk_positions = candidate.walk_positions.duplicate(true)
	for field: String in ["misses", "post_hint_misses"]:
		if candidate.get(field) is Dictionary:
			for id: Variant in candidate[field]:
				var count: Variant = candidate[field][id]
				if id is String and task_index.has(id) and int(task_scene[id]) == target \
					and (count is int or count is float) and count == int(count) and count >= 0:
					moved[field][id] = int(count)
	if candidate.get("missed_options") is Dictionary:
		for id: Variant in candidate.missed_options:
			if not id is String or not task_index.has(id) or int(task_scene[id]) != target or not candidate.missed_options[id] is Array:
				continue
			var options: Array = []
			for option: Variant in candidate.missed_options[id]:
				if (option is int or option is float) and option == int(option) and option >= 0 \
					and option < task_index[id].options.size() and int(option) not in options:
					options.append(int(option))
			if not options.is_empty():
				moved.missed_options[id] = options
	if candidate.get("revealed") is Array:
		for id: Variant in candidate.revealed:
			if id is String and task_index.has(id) and int(task_scene[id]) <= target and id not in moved.revealed:
				moved.revealed.append(id)
	if candidate.get("case_boards") is Dictionary:
		for id: Variant in candidate.case_boards:
			if id is String and task_index.has(id) and int(task_scene[id]) == target and id not in done \
				and _valid_board(id, candidate.case_boards[id]):
				moved.case_boards[id] = candidate.case_boards[id].duplicate(true)
	if candidate.get("notebook") is Dictionary:
		var completed: Dictionary = {}
		for id: String in done:
			completed[id] = true
		var marks: Dictionary = {}
		var notes: Dictionary = {}
		for case_id: String in content.get("notebook_cases", {}):
			var theories := available_theories(case_id, completed)
			if not theories.is_empty() and candidate.notebook.get("notes", {}).has(case_id):
				notes[case_id] = candidate.notebook.notes[case_id]
			for theory: Dictionary in theories:
				if candidate.notebook.get("marks", {}).has(theory.id):
					marks[theory.id] = candidate.notebook.marks[theory.id]
		moved.notebook = {"marks": marks, "notes": notes}
	return moved

func restore(candidate: Variant) -> bool:
	candidate = migrate(candidate)
	if not validate(candidate).is_empty():
		return false
	data = candidate.duplicate(true)
	if not data.has("walk_positions"):
		data.walk_positions = {}
	if not data.has("notebook"):
		data.notebook = {"marks": {}, "notes": {}}
	if not data.has("case_boards"):
		data.case_boards = {}
	for field: String in ["misses", "post_hint_misses", "missed_options"]:
		if not data.has(field):
			data[field] = {}
	if not data.has("revealed"):
		data.revealed = []
	data.scene_id = current().id
	data.chapter = current().chapter
	changed.emit()
	return true

func validate(candidate: Variant) -> String:
	candidate = migrate(candidate)
	var allowed := ["schema", "game", "content", "scene", "scene_id", "chapter", "actor", "done", "seen",
		"finished", "hints", "walk_positions", "notebook", "case_boards", "misses",
		"post_hint_misses", "missed_options", "revealed"]
	if not candidate is Dictionary:
		return "Invalid campaign state."
	for key: Variant in candidate:
		if key not in allowed:
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
	if candidate.get("scene_id", content.scenes[at].id) != content.scenes[at].id \
			or candidate.get("chapter", content.scenes[at].chapter) != content.scenes[at].chapter:
		return "Invalid scene identity."
	var positions: Variant = candidate.get("walk_positions",{})
	if not positions is Dictionary or positions.size()>content.scenes[at].actors.size():
		return "Invalid investigator positions."
	for id: Variant in positions:
		var foot: Variant = positions[id]
		if id not in content.scenes[at].actors or not foot is Array or foot.size() not in [3,4] or not foot[2] is bool:
			return "Invalid investigator position."
		if foot.size()==4 and foot[3] not in ["side","toward","away"]:
			return "Invalid investigator facing."
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
	for field: String in ["misses", "post_hint_misses"]:
		var entries: Variant = candidate.get(field, {})
		if not entries is Dictionary:
			return "Invalid miss history."
		for id: Variant in entries:
			var count: Variant = entries[id]
			if not id is String or not task_index.has(id) or int(task_scene[id]) != at \
					or not (count is int or count is float) or count != int(count) or count < 0:
				return "Invalid miss history."
	var missed: Variant = candidate.get("missed_options", {})
	if not missed is Dictionary:
		return "Invalid missed options."
	for id: Variant in missed:
		if not id is String or not task_index.has(id) or int(task_scene[id]) != at or not missed[id] is Array:
			return "Invalid missed options."
		var unique_options := {}
		for option: Variant in missed[id]:
			if not (option is int or option is float) or option != int(option) or option < 0 \
					or option >= task_index[id].options.size() or unique_options.has(int(option)):
				return "Invalid missed options."
			unique_options[int(option)] = true
	var revealed: Variant = candidate.get("revealed", [])
	if not revealed is Array:
		return "Invalid answer history."
	var unique_reveals := {}
	for id: Variant in revealed:
		if not id is String or not task_index.has(id) or int(task_scene[id]) > at or unique_reveals.has(id):
			return "Invalid answer history."
		unique_reveals[id] = true
	if candidate.has("notebook") and not _valid_notebook(candidate.notebook, completed):
		return "Invalid notebook entry."
	var drafts: Variant = candidate.get("case_boards", {})
	if not drafts is Dictionary or drafts.size() > content.scenes[at].tasks.size():
		return "Invalid case boards."
	for task_id: Variant in drafts:
		if task_scene.get(task_id, -1) != at or completed.has(task_id) or not _valid_board(task_id, drafts[task_id]):
			return "Invalid case board."
		for required: String in task_index[task_id].requires:
			if not completed.has(required):
				return "Case board prerequisite missing."
	return ""

func board_draft(id: String) -> Dictionary:
	if data.case_boards.has(id):
		var restored: Dictionary = data.case_boards[id].duplicate(true)
		restored.stage = int(restored.stage)
		for row: Array in restored.placements:
			for i: int in row.size():
				row[i] = int(row[i])
		return restored
	var placements := []
	for stage: Dictionary in task_index[id].puzzle.stages:
		var row := []
		row.resize(stage.slots.size())
		row.fill(-1)
		placements.append(row)
	return {"stage": 0, "placements": placements}

func store_board(id: String, draft: Dictionary) -> bool:
	if not available(id) or not _valid_board(id, draft):
		return false
	data.case_boards[id] = draft.duplicate(true)
	return true

func _valid_board(id: String, draft: Variant) -> bool:
	var stages: Array = task_index[id].get("puzzle", {}).get("stages", [])
	if stages.is_empty() or not draft is Dictionary or draft.size() != 2:
		return false
	var step: Variant = draft.get("stage")
	if typeof(step) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(step) or step != int(step) or step < 0 or step >= stages.size():
		return false
	var placements: Variant = draft.get("placements")
	if not placements is Array or placements.size() != stages.size():
		return false
	for index: int in stages.size():
		var row: Variant = placements[index]
		var count: int = stages[index].slots.size()
		if not row is Array or row.size() != count:
			return false
		var used := {}
		for tile: Variant in row:
			if typeof(tile) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(tile) or tile != int(tile) or tile < -1 or tile >= stages[index].pieces.size():
				return false
			if tile >= 0:
				if used.has(int(tile)) or index > int(step):
					return false
				used[int(tile)] = true
		if index < int(step) and not _settings_match(row, stages[index].answer):
			return false
	return true

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

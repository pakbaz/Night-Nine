extends VBoxContainer
## One case file, with a bank of movable evidence shared by mouse and keyboard.
signal draft_changed(draft: Dictionary)
signal submitted(values: Array)
signal hint_requested
signal wrong_attempt
signal attempt_scored(right: int, total: int)
signal answer_requested
signal closed

const INK := Color("f1ead8")
const MUTED := Color("b7c3b9")
const GOLD := Color("e9c276")
const TEAL := Color("72bdb4")
const RIGHT := Color("8fd19e")
const WRONG := Color("ec8f7c")
const PAPER := Color("d9d2ba")
const PAPER_INK := Color("242b28")
const STEPS := ["Pick a card.", "Pick the place where it belongs.", "Press Check."]
const EMPTY_SLOT := "Drop a card here"
## Checked results stay marked when the board is closed and reopened in one session.
static var remembered := {}
var task_id := ""
var stages: Array
var draft: Dictionary
var selected := -1
var stage_index := 0
## Slot index to true (right, locked) or false (wrong, flagged) after Check.
var marks := {}
var active_step := 0
var pieces: Array[Button] = []
var slots: Array[Button] = []
var notes: Array[Label] = []
var note_numbers: Array[Label] = []
var guide: Array[PanelContainer] = []
var guide_labels: Array[Label] = []
var lane: VBoxContainer
var bank: VBoxContainer
var step_label: Label
var prompt: Label
var response: Label
var confirm: Button
var goal: Label
var knowledge: Label
var background: Label
var hint_button: Button
var answer_button: Button
var lines: BoardLines

class EvidenceButton extends Button:
	var tile := -1
	var position_id := -1
	var board: VBoxContainer
	var caption: Label
	var value: Label
	var mark: Control
	var layout: HBoxContainer
	func build_slot() -> void:
		layout = HBoxContainer.new()
		layout.mouse_filter = Control.MOUSE_FILTER_IGNORE
		layout.add_theme_constant_override("separation", 10)
		add_child(layout)
		layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		layout.offset_left = 16
		layout.offset_right = -12
		layout.offset_top = 8
		layout.offset_bottom = -8
		var text_box := VBoxContainer.new()
		text_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
		text_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		text_box.add_theme_constant_override("separation", 2)
		layout.add_child(text_box)
		caption = Label.new()
		caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		caption.add_theme_font_size_override("font_size", 16)
		text_box.add_child(caption)
		value = Label.new()
		value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		value.add_theme_font_size_override("font_size", 19)
		text_box.add_child(value)
		mark = preload("res://ui/mark_icon.gd").new()
		mark.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		layout.add_child(mark)
		layout.minimum_size_changed.connect(fit)
	func fit() -> void:
		custom_minimum_size.y = maxf(64.0, layout.get_combined_minimum_size().y + 16.0)
	func _get_drag_data(_at: Vector2) -> Variant:
		var value_id: int = tile if position_id == -1 else int(board.draft.placements[board.stage_index][position_id])
		if value_id < 0 or board.is_locked_piece(value_id):
			return null
		var preview := Label.new()
		preview.text = str(board.stages[board.stage_index].pieces[value_id])
		preview.add_theme_font_size_override("font_size", 19)
		preview.modulate = Color("ffe1a4")
		set_drag_preview(preview)
		return {"case": board.get_instance_id(), "piece": value_id}
	func _can_drop_data(_at: Vector2, payload: Variant) -> bool:
		if position_id < 0 or board.marks.get(position_id, false) or not payload is Dictionary or payload.get("case") != board.get_instance_id():
			return false
		var value_id: Variant = payload.get("piece")
		return value_id is int and value_id >= 0 and value_id < board.pieces.size()
	func _drop_data(_at: Vector2, payload: Variant) -> void:
		board.place(int(payload.piece), position_id)

class BoardLines extends Control:
	var mode := ""
	var slots: Array[Button] = []
	var pieces: Array[Button] = []
	var placements: Array = []
	var marks := {}
	const THREADS := [Color("72bdb4"), Color("e9c276"), Color("b4a4d1"), Color("d69474"), Color("92b9dc")]
	func _draw() -> void:
		var previous := Vector2.ZERO
		for i: int in slots.size():
			var b := slots[i]
			if not is_instance_valid(b) or b.size.y < 1:
				continue
			var point := Vector2(b.global_position.x - global_position.x - 12.0, b.global_position.y - global_position.y + b.size.y * .5)
			var color := Color("e9c276") if int(placements[i]) >= 0 else Color("627774")
			if marks.has(i):
				color = Color("8fd19e") if marks[i] else Color("ec8f7c")
			if mode != "match" and i:
				draw_line(previous, Vector2(previous.x, point.y), color, 2.0, true)
				draw_line(Vector2(previous.x, point.y), point, color, 2.0, true)
			if mode == "match":
				var tile := int(placements[i])
				if tile >= 0:
					var origin := pieces[tile].get_global_rect()
					var start := Vector2(origin.end.x, origin.get_center().y) - global_position
					var bend := lerpf(start.x, point.x, .25 + .1 * tile)
					if not marks.has(i):
						color = THREADS[tile % THREADS.size()]
					draw_polyline(PackedVector2Array([start, Vector2(bend, start.y), Vector2(bend, point.y), point]), color, 2.0, true)
					draw_circle(point, 3.0, color, true, -1, true)
				else:
					draw_line(point - Vector2(6, 0), point + Vector2(4, 0), color, 2.0, true)
			else:
				draw_circle(point, 4.0, color, true, -1, true)
			previous = point

func configure(id: String, title: String, puzzle: Dictionary, progress: Dictionary,
		goal_text: String = "", background_text: String = "", perspective: String = "Steve") -> void:
	task_id = id
	stages = puzzle.stages
	draft = progress.duplicate(true)
	stage_index = int(draft.stage)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 10)
	var headline := HBoxContainer.new()
	add_child(headline)
	var heading := label_at(headline, title, 27, INK)
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	step_label = label_at(headline, "", 18, Color("1c1a12"))
	step_label.name = "StepCounter"
	step_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	step_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var pill := box(GOLD, GOLD, 0, 12)
	pill.content_margin_top = 3
	pill.content_margin_bottom = 3
	step_label.add_theme_stylebox_override("normal", pill)
	goal = label_at(self, goal_text, 19, GOLD)
	goal.name = "Goal"
	var context := column(self, 0)
	context.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	context.add_theme_constant_override("separation", 2)
	knowledge = label_at(context, "What %s knows" % perspective, 16, TEAL)
	knowledge.name = "Knowledge"
	background = label_at(context, background_text, 17, Color("cdd5cc"))
	background.name = "Background"
	label_at(self, puzzle.instruction, 17, INK)
	add_guide()
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 18)
	add_child(body)
	add_notes(body, puzzle.evidence)
	bank = column(body, 250)
	var right := column(body, 300)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	prompt = label_at(right, "", 19, TEAL)
	var graph := PanelContainer.new()
	graph.add_theme_stylebox_override("panel", StyleBoxEmpty.new())
	right.add_child(graph)
	lines = BoardLines.new()
	lines.mouse_filter = Control.MOUSE_FILTER_IGNORE
	graph.add_child(lines)
	lane = VBoxContainer.new()
	lane.add_theme_constant_override("separation", 8)
	graph.add_child(lane)
	lane.resized.connect(func(): lines.queue_redraw())
	# Feedback and buttons sit under the places, where the player is looking.
	var feedback := PanelContainer.new()
	feedback.name = "Feedback"
	var feedback_box := box(Color(0.05, 0.12, 0.13, 0.9), Color("4b6663"), 1, 6)
	feedback_box.content_margin_top = 8
	feedback_box.content_margin_bottom = 8
	feedback.add_theme_stylebox_override("panel", feedback_box)
	right.add_child(feedback)
	response = label_at(feedback, "", 18, GOLD)
	var actions := HFlowContainer.new()
	actions.add_theme_constant_override("h_separation", 10)
	actions.add_theme_constant_override("v_separation", 8)
	right.add_child(actions)
	confirm = button_at(actions, "Check", "CheckBoard", func(): check_step())
	var primary := box(GOLD, Color("fff0c8"), 1, 5)
	confirm.add_theme_stylebox_override("normal", primary)
	confirm.add_theme_stylebox_override("hover", box(Color("f4d394"), Color("fff6dc"), 2, 5))
	confirm.add_theme_stylebox_override("pressed", box(Color("c9a55f"), Color("fff0c8"), 1, 5))
	confirm.add_theme_stylebox_override("focus", outline())
	for state: String in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		confirm.add_theme_color_override(state, Color("1c1a12"))
	button_at(actions, "Clear this step", "ClearBoard", func(): clear_step())
	hint_button = button_at(actions, "Hint 1 of 3", "BoardHint", func(): hint_requested.emit())
	answer_button = button_at(actions, "Show answer", "BoardAnswer", func(): answer_requested.emit())
	answer_button.hide()
	button_at(actions, "Back to scene", "CloseBoard", func(): closed.emit())
	build_step()

func add_guide() -> void:
	var strip := HFlowContainer.new()
	strip.name = "Steps"
	strip.add_theme_constant_override("h_separation", 10)
	strip.add_theme_constant_override("v_separation", 6)
	add_child(strip)
	for i: int in STEPS.size():
		var chip := PanelContainer.new()
		strip.add_child(chip)
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		chip.add_child(row)
		var number := label_at(row, str(i + 1), 17, Color("1c1a12"))
		number.autowrap_mode = TextServer.AUTOWRAP_OFF
		number.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		number.custom_minimum_size = Vector2(26, 26)
		number.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		number.add_theme_stylebox_override("normal", box(GOLD, GOLD, 0, 13, 0))
		var text := label_at(row, STEPS[i], 18, INK)
		text.autowrap_mode = TextServer.AUTOWRAP_OFF
		text.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		guide.append(chip)
		guide_labels.append(text)
	var drag := label_at(strip, "You can also drag a card onto a place.", 16, MUTED)
	drag.autowrap_mode = TextServer.AUTOWRAP_OFF
	drag.size_flags_vertical = Control.SIZE_SHRINK_CENTER

func add_notes(parent: Node, evidence: Array) -> void:
	var panel := PanelContainer.new()
	panel.name = "CaseNotes"
	var paper := box(PAPER, Color("9c926e"), 1, 4, 16)
	panel.add_theme_stylebox_override("panel", paper)
	panel.custom_minimum_size.x = 400
	panel.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	parent.add_child(panel)
	var list := column(panel, 0)
	list.add_theme_constant_override("separation", 10)
	label_at(list, "Case notes", 22, Color("403a2d"))
	for i: int in evidence.size():
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		list.add_child(row)
		var number := label_at(row, str(i + 1), 16, PAPER)
		number.autowrap_mode = TextServer.AUTOWRAP_OFF
		number.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		number.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		number.custom_minimum_size = Vector2(26, 26)
		number.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		number.add_theme_stylebox_override("normal", box(Color("4a4233"), Color("4a4233"), 0, 13, 0))
		var note := label_at(row, str(evidence[i]), 18, PAPER_INK)
		note.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		note_numbers.append(number)
		notes.append(note)

func label_at(parent: Node, value: String, font_size: int, color: Color) -> Label:
	var item := Label.new()
	item.text = value
	item.add_theme_font_size_override("font_size", font_size)
	item.add_theme_color_override("font_color", color)
	item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(item)
	return item

func column(parent: Node, width: int) -> VBoxContainer:
	var stack := VBoxContainer.new()
	stack.custom_minimum_size.x = width
	stack.add_theme_constant_override("separation", 8)
	parent.add_child(stack)
	return stack

func box(bg: Color, border: Color, width: int = 1, radius: int = 6, margin: int = -1) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(width)
	style.set_corner_radius_all(radius)
	if margin >= 0:
		style.set_content_margin_all(margin)
	else:
		style.content_margin_left = 14
		style.content_margin_right = 14
		style.content_margin_top = 9
		style.content_margin_bottom = 9
	return style

func outline() -> StyleBoxFlat:
	var style := box(Color(0, 0, 0, 0), Color("fff0c8"), 2, 7)
	style.draw_center = false
	style.expand_margin_left = 3
	style.expand_margin_right = 3
	style.expand_margin_top = 3
	style.expand_margin_bottom = 3
	return style

func button_at(parent: Node, caption: String, id: String, action: Callable) -> Button:
	var button := Button.new()
	button.name = id
	button.text = caption
	button.add_theme_font_size_override("font_size", 18)
	button.pressed.connect(action)
	parent.add_child(button)
	return button

func evidence_button(parent: Node, id: String) -> EvidenceButton:
	var b := EvidenceButton.new()
	b.name = id
	b.board = self
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.custom_minimum_size.y = 44
	b.add_theme_font_size_override("font_size", 18)
	parent.add_child(b)
	return b

func paint(button: Button, bg: Color, border: Color, width: int, text: Color) -> void:
	button.add_theme_stylebox_override("normal", box(bg, border, width))
	button.add_theme_stylebox_override("pressed", box(bg, border, width))
	button.add_theme_stylebox_override("hover", box(bg.lightened(.1), GOLD, 2))
	button.add_theme_stylebox_override("focus", outline())
	for state: String in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "font_hover_pressed_color"]:
		button.add_theme_color_override(state, text)

func empty(holder: Node) -> void:
	for child: Node in holder.get_children():
		holder.remove_child(child)
		child.queue_free()

func build_step() -> void:
	empty(bank)
	empty(lane)
	pieces.clear()
	slots.clear()
	selected = -1
	var stage: Dictionary = stages[stage_index]
	step_label.text = "Step %d of %d" % [stage_index + 1, stages.size()] if stages.size() > 1 else ""
	step_label.visible = stages.size() > 1
	prompt.text = stage.prompt
	label_at(bank, "Cards", 21, TEAL)
	var order: Array = range(stage.pieces.size())
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(task_id + str(stage_index))
	for i: int in range(order.size() - 1, 0, -1):
		var other := rng.randi_range(0, i)
		var temp: int = order[i]
		order[i] = order[other]
		order[other] = temp
	var same: bool = order.size() >= stage.answer.size()
	for i: int in stage.answer.size():
		same = same and int(order[i]) == int(stage.answer[i])
	if same:
		order.append(order.pop_front())
	pieces.resize(order.size())
	for index: int in order:
		var tile := evidence_button(bank, "Piece%d" % index)
		tile.tile = index
		tile.text = stage.pieces[index]
		tile.pressed.connect(pick.bind(index))
		pieces[index] = tile
	for i: int in stage.slots.size():
		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left", 34 + (i % 2) * 34 if stage.mode == "route" else 20)
		lane.add_child(margin)
		var node := evidence_button(margin, "Slot%d" % i)
		node.position_id = i
		node.build_slot()
		node.pressed.connect(press_slot.bind(i))
		node.item_rect_changed.connect(lines.queue_redraw)
		slots.append(node)
	restore_marks()
	lines.mode = stage.mode
	lines.slots = slots
	lines.pieces = pieces
	lines.placements = draft.placements[stage_index]
	lines.queue_redraw.call_deferred()
	confirm.text = "Check"
	response.text = "Pick a card, then pick the place where it belongs. Press Check when every place has a card."
	if not marks.is_empty():
		response.text = "Cards with a check mark are right. Move the cards marked with a cross."
	refresh_tiles()
	if not pieces.is_empty():
		pieces[order[0]].grab_focus.call_deferred()

func restore_marks() -> void:
	marks = {}
	var memory: Dictionary = remembered.get(task_id, {})
	if int(memory.get("stage", -1)) != stage_index:
		return
	var row: Array = draft.placements[stage_index]
	var answer: Array = stages[stage_index].answer
	for slot: int in memory.marks:
		var entry: Array = memory.marks[slot]
		if slot >= row.size() or int(row[slot]) != int(entry[0]):
			continue
		if bool(entry[1]) == (int(row[slot]) == int(answer[slot])):
			marks[slot] = bool(entry[1])

func remember() -> void:
	var saved := {}
	var row: Array = draft.placements[stage_index]
	for slot: int in marks:
		saved[slot] = [int(row[slot]), marks[slot]]
	remembered[task_id] = {"stage": stage_index, "marks": saved}

func is_locked_piece(tile: int) -> bool:
	var slot: int = draft.placements[stage_index].find(tile)
	return slot >= 0 and marks.get(slot, false)

func piece_state(index: int) -> String:
	if selected == index:
		return "selected"
	var slot: int = draft.placements[stage_index].find(index)
	if slot < 0:
		return "free"
	return "locked" if marks.get(slot, false) else "placed"

func slot_state(index: int) -> String:
	if marks.has(index):
		return "right" if marks[index] else "wrong"
	if int(draft.placements[stage_index][index]) >= 0:
		return "filled"
	return "invite" if selected >= 0 else "empty"

func refresh_tiles() -> void:
	var stage: Dictionary = stages[stage_index]
	var row: Array = draft.placements[stage_index]
	for i: int in pieces.size():
		var state := piece_state(i)
		var used := row.find(i)
		match state:
			"selected":
				paint(pieces[i], GOLD, Color("fff0c8"), 2, Color("1c1a12"))
			"locked":
				paint(pieces[i], Color("17301f"), Color("4f7f59"), 1, RIGHT)
			"placed":
				paint(pieces[i], Color("10232a"), Color("33494b"), 1, Color("8d9a94"))
			_:
				paint(pieces[i], Color("1d3a42"), Color("6a8f8a"), 1, INK)
		pieces[i].tooltip_text = str(stage.pieces[i]) if used < 0 else "In “%s”" % stage.slots[used]
	for i: int in slots.size():
		var tile := int(row[i])
		var slot: EvidenceButton = slots[i]
		var state := slot_state(i)
		slot.caption.text = ("%d. " % (i + 1) if stage.mode == "order" else "") + str(stage.slots[i])
		slot.value.text = str(stage.pieces[tile]) if tile >= 0 else EMPTY_SLOT
		slot.mark.show_kind(state if state in ["right", "wrong"] else "")
		var caption_color := TEAL
		var value_color := INK
		match state:
			"right":
				paint(slot, Color("18352a"), RIGHT, 2, INK)
				caption_color = RIGHT
			"wrong":
				paint(slot, Color("3a2020"), WRONG, 2, INK)
				caption_color = WRONG
			"filled":
				paint(slot, Color("1d3a42"), TEAL, 2, INK)
			"invite":
				paint(slot, Color("1f3433"), GOLD, 2, INK)
				value_color = GOLD
			_:
				paint(slot, Color("0d1f24"), Color("6f8a86"), 2, INK)
				value_color = Color("8fa19c")
		slot.caption.add_theme_color_override("font_color", caption_color)
		slot.value.add_theme_color_override("font_color", value_color)
		slot.tooltip_text = slot.caption.text + ": " + slot.value.text
	lines.marks = marks
	var full := row.find(-1) < 0
	active_step = 1 if selected >= 0 else (2 if full else 0)
	for i: int in guide.size():
		var on := i == active_step
		guide[i].add_theme_stylebox_override("panel", box(Color("2c4440") if on else Color("10242a"), GOLD if on else Color("3d5658"), 2 if on else 1, 18, 6))
		guide_labels[i].add_theme_color_override("font_color", INK if on else MUTED)
	lines.queue_redraw()

func pick(index: int) -> void:
	var stage: Dictionary = stages[stage_index]
	if is_locked_piece(index):
		response.text = "“%s” is in the right place. It stays there." % stage.pieces[index]
		return
	if selected == index:
		selected = -1
		response.text = "You put the card down. Pick a card."
	else:
		selected = index
		response.text = "You picked “%s”. Now pick the place where it belongs." % stage.pieces[index]
	refresh_tiles()

func press_slot(index: int) -> void:
	var stage: Dictionary = stages[stage_index]
	if marks.get(index, false):
		response.text = "“%s” is right. That card stays there." % stage.slots[index]
	elif selected >= 0:
		place(selected, index)
	elif int(draft.placements[stage_index][index]) >= 0:
		pick(int(draft.placements[stage_index][index]))
	else:
		response.text = "Pick a card first."

func place(tile: int, target: int) -> void:
	var stage: Dictionary = stages[stage_index]
	var row: Array = draft.placements[stage_index]
	if marks.get(target, false):
		response.text = "“%s” is right. That card stays there." % stage.slots[target]
		return
	if is_locked_piece(tile):
		response.text = "“%s” is in the right place. It stays there." % stage.pieces[tile]
		return
	var previous := row.find(tile)
	if previous >= 0:
		row[previous] = row[target]
		marks.erase(previous)
	row[target] = tile
	marks.erase(target)
	selected = -1
	response.text = "“%s” is in “%s”." % [stage.pieces[tile], stage.slots[target]]
	if row.find(-1) < 0:
		response.text += " Press Check when you are ready."
	remember()
	draft_changed.emit(draft)
	refresh_tiles()

func clear_step() -> void:
	var row: Array = draft.placements[stage_index]
	for i: int in row.size():
		if not marks.get(i, false):
			row[i] = -1
			marks.erase(i)
	selected = -1
	response.text = "The right cards stay. The other places are empty again." if not marks.is_empty() else "All places are empty again."
	remember()
	draft_changed.emit(draft)
	refresh_tiles()

func check_step() -> void:
	var stage: Dictionary = stages[stage_index]
	var row: Array = draft.placements[stage_index]
	for i: int in row.size():
		if int(row[i]) < 0:
			response.text = "Put a card in “%s” first." % stage.slots[i]
			return
	marks = {}
	var right := 0
	for i: int in row.size():
		marks[i] = int(row[i]) == int(stage.answer[i])
		if marks[i]:
			right += 1
	var completed_rows := 0
	var total_rows := 0
	for index: int in stages.size():
		total_rows += stages[index].answer.size()
		if index < stage_index:
			completed_rows += stages[index].answer.size()
	selected = -1
	if right != row.size():
		attempt_scored.emit(completed_rows + right, total_rows)
		remember()
		refresh_tiles()
		if right == 0:
			response.text = "0 of %d are right. Move the cards marked with a cross." % row.size()
		else:
			response.text = "%d of %d are right. They are locked. Move the cards marked with a cross." % [right, row.size()]
		wrong_attempt.emit()
		return
	remembered.erase(task_id)
	attempt_scored.emit(completed_rows + right, total_rows)
	if stage_index + 1 < stages.size():
		stage_index += 1
		draft.stage = stage_index
		draft_changed.emit(draft)
		build_step()
		response.text = "Step %d is right. Now do step %d." % [stage_index, stage_index + 1]
	else:
		refresh_tiles()
		var values: Array = []
		for entries: Array in draft.placements:
			values.append_array(entries)
		submitted.emit(values)

func set_hint_label(value: String) -> void:
	hint_button.text = value

func show_answer_offer(on: bool) -> void:
	answer_button.visible = on

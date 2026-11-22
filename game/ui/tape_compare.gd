class_name NightTapeCompare
extends PanelContainer
signal play_requested(stream: AudioStreamWAV)
signal stop_requested
signal finding_requested(settings: Array)
signal hint_requested
signal wrong_attempt
signal answer_requested
signal closed
var recording := NightTapeRecording.new()
var trace: NightTapeTrace
var slider: HSlider
var offset_label: Label
var offset_mark: Label
var rows_box: VBoxContainer
var row_choices: Array[OptionButton] = []
var row_marks: Array[Label] = []
var solution: Array = []
var feedback: Label
var goal: Label
var background: Label
var hint_button: Button
var answer_button: Button
var voice: AudioStreamPlayer
var active_stream: AudioStreamWAV
var task_id := ""
var paused := false
var buttons: Array[BaseButton] = []

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	offset_left = 28
	offset_right = -28
	offset_top = 58
	offset_bottom = -28
	var style := StyleBoxFlat.new()
	style.bg_color = Color("11272e")
	style.border_color = Color("b7976e")
	style.set_border_width_all(1)
	style.set_corner_radius_all(9)
	style.set_content_margin_all(24)
	add_theme_stylebox_override("panel", style)
	var scroll:=ScrollContainer.new()
	scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	add_child(scroll)
	var box := VBoxContainer.new()
	box.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 10)
	scroll.add_child(box)
	_label(box, "FRANK’S RECORDER  /  TWO MORNINGS", 26)
	goal=_label(box,"",18)
	goal.modulate=Color("e9c276")
	_label(box,"What Steve knows",16).name="KnowledgeHeading"
	background=_label(box,"",16)
	_label(box, "Move Sunday until the idents line up. Compare every voice, then record your finding.", 18)
	trace = NightTapeTrace.new()
	box.add_child(trace)
	trace.offset_changed.connect(_set_offset)
	var timing := HBoxContainer.new()
	timing.add_theme_constant_override("separation", 12)
	box.add_child(timing)
	_button(timing, "Earlier", func(): _set_offset(slider.value - 0.01))
	slider = HSlider.new()
	slider.min_value = -0.75
	slider.max_value = 0.75
	slider.step = 0.01
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.custom_minimum_size.y = 40
	slider.tooltip_text = "Move Sunday in 0.01-second steps. Arrow keys also work."
	timing.add_child(slider)
	slider.value_changed.connect(_set_offset)
	_button(timing, "Later", func(): _set_offset(slider.value + 0.01))
	offset_label = _label(timing, "Sunday: +0.000 s", 19)
	offset_label.custom_minimum_size.x = 185
	offset_mark = _label(timing, "", 23)
	offset_mark.custom_minimum_size.x = 24
	# The transport shares the slider's row so the whole comparison fits on one screen.
	var transport := timing
	_button(transport, "Play Saturday", func(): _play("a"))
	_button(transport, "Play Sunday", func(): _play("b"))
	_button(transport, "Play together", func(): _play("both"))
	_button(transport, "Stop", _stop)
	var overlay := CheckButton.new()
	overlay.text = "Overlay traces"
	overlay.toggled.connect(func(on: bool): trace.overlay = on; trace.queue_redraw())
	transport.add_child(overlay)
	buttons.append(overlay)
	_label(box, "What matches?", 17).modulate = Color("e9c276")
	rows_box = VBoxContainer.new()
	rows_box.add_theme_constant_override("separation", 7)
	box.add_child(rows_box)
	feedback = _label(box, "You can compare the waveforms with or without sound.", 18)
	feedback.custom_minimum_size.y = 26
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 12)
	box.add_child(footer)
	var record := _button(footer, "Record finding", _submit)
	# The main action matches the gold Check button on case boards.
	for state: String in ["normal", "hover", "pressed"]:
		var gold := StyleBoxFlat.new()
		gold.bg_color = {"normal": Color("e9c276"), "hover": Color("f4d394"), "pressed": Color("c9a55f")}[state]
		gold.border_color = Color("fff0c8")
		gold.set_border_width_all(2 if state == "hover" else 1)
		gold.set_corner_radius_all(5)
		gold.content_margin_left = 14
		gold.content_margin_right = 14
		gold.content_margin_top = 8
		gold.content_margin_bottom = 8
		record.add_theme_stylebox_override(state, gold)
	for state: String in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		record.add_theme_color_override(state, Color("1c1a12"))
	hint_button=_button(footer, "Hint 1 of 3", func(): hint_requested.emit())
	answer_button=_button(footer, "Show answer", func(): answer_requested.emit())
	answer_button.hide()
	_button(footer, "Reset offset", func(): _set_offset(0))
	_button(footer, "Back to the room", close)
	hide()

func _label(parent: Node, text: String, font_size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(label)
	return label

func _button(parent: Node, text: String, action: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.pressed.connect(action)
	parent.add_child(button)
	buttons.append(button)
	return button

func open_task(id: String, saturday: AudioStreamWAV, sunday: AudioStreamWAV, metadata: Dictionary,
		player: AudioStreamPlayer, data: Dictionary,
		goal_text: String = "", background_text: String = "", perspective: String = "Steve") -> bool:
	if not recording.configure(saturday, sunday, metadata):
		return false
	voice = player
	goal.text=goal_text
	background.text=background_text
	var heading:=find_child("KnowledgeHeading",true,false) as Label
	heading.text="What %s knows" % perspective
	trace.recording = recording
	var previous: Array[int] = []
	if task_id == id:
		for choice: OptionButton in row_choices:
			previous.append(choice.selected)
	_configure_rows(data.get("rows", []), data.get("solution", []), previous)
	if task_id != id:
		task_id = id
		_set_offset(0)
	feedback.text = "You can compare the waveforms with or without sound."
	offset_mark.text = ""
	show()
	set_paused(false)
	trace.queue_redraw()
	slider.grab_focus()
	return true

func _set_offset(value: float) -> void:
	if paused:
		return
	var selected := clampf(snappedf(value, 0.01), -0.75, 0.75)
	if is_instance_valid(active_stream):
		_stop()
	slider.set_value_no_signal(selected)
	trace.offset = selected
	offset_label.text = "Sunday: %+.3f s" % selected
	trace.queue_redraw()

func _play(mode: String) -> void:
	if paused:
		return
	active_stream = recording.playback(mode, slider.value)
	if active_stream != null:
		play_requested.emit(active_stream)

func _stop() -> void:
	stop_requested.emit()
	active_stream = null
	trace.playhead = -100
	trace.queue_redraw()

func _configure_rows(rows: Array, answers: Array, previous: Array[int]) -> void:
	for choice: OptionButton in row_choices:
		buttons.erase(choice)
	for child: Node in rows_box.get_children():
		rows_box.remove_child(child)
		child.queue_free()
	row_choices.clear()
	row_marks.clear()
	solution = answers.duplicate()
	var row: HBoxContainer
	for index: int in rows.size():
		var data := rows[index] as Dictionary
		if index % 2 == 0:
			row = HBoxContainer.new()
			row.add_theme_constant_override("separation", 10)
			rows_box.add_child(row)
		var label := _label(row, str(data.get("label", "")), 16)
		label.custom_minimum_size.x = 190
		var choice := OptionButton.new()
		choice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		choice.add_item("Choose one")
		for text: String in data.get("options", []):
			choice.add_item(text)
		choice.tooltip_text = "Choose how the Saturday and Sunday recordings compare."
		row.add_child(choice)
		var mark := _label(row, "", 23)
		mark.custom_minimum_size.x = 24
		row_choices.append(choice)
		row_marks.append(mark)
		buttons.append(choice)
		if index < previous.size():
			choice.select(clampi(previous[index], 0, choice.item_count - 1))

func _submit() -> void:
	if paused:
		return
	var values: Array = []
	var right := 0
	for index: int in row_choices.size():
		var value := row_choices[index].selected - 1
		values.append(value)
		var correct := index < solution.size() and value == int(solution[index])
		row_marks[index].text = "✓" if correct else "✗"
		row_marks[index].modulate = Color("8ce6ad") if correct else Color("ff9b8f")
		if correct:
			right += 1
	var offset_correct := recording.aligned(slider.value)
	offset_mark.text = "✓" if offset_correct else "✗"
	offset_mark.modulate = Color("8ce6ad") if offset_correct else Color("ff9b8f")
	if offset_correct:
		right += 1
	var total := row_choices.size() + 1
	if right == total:
		feedback.text = "%d of %d right." % [right, total]
		finding_requested.emit(values)
		return
	feedback.text = "%d of %d right. Review the marked rows and offset." % [right, total]
	wrong_attempt.emit()

func set_paused(on: bool) -> void:
	paused = on
	trace.interaction_paused = on
	trace.dragging = false
	for button: BaseButton in buttons:
		button.disabled = on
	slider.editable = not on

func close() -> void:
	_stop()
	hide()
	closed.emit()

func reset_task() -> void:
	close()
	task_id = ""

func set_hint_label(value: String) -> void:
	hint_button.text=value

func show_answer_offer(on: bool) -> void:
	answer_button.visible=on

func _process(_delta: float) -> void:
	if not visible:
		return
	if is_instance_valid(voice) and voice.playing and voice.stream == active_stream:
		trace.playhead = recording.timeline_start + maxf(0, NightAudioClock.audible_position(voice))
	else:
		trace.playhead = -100
	trace.queue_redraw()

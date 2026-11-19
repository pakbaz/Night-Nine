class_name NightTapeCompare
extends PanelContainer
signal play_requested(stream: AudioStreamWAV)
signal stop_requested
signal finding_requested(settings: Array)
signal hint_requested
signal closed
var recording := NightTapeRecording.new()
var trace: NightTapeTrace
var slider: HSlider
var offset_label: Label
var conclusion: OptionButton
var feedback: Label
var voice: AudioStreamPlayer
var active_stream: AudioStreamWAV
var task_id := ""
var paused := false
var buttons: Array[BaseButton] = []

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	offset_left = 100
	offset_right = -100
	offset_top = 140
	offset_bottom = -65
	var style := StyleBoxFlat.new()
	style.bg_color = Color("11272e")
	style.border_color = Color("b7976e")
	style.set_border_width_all(1)
	style.set_corner_radius_all(9)
	style.set_content_margin_all(24)
	add_theme_stylebox_override("panel", style)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	add_child(box)
	_label(box, "FRANK’S RECORDER  /  TWO MORNINGS", 26)
	_label(box, "Move Sunday until the breath and first word line up. Compare the rest of the performance, then record your finding.", 18)
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
	offset_label.custom_minimum_size.x = 210
	var transport := HBoxContainer.new()
	transport.add_theme_constant_override("separation", 12)
	box.add_child(transport)
	_button(transport, "Play Saturday", func(): _play("a"))
	_button(transport, "Play Sunday", func(): _play("b"))
	_button(transport, "Play together", func(): _play("both"))
	_button(transport, "Stop", _stop)
	var overlay := CheckButton.new()
	overlay.text = "Overlay traces"
	overlay.toggled.connect(func(on: bool): trace.overlay = on; trace.queue_redraw())
	transport.add_child(overlay)
	buttons.append(overlay)
	var decision := HBoxContainer.new()
	decision.add_theme_constant_override("separation", 12)
	box.add_child(decision)
	conclusion = OptionButton.new()
	conclusion.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	conclusion.add_item("What did you learn?")
	for text: String in ["Same words only", "Different performances", "Identical performance"]:
		conclusion.add_item(text)
	conclusion.tooltip_text = "Choose a conclusion. Left and Right cycle without opening the menu."
	conclusion.gui_input.connect(_conclusion_key)
	decision.add_child(conclusion)
	_button(decision, "Record finding", _submit)
	feedback = _label(box, "You can compare the waveforms with or without sound.", 18)
	feedback.custom_minimum_size.y = 52
	feedback.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 12)
	box.add_child(footer)
	_button(footer, "Hint", func(): hint_requested.emit())
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

func _button(parent: Node, text: String, action: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.pressed.connect(action)
	parent.add_child(button)
	buttons.append(button)

func open_task(id: String, master: AudioStreamWAV, player: AudioStreamPlayer, data: Dictionary) -> bool:
	if not recording.configure(master, data.lead_a, data.lead_b):
		return false
	voice = player
	trace.recording = recording
	if task_id != id:
		task_id = id
		_set_offset(0)
		conclusion.select(0)
	feedback.text = "You can compare the waveforms with or without sound."
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

func _conclusion_key(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_LEFT,KEY_RIGHT]:
		var step := 1 if event.keycode==KEY_RIGHT else -1
		conclusion.select(posmod(conclusion.selected+step,conclusion.item_count))
		conclusion.accept_event()

func _submit() -> void:
	if paused:
		return
	if conclusion.selected == 0:
		feedback.text = "Choose a finding after comparing both takes."
		return
	if not recording.aligned(slider.value):
		feedback.text = "Adjust Sunday until the breath and first word are at the same time. Then compare the pauses."
		return
	if conclusion.selected != 3:
		feedback.text = "Look past the words. Compare the small peaks and gaps along both recordings."
		return
	finding_requested.emit([1, 2])

func set_paused(on: bool) -> void:
	paused = on
	trace.interaction_paused = on
	trace.dragging = false
	for button: BaseButton in buttons:
		button.disabled = on
	slider.editable = not on
	conclusion.disabled = on

func close() -> void:
	_stop()
	hide()
	closed.emit()

func reset_task() -> void:
	close()
	task_id = ""

func _process(_delta: float) -> void:
	if not visible:
		return
	if is_instance_valid(voice) and voice.playing and voice.stream == active_stream:
		var correction := 0.0
		if not voice.stream_paused and not OS.has_feature("movie"):
			correction = AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
		trace.playhead = recording.timeline_start + maxf(0, voice.get_playback_position() + correction)
	else:
		trace.playhead = -100
	trace.queue_redraw()

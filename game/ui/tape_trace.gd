class_name NightTapeTrace
extends Control
signal offset_changed(value: float)
var recording: NightTapeRecording
var offset := 0.0
var overlay := false
var playhead := -100.0
var dragging := false
var drag_start := 0.0
var drag_offset := 0.0
var interaction_paused := false
const LEFT := 40.0
const RIGHT := 22.0

func _ready() -> void:
	custom_minimum_size.y = 290
	focus_mode = Control.FOCUS_ALL
	mouse_default_cursor_shape = Control.CURSOR_DRAG
	clip_contents = true

func time_x(seconds: float) -> float:
	return LEFT + (seconds - recording.timeline_start) / (recording.timeline_end - recording.timeline_start) * (size.x - LEFT - RIGHT)

func _draw() -> void:
	draw_style_box(_background(), Rect2(Vector2.ZERO, size))
	if recording == null or recording.peaks.is_empty():
		return
	var font := ThemeDB.fallback_font
	var amber := Color("f2bd77")
	var teal := Color("79d9d0")
	for tick: int in range(int(recording.timeline_start * 4), int(recording.timeline_end * 4) + 1):
		var t := tick / 4.0
		var x := time_x(t)
		draw_line(Vector2(x, 34), Vector2(x, 258), Color(0.3, 0.48, 0.51, 0.3), 1)
		if tick % 2 == 0:
			draw_string(font, Vector2(x - 14, 281), "%.1f s" % t, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("b2c4c1"))
	for row: int in 2:
		var color := amber if row == 0 else teal
		if overlay and row == 1:
			color.a = 0.65
		var middle := 150.0 if overlay else 94.0 + row * 116.0
		draw_line(Vector2(LEFT, middle), Vector2(size.x - RIGHT, middle), Color(0.5, 0.6, 0.6, 0.3), 1)
		var lead := recording.lead_a if row == 0 else recording.lead_b + offset
		for index: int in recording.peaks.size():
			var x := time_x(lead + float(index * NightTapeRecording.BIN_FRAMES) / recording.rate)
			if x < LEFT or x > size.x - RIGHT:
				continue
			var peak := recording.peaks[index]
			draw_line(Vector2(x, middle - peak.y * 98), Vector2(x, middle - peak.x * 98), color, 1.3)
	draw_string(font, Vector2(LEFT, 27), "A  /  SATURDAY", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, amber)
	draw_string(font, Vector2(260 if overlay else LEFT, 27 if overlay else 153),
		"B  /  SUNDAY - drag to move", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, teal)
	if playhead >= recording.timeline_start and playhead <= recording.timeline_end:
		var x := time_x(playhead)
		draw_line(Vector2(x, 34), Vector2(x, 258), Color("fff7dd"), 2)
	if has_focus():
		draw_rect(Rect2(Vector2(2, 2), size - Vector2(4, 4)), Color("f2bd77"), false, 2)

func _background() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color("0c1c23")
	style.border_color = Color("48686c")
	style.set_border_width_all(1)
	style.set_corner_radius_all(5)
	return style

func _gui_input(event: InputEvent) -> void:
	if interaction_paused or recording == null:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed and (overlay or event.position.y >= 140):
			dragging = true
			drag_start = event.position.x
			drag_offset = offset
			grab_focus()
			accept_event()
		elif not event.pressed:
			dragging = false
			accept_event()
	elif event is InputEventMouseMotion and dragging:
		var seconds: float = (event.position.x - drag_start) / (size.x - LEFT - RIGHT) * (recording.timeline_end - recording.timeline_start)
		offset_changed.emit(clampf(snappedf(drag_offset + seconds, 0.01), -0.75, 0.75))
		accept_event()
	elif event is InputEventKey and event.pressed:
		if event.keycode in [KEY_LEFT, KEY_RIGHT]:
			var amount := 0.05 if event.shift_pressed else 0.01
			offset_changed.emit(clampf(offset + amount * (-1 if event.keycode == KEY_LEFT else 1), -0.75, 0.75))
			accept_event()

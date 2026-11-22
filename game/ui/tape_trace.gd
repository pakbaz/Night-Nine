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
	custom_minimum_size.y = 300
	focus_mode = Control.FOCUS_ALL
	mouse_default_cursor_shape = Control.CURSOR_DRAG
	clip_contents = true

func time_x(seconds: float) -> float:
	return LEFT + (seconds - recording.timeline_start) / (recording.timeline_end - recording.timeline_start) * (size.x - LEFT - RIGHT)

func _draw() -> void:
	draw_style_box(_background(), Rect2(Vector2.ZERO, size))
	if recording == null or recording.peaks_a.is_empty() or recording.peaks_b.is_empty():
		return
	var font := ThemeDB.fallback_font
	var amber := Color("f2bd77")
	var teal := Color("79d9d0")
	for tick: int in range(int(recording.timeline_start * 4), int(recording.timeline_end * 4) + 1):
		var t := tick / 4.0
		var x := time_x(t)
		draw_line(Vector2(x, 30), Vector2(x, 270), Color(0.3, 0.48, 0.51, 0.3), 1)
		if tick % 4 == 0:
			draw_string(font, Vector2(x - 14, 293), "%.0f s" % t, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("b2c4c1"))
	for row: int in 2:
		var color := amber if row == 0 else teal
		if overlay and row == 1:
			color.a = 0.65
		var middle := 120.0 if overlay else 66.0 + row * 132.0
		draw_line(Vector2(LEFT, middle), Vector2(size.x - RIGHT, middle), Color(0.5, 0.6, 0.6, 0.3), 1)
		var row_offset := 0.0 if row == 0 else recording.effective_offset(offset)
		var peaks := recording.peaks_a if row == 0 else recording.peaks_b
		for index: int in peaks.size():
			var x := time_x(row_offset + float(index * NightTapeRecording.BIN_FRAMES) / recording.rate)
			if x < LEFT or x > size.x - RIGHT:
				continue
			var peak: Vector2 = peaks[index]
			draw_line(Vector2(x, middle - peak.y * 72), Vector2(x, middle - peak.x * 72), color, 1.2)
		var caption_y := 217.0 + row * 26.0 if overlay else 125.0 + row * 132.0
		var segments := recording.segments_a if row == 0 else recording.segments_b
		for item: Dictionary in segments:
			var start_x := time_x(float(item.start) + row_offset)
			var end_x := time_x(float(item.end) + row_offset)
			var clipped_start := maxf(LEFT, start_x)
			var clipped_end := minf(size.x - RIGHT, end_x)
			if clipped_end <= clipped_start:
				continue
			draw_line(Vector2(clipped_start, caption_y - 11), Vector2(clipped_end, caption_y - 11), color, 2)
			draw_string(font, Vector2(clipped_start + 3, caption_y + 5), str(item.label),
				HORIZONTAL_ALIGNMENT_LEFT, maxf(0, clipped_end - clipped_start - 4), 13, color)
	draw_string(font, Vector2(LEFT, 24), "A  /  SATURDAY", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, amber)
	draw_string(font, Vector2(260 if overlay else LEFT, 47 if overlay else 155),
		"B  /  SUNDAY - drag to move", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, teal)
	if playhead >= recording.timeline_start and playhead <= recording.timeline_end:
		var x := time_x(playhead)
		draw_line(Vector2(x, 30), Vector2(x, 270), Color("fff7dd"), 2)
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

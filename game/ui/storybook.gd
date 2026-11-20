extends Control
## Illustrated story panels between scenes. The score's playback position is the
## clock, so every panel and caption lands on the bar its book names.
signal finished
signal line_shown(line: Dictionary)
## The player turned the page or skipped, so any narration in progress should stop.
signal page_turned
## Start this caption's narration now. Sent one at a time, never over a clip that is still playing.
signal narrate(line: Dictionary)

const CROSSFADE := 1.25
const CAPTION_IN := .7
const CLOSE := 1.4
## A short breath between two narrated captions.
const NARRATION_GAP := .1
## Book-clock time when the narration in progress ends. Voice and music pause together, so this survives pauses.
var narration_until := -INF
## The newest caption still waiting for the narrator.
var waiting_line: Dictionary = {}
## What happened to each caption's narration in this book, for QA.
var narration_log: Array[Dictionary] = []
var book: Dictionary = {}
var score: Node
var track: Dictionary = {}
var panels: Array = []
var index := -1
var fallback_clock := 0.0
var start_time := 0.0
var end_time := 0.0
var closing := -1.0
var paused := false
var music_driven := false
var layers: Array[TextureRect] = []
var layer_alpha: Array[float] = [0.0, 0.0]
var layer_panel: Array[int] = [-1, -1]
var front := 0
var caption_box: VBoxContainer
var captions: Array[Label] = []
var caption_times: Array[float] = []
var veil: ColorRect
var skip_button: Button
var guide: Label
var heading: Label

func _init() -> void:
	name = "Storybook"
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var black := ColorRect.new()
	black.color = Color(0.0, 0.0, 0.0)
	black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(black)
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var stage := Control.new()
	stage.name = "Panels"
	stage.clip_contents = true
	stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(stage)
	stage.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for i: int in 2:
		var picture := TextureRect.new()
		picture.name = "Panel%d" % i
		picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		picture.stretch_mode = TextureRect.STRETCH_SCALE
		picture.mouse_filter = Control.MOUSE_FILTER_IGNORE
		picture.modulate.a = 0.0
		stage.add_child(picture)
		layers.append(picture)
	var shade := TextureRect.new()
	shade.name = "CaptionShade"
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var gradient := Gradient.new()
	gradient.set_color(0, Color(0, 0, 0, 0))
	gradient.set_color(1, Color(0, 0, 0, .82))
	var fill := GradientTexture2D.new()
	fill.gradient = gradient
	fill.fill_from = Vector2(0, 0)
	fill.fill_to = Vector2(0, 1)
	shade.texture = fill
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	add_child(shade)
	shade.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	shade.offset_top = -380
	caption_box = VBoxContainer.new()
	caption_box.name = "Captions"
	caption_box.alignment = BoxContainer.ALIGNMENT_END
	caption_box.add_theme_constant_override("separation", 14)
	caption_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(caption_box)
	caption_box.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	caption_box.offset_left = -610
	caption_box.offset_right = 610
	caption_box.offset_top = -300
	caption_box.offset_bottom = -92
	heading = Label.new()
	heading.name = "BookTitle"
	heading.add_theme_font_size_override("font_size", 17)
	heading.add_theme_color_override("font_color", Color("e7b781"))
	heading.uppercase = true
	heading.add_theme_color_override("font_shadow_color", Color(0, 0, 0, .85))
	heading.add_theme_constant_override("shadow_outline_size", 7)
	heading.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(heading)
	heading.position = Vector2(46, 34)
	guide = Label.new()
	guide.name = "Guide"
	guide.text = "Space or click: next picture"
	guide.add_theme_font_size_override("font_size", 15)
	guide.modulate = Color(1, 1, 1, .6)
	guide.add_theme_color_override("font_shadow_color", Color(0, 0, 0, .85))
	guide.add_theme_constant_override("shadow_outline_size", 5)
	guide.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(guide)
	guide.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	guide.offset_left = 46
	guide.offset_top = -52
	guide.offset_bottom = -26
	skip_button = Button.new()
	skip_button.name = "SkipStory"
	skip_button.text = "Skip story"
	# Never take keyboard focus, so Space always turns the page instead.
	skip_button.focus_mode = Control.FOCUS_NONE
	skip_button.pressed.connect(skip)
	add_child(skip_button)
	skip_button.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	skip_button.offset_left = -200
	skip_button.offset_right = -44
	skip_button.offset_top = -78
	skip_button.offset_bottom = -32
	veil = ColorRect.new()
	veil.name = "Veil"
	veil.color = Color(0, 0, 0, 1)
	veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(veil)
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hide()

func play(story: Dictionary, music: Node) -> void:
	book = story
	score = music
	panels = book.get("panels", [])
	index = -1
	closing = -1.0
	paused = false
	front = 0
	layer_panel = [-1, -1]
	layer_alpha = [0.0, 0.0]
	for picture: TextureRect in layers:
		picture.modulate.a = 0.0
		picture.texture = null
	_clear_captions()
	narration_until = -INF
	waiting_line = {}
	narration_log.clear()
	heading.text = str(book.get("title", ""))
	var cue: Dictionary = book.get("music", {})
	music_driven = score != null and score.play_story(str(cue.get("file", "")), float(cue.get("bar", 0)), bool(cue.get("continue", false)))
	track = score.track_for_file(str(cue.get("file", ""))) if score != null else {}
	start_time = _time_of(float(cue.get("bar", 0)))
	end_time = _time_of(float(book.get("end_bar", 0)))
	fallback_clock = start_time
	veil.color.a = 1.0
	show()

func _time_of(bar: float) -> float:
	if track.is_empty():
		return bar * 3.2
	return score.bar_time(track, bar)

func now() -> float:
	if music_driven and score.current_file == str(book.get("music", {}).get("file", "")):
		var at: float = score.position()
		if at >= 0.0:
			return at
	return fallback_clock

func next() -> void:
	# A click beside the pause menu must not turn the page underneath it.
	if not visible or closing >= 0.0 or paused:
		return
	if index + 1 >= panels.size():
		skip()
		return
	var target := _time_of(float(panels[index + 1].bar))
	_turn_page()
	fallback_clock = target
	if music_driven:
		score.seek(target)

func skip() -> void:
	if visible and closing < 0.0 and not paused:
		_turn_page()
		closing = 0.0

func _turn_page() -> void:
	_drop_waiting("page_turned")
	narration_until = -INF
	page_turned.emit()

## Close without continuing the story, when a save is loaded over it.
func cancel() -> void:
	for connection: Dictionary in finished.get_connections():
		finished.disconnect(connection.callable)
	hide()

func finish_now() -> void:
	if visible:
		hide()
		finished.emit()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		next()
		accept_event()

func _process(delta: float) -> void:
	if not visible or paused:
		return
	fallback_clock += delta
	if closing >= 0.0:
		closing += delta
		veil.color.a = clampf(closing / CLOSE, 0.0, 1.0)
		if closing >= CLOSE:
			hide()
			finished.emit()
		return
	var t := now()
	if t >= end_time:
		_drop_waiting("book_closed")
		closing = 0.0
		return
	veil.color.a = maxf(0.0, veil.color.a - delta / .9)
	var current := -1
	for i: int in panels.size():
		if t >= _time_of(float(panels[i].bar)) - .05:
			current = i
	if current < 0:
		current = 0
	if current != index:
		_enter(current)
	for slot: int in 2:
		# The outgoing picture stays whole underneath until the new one is opaque.
		if slot == front:
			layer_alpha[slot] = move_toward(layer_alpha[slot], 1.0, delta / CROSSFADE)
		elif layer_alpha[front] >= 1.0:
			layer_alpha[slot] = 0.0
		layers[slot].modulate.a = layer_alpha[slot]
		if layer_panel[slot] >= 0:
			_frame(slot, t)
	_update_captions(t, delta)

func _enter(panel_index: int) -> void:
	index = panel_index
	var panel: Dictionary = panels[index]
	front = 1 - front
	var picture := layers[front]
	picture.texture = load(str(panel.image)) as Texture2D
	layer_panel[front] = index
	layer_alpha[front] = 0.0
	# The new picture fades in above the old one.
	picture.get_parent().move_child(picture, -1)
	_drop_waiting("panel_ended")
	_clear_captions()
	for line: Dictionary in panel.get("lines", []):
		var caption := Label.new()
		caption.text = str(line.text)
		caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		caption.custom_minimum_size.x = 1180
		caption.add_theme_font_size_override("font_size", 30)
		caption.add_theme_color_override("font_color", Color("f1ead8"))
		caption.add_theme_color_override("font_shadow_color", Color(0, 0, 0, .9))
		caption.add_theme_constant_override("shadow_offset_x", 0)
		caption.add_theme_constant_override("shadow_offset_y", 2)
		caption.add_theme_constant_override("shadow_outline_size", 6)
		caption.modulate.a = 0.0
		caption.set_meta("line", line)
		caption_box.add_child(caption)
		captions.append(caption)
		caption_times.append(_time_of(float(line.bar)))

func _frame(slot: int, t: float) -> void:
	var panel: Dictionary = panels[layer_panel[slot]]
	var picture := layers[slot]
	if picture.texture == null:
		return
	var begin := _time_of(float(panel.bar))
	var finish: float
	if layer_panel[slot] + 1 >= panels.size():
		# The last picture settles a bar before the book closes, and holds.
		finish = maxf(begin + 1.0, end_time - (score.bar_length(track) if not track.is_empty() else 3.2))
	else:
		finish = _time_of(float(panels[layer_panel[slot] + 1].bar)) + CROSSFADE
	var p := clampf(inverse_lerp(begin, finish, t), 0.0, 1.0)
	p = .5 - .5 * cos(p * PI)
	var from: Array = panel.get("from", [.5, .5, 1.0])
	var to: Array = panel.get("to", [.5, .5, 1.08])
	var focus := Vector2(lerpf(from[0], to[0], p), lerpf(from[1], to[1], p))
	var zoom := lerpf(from[2], to[2], p)
	var view := size
	var art := picture.texture.get_size()
	var cover := maxf(view.x / art.x, view.y / art.y) * maxf(1.0, zoom)
	var shown := art * cover
	var at := view * .5 - focus * shown
	picture.size = shown
	picture.position = Vector2(clampf(at.x, view.x - shown.x, 0.0), clampf(at.y, view.y - shown.y, 0.0))

func _update_captions(t: float, delta: float) -> void:
	for i: int in captions.size():
		var caption := captions[i]
		if t >= caption_times[i]:
			if caption.modulate.a == 0.0:
				var line: Dictionary = caption.get_meta("line")
				line_shown.emit(line)
				# Newest wins: a caption still waiting when a newer one appears stays silent.
				_drop_waiting("superseded")
				waiting_line = line
			caption.modulate.a = minf(1.0, caption.modulate.a + delta / CAPTION_IN + .0001)
	# Never start a clip over one that is still playing; after a stall, the line starts a little late instead of cutting the last one.
	if not waiting_line.is_empty() and t >= narration_until:
		var due := waiting_line
		waiting_line = {}
		narration_until = t + float(due.get("seconds", 0.0)) + NARRATION_GAP
		narration_log.append({"text": str(due.text), "fate": "narrated", "late": snappedf(t - _time_of(float(due.bar)), .001)})
		narrate.emit(due)

func _drop_waiting(fate: String) -> void:
	if not waiting_line.is_empty():
		narration_log.append({"text": str(waiting_line.text), "fate": fate})
		waiting_line = {}

func _clear_captions() -> void:
	for caption: Label in captions:
		caption.queue_free()
	captions.clear()
	caption_times.clear()

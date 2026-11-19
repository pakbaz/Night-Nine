extends Control
## Chapter and time-jump cards. Each page ends on a bar line of the music that
## is playing, then the card opens onto the scene.
signal finished

const FADE_IN := .8
const FADE_OUT := .55
const REVEAL := 1.3
var pages: Array = []
var page := 0
var page_end := 0.0
var music_end := -1.0
var clock := 0.0
var page_clock := 0.0
var paused := false
var closing := -1.0
var score: Node
var backdrop: ColorRect
var painting: TextureRect
var painting_clock := 0.0
var text_box: VBoxContainer
var kicker: Label
var title: Label
var rule: ColorRect
var when: Label
var goal: Label

func _init() -> void:
	name = "TitleCard"
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	backdrop = ColorRect.new()
	backdrop.color = Color(0.008, 0.018, 0.024, 1.0)
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(backdrop)
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# The scene's own painting, dimmed behind the text. It brightens into the scene as the card opens.
	painting = TextureRect.new()
	painting.name = "Painting"
	painting.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	painting.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	painting.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(painting)
	painting.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var vignette := TextureRect.new()
	vignette.name = "Vignette"
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shade := Gradient.new()
	shade.set_color(0, Color(0.008, 0.018, 0.024, .55))
	shade.set_color(1, Color(0.008, 0.018, 0.024, .97))
	var fill := GradientTexture2D.new()
	fill.gradient = shade
	fill.fill = GradientTexture2D.FILL_RADIAL
	fill.fill_from = Vector2(.5, .5)
	fill.fill_to = Vector2(1.15, 1.15)
	vignette.texture = fill
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	painting.add_child(vignette)
	vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	text_box = VBoxContainer.new()
	text_box.alignment = BoxContainer.ALIGNMENT_CENTER
	text_box.add_theme_constant_override("separation", 14)
	text_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(text_box)
	text_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	text_box.offset_left = 260
	text_box.offset_right = -260
	kicker = _line(19, Color("e7b781"))
	kicker.uppercase = true
	title = _line(54, Color("f1ead8"))
	var rule_row := CenterContainer.new()
	rule_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text_box.add_child(rule_row)
	rule = ColorRect.new()
	rule.color = Color("e7b781")
	rule.custom_minimum_size = Vector2(120, 2)
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rule_row.add_child(rule)
	when = _line(21, Color("9fb3ad"))
	goal = _line(26, Color("dcd6c6"))
	hide()

func _line(font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text_box.add_child(label)
	return label

## card: {"chapter": {...}, "page": {...}} from the campaign. place is the scene's dateline.
func play(card: Dictionary, place: String, music: Node, picture: String = "") -> void:
	score = music
	painting.texture = load(picture) as Texture2D if not picture.is_empty() and ResourceLoader.exists(picture) else null
	painting.visible = painting.texture != null
	painting.modulate = Color(.5, .5, .5, 1.0)
	painting_clock = 0.0
	pages.clear()
	if card.has("chapter"):
		var chapter: Dictionary = card.chapter.duplicate()
		var dateline := place
		if chapter.has("when") and not card.has("page"):
			dateline = str(chapter.when) + "  ·  " + place
		chapter["dateline"] = "" if card.has("page") else dateline
		chapter["seconds"] = 6.0
		pages.append(chapter)
	if card.has("page"):
		var extra: Dictionary = card.page.duplicate()
		extra["dateline"] = ""
		extra["seconds"] = 7.0
		pages.append(extra)
	if pages.is_empty():
		finished.emit()
		return
	page = -1
	clock = 0.0
	closing = -1.0
	paused = false
	backdrop.color.a = 1.0
	modulate.a = 1.0
	show()
	_next_page()

func _next_page() -> void:
	page += 1
	page_clock = 0.0
	var data: Dictionary = pages[page]
	kicker.text = str(data.get("kicker", ""))
	title.text = str(data.get("title", ""))
	when.text = str(data.get("dateline", ""))
	when.visible = not when.text.is_empty()
	goal.text = str(data.get("goal", ""))
	goal.visible = not goal.text.is_empty()
	text_box.modulate.a = 0.0
	page_end = _bar_aligned(float(data.seconds))
	var at: float = score.position() if score != null else -1.0
	music_end = at + page_end if at >= 0.0 and score.active_bar_length() > 0.0 else -1.0

func _bar_aligned(seconds: float) -> float:
	# Hold the page until the first bar line after its reading time.
	var bar: float = score.active_bar_length() if score != null else 0.0
	var at: float = score.position() if score != null else -1.0
	if bar <= 0.0 or at < 0.0:
		return seconds
	var beat: float = float(score.current_track.get("beat", 0.0))
	var target := at + seconds
	var line := beat + ceilf((target - beat) / bar) * bar
	return seconds + (line - target)

func skip() -> void:
	if visible and closing < 0.0:
		closing = 0.0

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
		skip()
		accept_event()

func _process(delta: float) -> void:
	if not visible or paused:
		return
	painting_clock += delta
	# A slow push toward the painting while the card is up.
	var push := 1.0 + .06 * smoothstep(0.0, 12.0, painting_clock)
	painting.pivot_offset = painting.size * .5
	painting.scale = Vector2.ONE * push
	if closing >= 0.0:
		# Open onto the scene: text first, then the painting lights up and gives way.
		closing += delta
		text_box.modulate.a = maxf(0.0, text_box.modulate.a - delta / FADE_OUT)
		var open := smoothstep(0.0, REVEAL, closing)
		backdrop.color.a = 1.0 - open
		painting.modulate = Color(.5 + .5 * open, .5 + .5 * open, .5 + .5 * open, 1.0 - smoothstep(.55, 1.0, open / 1.0))
		if closing >= REVEAL:
			hide()
			finished.emit()
		return
	page_clock += delta
	var left := page_end - page_clock
	# Follow the music itself, so the card opens on a bar line. If the music
	# was still loading when the card appeared, take up its bar grid now.
	var at: float = score.position() if score != null else -1.0
	var bar: float = score.active_bar_length() if score != null else 0.0
	if music_end < 0.0 and at >= 0.0 and bar > 0.0:
		var beat: float = float(score.current_track.get("beat", 0.0))
		var target := at + maxf(left, FADE_OUT + .25)
		music_end = beat + ceilf((target - beat) / bar) * bar
	if music_end >= 0.0 and at >= 0.0 and music_end - at < bar + float(pages[page].seconds) + 1.0:
		left = music_end - at
	if left > FADE_OUT:
		text_box.modulate.a = minf(1.0, page_clock / FADE_IN)
	else:
		text_box.modulate.a = maxf(0.0, left / FADE_OUT)
	if left <= 0.0:
		if page + 1 < pages.size():
			_next_page()
		else:
			closing = 0.0
			text_box.modulate.a = 0.0

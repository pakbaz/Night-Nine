extends VBoxContainer
## One settings row: every choice is visible, and the player picks one.
signal changed(index: int)

const INK := Color("f1ead8")
const MUTED := Color("b7c3b9")
const GOLD := Color("e9c276")
const RIGHT := Color("8fd19e")
const WRONG := Color("ec8f7c")
const MARK := preload("res://ui/mark_icon.gd")
var options: Array
var selected := -1
var choices: Array[Button] = []
var title: Label
var mark: Control
var mark_text: Label
var mark_state := ""
var group := ButtonGroup.new()
static var radio := {}

func configure(label: String, items: Array, number: int = 0) -> void:
	options = items
	add_theme_constant_override("separation", 6)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	add_child(header)
	title = Label.new()
	title.text = ("%d. " % number if number > 0 else "") + label
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", 18)
	title.add_theme_color_override("font_color", INK)
	header.add_child(title)
	mark = MARK.new()
	mark.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(mark)
	mark_text = Label.new()
	mark_text.add_theme_font_size_override("font_size", 16)
	mark_text.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(mark_text)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 4)
	add_child(list)
	for index: int in items.size():
		var choice := CheckBox.new()
		choice.text = str(items[index])
		choice.tooltip_text = label + ": " + str(items[index])
		choice.button_group = group
		choice.focus_mode = Control.FOCUS_ALL
		choice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		choice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		choice.add_theme_font_size_override("font_size", 17)
		for icon: String in ["radio_checked", "radio_checked_disabled"]:
			choice.add_theme_icon_override(icon, _radio(true))
		for icon: String in ["radio_unchecked", "radio_unchecked_disabled"]:
			choice.add_theme_icon_override(icon, _radio(false))
		choice.toggled.connect(func(on: bool):
			if on:
				_picked(index))
		list.add_child(choice)
		choices.append(choice)
	clear_mark()

func choose(index: int) -> void:
	if mark_state == "right" or index < 0 or index >= choices.size():
		return
	choices[index].button_pressed = true

func set_mark(ok: bool) -> void:
	mark_state = "right" if ok else "wrong"
	mark.show_kind(mark_state)
	mark_text.text = "Right" if ok else "Not right"
	mark_text.add_theme_color_override("font_color", RIGHT if ok else WRONG)
	mark_text.show()
	for index: int in choices.size():
		choices[index].disabled = ok and index != selected
	_style()

func clear_mark() -> void:
	mark_state = ""
	mark.show_kind("")
	mark_text.hide()
	for choice: Button in choices:
		choice.disabled = false
	_style()

func _picked(index: int) -> void:
	if selected == index:
		return
	selected = index
	if mark_state == "wrong":
		clear_mark()
	else:
		_style()
	changed.emit(index)

func _box(bg: Color, border: Color, width: int = 1) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = bg
	box.border_color = border
	box.set_border_width_all(width)
	box.set_corner_radius_all(6)
	box.content_margin_left = 12
	box.content_margin_right = 12
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	return box

func _style() -> void:
	for index: int in choices.size():
		var choice := choices[index]
		var picked := index == selected
		var border := Color("59787c")
		var bg := Color("16333d")
		if picked:
			border = RIGHT if mark_state == "right" else (WRONG if mark_state == "wrong" else GOLD)
			bg = Color("1d3a2c") if mark_state == "right" else (Color("3a2020") if mark_state == "wrong" else Color("2c4440"))
		var normal := _box(bg, border, 2 if picked else 1)
		var hover := _box(bg.lightened(.12), GOLD, 2)
		var focus := _box(Color(0, 0, 0, 0), GOLD, 2)
		focus.draw_center = false
		for state: String in ["normal", "pressed"]:
			choice.add_theme_stylebox_override(state, normal)
		for state: String in ["hover", "hover_pressed"]:
			choice.add_theme_stylebox_override(state, hover)
		choice.add_theme_stylebox_override("disabled", _box(Color("10252b"), Color("2f4446")))
		choice.add_theme_stylebox_override("focus", focus)
		var text := INK if picked or selected < 0 else MUTED
		for state: String in ["font_color", "font_pressed_color", "font_hover_color", "font_hover_pressed_color", "font_focus_color"]:
			choice.add_theme_color_override(state, text)
		choice.add_theme_color_override("font_disabled_color", Color("72807b"))

## A ring, with a gold dot when picked, drawn once and shared by every row.
func _radio(on: bool) -> Texture2D:
	if radio.has(on):
		return radio[on]
	var image := Image.create(22, 22, false, Image.FORMAT_RGBA8)
	var centre := Vector2(10.5, 10.5)
	for y: int in 22:
		for x: int in 22:
			var distance := Vector2(x, y).distance_to(centre)
			var ring := clampf(1.6 - absf(distance - 8.5), 0.0, 1.0)
			var dot := clampf(5.0 - distance, 0.0, 1.0) if on else 0.0
			image.set_pixel(x, y, Color(GOLD, dot) if dot > ring else Color(INK if on else MUTED, ring))
	radio[on] = ImageTexture.create_from_image(image)
	return radio[on]

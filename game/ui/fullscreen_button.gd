extends Button
## A small corner button that enters and leaves full screen. Browsers also leave full screen on Esc.

const ICON := Color("e9e5d7")

func _init() -> void:
	name = "FullscreenButton"
	focus_mode = Control.FOCUS_NONE
	action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	for state: String in ["normal", "hover", "pressed", "focus"]:
		var box := StyleBoxFlat.new()
		box.bg_color = Color(0.02, 0.06, 0.07, .55) if state == "normal" else Color("31545b")
		box.border_color = Color(0.35, 0.47, 0.49, .8)
		box.set_border_width_all(1)
		box.set_corner_radius_all(5)
		box.set_content_margin_all(0)
		add_theme_stylebox_override(state, box)
	pressed.connect(toggle)

func _ready() -> void:
	get_viewport().size_changed.connect(refresh)
	mouse_entered.connect(queue_redraw)
	mouse_exited.connect(queue_redraw)
	refresh()

static func is_fullscreen() -> bool:
	var mode := DisplayServer.window_get_mode()
	return mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN

func toggle() -> void:
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if is_fullscreen() else DisplayServer.WINDOW_MODE_FULLSCREEN)
	refresh()

func refresh() -> void:
	tooltip_text = "Leave full screen (Esc)" if is_fullscreen() else "Full screen"
	queue_redraw()

func _draw() -> void:
	var color := ICON if is_hovered() else Color(ICON, .82)
	var middle := size * .5
	var arm := size.x * .17
	var reach := size.x * .26
	var leaving := is_fullscreen()
	for corner: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1), Vector2(1, 1)]:
		# Entering: brackets in the outer corners. Leaving: brackets turned inward.
		var point := middle + corner * (reach if not leaving else reach * .42)
		var direction := -corner if not leaving else corner
		draw_line(point, point + Vector2(direction.x * arm, 0), color, 2.0, true)
		draw_line(point, point + Vector2(0, direction.y * arm), color, 2.0, true)

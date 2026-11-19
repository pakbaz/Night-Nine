extends Button
## Mouse and keyboard share the illustrated object's real hit rectangle.
var show_names := false:
	set(value):
		show_names = value
		queue_redraw()

func _ready() -> void:
	flat = true
	focus_mode = Control.FOCUS_ALL
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	for state: String in ["normal", "hover", "pressed", "disabled", "focus", "hover_pressed"]:
		add_theme_stylebox_override(state,StyleBoxEmpty.new())
	for state: String in ["font_color","font_hover_color","font_pressed_color","font_focus_color","font_disabled_color","font_hover_pressed_color"]:
		add_theme_color_override(state,Color.TRANSPARENT)
	mouse_entered.connect(queue_redraw)
	mouse_exited.connect(queue_redraw)
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)

func _draw() -> void:
	if not show_names and not is_hovered() and not has_focus():
		if not disabled:
			var mark := size * .5
			draw_circle(mark, 6, Color(.04,.06,.06,.72), true, -1, true)
			draw_arc(mark, 5, 0, TAU, 24, Color("e8ce9c"), 1.25, true)
			draw_circle(mark, 1.35, Color("e8ce9c"), true, -1, true)
		return
	var face := get_theme_default_font()
	var fs := 18
	var text_extent := face.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,fs)
	var width := text_extent.x+30.0
	var h := 31.0
	var pos := Vector2((size.x-width)*0.5,size.y-h)
	var active := not disabled
	var hover := is_hovered() or has_focus()
	var ink := Color("eee6cd") if active else Color("b4b6a9")
	var box := Rect2(pos,Vector2(width,h))
	draw_rect(box,Color(0.035,0.052,0.059,.93 if hover else .78))
	draw_line(pos,pos+Vector2(0,h),Color("e6b980") if active else Color("778180"),3.0)
	draw_string(face,pos+Vector2(15,22),text,HORIZONTAL_ALIGNMENT_LEFT,-1,fs,ink)
	if hover and active:
		draw_rect(box,Color("e4c08f"),false,1.2)

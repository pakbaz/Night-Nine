extends Control
## A drawn check or cross, so the mark does not depend on font glyphs.
var kind := ""

func _init() -> void:
	custom_minimum_size = Vector2(26, 26)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false

func show_kind(value: String) -> void:
	kind = value
	visible = not value.is_empty()
	queue_redraw()

func _draw() -> void:
	var c := size * .5
	var r := minf(size.x, size.y) * .5 - 1.0
	if kind == "right":
		draw_circle(c, r, Color("8fd19e"), true, -1, true)
		draw_polyline(PackedVector2Array([c + Vector2(-r * .5, 0), c + Vector2(-r * .12, r * .42), c + Vector2(r * .52, -r * .38)]), Color("12301c"), 3.0, true)
	elif kind == "wrong":
		draw_circle(c, r, Color("ec8f7c"), true, -1, true)
		var d := r * .4
		draw_line(c + Vector2(-d, -d), c + Vector2(d, d), Color("3a1410"), 3.0, true)
		draw_line(c + Vector2(-d, d), c + Vector2(d, -d), Color("3a1410"), 3.0, true)

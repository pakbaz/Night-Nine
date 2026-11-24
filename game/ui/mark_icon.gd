extends Control
## A drawn check, cross or padlock, so the mark does not depend on font glyphs.
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
	elif kind == "locked":
		var ink := Color("7f9894")
		var w := r * 1.3
		var body := Rect2(c + Vector2(-w * .5, -r * .05), Vector2(w, r * .95))
		var loop := w * .32
		var thickness := maxf(2.0, r * .16)
		draw_arc(c + Vector2(0, -r * .05), loop, PI, TAU, 24, ink, thickness, true)
		for side: float in [-1.0, 1.0]:
			draw_line(c + Vector2(side * loop, -r * .05), c + Vector2(side * loop, r * .05), ink, thickness, true)
		draw_rect(body, ink)
		draw_circle(body.get_center() + Vector2(0, -r * .08), r * .13, Color("0b1518"), true, -1, true)
		draw_line(body.get_center() + Vector2(0, -r * .02), body.get_center() + Vector2(0, r * .22), Color("0b1518"), maxf(1.5, r * .1), true)

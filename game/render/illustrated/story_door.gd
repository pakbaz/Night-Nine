extends Node2D
## Open the leaf cut from the wide painting to reveal the matching interior.

const OPEN_SECONDS := 0.74
const CAN_PASS := 0.70
const FULL_ANGLE := 1.48

var open_fraction := 0.0
var _unlocked := false
var _seen_closed := false
var _canvas := Vector2.ZERO
var _corners := PackedVector2Array()
var _plate: Texture2D
var _interior: Texture2D
var _hinge := "left"
var _bars := 0

func configure(record: Dictionary, plate: Texture2D, room_id: String, canvas_size: Vector2, unlocked: bool) -> void:
	_plate = plate
	_canvas = canvas_size
	_corners.clear()
	for pair: Array in record.corners:
		_corners.append(Vector2(pair[0], pair[1]) * _canvas)
	_hinge = record.get("hinge", "left")
	_bars = record.get("bars", 0)
	_interior = load("res://assets/illustrated/campaign/doors/%s.webp" % room_id)
	snap_unlocked(unlocked)

func snap_unlocked(wanted: bool) -> void:
	_unlocked = wanted
	_seen_closed = false
	open_fraction = 1.0 if wanted else 0.0
	queue_redraw()

func set_unlocked(wanted: bool) -> void:
	if wanted == _unlocked:
		return
	_unlocked = wanted
	if not wanted or not _seen_closed:
		snap_unlocked(wanted)

func advance(delta: float, in_exploration: bool) -> void:
	if not in_exploration:
		return
	if not _unlocked:
		_seen_closed = true
	elif open_fraction < 1.0:
		open_fraction = minf(1.0, open_fraction + delta / OPEN_SECONDS)
		queue_redraw()

func is_cleared() -> bool:
	return open_fraction >= CAN_PASS

func _point(u: float, v: float) -> Vector2:
	return _corners[0].lerp(_corners[1], u).lerp(_corners[3].lerp(_corners[2], u), v)

func _project(u: float, v: float, hinge: float, angle: float) -> Vector2:
	# The hinge remains fixed. The free edge recedes toward the eye line.
	var depth := absf(u - hinge) * sin(angle)
	var contracted_u := hinge + (u - hinge) * cos(angle)
	return _point(contracted_u, lerpf(v, 0.43, depth * 0.28))

func _slat(u0: float, u1: float, v0: float, v1: float, pivot: float, angle: float) -> void:
	var vertices := PackedVector2Array()
	var uvs := PackedVector2Array()
	for uv: Vector2 in [Vector2(u0,v0),Vector2(u1,v0),Vector2(u1,v1),Vector2(u0,v1)]:
		vertices.append(_project(uv.x,uv.y,pivot,angle))
		uvs.append(_point(uv.x,uv.y) / _canvas)
	var tint := 1.0 - 0.16 * sin(angle)
	draw_polygon(vertices,PackedColorArray([Color(tint,tint,tint)]),uvs,_plate)

func _draw() -> void:
	if open_fraction <= 0.0 or not _interior or not _plate or _corners.size() != 4:
		return
	draw_polygon(_corners,PackedColorArray([Color.WHITE]),PackedVector2Array([Vector2.ZERO,Vector2.RIGHT,Vector2.ONE,Vector2.DOWN]),_interior)
	var angle := FULL_ANGLE * smoothstep(0.0,1.0,open_fraction)
	if _hinge == "double":
		_slat(0,0.5,0,1,0,angle)
		_slat(0.5,1,0,1,1,angle)
	elif _bars > 0:
		var pivot := 0.0 if _hinge == "left" else 1.0
		for i in range(_bars + 1):
			var u := float(i) / _bars
			_slat(maxf(0,u-.014),minf(1,u+.014),0,1,pivot,angle)
		for v: float in [0.018,0.46,0.805,0.982]:
			_slat(0,1,v-.018,v+.018,pivot,angle)
	else:
		_slat(0,1,0,1,0 if _hinge == "left" else 1,angle)

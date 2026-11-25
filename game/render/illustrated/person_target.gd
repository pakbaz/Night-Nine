extends Control
## A transparent, silhouette-only GUI surface. Empty pixels pass through to props and the floor.
signal person_pressed(id: String)
var pick: Callable
var caption: Callable

func _has_point(at: Vector2) -> bool:
	return pick.is_valid() and not str(pick.call(get_global_transform_with_canvas()*at)).is_empty()

func _get_tooltip(at: Vector2) -> String:
	return caption.call(pick.call(get_global_transform_with_canvas()*at))

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var id: String = pick.call(get_global_transform_with_canvas()*event.position)
		if not id.is_empty():
			accept_event()
			person_pressed.emit(id)

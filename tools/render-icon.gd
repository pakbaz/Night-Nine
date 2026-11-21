extends SceneTree

func _initialize() -> void:
	var image := Image.new()
	var result := image.load_svg_from_string(FileAccess.get_file_as_string("res://icon.svg"))
	if result != OK or image.is_empty():
		push_error("Could not render the N9 logo from icon.svg")
		quit(1)
		return
	result = image.save_png("res://icon.png")
	if result != OK:
		push_error("Could not save the N9 splash image: " + error_string(result))
	quit(0 if result == OK else 1)

extends SceneTree

func _initialize() -> void:
	var text := "Night Nine - engine and dependency notices\n\n"
	text += "Generated from Godot " + Engine.get_version_info().string + ".\n"
	text += "These licenses apply to the listed engine components, not to the original game content.\n\n"
	text += "Environment texture: wood_floor_deck by Dimitrios Savva, Poly Haven. CC0-1.0.\n"
	text += "Source: https://polyhaven.com/a/wood_floor_deck\nLicense: https://polyhaven.com/license\n\n"
	text += Engine.get_license_text() + "\n\n"
	for component: Dictionary in Engine.get_copyright_info():
		text += component.name + "\n"
		for part: Dictionary in component.parts:
			text += "Files: " + ", ".join(part.files) + "\n"
			text += "Copyright: " + "; ".join(part.copyright) + "\n"
			text += "License: " + part.license + "\n"
		text += "\n"
	var licenses: Dictionary = Engine.get_license_info()
	for name_: String in licenses:
		text += name_ + "\n" + str(licenses[name_]) + "\n\n"
	var file := FileAccess.open("res://LICENSES.txt", FileAccess.WRITE)
	file.store_string(text)
	file.close()
	quit()

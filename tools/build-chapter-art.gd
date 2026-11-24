extends SceneTree
## Writes the small chapter pictures for Play Chapters: one cover-cropped copy of
## each chapter's opening painting. Run from the repository root:
##   bash tools/godot.sh --headless --script "$PWD/tools/build-chapter-art.gd"
## then import the new files with tools/godot.sh --headless --editor --import --quit.

const OUTPUT := "res://assets/illustrated/chapters/"
const SIZE := Vector2i(320, 180)
const PROLOGUE := {"p_bay": "bay.png", "p_veyr": "veyr.png", "p_meeting": "meeting.png"}

func _initialize() -> void:
	var content: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	var previous := ""
	var written: Array[String] = []
	for scene: Dictionary in content.scenes:
		if str(scene.chapter) == previous:
			continue
		previous = str(scene.chapter)
		var id := str(scene.id)
		var source: String = "res://assets/illustrated/rooms/" + str(PROLOGUE[id]) if PROLOGUE.has(id) \
			else "res://assets/illustrated/campaign/rooms/" + id + ".webp"
		var image := Image.load_from_file(ProjectSettings.globalize_path(source))
		if image == null or image.is_empty():
			push_error("Missing chapter painting: " + source)
			quit(1)
			return
		var aspect := float(SIZE.x) / SIZE.y
		var crop := Rect2i(Vector2i.ZERO, image.get_size())
		if float(crop.size.x) / crop.size.y > aspect:
			crop.size.x = roundi(crop.size.y * aspect)
			crop.position.x = (image.get_width() - crop.size.x) / 2
		else:
			crop.size.y = roundi(crop.size.x / aspect)
			crop.position.y = (image.get_height() - crop.size.y) / 2
		var picture := image.get_region(crop)
		picture.convert(Image.FORMAT_RGB8)
		picture.resize(SIZE.x, SIZE.y, Image.INTERPOLATE_LANCZOS)
		var error := picture.save_webp(ProjectSettings.globalize_path(OUTPUT + id + ".webp"), true, .86)
		if error != OK:
			push_error("Could not save the chapter picture for " + id + ": " + error_string(error))
			quit(1)
			return
		written.append(id)
	print("Chapter pictures: ", ", ".join(written))
	quit(0)

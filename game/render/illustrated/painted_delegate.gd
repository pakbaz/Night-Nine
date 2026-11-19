extends "res://render/illustrated/illustrated_actor.gd"
## The neutral face is already painted on the parent room texture.
func configure_delegate(actor_id: String) -> void:
	var folder := "res://assets/illustrated/cast/" + actor_id + "/"
	manifest = JSON.parse_string(FileAccess.get_file_as_string(folder + "sprite.json"))
	var atlas := load(folder + str(manifest.atlas)) as Texture2D
	eyes = patch(atlas)
	mouth = patch(atlas)
	phase = 2.4 if actor_id == "general_us" else 3.75

class_name NightDesktop
extends NightPlatform

func save_root() -> String:
	var override: String = OS.get_environment("NIGHT_NINE_SAVE_DIR")
	return override if not override.is_empty() else "user://saves"

class_name NightPlatform
extends RefCounted
## Platform boundary for native saves and future console services.
## Console SDK implementations belong in private platform integration repositories.

func save_root() -> String:
	return "user://saves"

func supports_cloud_saves() -> bool:
	return false

func request_pause() -> void:
	pass

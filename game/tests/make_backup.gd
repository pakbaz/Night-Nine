extends SceneTree
## Test-only: write a browser save backup that resumes at a chosen scene with chosen leads done.
## NIGHT_NINE_BACKUP_SCENE=c1_flat NIGHT_NINE_BACKUP_DONE=c1_flat.saturday,c1_flat.sunday
## NIGHT_NINE_BACKUP_OUT=/path/backup.json (with isolated NIGHT_NINE_SAVE_DIR)
var game: Node

func _initialize() -> void:
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue = false
	await process_frame
	var scene_id := OS.get_environment("NIGHT_NINE_BACKUP_SCENE")
	var done := OS.get_environment("NIGHT_NINE_BACKUP_DONE").split(",", false)
	var output := OS.get_environment("NIGHT_NINE_BACKUP_OUT")
	var campaign = game.campaign
	campaign.reset()
	while campaign.current().id != scene_id:
		var scene: Dictionary = campaign.current()
		campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				campaign.switch_actor(task.actor)
			campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
			campaign.mark_seen(task.get("lead", []) + task.lines)
			if not str(task.get("finding", "")).is_empty():
				campaign.mark_seen([task.finding])
		campaign.mark_seen(scene.get("recap", []) + scene.outro)
		if not campaign.advance():
			push_error("Could not reach " + scene_id)
			quit(1)
			return
	var here: Dictionary = campaign.current()
	campaign.mark_seen(here.get("context", []) + here.intro)
	for id: String in done:
		var task: Dictionary = campaign.task_index[id]
		if not task.actor.is_empty():
			campaign.switch_actor(task.actor)
		campaign.choose(id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		campaign.mark_seen(task.get("lead", []) + task.lines)
		if not str(task.get("finding", "")).is_empty():
			campaign.mark_seen([task.finding])
	game.started = true
	game.menu.hide()
	game._load_stage(false)
	await process_frame
	game._save("export")
	var result: Dictionary = game.saves.export_slot("export")
	var file := FileAccess.open(output, FileAccess.WRITE)
	file.store_string(result.text)
	file.close()
	print("Backup at ", scene_id, ": ", output)
	await game.drain_audio()
	quit(0)

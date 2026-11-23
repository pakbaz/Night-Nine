extends SceneTree
## Review captures: render scenes as the player sees them, for visual and perspective review.
## NIGHT_NINE_CAPTURE_PLAN is a JSON list of shots:
##   {"name": "c1_escape-gate-open", "scene": "c1_escape", "done": ["c1_escape.power"],
##    "walk": [0.5, 0.8], "line": "c1_escape.in.01", "focus": "c1_escape.power", "wait": 30}
## "wait" is how many frames to let a line's camera move or dissolve finish before the shot.
## "solve" completes one more lead after entering, without starting the scene's exit.
## Run windowed (not headless) with NIGHT_NINE_QA_DIR and NIGHT_NINE_SAVE_DIR set.
var game: Node

func _initialize() -> void:
	run.call_deferred()

func frames(count: int) -> void:
	for i: int in count:
		await process_frame

func enter(scene_id: String, done: Array) -> void:
	var campaign = game.campaign
	campaign.reset()
	while campaign.current().id != scene_id:
		var scene: Dictionary = campaign.current()
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				campaign.switch_actor(task.actor)
			campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		campaign.advance()
	campaign.mark_seen(campaign.current().get("context", []) + campaign.current().intro)
	for id: String in done:
		var task: Dictionary = campaign.task_index[id]
		if not task.actor.is_empty():
			campaign.switch_actor(task.actor)
		campaign.choose(id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		campaign.mark_seen(task.get("lead", []) + task.lines)
	game._load_stage(false)
	await frames(4)
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	game._refresh()
	await frames(2)

func save(folder: String, name: String) -> void:
	await frames(6)
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(folder.path_join(name + ".png"))

func run() -> void:
	var folder := OS.get_environment("NIGHT_NINE_QA_DIR")
	var plan: Variant = JSON.parse_string(OS.get_environment("NIGHT_NINE_CAPTURE_PLAN"))
	if folder.is_empty() or not plan is Array:
		push_error("Set NIGHT_NINE_QA_DIR and NIGHT_NINE_CAPTURE_PLAN.")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(folder)
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue = false
	await frames(2)
	game.started = true
	game.menu.hide()
	for shot: Dictionary in plan:
		await enter(str(shot.scene), shot.get("done", []))
		if shot.has("solve"):
			# Solve one lead in place, as play does, without starting the scene's exit.
			var solved: Dictionary = game.campaign.task_index[str(shot.solve)]
			game.campaign.choose(str(shot.solve), int(solved.answer), solved.get("puzzle", {}).get("solution", []))
			game._refresh()
			await frames(2)
		var stage = game.stage
		if shot.has("walk") and stage.get("floor_stage") and stage.floor_stage.has_actor():
			var body: Node2D = stage.floor_stage.bodies[stage.floor_stage.active_actor].body
			body.position = Vector2(shot.walk[0], shot.walk[1]) * stage.ART
			stage.floor_stage.draw_body(stage.floor_stage.active_actor, false)
		if shot.has("focus"):
			stage.set_focus(game.campaign.current().tasks.find(game.campaign.task_index[str(shot.focus)]))
		if shot.has("line"):
			game._speak([str(shot.line)], Callable())
			await frames(int(shot.get("wait", 30)))
		await save(folder, str(shot.name))
		if shot.has("line"):
			while game.dialogue_panel.visible:
				game._next_line()
				await frames(1)
		if shot.has("focus"):
			stage.set_focus(-1)
		print("Captured ", shot.name)
	await game.drain_audio()
	quit(0)

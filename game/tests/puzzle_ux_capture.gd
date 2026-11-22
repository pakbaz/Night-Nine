extends SceneTree
## Test-only: capture the case board and settings rows for visual review. Run without --headless.
var game: Node
var out := ""

func _initialize() -> void:
	run.call_deferred()

func frames(n: int = 4) -> void:
	for i: int in n:
		await process_frame

func shot(name_: String) -> void:
	await frames(6)
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(out.path_join(name_ + ".png"))
	print("Saved ", out.path_join(name_ + ".png"))

func reach(id: String) -> void:
	game.campaign.reset()
	var target: int = game.campaign.task_scene[id]
	for i: int in range(target + 1):
		var scene: Dictionary = game.campaign.current()
		game.campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if task.id == id:
				break
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
			game.campaign.mark_seen(task.lines)
			if not str(task.get("finding", "")).is_empty():
				game.campaign.mark_seen([task.finding])
		if i != target:
			game.campaign.mark_seen(scene.outro)
			game.campaign.advance()
	var wanted: String = game.campaign.task_index[id].actor
	if not wanted.is_empty():
		game.campaign.switch_actor(wanted)
	game.campaign.mark_seen(game.campaign.task_index[id].get("lead", []))
	game.started = true
	game.menu.hide()
	game._load_stage(false)
	await frames()
	game._open_task(id)
	await frames()

func run() -> void:
	out = OS.get_environment("PUZZLE_UX_OUT")
	if out.is_empty():
		out = ProjectSettings.globalize_path("res://").path_join("../tmp/puzzle-ux").simplify_path()
	DirAccess.make_dir_recursive_absolute(out)
	var prefix := OS.get_environment("PUZZLE_UX_PREFIX")
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue = false
	await frames(10)
	await reach("c1_pier.bait")
	await shot(prefix + "pier-bait-board")
	var board: Control = game.case_board
	var stage: Dictionary = board.stages[0]
	board.pick(int(stage.answer[1]))
	await shot(prefix + "pier-bait-selected")
	# Two right, the rest swapped, then check.
	for i: int in stage.answer.size():
		var tile: int = int(stage.answer[i])
		if i >= 2:
			tile = int(stage.answer[2 + (i - 1) % (stage.answer.size() - 2)])
		board.place(tile, i)
	board.check_step()
	await shot(prefix + "pier-bait-wrong-check")
	await reach("c1_escape.order")
	await shot(prefix + "escape-order-step1")
	await reach("c1_escape.power")
	var rows: Array = game.puzzle_controls
	var solution: Array = game.campaign.task_index["c1_escape.power"].puzzle.solution
	for i: int in rows.size():
		var wanted: int = int(solution[i]) if i != 1 else (int(solution[i]) + 1) % rows[i].options.size()
		if rows[i].has_method("choose"):
			rows[i].choose(wanted)
		else:
			for step: int in wanted + 1:
				rows[i].shift(1)
	await shot(prefix + "escape-power-rows")
	for child: Node in game.interaction.get_children():
		if child is Button and child.text == "Apply settings":
			child.pressed.emit()
	await shot(prefix + "escape-power-rows-wrong")
	root.size = Vector2i(1280, 800)
	await reach("c1_pier.bait")
	await shot(prefix + "pier-bait-1280x800")
	await game.drain_audio()
	quit(0)

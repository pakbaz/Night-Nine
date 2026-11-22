extends Node
## Drive one stretch of the game hands-free for Godot's Movie Maker mode, so the
## real picture and mixed sound can be recorded and reviewed.
## Set NIGHT_NINE_SHOWREEL to "opening", "dread", "ending", "after" (epilogue to
## one year later) or "year" (the one-year card alone). Once a second it logs the
## score's levels and, during a storybook, the book's own clock and captions.
var game: Node
var segment := ""

var mix_clock := 0.0
var elapsed := 0.0

func _ready() -> void:
	segment = OS.get_environment("NIGHT_NINE_SHOWREEL")
	# macOS can stop drawing a covered or minimized window while the game keeps
	# running, and Movie Maker then writes the last drawn frame again and again.
	# Render the viewports ourselves at the start of every frame so each written
	# frame is current (at most one frame behind) whatever the window is doing.
	if OS.get_environment("NIGHT_NINE_SHOWREEL_NO_FORCE").is_empty():
		get_tree().process_frame.connect(func(): RenderingServer.force_draw(false, 0.0))
	if not OS.get_environment("NIGHT_NINE_SHOWREEL_MINIMIZE").is_empty():
		# Only for proving the fix: a minimized window never draws on its own.
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	_run.call_deferred()

func _process(delta: float) -> void:
	# Log the score's levels once a second, so a quiet stretch in the recording can be explained.
	mix_clock += delta
	elapsed += delta
	if mix_clock < 1.0 or game == null:
		return
	mix_clock -= 1.0
	var score: Node = game.score
	var deck: float = score.players[score.active_index].volume_db if score.active_index >= 0 else -80.0
	print("mix %.0f cue=%s file=%s at=%.1f deck=%.1f duck=%.1f lift=%.1f ride=%.1f card=%s book=%s can_draw=%s" % [elapsed, score.cue, str(score.current_file).get_file(), score.position(), deck, score.duck_db, score.lift_db, score.ride_db, game.title_card.visible, game.storybook.visible, DisplayServer.window_can_draw()])
	var book: Node = game.storybook
	if book.visible:
		var expected := -1
		for i: int in book.panels.size():
			if book.now() >= book._time_of(float(book.panels[i].bar)) - .05:
				expected = i
		print("book clock=%.2f fallback=%.2f driven=%s same_file=%s index=%d expected=%d captions=%d shown=%d end=%.2f closing=%.2f paused=%s" % [book.now(), book.fallback_clock, book.music_driven, score.current_file == str(book.book.get("music", {}).get("file", "")), book.index, expected, book.captions.size(), book.captions.filter(func(c): return c.modulate.a > 0.0).size(), book.end_time, book.closing, book.paused])

func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout

func until(condition: Callable, seconds: float) -> void:
	var left := seconds
	while left > 0.0 and not condition.call():
		await get_tree().process_frame
		left -= get_process_delta_time()

func solve_all(refresh := true) -> void:
	for task: Dictionary in game.campaign.current().tasks:
		if not task.actor.is_empty():
			game.campaign.switch_actor(task.actor)
		game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		game.campaign.mark_seen(task.lines)
	if refresh:
		game._refresh()

func jump_to(scene_id: String) -> void:
	game.campaign.reset()
	while game.campaign.current().id != scene_id:
		# No stage is loaded while skipping ahead, so leave the HUD alone.
		solve_all(false)
		game.campaign.mark_seen(game.campaign.current().get("context", []) + game.campaign.current().intro)
		game.campaign.mark_seen(game.campaign.current().outro)
		game.campaign.advance()
	game.started = true
	game.menu.hide()

func play_dialogue(limit: float) -> void:
	# Let lines play at their natural length, as a player with auto-advance would hear them.
	await until(func(): return not game.dialogue_panel.visible, limit)

func leave_scene() -> void:
	await play_dialogue(60.0)
	await wait(1.5)
	game._depart()
	await play_dialogue(60.0)

func _run() -> void:
	game.auto_dialogue = true
	await wait(1.0)
	match segment:
		"opening":
			# Title, the narrated backstory, the prologue card and the first lines on the boat.
			await wait(2.0)
			game._new_game()
			await until(func(): return game.title_card.visible, 90.0)
			await until(func(): return not game.title_card.visible, 15.0)
			await play_dialogue(20.0)
			await wait(2.0)
		"dread":
			# End of Chapter 1: the ninth-night tone, the procession film and the Chapter 2 card.
			jump_to("c1_escape")
			game._load_stage(false)
			solve_all()
			await leave_scene()
			await until(func(): return game.title_card.visible, 40.0)
			await until(func(): return not game.title_card.visible, 15.0)
			await wait(4.0)
		"year":
			# One year later on its own: the card and the first lines.
			jump_to("one_year")
			game._load_stage(true)
			await until(func(): return not game.title_card.visible, 30.0)
			await play_dialogue(20.0)
		"after":
			# From the epilogue card to one year later: the lanterns and the closing storybook.
			jump_to("epilogue")
			game._load_stage(true)
			await until(func(): return not game.title_card.visible, 30.0)
			solve_all()
			await wait(2.0)
			await leave_scene()
			await until(func(): return game.storybook.visible, 30.0)
			await until(func(): return game.title_card.visible, 120.0)
			await wait(4.0)
		"ending":
			# The ship rises, the epilogue, the lanterns, the closing storybook and one year later.
			jump_to("c10_report")
			game._load_stage(false)
			solve_all()
			await leave_scene()
			await until(func(): return game.title_card.visible, 40.0)
			await until(func(): return not game.title_card.visible, 15.0)
			solve_all()
			await wait(6.0)
			await leave_scene()
			await until(func(): return game.storybook.visible, 30.0)
			await until(func(): return game.title_card.visible, 120.0)
			await until(func(): return not game.title_card.visible, 15.0)
			await wait(3.0)
	await game.drain_audio()
	get_tree().quit()

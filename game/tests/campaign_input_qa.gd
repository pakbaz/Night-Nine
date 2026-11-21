extends Node
## Exercise real GUI input, including popup selectors and modal audio pause.
var game: Node
var checks := 0
var failures: Array[String] = []
var report_root := ""

func _ready() -> void:
	_run.call_deferred()

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)
		print("Input failure state: ", JSON.stringify({"check": message, "menu": game.menu.visible, "journal": game.journal.visible, "dialogue": game.dialogue_panel.visible, "transitioning": game.transitioning, "task": game.selected_task, "line": game.active_line}))
		RenderingServer.force_draw(false)
		get_viewport().get_texture().get_image().save_png(report_root.path_join("failure-%02d.png" % checks))

func button(text: String, parent: Node) -> Button:
	for candidate: Node in parent.find_children("*","Button",true,false):
		if candidate.text == text and candidate.is_visible_in_tree():
			return candidate
	return null

func click(control: Control) -> void:
	if control == null:
		check(false,"Expected visible control")
		return
	await get_tree().process_frame
	var point: Vector2 = control.get_global_transform_with_canvas() * (control.size * 0.5)
	var move := InputEventMouseMotion.new()
	move.position=point
	control.get_viewport().push_input(move,true)
	for pressed: bool in [true,false]:
		var event := InputEventMouseButton.new()
		event.position=point
		event.button_index=MOUSE_BUTTON_LEFT
		event.button_mask=MOUSE_BUTTON_MASK_LEFT if pressed else 0
		event.pressed=pressed
		control.get_viewport().push_input(event,true)
	# Send a complete click in one frame so native pointer motion cannot split it.
	# Let deferred GUI/layout changes settle before the next control is located.
	for frame: int in 2:
		await get_tree().process_frame

func solve_case_board(task: Dictionary) -> void:
	var board: Control = game.case_board
	var scroll := game.interaction.get_parent() as ScrollContainer
	for stage: Dictionary in task.puzzle.stages:
		for slot: int in stage.answer.size():
			var tile: Button = board.pieces[int(stage.answer[slot])]
			var destination: Button = board.slots[slot]
			scroll.ensure_control_visible(tile)
			await click(tile)
			scroll.ensure_control_visible(destination)
			await click(destination)
			check(int(board.draft.placements[board.stage_index][slot]) == int(stage.answer[slot]),"Place evidence on "+str(stage.slots[slot])+" in "+str(task.id))
		scroll.ensure_control_visible(board.confirm)
		await click(board.confirm)

func key(code: Key, target: Window = null) -> void:
	if target == null:
		target = get_window()
	for pressed: bool in [true,false]:
		var event := InputEventKey.new()
		event.keycode=code
		event.physical_keycode=code
		event.pressed=pressed
		event.window_id=target.get_window_id()
		# Embedded PopupMenu handles keys in Window's input path, before its
		# own viewport. Send through its embedder to exercise that real route.
		if target.is_embedded():
			get_window().push_input(event,true)
		elif target == get_window():
			target.push_input(event,true)
		else:
			Input.parse_input_event(event)
		await get_tree().process_frame

func _run() -> void:
	Engine.max_fps = 60
	report_root=OS.get_environment("NIGHT_NINE_QA_DIR")
	if report_root.is_empty():
		report_root=ProjectSettings.globalize_path("res://../tmp/qa")
	DirAccess.make_dir_recursive_absolute(report_root)
	game.auto_dialogue=false
	get_window().grab_focus()
	await get_tree().create_timer(0.2).timeout
	await get_tree().process_frame
	await click(button("New game",game.menu))
	if game.new_game_confirmation.visible:
		await key(KEY_ENTER,game.new_game_confirmation)
	check(game.started and game.storybook.visible,"Mouse starts a new campaign with the backstory")
	await get_tree().create_timer(.4).timeout
	var first_panel: int = game.storybook.index
	await click(game.storybook)
	await get_tree().create_timer(.2).timeout
	check(game.storybook.index == first_panel + 1,"A click turns the storybook page")
	await key(KEY_SPACE)
	await get_tree().create_timer(.2).timeout
	check(game.storybook.index == first_panel + 2,"Space turns the storybook page")
	await key(KEY_ESCAPE)
	check(game.menu.visible and game.storybook.paused,"Escape pauses the storybook")
	await key(KEY_ESCAPE)
	check(not game.menu.visible and not game.storybook.paused,"Escape resumes the storybook")
	await click(button("Skip story",game.storybook))
	var card_deadline: int=Time.get_ticks_msec()+4000
	while not game.title_card.visible and Time.get_ticks_msec()<card_deadline:
		await get_tree().process_frame
	check(game.title_card.visible and game.campaign.current().id=="p_bay","Skipping the story opens the prologue card")
	await key(KEY_SPACE)
	card_deadline=Time.get_ticks_msec()+4000
	while game.title_card.visible and Time.get_ticks_msec()<card_deadline:
		await get_tree().process_frame
	check(game.dialogue_panel.visible and game.active_line=="p_bay.in.01","The bay arrival begins after the card")
	# The recorder checks below run in the Archivist's memory, now at the end of Interlude 1.
	game.campaign.reset()
	while game.campaign.current().id != "p_veyr":
		for task: Dictionary in game.campaign.current().tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		game.campaign.mark_seen(game.campaign.current().intro)
		game.campaign.advance()
	game._load_stage(true)
	await key(KEY_SPACE)
	card_deadline=Time.get_ticks_msec()+4000
	while game.title_card.visible and Time.get_ticks_msec()<card_deadline:
		await get_tree().process_frame
	check(game.dialogue_panel.visible,"The Archivist's memory begins after its page")
	var arrival: Dictionary=game.campaign.content.lines[game.active_line]
	var arrival_take: Dictionary=game._recording_for(arrival.audio,arrival.text).take
	if game.voice_manifest.get("enabled",true):
		check(not arrival_take.is_empty() and game.voice.playing and game.voice.stream.resource_path==arrival_take.file,
			"Play the approved arrival recording")
	else:
		check(not game.voice.playing and game.line_remaining>=game._reading_time(arrival.text)-.2,
			"Text-only arrival uses reading time without recorded voice")
	game._save("qa-mid-dialogue")
	game._load("qa-mid-dialogue")
	check(game.dialogue_panel.visible and game.active_line=="p_veyr.in.01","Load repeats the interrupted arrival line")
	await click(button("Skip scene",game.dialogue_panel))
	check(not game.dialogue_panel.visible,"Mouse skips arrival dialogue")
	await click(game.hotspots[0])
	check(game.dialogue_panel.visible and game.active_line=="p_veyr.shield.01","First opening plays the lead-in")
	await key(KEY_ENTER)
	check(game.root.get_node("InteractionPanel").visible,"Enter advances the lead-in to the puzzle")
	check(button("Back",game.interaction)!=null and game.interaction.find_child("Goal",true,false)!=null
		and game.interaction.find_child("Background",true,false)!=null,"Puzzle shows its goal and background")
	await click(button("Back",game.interaction))
	await click(game.hotspots[0])
	check(game.root.get_node("InteractionPanel").visible and not game.dialogue_panel.visible,"Reopening skips the seen lead-in")
	var gain := button("−6 dB",game.interaction)
	check(is_instance_valid(gain),"Recorder puzzle is available")
	if gain:
		gain.grab_focus()
		await key(KEY_SPACE)
		check(gain.button_pressed,"Keyboard selects minus-six-decibel setting")
		RenderingServer.force_draw(false)
		get_viewport().get_texture().get_image().save_png(report_root.path_join("recorder-input.png"))
		await click(button("Apply settings",game.interaction))
		check("p_veyr.levels" in game.campaign.data.done,"Mouse applies recorder settings")
	await click(button("Skip scene",game.dialogue_panel))
	await click(game.hotspots[1])
	await click(button("Listen: the last wind on Veyr",game.interaction))
	check(game.voice.playing,"Listen control plays the local cue")
	var meter: ShaderMaterial = game.stage.recorder
	check(is_instance_valid(meter),"Painted field recorder is present")
	var level: float = meter.get_shader_parameter("signal")
	await get_tree().create_timer(.15).timeout
	check(not is_equal_approx(level,meter.get_shader_parameter("signal")),"The meter responds during playback")
	await key(KEY_ESCAPE)
	check(game.menu.visible and game.voice.stream_paused,"Menu pauses playback")
	var paused: float = meter.get_shader_parameter("signal")
	await get_tree().create_timer(.15).timeout
	check(is_equal_approx(paused,meter.get_shader_parameter("signal")),"Pause holds the recorder meter")
	await click(button("Save game",game.menu))
	await click(button("Load saved game",game.menu))
	check(not game.menu.visible and not game.voice.stream_paused and not game.ambience.stream_paused,"Loading resumes audio")
	await key(KEY_J)
	check(game.journal.visible,"Journal keyboard shortcut opens")
	await key(KEY_ESCAPE)
	check(not game.journal.visible and not game.menu.visible,"Escape closes journal")
	await key(KEY_ESCAPE)
	await click(button("New game",game.menu))
	check(game.new_game_confirmation.visible,"New game asks before replacing progress")
	await key(KEY_ESCAPE,game.new_game_confirmation)
	check("p_veyr.levels" in game.campaign.data.done,"Cancel preserves progress")
	await click(button("Continue",game.menu))
	await click(game.hotspots[1])
	await click(button("Continue",game.interaction))
	var departure_deadline:=Time.get_ticks_msec()+5000
	while game.campaign.current().id=="p_veyr" and game.active_line!="p_veyr.out.02" and Time.get_ticks_msec()<departure_deadline:
		await key(KEY_SPACE)
	check(game.active_line=="p_veyr.out.02","Departure dialogue advances with Space")
	await click(button("Menu",game.root))
	await click(button("Save game",game.menu))
	await click(button("Load saved game",game.menu))
	check(game.active_line=="p_veyr.out.02" and game.transitioning,"Load resumes interrupted departure")
	await click(button("Skip scene",game.dialogue_panel))
	if game.campaign.current().id!="c4_safe":
		print("Departure state: ", JSON.stringify({"scene": game.campaign.data.scene, "line": game.active_line, "dialogue": game.dialogue_panel.visible, "transitioning": game.transitioning, "menu": game.menu.visible, "queue": game.queue}))
	check(game.campaign.current().id=="c4_safe","Resumed departure enters the next location")
	var result := {"checks":checks,"failures":failures,"input":"viewport mouse and keyboard events"}
	var path := report_root.path_join("campaign-input-results.json")
	var file := FileAccess.open(path,FileAccess.WRITE)
	file.store_string(JSON.stringify(result,"\t"))
	file.close()
	print(JSON.stringify(result))
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

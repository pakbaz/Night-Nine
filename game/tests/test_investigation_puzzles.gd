extends SceneTree

var checks := 0
var failures: Array[String] = []

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func solve_scene(state: NightCampaign) -> void:
	while not state.can_leave():
		for task: Dictionary in state.current().tasks:
			if not state.available(task.id):
				continue
			if not task.actor.is_empty():
				state.switch_actor(task.actor)
			check(state.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[])).ok,
				"Solve prerequisite "+task.id)

func verify_tape_layout(panel: NightTapeCompare, player: AudioStreamPlayer, state: NightCampaign) -> void:
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	root.content_scale_size = Vector2i.ZERO
	var presentation: Node = load("res://scripts/campaign.gd").new()
	panel.theme = presentation._theme()
	presentation.free()
	var takes: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(
		"res://content/voice-manifest.json")).takes
	for window_size: Vector2i in [Vector2i(1440, 900), Vector2i(960, 600)]:
		root.size = window_size
		for id: String in ["c6_iris.takes", "c8_beach.second"]:
			var task: Dictionary = state.task_index[id]
			check(panel.open_task(id, load(takes[task.sounds[0]].file), load(takes[task.sounds[1]].file), {},
				player, task.puzzle), "Open " + id + " at " + str(window_size))
			for choice: OptionButton in panel.row_choices:
				choice.select(choice.item_count - 1)
			for frame: int in 4:
				await process_frame
			(panel.get_child(0) as ScrollContainer).ensure_control_visible(panel.slider)
			for frame: int in 3:
				await process_frame
			check(panel.slider.size.x >= 240.0, id + " keeps a usable slider at " + str(window_size))
			for control: Control in [panel.slider, panel.play_a_button, panel.play_b_button]:
				var rect := control.get_global_rect()
				check(rect.position.x >= 0 and rect.end.x <= window_size.x,
					id + " keeps " + control.get_class() + " within the window")
			if id == "c8_beach.second":
				check(panel.row_choices.size() == 3, "Voicemail shows the breath, gap and message questions")
			var rect := panel.slider.get_global_rect()
			var start := rect.position + Vector2(rect.size.x * .35, rect.size.y * .5)
			var finish := rect.position + Vector2(rect.size.x * .7, rect.size.y * .5)
			var down := InputEventMouseButton.new()
			down.position = start
			down.button_index = MOUSE_BUTTON_LEFT
			down.pressed = true
			root.push_input(down, true)
			await process_frame
			var before: float = panel.slider.value
			var move := InputEventMouseMotion.new()
			move.position = finish
			move.relative = finish - start
			move.button_mask = MOUSE_BUTTON_MASK_LEFT
			root.push_input(move, true)
			await process_frame
			var up := InputEventMouseButton.new()
			up.position = finish
			up.button_index = MOUSE_BUTTON_LEFT
			root.push_input(up, true)
			await process_frame
			check(panel.slider.value > before + .25 and is_equal_approx(panel.trace.offset, panel.slider.value),
				id + " supports mouse dragging at " + str(window_size))

func _initialize() -> void:
	var state:=NightCampaign.new()
	solve_scene(state)
	state.advance()
	for id: String in ["c1_flat.saturday","c1_flat.sunday"]:
		var task: Dictionary=state.task_index[id]
		check(state.choose(id,int(task.answer),task.get("puzzle",{}).get("solution",[])).ok,"Reach the comparison")
	var values:=[0,2,1,-1]
	check(state.store_puzzle_draft("c1_flat.compare",{"values":values,"offset":-.35}),
		"Store tape rows and offset for retry")
	state.record_miss("c1_flat.compare")
	state.record_puzzle_score("c1_flat.compare",4,5)
	for level: int in 3:
		state.hint("c1_flat.compare")
	state.record_miss("c1_flat.compare")
	state.record_miss("c1_flat.compare")
	check(state.answer_available("c1_flat.compare"),"Unlock the separate tape answer offer")
	var saved: Dictionary=state.data.duplicate(true)
	check(state.validate(saved).is_empty(),"Validate an incomplete tape save")
	var restored:=NightCampaign.new()
	check(restored.restore(saved)
		and restored.puzzle_draft("c1_flat.compare").values==values
		and is_equal_approx(float(restored.puzzle_draft("c1_flat.compare").offset),-.35),
		"Restore tape rows and offset")
	check(int(restored.data.misses["c1_flat.compare"])==3
		and int(restored.data.puzzle_scores["c1_flat.compare"].best)==4,
		"Restore wrong-attempt and scoring state")

	var panel:=NightTapeCompare.new()
	root.add_child(panel)
	await process_frame
	var metadata: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(
		"res://assets/audio/effects/morning-tapes.json"))
	var saturday:=load("res://assets/audio/effects/tape-saturday.wav") as AudioStreamWAV
	var sunday:=load("res://assets/audio/effects/tape-sunday.wav") as AudioStreamWAV
	var player:=AudioStreamPlayer.new()
	root.add_child(player)
	var puzzle: Dictionary=restored.task_index["c1_flat.compare"].puzzle
	check(panel.open_task("c1_flat.compare",saturday,sunday,metadata,player,puzzle,
		"Compare","Two mornings","Steve",restored.puzzle_draft("c1_flat.compare")),
		"Open a saved waveform investigation")
	panel.set_hint_label(restored.hint_label("c1_flat.compare"))
	panel.show_answer_offer(restored.answer_available("c1_flat.compare"))
	check(is_equal_approx(panel.slider.value,-.35) and panel.row_choices[0].selected==1
		and panel.row_choices[3].selected==0,"Restore waveform controls")
	check(panel.hint_button.text=="Hint 3 of 3" and panel.answer_button.visible,
		"Restore tape hint level and Show answer availability")
	var tape_result:={"wrong":false,"score":[]}
	panel.wrong_attempt.connect(func(): tape_result.wrong=true)
	panel.attempt_scored.connect(func(right: int,total: int): tape_result.score=[right,total])
	panel.row_choices[3].select(2)
	panel._submit()
	check(tape_result.wrong and tape_result.score==[4,5] and panel.feedback.text.contains("4 of 5"),
		"Wrong tape retry reports a specific score")
	panel.close()
	panel.reset_task()
	check(panel.open_task("c1_flat.compare",saturday,sunday,metadata,player,puzzle,
		"Compare","Two mornings","Steve",restored.puzzle_draft("c1_flat.compare")),
		"Reopen the waveform after returning to the room")
	panel.set_hint_label(restored.hint_label("c1_flat.compare"))
	panel.show_answer_offer(restored.answer_available("c1_flat.compare"))
	check(panel.hint_button.text=="Hint 3 of 3" and panel.answer_button.visible
		and is_equal_approx(panel.slider.value,-.35),
		"Reopen with help controls and saved alignment intact")

	var door: Dictionary = state.task_index["c4_safe.match"].puzzle
	check(panel.open_task("c4_safe.match", load(door.recording_a), load(door.recording_b), {},
		player, door) and not panel.recording.aligned(panel.slider.value),
		"Starting the door comparison leaves the two recordings for the player to align")
	panel._set_offset(panel.recording.expected_offset)
	check(panel.recording.aligned(panel.slider.value), "The two actual door recordings can be aligned")

	await verify_tape_layout(panel, player, state)
	print(JSON.stringify({"checks":checks,"failures":failures}))
	panel.free()
	player.free()
	quit(0 if failures.is_empty() else 1)

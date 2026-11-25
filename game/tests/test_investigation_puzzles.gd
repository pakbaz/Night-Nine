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

	print(JSON.stringify({"checks":checks,"failures":failures}))
	panel.free()
	player.free()
	quit(0 if failures.is_empty() else 1)

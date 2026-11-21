extends Node
## Use actual GUI input to investigate, align, play and record the opening clue.
var game: Node
var checks := 0
var failures: Array[String] = []
var folder := ""

func _ready() -> void:
	_run.call_deferred()

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func frames(count: int = 3) -> void:
	for index: int in count:
		await get_tree().process_frame

func wait_for_approach() -> void:
	var deadline := Time.get_ticks_msec()+20000
	while game.stage.has_method("is_walking") and game.stage.is_walking() and Time.get_ticks_msec()<deadline:
		await get_tree().process_frame

func button(text: String, parent: Node) -> Button:
	for candidate: Node in parent.find_children("*", "Button", true, false):
		if candidate.text == text and candidate.is_visible_in_tree():
			return candidate
	return null

func click(control: Control) -> void:
	if control == null:
		check(false, "Expected visible input control")
		return
	await frames(1)
	var point := control.get_global_transform_with_canvas() * (control.size * 0.5)
	var move := InputEventMouseMotion.new()
	move.position = point
	control.get_viewport().push_input(move, true)
	await frames(1)
	for pressed: bool in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		control.get_viewport().push_input(event, true)
		await frames(1)
	await frames(2)

func key(code: Key, target: Window = null) -> void:
	if target == null:
		target = get_window()
	for pressed: bool in [true, false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.physical_keycode = code
		event.pressed = pressed
		event.window_id = target.get_window_id()
		Input.parse_input_event(event)
		await frames(1)

func capture(name_: String) -> void:
	await get_tree().create_timer(0.2).timeout
	RenderingServer.force_draw(false)
	check(get_viewport().get_texture().get_image().save_png(folder.path_join(name_ + ".png")) == OK, "Capture " + name_)

func _run() -> void:
	Engine.max_fps = 60
	folder = OS.get_environment("NIGHT_NINE_QA_DIR")
	if folder.is_empty():
		folder = ProjectSettings.globalize_path("res://../tmp/qa/tape-compare")
	DirAccess.make_dir_recursive_absolute(folder)
	game.campaign.reset()
	while game.campaign.current().id != "c1_flat":
		var scene: Dictionary = game.campaign.current()
		game.campaign.mark_seen(scene.intro)
		for task: Dictionary in scene.tasks:
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
			game.campaign.mark_seen(task.lines)
		game.campaign.mark_seen(scene.outro)
		game.campaign.advance()
	game.started = true
	game.auto_dialogue = false
	game.menu.hide()
	game._load_stage(true)
	# Chapter cards are timed in story_flow_qa.gd; this check starts at the first line.
	if game.title_card.visible:
		game.title_card.finish_now()
	game._skip_dialogue()
	for task: Dictionary in game.campaign.current().tasks:
		if task.id == "c1_flat.compare":
			break
		game._choose(task.id, int(task.answer))
		if task.id=="c1_flat.saturday":
			while game.dialogue_panel.visible and game.active_line!="c1_flat.in.04":
				game._next_line()
			check(game.speaker.text == "NORA REYES", "Show Nora's apparent identity during the first greeting")
		game._skip_dialogue()
	await frames()
	var compare_task: Dictionary=game.campaign.task_index["c1_flat.compare"]
	var compare_index: int=game.campaign.current().tasks.find(compare_task)
	await click(game.hotspots[compare_index])
	await wait_for_approach()
	var panel: NightTapeCompare = game.tape_compare
	check(panel.visible and not game.root.get_node("InteractionPanel").visible, "Open the waveform workbench from the scene hotspot")
	var active_take: Dictionary=game._recording_for("recording.greeting").take
	var master:=load(str(active_take.file)) as AudioStreamWAV
	check(master!=null and panel.recording.rate==master.mix_rate and panel.recording.pcm==master.data,"Use every PCM sample of the active greeting")
	await click(button("Record finding", panel))
	check("c1_flat.compare" not in game.campaign.data.done, "An empty finding does not solve the clue")
	panel.conclusion.grab_focus()
	for index: int in 3:
		await key(KEY_RIGHT)
	check(panel.conclusion.selected == 3, "Choose the conclusion by keyboard")
	await click(button("Record finding", panel))
	check("c1_flat.compare" not in game.campaign.data.done, "The conclusion alone cannot bypass alignment")
	await capture("unaligned")
	var trace := panel.trace
	var start := trace.get_global_transform_with_canvas() * Vector2(trace.size.x * 0.6, 210)
	var local_delta := -0.35 / (panel.recording.timeline_end - panel.recording.timeline_start) * (trace.size.x - NightTapeTrace.LEFT - NightTapeTrace.RIGHT)
	var finish := trace.get_global_transform_with_canvas() * Vector2(trace.size.x * 0.6 + local_delta, 210)
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	down.position = start
	get_viewport().push_input(down, true)
	await frames(1)
	var move := InputEventMouseMotion.new()
	move.position = finish
	move.relative = finish - start
	move.button_mask = MOUSE_BUTTON_MASK_LEFT
	get_viewport().push_input(move, true)
	await frames(1)
	down = InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.position = finish
	get_viewport().push_input(down, true)
	await frames()
	check(is_equal_approx(panel.slider.value, -0.35), "Dragging Sunday aligns the actual waveform")
	panel.slider.grab_focus()
	await key(KEY_LEFT)
	check(is_equal_approx(panel.slider.value, -0.36), "Keyboard can fine-adjust the offset")
	await key(KEY_RIGHT)
	check(is_equal_approx(panel.slider.value, -0.35), "Keyboard adjustment returns to the shared onset")
	await click(button("Play together", panel))
	check(game.voice.playing and game.voice.stream == panel.active_stream, "Play the actual aligned recordings through the normal game mixer")
	var deadline := Time.get_ticks_msec() + 1500
	while game.voice.get_playback_position() <= 0.05 and Time.get_ticks_msec() < deadline:
		await get_tree().create_timer(0.05).timeout
	check(game.voice.get_playback_position() > 0.05, "Mixed evidence audio advances")
	await key(KEY_ESCAPE)
	check(game.menu.visible and panel.paused and game.voice.stream_paused, "Pause evidence playback and controls through the menu")
	var old_offset := panel.slider.value
	panel._set_offset(0)
	check(panel.slider.value == old_offset, "Paused controls preserve the investigation position")
	await click(button("Continue", game.menu))
	check(panel.visible and not panel.paused and not game.voice.stream_paused, "Continue resumes the same comparison")
	await click(button("Notebook", game.root))
	check(game.journal.visible and panel.paused, "Notebook pauses the evidence view")
	check(not game.casebook.transcript.contains("Iris:") and game.casebook.transcript.contains("Nora Reyes:"), "Notebook retains the apparent name in earlier dialogue")
	await key(KEY_ESCAPE)
	await click(button("Stop", panel))
	check(not game.voice.playing, "Stop releases the evidence playback")
	panel.conclusion.select(1)
	await click(button("Record finding", panel))
	check("c1_flat.compare" not in game.campaign.data.done, "Aligned words alone are not the correct conclusion")
	await click(button("Hint 1 of 3", panel))
	check(not panel.feedback.text.contains("0.35"), "First hint guides observation without the answer")
	await click(button("Hint 2 of 3", panel))
	check(not panel.feedback.text.contains("0.35"), "Second hint supplies direction without the exact offset")
	await click(button("Hint 3 of 3", panel))
	check(not panel.feedback.text.begins_with("Answer:"), "Final hint still guides without revealing the answer")
	for miss: int in 2:
		panel.conclusion.select(1)
		await click(button("Record finding",panel))
	var show_answer:=button("Show answer",panel)
	check(is_instance_valid(show_answer) and show_answer.visible,"Two misses after hint three offer the separate answer")
	await click(show_answer)
	await key(KEY_ENTER,game.answer_confirmation)
	check(panel.feedback.text.begins_with("Answer:"),"Confirmed answer reveal is separate from hints")
	await click(button("Back to the room", panel))
	check(not panel.visible and not game.voice.playing, "Back closes the workbench and stops its audio")
	await frames()
	await click(game.hotspots[compare_index])
	await wait_for_approach()
	check(is_equal_approx(panel.slider.value, -0.35), "Reopening preserves the current-session offset")
	var overlay: CheckButton
	for control: BaseButton in panel.buttons:
		if control is CheckButton:
			overlay = control
	await click(overlay)
	check(panel.trace.overlay, "Overlay compares both visible traces")
	await capture("aligned-overlay")
	get_window().size = Vector2i(960, 600)
	await frames(8)
	var room: Rect2 = game.root.get_global_rect()
	var back:=button("Back to the room",panel)
	(panel.get_child(0) as ScrollContainer).ensure_control_visible(back)
	await frames(3)
	check(room.encloses(back.get_global_rect()), "Keep the final controls within the 960 by 600 window")
	await capture("small-window")
	panel.conclusion.select(3)
	await click(button("Record finding", panel))
	check("c1_flat.compare" in game.campaign.data.done and not panel.visible, "Record the solved finding through the real campaign state")
	check(game.dialogue_panel.visible and game.active_line == "c1_flat.compare.01", "Play Steve's recorded discovery")
	game._skip_dialogue()
	game._save("tape-solved")
	check(game._load("tape-solved") and "c1_flat.compare" in game.campaign.data.done, "Save and load preserve the completed comparison")
	check(not panel.visible, "Loading clears the transient workbench")
	var report := {"checks": checks, "failures": failures, "input": "viewport mouse drag and keyboard events", "physical_audio_output_verified": false}
	var file := FileAccess.open(folder.path_join("tape-results.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print(JSON.stringify(report))
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

extends SceneTree

func _initialize() -> void:
	_capture.call_deferred()

func _capture() -> void:
	var folder := OS.get_environment("NIGHT_NINE_QA_DIR")
	if folder.is_empty():
		folder = ProjectSettings.globalize_path("res://../tmp/morning-tapes")
	DirAccess.make_dir_recursive_absolute(folder)
	root.size = Vector2i(1600, 1000)
	var backdrop := ColorRect.new()
	backdrop.color = Color("08171d")
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(backdrop)
	var player := AudioStreamPlayer.new()
	root.add_child(player)
	var panel := NightTapeCompare.new()
	root.add_child(panel)
	var content: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	var task: Dictionary
	for scene: Dictionary in content.scenes:
		if scene.id != "c1_flat":
			continue
		for candidate: Dictionary in scene.tasks:
			if candidate.id == "c1_flat.compare":
				task = candidate
				break
	var metadata: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string(str(task.puzzle.segments)))
	var saturday := load(str(task.puzzle.recording_a)) as AudioStreamWAV
	var sunday := load(str(task.puzzle.recording_b)) as AudioStreamWAV
	if not panel.open_task(task.id, saturday, sunday, metadata, player, task.puzzle,
			task.goal, task.background, "Steve"):
		push_error(panel.recording.error)
		quit(1)
		return
	panel._set_offset(-0.35)
	for index: int in panel.row_choices.size():
		panel.row_choices[index].select(int(task.puzzle.solution[index]) + 1)
	for control: BaseButton in panel.buttons:
		if control is CheckButton:
			(control as CheckButton).button_pressed = true
	for frame: int in 8:
		await process_frame
	(panel.get_child(0) as ScrollContainer).scroll_vertical = 0
	for frame: int in 4:
		await process_frame
	RenderingServer.force_draw(false)
	var path := folder.path_join("morning-tape-comparison.png")
	var result := root.get_texture().get_image().save_png(path)
	print(JSON.stringify({"screenshot": path, "result": result}))
	quit(0 if result == OK else 1)

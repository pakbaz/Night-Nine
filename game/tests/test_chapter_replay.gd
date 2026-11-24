extends SceneTree

var checks := 0
var failures: Array[String] = []

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)

func _solve_scene(game: Node) -> bool:
	while not game.campaign.can_leave():
		var moved := false
		for task: Dictionary in game.campaign.current().tasks:
			if not game.campaign.available(task.id):
				continue
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			var solution: Array = task.get("puzzle", {}).get("solution", []).duplicate()
			for index: int in solution.size():
				solution[index] = int(solution[index])
			moved = game.campaign.choose(task.id, int(task.answer), solution).ok or moved
		if not moved:
			return false
	return true

func _chapter_button(game: Node, scene_index: int) -> Button:
	return game.chapter_panel.find_child("Chapter_%02d" % scene_index, true, false) as Button

func _run() -> void:
	var game: Node = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	await process_frame
	game._new_game()
	check(game.saves.read_slot("chapter-00").get("ok", false), "Starting a game unlocks the prologue")
	var chapter_two := -1
	for entry: Dictionary in game.campaign.chapter_list():
		if entry.chapter == "Chapter 2":
			chapter_two = int(entry.scene)
			break
	while int(game.campaign.data.scene) < chapter_two:
		check(_solve_scene(game), "The main campaign can finish the current chapter scene")
		game.campaign.mark_seen(game.campaign.current().get("context", []) + game.campaign.current().intro)
		check(game.campaign.advance(), "The main campaign reaches the next scene")
	game._record_reached_chapters(game.campaign.data)
	game._save("autosave")
	var main_state: Dictionary = game.saves.read_slot("autosave").state
	var before_replay_file := FileAccess.get_file_as_string(game.save_root.path_join("autosave.json"))
	check(int(main_state.scene) == chapter_two, "The autosave remains at the latest reached chapter")
	game.menu.show()
	game._pause_audio(true)
	# A line of dialogue in progress brings its panel to the front.
	game.dialogue_panel.move_to_front()
	game.menu_chapters.pressed.emit()
	check(game.dialogue_panel.get_index() < game.chapter_backdrop.get_index(), "Dialogue stays under the chapter art")
	check(game.chapter_panel.visible and game.chapter_buttons.size() == 15, "Play Chapters lists every authored chapter")
	var chapter_rect: Rect2 = game.chapter_panel.get_global_rect()
	var viewport_rect: Rect2 = root.get_visible_rect()
	check(chapter_rect.position.x >= 0.0 and chapter_rect.position.y >= 0.0 \
			and chapter_rect.end.x <= viewport_rect.end.x and chapter_rect.end.y <= viewport_rect.end.y,
		"Chapter selector stays inside the viewport")
	var prologue: Button = _chapter_button(game, 0)
	var chapter_one: Button = _chapter_button(game, 1)
	var chapter_one_next: Button = _chapter_button(game, chapter_two)
	var future: Button = _chapter_button(game, chapter_two + 2)
	check(prologue != null and not prologue.disabled and chapter_one != null and not chapter_one.disabled,
		"Reached chapters are available for replay")
	check(chapter_one_next != null and not chapter_one_next.disabled, "A chapter unlocks when play reaches it")
	check(future != null and future.disabled, "Unreached chapters remain locked")
	await process_frame
	check(game.menu.visible and not game.menu_box.visible and game.chapter_backdrop.visible,
		"Play Chapters opens inside the menu panel, over the chapter art")
	check(game.chapter_scroll.get_v_scroll_bar().visible, "The chapter list scrolls with a visible scrollbar")
	var picture := chapter_one.find_child("Picture", true, false) as TextureRect
	check(picture != null and picture.texture != null and picture.texture.resource_path.ends_with("chapters/c1_flat.webp"),
		"Reached chapters show their opening painting")
	var hidden_title := future.find_child("Title", true, false) as Label
	check(future.find_child("Lock", true, false) != null and future.find_child("Picture", true, false) == null
		and hidden_title != null and hidden_title.text == "Locked", "Locked chapters keep their title and painting hidden")
	check(chapter_one_next.has_focus() and game.chapter_title.text == "The Aquarium Is Closed"
		and game.chapter_art.texture != null and game.chapter_art.texture.resource_path.ends_with("rooms/c2_aquarium.webp"),
		"The latest reached chapter is selected and shown over its painting")
	chapter_one.mouse_entered.emit()
	check(game.chapter_title.text == "Good Morning, Sleepyhead" and game.chapter_kicker.text == "Chapter 1",
		"Pointing at a chapter introduces it")
	game.chapter_return.pressed.emit()
	check(not game.chapter_panel.visible and not game.chapter_backdrop.visible and game.menu_box.visible and game.menu.visible,
		"The chapter Return button restores the main menu")
	game.menu_chapters.pressed.emit()
	chapter_one = _chapter_button(game, 1)
	var latest_task: Dictionary = game.campaign.current().tasks.front()
	game.campaign.hint(str(latest_task.id))
	chapter_one.pressed.emit()
	check(game.replaying_chapter and game.campaign.current().id == "c1_flat",
		"Playing Chapter 1 opens its first scene")
	var main_file := FileAccess.get_file_as_string(game.save_root.path_join("autosave.json"))
	check(main_file != before_replay_file and int(game.saves.read_slot("autosave").state.hints[latest_task.id]) == 1,
		"Starting replay preserves the latest in-memory main progress")
	game._save("autosave")
	check(FileAccess.get_file_as_string(game.save_root.path_join("autosave.json")) == main_file,
		"Chapter replay never overwrites the main autosave")
	game._return_from_chapter_replay()
	check(not game.replaying_chapter and int(game.campaign.data.scene) == chapter_two,
		"Returning from replay restores Continue to the latest chapter")
	check(int(game.campaign.data.hints.get(latest_task.id, 0)) == 1,
		"Returning from replay restores unsaved main progress")
	game._play_chapter(1)
	var second_main_file := FileAccess.get_file_as_string(game.save_root.path_join("autosave.json"))
	while str(game.campaign.current().chapter) == "Chapter 1":
		check(_solve_scene(game), "Chapter replay can finish each scene in the chapter")
		var next_index := int(game.campaign.data.scene) + 1
		if next_index >= game.campaign.content.scenes.size() \
				or str(game.campaign.content.scenes[next_index].chapter) != "Chapter 1":
			break
		check(game.campaign.advance(), "Chapter replay advances between scenes in the chapter")
	game._enter_next_scene()
	check(not game.replaying_chapter and int(game.campaign.data.scene) == chapter_two,
		"Finishing a chapter replay returns to the main saved chapter")
	check(game.menu.visible, "The saved game menu is ready after replay")
	check(FileAccess.get_file_as_string(game.save_root.path_join("autosave.json")) == second_main_file,
		"Completing a replay preserves the main save byte-for-byte")
	var chapter_count: int = game.chapter_buttons.size()
	game.shutdown_audio()
	game.queue_free()
	await process_frame
	var resumed: Node = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(resumed)
	await process_frame
	resumed._continue()
	check(resumed.started and int(resumed.campaign.data.scene) == chapter_two \
			and int(resumed.campaign.data.hints.get(latest_task.id, 0)) == 1,
		"Continue loads the latest main chapter after a replay")
	check(resumed.saves.read_slot("chapter-01").get("ok", false),
		"Chapter replay unlocks persist across a restart")
	var output_dir := OS.get_environment("NIGHT_NINE_QA_DIR")
	if output_dir.is_empty():
		output_dir = ProjectSettings.globalize_path("res://../tmp/qa")
	DirAccess.make_dir_recursive_absolute(output_dir)
	var result := {"checks": checks, "failures": failures, "chapters": chapter_count}
	var output := FileAccess.open(output_dir.path_join("chapter-replay-results.json"), FileAccess.WRITE)
	output.store_string(JSON.stringify(result, "\t"))
	output.close()
	print(JSON.stringify(result))
	resumed.shutdown_audio()
	resumed.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
	_run.call_deferred()

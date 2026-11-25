extends SceneTree

var checks := 0
var failures: Array[String] = []
var game: Node

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)

func frames(count: int = 3) -> void:
	for index: int in count:
		await process_frame

func scene_index(id: String) -> int:
	for index: int in game.campaign.content.scenes.size():
		if game.campaign.content.scenes[index].id == id:
			return index
	return -1

func enter_scene(id: String, done: Array = [], seen: Array = [], play_intro: bool = false) -> void:
	game.campaign.reset()
	game.campaign.data.scene = scene_index(id)
	game.campaign.data.scene_id = id
	game.campaign.data.chapter = game.campaign.current().chapter
	game.campaign.data.done = done.duplicate()
	game.campaign.data.seen = seen.duplicate()
	game.campaign.data.actor = game.campaign.current().actors[0]
	game.started = true
	game.menu.hide()
	game._load_stage(play_intro)
	if game.title_card.visible:
		game.title_card.finish_now()
	await frames(4)

func theory_ids(state: NightCampaign) -> Array[String]:
	var ids: Array[String] = []
	for case_id: String in state.content.get("notebook_cases", {}):
		for theory: Dictionary in state.available_theories(case_id, state.data.done):
			ids.append(str(theory.id))
	return ids

func reach_scene(id: String) -> NightCampaign:
	var state := NightCampaign.new()
	while state.current().id != id:
		state.mark_seen(state.current().get("context", []) + state.current().get("intro", []))
		while not state.can_leave():
			var moved := false
			for task: Dictionary in state.current().tasks:
				if not state.available(task.id):
					continue
				if not task.actor.is_empty():
					state.switch_actor(task.actor)
				var result: Dictionary = state.choose(task.id, int(task.answer),
					task.get("puzzle", {}).get("solution", []))
				if result.get("ok", false):
					state.mark_seen(task.get("lead", []) + task.lines)
					if not str(task.get("finding", "")).is_empty():
						state.mark_seen([task.finding])
					moved = true
			if not moved:
				break
		state.mark_seen(state.current().get("recap", []) + state.current().get("outro", []))
		if not state.advance():
			break
	return state

func _run() -> void:
	game = preload("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	await frames(5)
	game.auto_dialogue = false
	await enter_scene("c8_lab")
	game._skip_dialogue()
	game._speak(["c8_lab.notebook.find"], Callable())
	await frames(5)
	check(game.words.get_content_height() <= game.words.size.y + 1
		and game.dialogue_panel.get_global_rect().end.y <= game.root.size.y,
		"The full lab finding and Continue button fit in the staged caption")
	game._skip_dialogue()

	await enter_scene("c1_pier", [], [], true)
	var arrival: Dictionary = game.campaign.current()
	check(game.active_line == arrival.context[0], "A new scene speaks context before its intro")
	game._skip_dialogue()

	await enter_scene("c1_pier", [], [arrival.context[0]], false)
	check(game.active_line == arrival.context[1], "A resumed scene finishes context before its intro")
	game._skip_dialogue()

	await enter_scene("c1_escape")
	var escape: Dictionary = game.campaign.current()
	check(escape.intro.is_empty() and game._untouched_scene(), "A context-only scene can still be untouched")
	check(game.active_line == escape.context[0], "A context-only scene resumes at its first unheard line")
	game._skip_dialogue()

	await enter_scene("c1_escape", ["c1_escape.order"], escape.context)
	check(game.objective.text == escape.objective_steps[0], "The objective advances after its first step is finished")

	var flat: Dictionary = game.campaign.content.scenes[scene_index("c1_flat")]
	var saturday_seen: Array = flat.context + flat.intro
	var saturday_done: Dictionary = game.campaign.task_index["c1_flat.saturday"]
	saturday_seen.append_array(saturday_done.lines)
	if not str(saturday_done.finding).is_empty():
		saturday_seen.append(saturday_done.finding)
	await enter_scene("c1_flat", ["c1_flat.saturday"], saturday_seen)
	var before_sunday := theory_ids(game.campaign)
	var sunday: Dictionary = game.campaign.task_index["c1_flat.sunday"]
	game.replaying_chapter = true
	game._choose(sunday.id, int(sunday.answer), sunday.get("puzzle", {}).get("solution", []))
	game.replaying_chapter = false
	check(theory_ids(game.campaign) == before_sunday, "The second greeting does not unlock a theory by itself")
	check(not game.status.text.to_lower().contains("notebook"), "Do not nudge the notebook before a theory unlocks")
	game._skip_dialogue()

	var compare: Dictionary = game.campaign.task_index["c1_flat.compare"]
	for level: int in 3:
		game.campaign.hint(compare.id)
	game.campaign.record_miss(compare.id)
	game.campaign.record_miss(compare.id)
	game._open_task(compare.id)
	check(game.tape_compare.visible and game.tape_compare.hint_button.text == "Hint 3 of 3"
		and game.tape_compare.answer_button.visible, "Opening the actual tape workbench restores earned help")
	game.tape_compare.close()
	game.replaying_chapter = true
	game._choose(compare.id, int(compare.answer), compare.get("puzzle", {}).get("solution", []))
	game.replaying_chapter = false
	check(theory_ids(game.campaign).size() > before_sunday.size(), "The tape comparison actually unlocks theories")
	check(game.status.text.to_lower().contains("notebook"),
		"Nudge the notebook when a theory actually unlocks: " + game.status.text)
	game._skip_dialogue()

	game.casebook.open_book(game.campaign, "", "")
	game.casebook.selected_case = "greeting"
	game.casebook._draw_page()
	var grief := game.casebook.find_child("grief_struck", true, false) as Button
	check(is_instance_valid(grief), "The unlocked grief theory can be crossed out")
	if grief:
		grief.set_pressed_no_signal(true)
		grief.pressed.emit()
		await frames(2)
		var reaction := game.casebook.find_child("Reaction_grief", true, false) as Label
		check(is_instance_valid(reaction) and reaction.visible and not reaction.text.is_empty(),
			"A meaningful cross-out adds a short unvoiced notebook reaction")

	var early := reach_scene("c3_house")
	while "c3_house.rules" not in early.data.done:
		for task: Dictionary in early.current().tasks:
			if early.available(task.id):
				if not task.actor.is_empty():
					early.switch_actor(task.actor)
				var result: Dictionary = early.choose(task.id, int(task.answer),
					task.get("puzzle", {}).get("solution", []))
				if result.get("ok", false):
					early.mark_seen(task.get("lead", []) + task.lines)
					if not str(task.get("finding", "")).is_empty():
						early.mark_seen([task.finding])
	game.casebook.open_book(early, "", "")
	game.casebook.selected_case = "penhallow"
	game.casebook._draw_page()
	var agnes := game.casebook.find_child("just_agnes_struck", true, false) as Button
	check(is_instance_valid(agnes), "The early Agnes theory can be crossed out")
	if agnes:
		agnes.set_pressed_no_signal(true)
		agnes.pressed.emit()
		await frames(2)
	var saved: Dictionary = early.data.duplicate(true)
	var restored := NightCampaign.new()
	check(restored.restore(saved), "An early notebook flag survives save validation")
	check(bool(restored.data.notebook.get("flags", {}).get("just_agnes_early", false)),
		"Crossing out just Agnes early persists across reload")
	restored.data.scene = scene_index("c10_town")
	restored.data.scene_id = "c10_town"
	game.casebook.open_book(restored, "", "")
	game.casebook.selected_case = "penhallow"
	game.casebook._draw_page()
	var acknowledgment := game.casebook.find_child("AgnesAcknowledgment", true, false) as Label
	check(is_instance_valid(acknowledgment) and acknowledgment.visible,
		"Agnes gets an optional unvoiced acknowledgment in c10_town after the early flag")

	print(JSON.stringify({"checks": checks, "failures": failures}))
	game.queue_free()
	await frames(6)
	quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
	_run.call_deferred()

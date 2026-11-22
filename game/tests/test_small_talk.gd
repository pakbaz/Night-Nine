extends SceneTree
var game: Node
var failures: Array[String] = []
var observations: Array[String] = []
var checks := 0

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, description: String) -> void:
	checks += 1
	if ok:
		observations.append(description)
	else:
		failures.append(description)
		push_error(description)

func click(point: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = point
	root.push_input(motion, true)
	for pressed: bool in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed else 0
		event.pressed = pressed
		root.push_input(event, true)

func reach_flat() -> void:
	while game.campaign.current().id != "c1_flat":
		var scene: Dictionary = game.campaign.current()
		game.campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
			game.campaign.mark_seen(task.lines)
			if not str(task.get("finding", "")).is_empty():
				game.campaign.mark_seen([task.finding])
		game.campaign.mark_seen(scene.outro)
		if not game.campaign.advance():
			check(false, "Reach the Chapter 1 flat")
			return

## The upper middle of a painted portrait: the head and shoulders, never a transparent edge.
func portrait_point(person: Node2D) -> Vector2:
	var body: Sprite2D = person.body
	var rect: Rect2 = body.get_rect()
	return body.get_global_transform_with_canvas() * Vector2(rect.get_center().x, rect.position.y + rect.size.y * .22)

func open_painted(scene_id: String, speaker: String, shown: String) -> void:
	game.root.get_node("InteractionPanel").hide()
	var person: Node2D = game.stage.actors.get(speaker)
	check(person != null and person.is_visible_in_tree(), "Show " + shown + " in " + scene_id)
	if person == null:
		return
	click(portrait_point(person))
	await process_frame
	check(game.root.get_node("InteractionPanel").visible and game.interaction.get_child(0).text == shown,
		"Clicking " + shown + "'s painted figure in " + scene_id + " opens their talk panel")
	game.root.get_node("InteractionPanel").hide()

func enter(scene_id: String) -> void:
	while game.campaign.current().id != scene_id:
		var scene: Dictionary = game.campaign.current()
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		game.campaign.advance()
	game.campaign.mark_seen(game.campaign.current().get("context", []) + game.campaign.current().intro)
	game._load_stage(false)
	for i: int in 4:
		await process_frame
	game._process(.001)

func button_with_text(text: String) -> Button:
	for button: Button in game.interaction.find_children("*", "Button", true, false):
		if button.text == text:
			return button
	return null

func run() -> void:
	var output := OS.get_environment("NIGHT_NINE_QA_DIR")
	if output.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set isolated QA and save directories.")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output)
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue = false
	game.started = true
	game.menu.hide()
	await enter("p_bay")
	await open_painted("p_bay", "helen", "Helen Mercer")
	game.campaign.reset()
	reach_flat()
	game.campaign.mark_seen(game.campaign.current().get("context", []) + game.campaign.current().intro)
	var topic: Dictionary = game.campaign.available_talk("iris")[0]
	game.started = true
	game.menu.hide()
	game._load_stage(false)
	await process_frame
	await process_frame
	game._process(.001)
	check(game.people_buttons.has("iris"), "Nora has a portrait button")
	var portrait: Button = game.people_buttons.get("iris")
	check(portrait != null and game.people_bar.visible and portrait.visible and portrait.icon != null,
		"The people bar shows Nora's face")
	check(portrait.tooltip_text == "Nora Reyes", "The portrait tooltip uses Nora's display name")
	check(portrait.has_node("Unheard"), "An unheard marker appears on Nora's portrait")
	portrait.pressed.emit()
	check(game.root.get_node("InteractionPanel").visible, "Nora's portrait opens the interaction panel")
	check(game.interaction.get_child(0).text == "Nora Reyes", "The talk panel is headed with Nora's name")
	check(button_with_text(topic.topic) != null, "The talk panel lists the available topic")
	button_with_text(topic.topic).pressed.emit()
	check(game.dialogue_panel.visible and game.active_line == topic.lines[0], "Picking a topic starts its first dialogue line")
	check(game.words.text.contains(str(game.campaign.content.lines[topic.lines[0]].text)), "The talk line appears in the dialogue panel")
	game._process(.001)
	check(not game.people_bar.visible, "The people bar hides during dialogue")
	while game.dialogue_panel.visible:
		game._next_line()
	check(topic.lines.all(func(id: String): return id in game.campaign.data.seen), "Talk lines are marked seen")
	check(game.campaign.talk_heard(topic), "The completed topic is heard")
	check(game.root.get_node("InteractionPanel").visible, "The panel reopens while Nora has unheard topics")
	var heard_button := button_with_text("✓ " + str(topic.topic))
	check(heard_button != null and heard_button.modulate == Color("8aa498"),
		"Heard topics stay replayable, muted, and show a check")
	game.root.get_node("InteractionPanel").hide()
	game._open_objects()
	var people_entry := button_with_text("Talk to Nora Reyes")
	check(people_entry != null and people_entry.focus_mode == Control.FOCUS_ALL,
		"The Objects list has a keyboard-accessible People entry")
	game.root.get_node("InteractionPanel").hide()
	var iris_body: Node2D = game.stage.floor_stage.bodies.iris.body
	click(game.stage.distant.to_global(iris_body.position))
	check(game.root.get_node("InteractionPanel").visible and game.interaction.get_child(0).text == "Nora Reyes",
		"Clicking Nora's walking figure opens the same talk panel")
	await enter("c1_dinner")
	await open_painted("c1_dinner", "carmen", "Carmen Reyes")
	var receipt := FileAccess.open(output.path_join("small-talk.json"), FileAccess.WRITE)
	receipt.store_string(JSON.stringify({"checks":checks,"observations":observations,"failures":failures}, "\t") + "\n")
	receipt.close()
	print("Small talk checks: ", checks, " failures: ", failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

extends SceneTree
var game: Node
var failures: Array[String] = []
var observations: Array[String] = []
var checks := 0
var tested := {}
var channels := {}

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, description: String) -> void:
	checks += 1
	if ok:
		observations.append(description)
	else:
		failures.append(description)
		push_error(description)

func hover(point: Vector2) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = point
	root.push_input(motion, true)

func click(point: Vector2) -> void:
	hover(point)
	for pressed: bool in [true, false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed else 0
		event.pressed = pressed
		root.push_input(event, true)

func key(code: Key) -> void:
	for down: bool in [true,false]:
		var event := InputEventKey.new()
		event.keycode = code
		event.pressed = down
		root.push_input(event,true)

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

func click_person(id: String) -> bool:
	var sprite: Sprite2D
	var stage: Node = game.stage
	var samples: Array[Vector2] = []
	if stage.get("talk_figures") is Dictionary and stage.talk_figures.has(id):
		sprite = stage.talk_figures[id]
	elif stage.get("floor_stage") and stage.floor_stage.visible and stage.floor_stage.bodies.has(id):
		sprite = stage.floor_stage.bodies[id].sprite
	elif stage.painted_people.has(id):
		# Actual head/torso coordinates read from the paintings, not from hit polygons.
		var marks := {
			"general_us":Vector2(.12,.43),"general_cn":Vector2(.887,.433),
			"lyle":Vector2(.477,.416),"dale":Vector2(.379,.43),
			"mateo":Vector2(.09,.42),"luis":Vector2(.21,.38),
			"iris":Vector2(.48,.38),"carmen":Vector2(.67,.30),
			"rafa":Vector2(.83,.21),"tomas":Vector2(.89,.40),
		}
		var mark: Vector2 = marks[id]
		samples.append(stage.distant.to_global(mark*stage.ART))
	elif stage.actors.has(id):
		sprite = stage.actors[id].body
	if sprite and sprite.is_visible_in_tree():
		var rect := sprite.get_rect()
		for y: float in [.20,.34,.12,.5,.68,.82]:
			for x: float in [.50,.44,.56,.39,.61]:
				var local := rect.position + rect.size * Vector2(x,y)
				if sprite.is_pixel_opaque(local):
					samples.append(sprite.to_global(local))
	var shown: String = game._speaker_name(id)
	for point: Vector2 in samples:
		hover(point)
		if root.gui_get_hovered_control() != game.person_target or game.person_target.get_tooltip(point) != "Talk to "+shown:
			continue
		click(point)
		return game.root.get_node("InteractionPanel").visible and game.interaction.get_child(0).text == shown \
			and button_with_text(game.campaign.available_talk(id)[0].topic) != null
	return false

func check_current_contacts() -> void:
	var scene_id: String = game.campaign.current().id
	for topic: Dictionary in game.campaign.available_talk():
		var id: String = topic.speaker
		var pair := scene_id + ":" + id
		if tested.has(pair) or channels.has(pair):
			continue
		var channel: String = game.stage.people.get("remote",{}).get(id,"")
		if not channel.is_empty():
			key(KEY_I)
			var entry := button_with_text(channel + ": " + game._speaker_name(id))
			check(entry != null and not game.stage.talk_body_visible(id), "Remote only: "+pair)
			if entry:
				entry.grab_focus()
				key(KEY_ENTER)
				check(game.interaction.get_child(0).text == game._speaker_name(id), "Contact via "+channel+": "+pair)
			channels[pair] = true
		else:
			var ok := click_person(id)
			tested[pair] = ok
			check(ok, "Hover and click in-scene figure: "+pair)
		game.root.get_node("InteractionPanel").hide()
		game._process(.001)

func coverage() -> void:
	game.campaign.reset()
	for scene: Dictionary in game.campaign.content.scenes:
		await enter(scene.id)
		if scene.id == "c9_wake":
			check(not game.stage.talk_body_visible("frank") and not game.stage.talk_body_visible("helen"),
				"Sleeping parents are not standing talk targets")
		if scene.id == "c7_gate":
			check(not game.stage.talk_figures.shaw.is_visible_in_tree(), "Do not show Shaw before the truck introduction")
		await check_current_contacts()
		if DisplayServer.get_name() != "headless" and scene.id in ["c1_pier","c1_dinner","i2_nora","epilogue"]:
			hover(Vector2(4,4))
			game.stage._process(1.0)
			await process_frame
			await process_frame
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png(OS.get_environment("NIGHT_NINE_QA_DIR").path_join(scene.id+".png"))
		for task: Dictionary in scene.tasks:
			game.campaign.mark_seen(task.get("lead",[]))
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[]))
			game.campaign.mark_seen(task.lines)
			game._refresh()
			game._process(.001)
			if task.id == "c2_ship.command":
				check(not game.stage.talk_body_visible("iris") and not game.stage.talk_body_visible("lyle_copy"),
					"The escorted copies cannot be clicked after dismissal")
			if task.id == "postcredits.answer":
				check(game.stage.in_cutaway() and not game.stage.talk_body_visible("shaw"), "No night-shift figures on the dawn cutaway")
			await check_current_contacts()
		var expected := {}
		for topic: Dictionary in scene.get("talk",[]):
			expected[scene.id + ":" + topic.speaker] = true
		for pair: String in expected:
			check(tested.has(pair) or channels.has(pair), "Reach the authored contact: "+pair)

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
	var boat_shelf: Vector2 = game.stage.props.to_global(Vector2(470.0/711*1600,310.0/400*900))
	hover(boat_shelf)
	check(game.stage.actors.helen.hit(boat_shelf) and root.gui_get_hovered_control() != game.person_target,
		"Helen cannot be clicked through the solid foreground shelf")
	check(click_person("helen"), "Helen's seated figure on the boat opens her topics")
	game.root.get_node("InteractionPanel").hide()
	check(not game.root.has_node("PeopleBar"), "No fixed portrait strip covers the scene")
	await enter("c1_pier")
	game._process(.001)
	check(not game.hotspots[1].visible, "Deputy Lyle has no separate floating object dot on the pier")
	for id: String in ["pell","lyle_copy"]:
		game._process(.001)
		var name_in_scene: String = game._speaker_name(id)
		var mark := Vector2(.56,.57) if id=="lyle_copy" else Vector2(.82,.68)
		click(game.stage.distant.to_global(mark * Vector2(1600,900)))
		await process_frame
		check(game.root.get_node("InteractionPanel").visible and game.interaction.get_child(0).text == name_in_scene,
			"The Chapter 1 pier has a clickable " + name_in_scene)
		if id == "lyle_copy":
			var lyle_lead := button_with_text("Deputy Lyle")
			var lyle_talk := button_with_text("The boys’ game")
			check(lyle_lead != null and lyle_talk != null,
				"Clicking Lyle Boone merges his Deputy Lyle lead with his small talk")
			# Opening the Deputy Lyle lead shows Lyle (not Agnes) alongside the dialogue prompt.
			game._inspect_on_arrival("c1_pier.door")
			await process_frame
			while game.dialogue_panel.visible:
				check(not (game.stage.actors.has("agnes") and game.stage.actors.agnes.visible),
					"Agnes does not appear during Lyle Boone's spoken lines")
				game._next_line()
				await process_frame
			check(game.selected_task == "c1_pier.door" and game.root.get_node("InteractionPanel").visible,
				"Deputy Lyle's lead opens its prompt directly after his lines")
			check(not (game.stage.actors.has("agnes") and game.stage.actors.agnes.visible),
				"Agnes does not appear on the left during Deputy Lyle's dialogue prompt")
			check(game.stage.actors.has("lyle_copy") and game.stage.actors.lyle_copy.visible,
				"Lyle Boone stays on screen during his own dialogue prompt")
			game.stage.set_focus(-1)
		game.root.get_node("InteractionPanel").hide()
	game._process(.001)
	var pier_object: Button = game.hotspots[0]
	click(pier_object.get_global_rect().get_center())
	check(game.stage.floor_stage.pending == "c1_pier.whistle", "Pier object still starts its investigation from the marker")
	await enter("c1_dinner")
	game._process(.001)
	check(game.stage.talk_figures.is_empty(), "Dinner at La Marea uses the painted family instead of pasted sprites")
	check(not (game.stage.actors.has("carmen") and game.stage.actors.carmen.visible),
		"Carmen's portrait does not float over the painted family dinner")
	await enter("c3_house")
	game._process(.001)
	var carmen_sprite: Sprite2D = game.stage.talk_figures.get("carmen")
	check(carmen_sprite != null, "Carmen stands in June Calder's house")
	if carmen_sprite != null:
		var foot_x: float = carmen_sprite.position.x / game.stage.ART.x
		var foot_y: float = carmen_sprite.position.y / game.stage.ART.y
		# The writing desk and its front-right leg extend to x=0.36; keep Carmen's shoes well clear on open floor.
		check(foot_x >= 0.43 and foot_y <= 0.69, "Carmen stands on open floor clear of the writing desk leg (%.3f, %.3f)" % [foot_x, foot_y])
		var img: Image = carmen_sprite.texture.get_image()
		var puddle := 0
		for y: int in range(img.get_height() - 32, img.get_height()):
			for x: int in img.get_width():
				var c := img.get_pixel(x, y)
				var lum := 0.299 * c.r + 0.587 * c.g + 0.114 * c.b
				var sat := maxf(c.r, maxf(c.g, c.b)) - minf(c.r, minf(c.g, c.b))
				if c.a > 0.25 and lum > 0.58 and sat < 0.14:
					puddle += 1
		check(puddle < 25, "Carmen's shoes carry no light studio-floor puddle (%d pixels)" % puddle)
	await enter("c3_archive")
	game._process(.001)
	check(game.stage.furniture != null and game.stage.furniture.visible,
		"The archive foreground table and reel winder occlude characters standing behind them")
	for who: String in ["calder", "tomas", "agnes"]:
		var fig: Sprite2D = game.stage.talk_figures.get(who)
		check(fig != null and fig.position.y / game.stage.ART.y >= 0.64,
			"%s stands behind the archive foreground table rather than on top of it" % who)
		if fig != null and game.stage.furniture != null:
			var shin := Vector2(fig.position.x, game.stage.ART.y * 0.58)
			check(Geometry2D.is_point_in_polygon(shin, game.stage.furniture.polygon),
				"%s's lower legs are masked behind the archive table and equipment" % who)
	game.campaign.reset()
	await enter("c1_flat")
	check(not game.campaign.available_talk("iris").is_empty(), "Nora can talk after the Saturday morning opening")
	var saturday: Dictionary = game.campaign.task_index["c1_flat.saturday"]
	var topic: Dictionary = game.campaign.available_talk("iris")[0]
	check(click_person("iris"), "Nora is painted and clickable before either cassette")
	key(KEY_ENTER)
	check(game.dialogue_panel.visible and game.active_line == topic.lines[0], "Picking a topic starts its first dialogue line")
	check(game.words.text.contains(str(game.campaign.content.lines[topic.lines[0]].text)), "The talk line appears in the dialogue panel")
	game._process(.001)
	check(not game.person_target.visible, "The pointer cannot talk over dialogue")
	while game.dialogue_panel.visible:
		game._next_line()
	check(topic.lines.all(func(id: String): return id in game.campaign.data.seen), "Talk lines are marked seen")
	check(game.campaign.talk_heard(topic), "The completed topic is heard")
	check(game.root.get_node("InteractionPanel").visible, "The panel reopens while Nora has unheard topics")
	var heard_button := button_with_text("✓ " + str(topic.topic))
	check(heard_button != null and heard_button.modulate == Color("8aa498"),
		"Heard topics stay replayable, muted, and show a check")
	game.root.get_node("InteractionPanel").hide()
	game._process(.001)
	key(KEY_I)
	var people_entry := button_with_text("Talk to Nora Reyes")
	check(people_entry != null and people_entry.focus_mode == Control.FOCUS_ALL,
		"The Objects list has a keyboard-accessible People entry")
	for _tab: int in 20:
		if root.gui_get_focus_owner() == people_entry:
			break
		key(KEY_TAB)
	key(KEY_ENTER)
	check(game.root.get_node("InteractionPanel").visible and game.interaction.get_child(0).text == "Nora Reyes",
		"I, Tab and Enter reach Nora's talk panel without a pointer")
	game.root.get_node("InteractionPanel").hide()
	# Nora talks over each cassette once. Clicking a solved cassette again only recalls Steve's finding.
	var sunday: Dictionary = game.campaign.task_index["c1_flat.sunday"]
	game.campaign.choose(saturday.id, int(saturday.answer), saturday.get("puzzle", {}).get("solution", []))
	game.campaign.mark_seen(saturday.get("lead", []) + saturday.lines + [saturday.finding])
	game.campaign.choose(sunday.id, int(sunday.answer), sunday.get("puzzle", {}).get("solution", []))
	game.campaign.mark_seen(sunday.lines + [sunday.finding])
	for task: Dictionary in [saturday, sunday]:
		game._open_task(task.id)
		check(game.dialogue_panel.visible and game.active_line == task.finding and game.queue.is_empty(),
			"Clicking the solved " + str(task.title).to_lower() + " again only recalls Steve's finding")
		while game.dialogue_panel.visible:
			game._next_line()
	await coverage()
	var receipt := FileAccess.open(output.path_join("small-talk.json"), FileAccess.WRITE)
	receipt.store_string(JSON.stringify({"checks":checks,"observations":observations,"failures":failures,"bodies":tested,"channels":channels}, "\t") + "\n")
	receipt.close()
	print("Small talk checks: ", checks, " failures: ", failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

extends SceneTree
## Story staging: the room shows what the story says is happening at each moment.
var game: Node
var failures: Array[String] = []
var checks := 0

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures.append(description)
		push_error(description)

func frames(count: int) -> void:
	for i: int in count:
		await process_frame

func enter(scene_id: String, done: Array = []) -> void:
	var campaign = game.campaign
	campaign.reset()
	while campaign.current().id != scene_id:
		var scene: Dictionary = campaign.current()
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				campaign.switch_actor(task.actor)
			campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		campaign.advance()
	campaign.mark_seen(campaign.current().get("context", []) + campaign.current().intro)
	for id: String in done:
		var task: Dictionary = campaign.task_index[id]
		if not task.actor.is_empty():
			campaign.switch_actor(task.actor)
		campaign.choose(id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		check(id in campaign.data.done, "Test setup completes " + id)
	campaign.switch_actor(campaign.current().actors[0])
	game._load_stage(false)
	await frames(3)
	# Let any arrival dialogue finish, as a player reading on would.
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	game._refresh()
	await frames(2)

func arrive(scene_id: String) -> void:
	var campaign = game.campaign
	campaign.reset()
	while campaign.current().id != scene_id:
		var scene: Dictionary = campaign.current()
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				campaign.switch_actor(task.actor)
			campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		campaign.advance()
	game._load_stage(true)
	await frames(3)
	if game.title_card.visible:
		game.title_card.finish_now()
		await frames(3)

func plate() -> String:
	return game.stage.background.texture.resource_path

## True when a story layer painting (room or walking view) with this name is visible.
func painting_shown(name: String) -> bool:
	for entry: Dictionary in game.stage.story_layers:
		for node: Sprite2D in entry.nodes:
			if node.texture.resource_path.get_file().get_basename() == name and node.visible:
				return true
	return false

func layer_shown(name: String) -> bool:
	for entry: Dictionary in game.stage.story_layers:
		if str(entry.record.file).get_file().get_basename() == name:
			return entry.nodes.all(func(node: Sprite2D): return node.visible)
	return false

## Play one line through the real dialogue path and report what fills the frame.
func shown_during(line_id: String) -> String:
	game._speak([line_id], Callable())
	await frames(3)
	var shown: String = game.stage.shown_still()
	if shown.is_empty():
		shown = plate()
	while game.dialogue_panel.visible:
		game._next_line()
	await frames(2)
	return shown

## Play one line and report whether a person's portrait is on screen while it plays.
func portrait_during(line_id: String, who: String) -> bool:
	game._speak([line_id], Callable())
	await frames(3)
	var person: Node = game.stage.actors.get(who)
	var shown: bool = person != null and person.visible
	while game.dialogue_panel.visible:
		game._next_line()
	await frames(2)
	return shown

## Where the camera aims while a line plays, in art space.
func aim_during(line_id: String) -> Vector2:
	game._speak([line_id], Callable())
	await frames(3)
	var goal: Vector2 = game.stage.camera_goal
	while game.dialogue_panel.visible:
		game._next_line()
	await frames(2)
	return goal

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
	await frames(2)

	# Chapter 2: Steve is walked to the chair and strapped in until he gets himself out.
	await enter("c2_ship")
	check(layer_shown("c2_ship-steve-strapped"), "Show Steve strapped into the scan chair when the scan begins")
	check(layer_shown("c2_ship-nora-asleep"), "Show Nora asleep in the amber capsule while Steve is in the chair")
	var chair_crop: Sprite2D = game.stage.physical_art[game.campaign.current().tasks.find(game.campaign.task_index["c2_ship.escape"])]
	check(chair_crop.get_children().any(func(node: Node): return node is Sprite2D and node.visible and node.texture == chair_crop.get_child(0).texture),
		"The chair's clickable crop shows Steve too")
	check(not game.stage.walking_view(), "Steve cannot walk around while he is strapped in")
	check(not await portrait_during("c2_ship.in.03", "steve"), "No standing Steve portrait while he is painted into the chair")
	check(await portrait_during("c2_ship.in.01", "iris"), "Nora's copy, who walked him down, is on screen")
	var chair: Vector2 = game.stage.scene_props["c2_ship.escape"]
	check((await aim_during("c2_ship.command.lead.01")).distance_to(chair) < 1.0, "The attendant's lines keep the camera on Steve in the chair")
	check((await aim_during("c2_ship.command.02")).distance_to(chair) < 1.0, "Steve's strapped-in lines keep the camera on the chair")
	await enter("c2_ship", ["c2_ship.command", "c2_ship.escape"])
	check(not layer_shown("c2_ship-steve-strapped"), "Show the empty chair once Steve is free")
	check(layer_shown("c2_ship-nora-asleep"), "Nora stays asleep in her capsule after Steve is free")
	check(game.stage.walking_view(), "Steve can walk once he is out of the chair")
	check(await portrait_during("c2_ship.escape.02", "steve"), "Steve appears standing once he is out of the chair")
	# Nora sleeps in the amber capsule; the room shows her when Steve reaches it.
	var nora_lead: String = await shown_during("c2_ship.nora.lead.01")
	check(nora_lead.ends_with("stills/c2_ship-nora-asleep.webp"), "Show Nora asleep in the amber capsule when Steve finds her")
	# The rescue and the dawn beach are shown, not only told.
	await enter("c2_ship", ["c2_ship.command", "c2_ship.escape", "c2_ship.nora"])
	var rescue: String = await shown_during("c2_ship.intake.find")
	check(rescue.ends_with("stills/c2_ship-admiral-rescue.webp"), "Show Admiral dragging Steve to the surface")
	var dawn: String = await shown_during("c2_ship.out.02")
	check(dawn.ends_with("stills/c2_ship-dawn-beach.webp"), "Show June finding Steve on the beach at dawn")
	var other: String = await shown_during("c2_ship.out.01")
	check(other == plate(), "Lines without a story painting keep the room in view")
	# The aquarium: Nora's copy and Lyle catch Steve at the end, and are seen doing it.
	await enter("c2_aquarium", ["c2_aquarium.plan", "c2_aquarium.guard", "c2_aquarium.intercom"])
	check(await portrait_during("c2_aquarium.out.03", "iris"), "Nora's copy is on screen when she finds Steve in the aquarium")
	check(await portrait_during("c2_aquarium.out.04", "lyle_copy"), "Lyle is on screen when he finds Steve in the aquarium")
	await enter("c2_aquarium")
	check(not await portrait_during("c2_aquarium.plan.01", "iris"), "Nobody else is in the aquarium before they arrive")
	# Chapter 3 opens by recalling the dawn beach before June's house.
	await enter("c3_house")
	var recall: String = await shown_during("c3_house.ctx.01")
	check(recall.ends_with("stills/c2_ship-dawn-beach.webp"), "Bridge from the night at sea to June's house with the dawn beach")

	# Paintings are never warped or morphed between poses: a departure shows one
	# painting, then dissolves cleanly to the next, so nothing melts or disappears.
	for scene_id: String in ["c6_jail", "c8_rig", "c1_escape"]:
		await enter(scene_id)
		game.stage.begin_departure_cut()
		for progress: float in [.2, .5, .8]:
			game.stage.set_departure_progress(progress)
			var warped: bool = game.stage.chapter_frames.any(func(layer: TextureRect): return layer.material != null)
			check(not warped, "No morphing between paintings in the %s departure at %.1f" % [scene_id, progress])
		if is_instance_valid(game.stage.chapter_film):
			var film: ShaderMaterial = game.stage.chapter_film.action
			check(film.get_shader_parameter("warp") == false, "The %s film adds light, not distortion" % scene_id)

	# Transitions: rooms fade up from the dark, story paintings dissolve in and out,
	# and a location's ambience crossfades into the next one.
	await enter("c2_ship", ["c2_ship.command", "c2_ship.escape", "c2_ship.nora"])
	game._load_stage(false)
	await frames(2)
	var shade: ColorRect = game.stage.get("arrival_shade")
	check(is_instance_valid(shade) and shade.color.a > .8, "A new room starts from the dark")
	await create_timer(1.2).timeout
	check(not is_instance_valid(game.stage.get("arrival_shade")), "Then fades up within a second")
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	game._speak(["c2_ship.intake.find", "c2_ship.out.01"], Callable())
	await frames(2)
	var still: TextureRect = game.stage.story_still
	check(still.visible and still.modulate.a < .5, "A story painting dissolves in rather than cutting")
	await create_timer(.8).timeout
	check(still.modulate.a > .99 and still.scale.x > 1.0, "It settles in and drifts slowly closer")
	game._next_line()
	await frames(2)
	check(still.visible and still.modulate.a > .5 and game.stage.shown_still().is_empty(), "It dissolves out rather than cutting")
	await create_timer(1.0).timeout
	check(not still.visible, "And is gone once the room is back")
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	# Leaving a place shows the way to the next one: a bridge painting dissolves in,
	# the next place's sound and music rise under it, and the new room dissolves out of it.
	var flat_leads: Array = game.campaign.content.scenes.filter(func(scene: Dictionary): return scene.id == "c1_flat")[0].tasks.map(func(task: Dictionary): return task.id)
	# Entering with every lead solved plays the recap and farewell, then the departure begins.
	await enter("c1_flat", flat_leads)
	check(game.campaign.current().id == "c1_flat" and game.light_remaining > 0.0, "The departure from the flat has begun")
	var bridge: Array = game.stage.chapter_frames
	check(bridge.size() == 1 and bridge[0].texture.resource_path.ends_with("bridges/c1_flat-c1_pier.webp"), "Leaving the flat shows the walk down to the harbor")
	check(bridge.size() == 1 and bridge[0].modulate.a < .5, "The bridge painting dissolves in rather than cutting")
	check(game.ambience.stream.resource_path.ends_with("c1_pier.ogg") and game.ambience_out.stream != null
		and game.ambience_out.stream.resource_path.ends_with("c1_flat.ogg"), "The harbor's sound rises under the bridge while the flat's fades")
	var pier_music: String = game.score.manifest.scene_music.c1_pier.file
	check(game.score.current_file == pier_music, "The harbor's music comes in under the bridge")
	await create_timer(1.4).timeout
	check(bridge.size() == 1 and bridge[0].modulate.a > .99, "The bridge painting holds")
	var waited := 0
	while game.campaign.current().id == "c1_flat" and waited < 600:
		waited += 1
		await frames(5)
	await frames(3)
	var incoming: TextureRect = game.stage.get("incoming_frame")
	check(is_instance_valid(incoming) and incoming.texture.resource_path.ends_with("bridges/c1_flat-c1_pier.webp"), "The harbor dissolves out of the bridge painting")
	check(not is_instance_valid(game.stage.get("arrival_shade")), "No dip to black between the bridge and the harbor")
	check(game.ambience.stream.resource_path.ends_with("c1_pier.ogg") and game.ambience_level > .3, "The harbor's sound carries on from the bridge instead of restarting")
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	# Each place opens with Steve's narration of how he got there, then its first lines.
	await arrive("c3_house")
	check(game.active_line == "c3_house.ctx.01", "Chapter 3 opens with how June found Steve on the beach")
	check(game.stage.shown_still().ends_with("stills/c2_ship-dawn-beach.webp"), "Over the dawn beach painting")
	while game.dialogue_panel.visible and game.active_line.begins_with("c3_house.ctx"):
		game._next_line()
		await frames(1)
	check(game.active_line == "c3_house.in.01", "Then June's house")
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	await arrive("c1_pier")
	check(game.active_line == "c1_pier.ctx.01", "Sunday on the harbor opens with Steve's narration")
	await frames(3)
	var standing: Array = game.stage.actors.keys().filter(func(id: String): return game.stage.actors[id].visible)
	check(standing.is_empty(), "The opening narration is an establishing shot, with no portraits (%s)" % ", ".join(standing))
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	await arrive("c4_safe")
	check(game.active_line == "c4_safe.ctx.01" and game.stage.shown_still().ends_with("stills/c4_safe-arrival.webp"),
		"Chapter 4 opens on the drive up to the safe house")
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)

	# The balcony is one place: walking and close-ups use the same painting, and Mr. Bell's
	# gate is painted open (never a pasted picture) once Steve opens it.
	await enter("c1_escape")
	check(game.stage.floor_stage != null and game.stage.floor_stage.wide == null, "The balcony walks on the same painting it shows up close")
	check(not ResourceLoader.exists("res://assets/illustrated/campaign/doors/c1_escape.webp"), "No pasted door picture on the balcony")
	check(not layer_shown("c1_escape-gate-open"), "Mr. Bell's gate starts closed")
	await enter("c1_escape", ["c1_escape.order", "c1_escape.power"])
	check(layer_shown("c1_escape-gate-open"), "Mr. Bell's gate is painted open after Steve opens it")
	await enter("c1_escape")
	check(not await portrait_during("c1_escape.in.01", "iris"), "Nora's phone call behind the bedroom door is heard, not shown")
	await enter("c1_escape", ["c1_escape.order", "c1_escape.power"])
	check(await portrait_during("c1_escape.cross.03", "iris"), "Nora comes out to Steve on the balcony")
	var outro_shot: String = await shown_during("c1_escape.out.03")
	check(outro_shot.ends_with("stills/c1_escape-beach-procession.webp"), "Steve watches the procession from the beach")

	# Sleepers are seen asleep, and each wakes when Steve reaches them.
	await enter("c9_wake")
	for who: String in ["frank", "helen", "rook", "agnes"]:
		check(layer_shown("c9_wake-%s-asleep" % who), "Row nine shows %s asleep in the pod" % who)
	await enter("c9_wake", ["c9_wake.frank"])
	check(not layer_shown("c9_wake-frank-asleep") and layer_shown("c9_wake-helen-asleep"), "Frank's pod opens once he wakes; Helen still sleeps")
	await enter("c9_gallery")
	check(layer_shown("c9_gallery-nora-held") and not await portrait_during("c9_gallery.in.01", "nora"), "Nora is held in her bed, not standing beside it")
	await enter("c9_gallery", ["c9_gallery.link"])
	check(not layer_shown("c9_gallery-nora-held"), "Once Iris breaks the link, Nora is up")
	# June is behind the bars of cell two until Steve proves which June is real.
	await enter("c6_jail")
	check(layer_shown("c6_jail-june-in-cell"), "June sits in cell two")
	check(not await portrait_during("c6_jail.crossword.lead.02", "calder"), "June in the cell speaks through the bars, not as a second standing Sheriff")
	await enter("c6_jail", ["c6_jail.mail", "c6_jail.distract", "c6_jail.crossword"])
	check(not layer_shown("c6_jail-june-in-cell"), "Cell two is empty once June is out")
	# Nora wakes beside Dale and Lyle, whose pods stand open.
	await enter("i2_nora")
	check(layer_shown("i2_nora-pods-open") and game.stage.floor_stage.wide == null, "The Gallery shows the opened pods in the one painting Nora walks on")

	# Doors that open in the story are painted open in place: no pasted pictures, no
	# warped cut-out of the door, only the room as it looks with that door open.
	for case: Array in [["c6_jail", "c6_jail-cell-open-wide", ["c6_jail.mail", "c6_jail.distract", "c6_jail.crossword"]],
			["c2_aquarium", "c2_aquarium-staff-door-open", ["c2_aquarium.plan", "c2_aquarium.guard"]]]:
		await enter(case[0])
		check(not ResourceLoader.exists("res://assets/illustrated/campaign/doors/%s.webp" % case[0]), "No pasted door picture in " + case[0])
		check(not painting_shown(case[1]), "The door in %s starts closed" % case[0])
		await enter(case[0], case[2])
		check(painting_shown(case[1]), "The door in %s is painted open once the story opens it" % case[0])
		var passage: Dictionary = {}
		for blocker: Dictionary in game.stage.floor_stage.blockers:
			if blocker.has("opens_after"):
				passage = blocker
		check(not passage.is_empty() and not game.stage.floor_stage.solids.any(func(solid: PackedVector2Array): return solid == game.stage.floor_stage.points(passage.polygon)),
			"The open doorway in %s can be walked through" % case[0])

	var receipt := FileAccess.open(output.path_join("story-staging.json"), FileAccess.WRITE)
	receipt.store_string(JSON.stringify({"checks": checks, "failures": failures}, "\t") + "\n")
	receipt.close()
	print("Story staging checks: ", checks, " failures: ", failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

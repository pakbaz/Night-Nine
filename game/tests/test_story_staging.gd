extends SceneTree
## Story staging: the room shows what the story says is happening at each moment.
const SOCIAL := preload("res://render/illustrated/social_direction.gd")
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

## True when every cut-out the walking floor paints in front of walkers shows this story layer too.
func occluders_show(name: String) -> bool:
	var occluders: Array = game.stage.floor_stage.cast.get_children().filter(func(node: Node): return node is Polygon2D)
	return not occluders.is_empty() and occluders.all(func(occluder: Polygon2D): return occluder.get_children().any(
		func(node: Node): return node is Polygon2D and node.visible and node.texture.resource_path.get_file().get_basename() == name))

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

## Solve one lead in place, without replaying the scene's dialogue.
func solve(id: String) -> void:
	var task: Dictionary = game.campaign.task_index[id]
	game.campaign.choose(id, int(task.answer), task.get("puzzle", {}).get("solution", []))
	game._refresh()
	await frames(2)

## The kind of shot a line is played in.
func shot_during(line_id: String) -> Dictionary:
	game._speak([line_id], Callable())
	await frames(3)
	var shot := {"type": str(game.stage.dialogue_shot.get("type", "")), "goal": game.stage.camera_goal}
	while game.dialogue_panel.visible:
		game._next_line()
	await frames(2)
	return shot

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
	check(layer_shown("c2_ship-attendant-chair"), "The attendant stands at the scan chair with a slate")
	check(not layer_shown("c2_ship-attendant-column") and not layer_shown("c2_ship-hatch-flooding"), "The attendant is painted in one place at a time")
	check(not occluders_show("c2_ship-attendant-column"), "The speaker column shows no attendant while they are at the chair")
	game._speak(["c2_ship.command.lead.06"], Callable())
	await frames(3)
	var scanner: ColorRect = game.stage.hull.get_node_or_null("ChairScan")
	check(is_instance_valid(scanner) and scanner.is_visible_in_tree(), "The copying light is on Steve during the scan")
	for escort: String in ["iris", "lyle_copy"]:
		var watcher: Node2D = game.stage.actors.get(escort)
		check(is_instance_valid(watcher) and watcher.is_visible_in_tree(), "%s watches the scan until the attendant sends the escorts back" % escort)
	# The escorts stand to the left of the speaker column so Lyle never covers the intercom.
	var intercom_index: int = game.campaign.current().tasks.find(game.campaign.task_index["c2_ship.command"])
	var intercom_point: Vector2 = game.stage.project_target(intercom_index)
	check(not game.stage.actors.lyle_copy.hit(intercom_point) and not game.stage.actors.iris.hit(intercom_point),
		"Neither escort covers the intercom hotspot during the scan")
	if is_instance_valid(scanner):
		var phase: float = scanner.material.get_shader_parameter("phase")
		await frames(5)
		check(scanner.material.get_shader_parameter("phase") != phase, "The scan sweeps across the chair while the line holds")
	game._next_line()
	await frames(2)
	await solve("c2_ship.command")
	var leaving: String = await shown_during("c2_ship.command.02")
	check(leaving.ends_with("stills/c2_ship-escorts-leave.webp"), "Show Nora's copy and Lyle going back up to town")
	for escort: String in ["iris", "lyle_copy"]:
		check(not game.stage.actor_visible(escort), "%s is gone before the escape" % escort)
	check(not await portrait_during("c2_ship.escape.lead.01", "iris"), "Only the attendant watches the rest of the scan")
	scanner = game.stage.hull.get_node_or_null("ChairScan")
	check(is_instance_valid(scanner) and scanner.is_visible_in_tree(), "The scan starts again after the escorts leave")
	check(layer_shown("c2_ship-attendant-chair"), "The attendant stays at the chair until the release")
	var release: String = await shown_during("c2_ship.escape.03")
	check(release.ends_with("stills/c2_ship-chair-release.webp"), "Show the buckle springing open as the attendant turns to the column")
	var intercom: String = await shown_during("c2_ship.escape.04")
	check(intercom.ends_with("stills/c2_ship-attendant-intercom.webp"), "Show the attendant arguing with the column while Steve slips out")
	await enter("c2_ship", ["c2_ship.command", "c2_ship.escape"])
	scanner = game.stage.hull.get_node_or_null("ChairScan")
	check(not is_instance_valid(scanner) or not scanner.is_visible_in_tree(), "The scan stops on release")
	check(not layer_shown("c2_ship-steve-strapped"), "Show the empty chair once Steve is free")
	check(layer_shown("c2_ship-nora-asleep"), "Nora stays asleep in her capsule after Steve is free")
	check(layer_shown("c2_ship-attendant-column") and not layer_shown("c2_ship-attendant-chair"), "After the release the attendant argues at the speaker column")
	check(occluders_show("c2_ship-attendant-column"), "The speaker column cut-out in front of walkers keeps the attendant's hand and robe")
	check(not game.stage.actor_visible("iris") and not game.stage.actor_visible("lyle_copy"), "The escorts are not in the room for the escape")
	check(game.stage.walking_view(), "Steve can walk once he is out of the chair")
	check(await portrait_during("c2_ship.escape.02", "steve"), "Steve appears standing once he is out of the chair")
	# Nora sleeps in the amber capsule; the room shows her when Steve reaches it.
	var nora_lead: String = await shown_during("c2_ship.nora.lead.01")
	check(nora_lead.ends_with("stills/c2_ship-nora-asleep.webp"), "Show Nora asleep in the amber capsule when Steve finds her")
	# The alarm, the flooded tunnel, the rescue and the dawn beach are shown, not only told.
	await enter("c2_ship", ["c2_ship.command", "c2_ship.escape", "c2_ship.nora"])
	check(SOCIAL.action_for("c2_ship", "c2_ship.intake", []) == "kneel", "Steve kneels at the intake hatch in the floor")
	check(layer_shown("c2_ship-attendant-column") and not layer_shown("c2_ship-hatch-flooding"), "The hatch stays shut until Steve opens the valve")
	var denial: String = await shown_during("c2_ship.intake.lead.01")
	check(denial.ends_with("stills/c2_ship-attendant-turns.webp"), "Show the attendant turning to the empty chair when the Prefect denies the release")
	var valve: String = await shown_during("c2_ship.intake.lead.03")
	check(valve.ends_with("stills/c2_ship-valve-alarm.webp"), "Show Steve hauling the valve wheel as the sea bursts in")
	check(layer_shown("c2_ship-hatch-flooding") and not layer_shown("c2_ship-attendant-column"), "Once the valve opens, the attendant wades after Steve at the flooding hatch")
	check(not game.stage.walking_view(), "Steve is down the hatch and cannot walk the room")
	var tunnel: String = await shown_during("c2_ship.out.01")
	check(tunnel.ends_with("stills/c2_ship-flooded-tunnel.webp"), "Show the tunnel flooding when Steve says it is")
	var burst: String = await shown_during("c2_ship.intake.02")
	check(burst.ends_with("stills/c2_ship-admiral-burst.webp"), "Show Admiral surging up in front of the attendant")
	var rescue: String = await shown_during("c2_ship.intake.find")
	check(rescue.ends_with("stills/c2_ship-admiral-rescue.webp"), "Show Admiral dragging Steve to the surface")
	var dawn: String = await shown_during("c2_ship.out.02")
	check(dawn.ends_with("stills/c2_ship-dawn-beach.webp"), "Show June finding Steve on the beach at dawn")
	var other: String = await shown_during("c2_ship.escape.02")
	check(other == plate(), "Lines without a story painting keep the room in view")
	# The aquarium: Nora's copy and Lyle catch Steve at the end, and are seen doing it.
	await enter("c2_aquarium", ["c2_aquarium.plan", "c2_aquarium.guard"])
	await solve("c2_aquarium.intercom")
	check(not game.stage.actor_visible("iris") and not game.stage.actor_visible("lyle_copy"), "Nobody catches Steve while he is still listening to the tape")
	check(not await portrait_during("c2_aquarium.recap.01", "iris"), "Nora's copy is not there while Steve sums up the north wing")
	check(await portrait_during("c2_aquarium.out.03", "iris"), "Nora's copy appears when she finds Steve in the aquarium")
	check(game.stage.actor_visible("iris") and game.stage.actor_visible("lyle_copy"), "Once they find Steve, they stay")
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
	game._speak(["c2_ship.intake.find", "c2_ship.escape.02"], Callable())
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
	check(await portrait_during("c4_safe.match.lead.02", "calder"), "June stays with Steve while they compare the audio")
	check(not await portrait_during("c4_safe.in.02", "rook_copy"), "Talking about Adrian does not summon his portrait")
	check(not await portrait_during("c4_safe.record.01", "rook_copy"), "Steve hears Rook through the office door")
	check((await shown_during("c4_safe.screens.01")).ends_with("c4_safe-feed-3.webp"), "The feed reveals the sleeping Rook, not his standing double")
	check(await portrait_during("c4_safe.out.02", "calder") and await portrait_during("c4_safe.out.02", "rook_copy"),
		"June and Rook share the shot when he assigns her to the east wing")
	check(not await portrait_during("c4_safe.out.03", "calder"), "June has left when Rook turns back to Steve")

	await enter("c4_escape", ["c4_escape.tube"])
	check(not game.stage.in_cutaway(), "The transfer bay and its parked van are available before the drill")
	await solve("c4_escape.fault")
	check((await shown_during("c4_escape.fault.02")).ends_with("c4_escape-drill.webp"), "The escort boards Steve as the bells ring")
	check(game.stage.in_cutaway() and not game.stage.walking_view(), "Between boarding and the jump the player cannot walk back around the parked van")
	check((await shown_during("c4_escape.van.lead.01")).ends_with("inserts/c4_escape-motion.webp"), "Show Steve uncuffed inside the moving van with both agents up front")
	check((await shown_during("c4_escape.van.01")).ends_with("c4_escape-rear-door.webp"), "Steve slips unseen from the rear door on the blind gravel bend")
	check((await shown_during("c4_escape.van.02")).ends_with("c4_escape-jump.webp"), "Steve lands in the ditch with the spare radio as the van continues down the hill")
	check("unseen" in game.campaign.content.lines["c4_escape.van.find"].text.to_lower()
		and "grabbed" not in game.campaign.content.lines["c4_escape.van.02"].text.to_lower(),
		"The agents do not see Steve slip out of the van")
	var woods := await shown_during("c4_escape.out.04")
	check(woods.ends_with("c4_escape-creek.webp"), "Steve follows the creek on his last line")
	game.stage.begin_departure_cut()
	check(not game.stage.chapter_frames.is_empty() and game.stage.chapter_frames[0].texture.resource_path == woods,
		"The chapter cut continues from the woods without replaying the van departure")

	# The balcony is one place: walking and close-ups use the same painting, and Mr. Bell's
	# gate is painted open (never a pasted picture) once Steve opens it.
	await enter("c1_escape")
	check(game.stage.floor_stage != null and game.stage.floor_stage.wide == null, "The balcony walks on the same painting it shows up close")
	check(not ResourceLoader.exists("res://assets/illustrated/campaign/doors/c1_escape.webp"), "No pasted door picture on the balcony")
	check(not layer_shown("c1_escape-gate-open"), "Mr. Bell's gate starts closed")
	check(ResourceLoader.exists("res://assets/illustrated/campaign/layers/c1_escape-coat-hung.webp") and layer_shown("c1_escape-coat-hung"),
		"Nora's raincoat is already hanging on the balcony hook when exploration begins")
	await arrive("c1_escape")
	check(layer_shown("c1_escape-coat-hung"), "The raincoat is visible on the balcony hook as the scene opens")
	await enter("c1_escape", ["c1_escape.order"])
	check(layer_shown("c1_escape-coat-hung"), "The raincoat stays on its hook")
	var locked_out: Dictionary = await shot_during("c1_escape.in.02")
	check(locked_out.type == "detail" and locked_out.goal.x < game.stage.ART.x * .4,
		"Steve's 'the balcony door's locked' line shows the locked balcony door")
	await enter("c1_escape", ["c1_escape.order", "c1_escape.power"])
	check(layer_shown("c1_escape-gate-open"), "Mr. Bell's gate is painted open after Steve opens it")
	check(not game.stage.actor_visible("iris"), "Nora stays inside until the crash brings her to the door")
	await enter("c1_escape")
	check(not await portrait_during("c1_escape.in.01", "iris"), "Nora's phone call behind the bedroom window is heard, not shown")
	await enter("c1_escape", ["c1_escape.order", "c1_escape.power"])
	await solve("c1_escape.cross")
	check(game.stage.actor_visible("iris"), "The crash of the irises brings Nora to the balcony door")
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
	await enter("c6_iris")
	check(not game.campaign.available("c6_iris.takes") and not game.stage.actor_visible("iris"), "The meeting waits for Stephen's market alibi")
	check(game.stage.floor_stage.bodies.has("stephen") and game.stage.floor_stage.bodies.stephen.body.visible, "Stephen plans his market errand with Steve before he leaves")
	check(game._next_actor() == "stephen" and game.campaign.task_index["c6_iris.alibi"].actor == "stephen",
		"Switch to Stephen for the market sighting before handing the pier meeting back to Steve")
	await enter("c6_iris", ["c6_iris.alibi"])
	check(game.campaign.available("c6_iris.takes"), "Steve can keep the appointment after the market sighting")
	check(not game.stage.floor_stage.bodies.stephen.body.visible and not game.stage.actor_visible("stephen"), "Stephen stays at the market while Steve meets Iris")
	check(game.campaign.available_talk("stephen").is_empty(), "Nobody chats with Stephen on the pier; he is at the bread window")
	check(game.stage.actor_visible("iris"), "Iris meets Steve alone on the pier")
	await enter("c6_jail")
	check(layer_shown("c6_jail-june-in-cell"), "June sits in cell two")
	check(not await portrait_during("c6_jail.crossword.lead.02", "calder"), "June in the cell speaks through the bars, not as a second standing Sheriff")
	await enter("c6_jail", ["c6_jail.mail", "c6_jail.crossword"])
	check(not layer_shown("c6_jail-june-in-cell"), "Cell two is empty once June is out")
	# Only people who are really there stand in the Sheriff's office. June's copy is out on
	# the harbor, heard on the radio; Gus waits at his bakery; Iris never comes inside.
	await enter("c6_jail")
	check(not game.stage.actor_visible("calder"), "No standing Sheriff in the office while June is locked in cell two and her copy is out on the harbor")
	check(not game.stage.actor_visible("gus"), "Gus is at his bakery, not standing in the Sheriff's office")
	check(not game.stage.actor_visible("iris") and not game.stage.floor_stage.bodies.has("iris"), "Iris waits outside; Nora's face would be recognised in the Sheriff's office")
	check(not game.stage.actor_visible("stephen") and not game.stage.floor_stage.bodies.has("stephen"), "Stephen waits with Iris behind the bakery; Steve visits Pell alone")
	var deputy_lines: Array = game.campaign.content.lines.values().filter(func(line: Dictionary): return line.id.begins_with("c6_jail.") and line.speaker == "lyle_copy")
	check(deputy_lines.is_empty() and not game.stage.actor_visible("lyle_copy"), "Lyle's copy is out on the harbor; he never sees Steve, so he has nothing to report")
	await enter("c6_jail", ["c6_jail.mail", "c6_jail.crossword"])
	check(game.stage.actor_visible("calder"), "Once she is out of the cell, June stands with Steve")
	# The man with Steve's face hides in the record library until he steps out.
	await enter("c5_station")
	check(not game.stage.actor_visible("stephen"), "Nobody else is visible at KBWR when Steve only hears breathing")
	await enter("c5_station", ["c5_station.automation", "c5_station.sleeve"])
	check(not game.stage.actor_visible("stephen"), "The other man stays hidden while Steve is still searching")
	await enter("c5_station", ["c5_station.automation", "c5_station.sleeve", "c5_station.halcyon"])
	check(game.stage.actor_visible("stephen"), "The man with Steve's face steps out once Steve has the notebook and Halcyon's paperwork")
	# The President is not waiting at the gate; she comes to the delegation hatch for her letter.
	await enter("c7_gate")
	check(not game.stage.actor_visible("ward"), "The President is not standing at the gate when Steve arrives")
	check(game.campaign.available_talk("ward").is_empty(), "Nobody chats with the President before they have met her")
	await enter("c7_gate", ["c7_gate.post"])
	check(game.stage.actor_visible("ward"), "The President is at the delegation hatch after Pell's letter")
	# Steve's face is on every poster, so he stays out of sight in the truck until it is through the gate.
	await enter("c7_gate")
	var investigators: Array = game.campaign.current().actors
	check(game.campaign.data.actor == "stephen", "Chapter 7 opens with Stephen, who may be seen at the gate")
	check(not game.stage.floor_stage.bodies.steve.body.visible and not game.stage.actor_visible("steve"), "Steve does not stand in front of the gate guard")
	check(game.actor.is_item_disabled(investigators.find("steve")), "Steve cannot be picked from the name menu while he hides")
	game.campaign.switch_actor("pell")
	game._refresh()
	check(game._next_actor() == "stephen", "Q skips Steve while he hides")
	game.campaign.switch_actor("steve")
	game._refresh()
	await frames(2)
	check(game.campaign.data.actor != "steve" and game.stage.floor_stage.active_actor == game.campaign.data.actor, "A saved game with Steve chosen at the gate opens with someone who can walk")
	check(game.campaign.available_talk("pell").is_empty() and game.campaign.available_talk("shaw").is_empty(), "Steve chats with nobody while he hides in the truck")
	check("c7_gate-under-desk" in await shown_during("c7_gate.badge.02"), "The gate check is shown from inside the truck, with Steve under the sound desk")
	await enter("c7_gate", ["c7_gate.badge"])
	check(game.stage.floor_stage.bodies.steve.body.visible and not game.actor.is_item_disabled(investigators.find("steve")), "Steve climbs out once the truck is through the gate")
	check(not game.campaign.available_talk("pell").is_empty(), "Steve and Pell can chat inside the fence")
	check(game.campaign.available_talk("shaw").is_empty(), "Steve has not met Shaw yet")
	game.campaign.mark_seen(["c7_gate.truck.02"])
	check(not game.campaign.available_talk("shaw").is_empty(), "Steve can chat with Shaw once she has introduced herself")
	# The Choir stops the scan; June brings Helen, Frank and Nora down from row nine.
	await enter("c9_choir")
	check("c9_choir-scan" in await shown_during("c9_choir.in.01"), "Saren's scan shows Steve strapped in the chair")
	check("c9_choir-stop" in await shown_during("c9_choir.in.07"), "The Choir's stop shows the straps open and June arriving with Steve's family")
	# Cell two, the back door and the bakery van are shown where they happen.
	await enter("c6_jail", ["c6_jail.mail", "c6_jail.crossword"])
	check("c6_jail-back-door" in await shown_during("c6_jail.crossword.06"), "Pell holds the back door while June's copy pulls up out front")
	# Once they are out of the back door, the closing lines do not cut back to the jail.
	for line_id: String in ["c6_jail.crossword.find", "c6_jail.recap.01"]:
		check("c6_jail-back-door" in await shown_during(line_id), "June goes out the back with the crossword in her hand: " + line_id)
	for line_id: String in ["c6_jail.recap.02", "c6_jail.recap.03"]:
		check("c6_jail-bakery" in await shown_during(line_id), "Five fugitives and a beagle meet behind the bakery: " + line_id)
	check("c6_jail-bakery" in await shown_during("c6_jail.out.02"), "Gus hands over the van behind his bakery")
	check("c6_jail-posters" in await shown_during("c6_jail.out.06"), "The new posters go up at dusk")
	# Nora wakes beside Dale and Lyle, whose pods stand open.
	await arrive("i2_nora")
	check(not layer_shown("i2_nora-pods-open"), "Nora's neighbors are still under glass at the start of the wake cycle")
	await shown_during("i2_nora.in.04")
	check(not layer_shown("i2_nora-pods-open"), "The glass stays closed while the beds breathe for all three sleepers")
	await shown_during("i2_nora.in.05")
	check(layer_shown("i2_nora-pods-open"), "The pods open only after the slow wake Iris set completes")
	await enter("i2_nora")
	check(layer_shown("i2_nora-pods-open") and game.stage.floor_stage.wide == null, "The Gallery shows the opened pods in the one painting Nora walks on")
	check(layer_shown("i2_nora-guard"), "A Veyri guard walks his lap while Nora times it")
	check("i2_nora-guard-passes" in await shown_during("i2_nora.patrol.lead.01"), "Nora watches the guard pass before she counts his lap")
	check("i2_nora-crossing" in await shown_during("i2_nora.patrol.01"), "Nora, Dale and Lyle cross while the far door is shut")
	await enter("i2_nora", ["i2_nora.patrol"])
	check(not layer_shown("i2_nora-guard"), "The guard is behind the far door once they have crossed")

	# Doors that open in the story are painted open in place: no pasted pictures, no
	# warped cut-out of the door, only the room as it looks with that door open.
	for case: Array in [["c6_jail", "c6_jail-cell-open-wide", ["c6_jail.mail", "c6_jail.crossword"]],
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

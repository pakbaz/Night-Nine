extends SceneTree
## Exercise the normal GUI and campaign save path with the imported production art.
var failures: Array[String] = []
var observations: Array[String] = []
var checks := 0
var game: Node

func _initialize() -> void:
	test.call_deferred()

func check(ok: bool, description: String) -> void:
	checks+=1
	if ok:
		observations.append(description)
	if not ok:
		failures.append(description)
		push_error(description)

func click(point: Vector2) -> void:
	var mouse := InputEventMouseMotion.new()
	mouse.position = point
	root.push_input(mouse,true)
	for down: bool in [true,false]:
		var event := InputEventMouseButton.new()
		event.position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if down else 0
		event.pressed = down
		root.push_input(event,true)

func test() -> void:
	if OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Use a QA save directory for the exploration input test.")
		quit(2)
		return
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue=false
	var campaign: NightCampaign = game.campaign
	while campaign.current().id!="c1_pier":
		var scene: Dictionary = campaign.current()
		campaign.mark_seen(scene.intro)
		for task: Dictionary in scene.tasks:
			if task.actor!="":
				campaign.switch_actor(task.actor)
			campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[]))
			campaign.mark_seen(task.lines)
			if not str(task.get("finding","")).is_empty():
				campaign.mark_seen([task.finding])
		campaign.mark_seen(scene.outro)
		if not campaign.advance():
			push_error("Cannot prepare the opening state.")
			quit(2)
			return
	campaign.mark_seen(campaign.current().intro)
	game.started=true
	game.menu.hide()
	game._load_stage(false)
	await process_frame
	await process_frame
	var floor_stage: Node=game.stage.floor_stage
	check(game.stage.walking_view(),"Walking view available.")
	check(floor_stage.bodies.has("steve"),"Actual generated Steve walk atlas imported.")
	var person: Dictionary=floor_stage.bodies.steve
	check(person.sprite.texture.resource_path.ends_with("steve-idle.webp"),"Actual idle character visible.")
	check(not game.stage.actors.has("agnes") or not game.stage.actors.agnes.visible,"No detached portrait on the pier.")
	var start: Vector2=person.body.position
	click(game.stage.distant.to_global(floor_stage.point([.49,.84])))
	check(game.stage.is_walking(),"An unhandled floor click starts a normal path.")
	var frames_seen := {}
	for frame_: int in 38:
		game._process(.025)
		frames_seen[person.sprite.frame]=true
	check(person.body.position.distance_to(start)>100.0 and frames_seen.size()>=4,"Parallax-grounded walk shows distinct animation poses.")
	check(person.sprite.flip_h,"Leftward travel mirrors the rightward sheet.")
	var parked: Vector2=person.body.position
	game.menu.show()
	game._pause_audio(true)
	game._process(.5)
	check(person.body.position==parked,"Menu pauses movement.")
	game._save("manual")
	game.menu.hide()
	game._pause_audio(false)
	check(game._load("manual"),"Reload the actual walking investigator save.")
	floor_stage=game.stage.floor_stage
	person=floor_stage.bodies.steve
	check(person.body.position.distance_to(parked)<.1 and person.left,"Foot position and facing survive reload.")
	await process_frame
	await process_frame
	click(game.hotspots[0].get_global_rect().get_center())
	check(game.stage.is_walking() and not game.root.get_node("InteractionPanel").visible,"Physical evidence waits for the approach.")
	var action_seen:=false
	for i: int in 440:
		if not game.stage.is_walking():
			break
		game._process(.025)
		action_seen=action_seen or floor_stage.performance_action=="observe"
	check(action_seen,"Steve observes the whistle on arrival.")
	if game.dialogue_panel.visible:
		check(game.active_line in campaign.task_index["c1_pier.whistle"].lead,"The whistle opens with its lead-in")
		game._skip_dialogue()
		await process_frame
	check(game.selected_task=="c1_pier.whistle" and game.root.get_node("InteractionPanel").visible,"Arrival opens the requested evidence.")
	check(person.body.position.distance_to(floor_stage.point(floor_stage.approach.whistle))<.1,"Actor stops on the registered prop approach.")
	game.root.get_node("InteractionPanel").hide()
	game.stage.set_focus(-1)
	var before_key:Vector2=person.body.position
	var event := InputEventKey.new()
	event.keycode=KEY_D
	event.physical_keycode=KEY_D
	event.pressed=true
	Input.parse_input_event(event)
	Input.flush_buffered_events()
	game._process(.15)
	var released := event.duplicate() as InputEventKey
	released.pressed=false
	Input.parse_input_event(released)
	Input.flush_buffered_events()
	game._process(.02)
	check(person.body.position.x>before_key.x and person.sprite.texture.resource_path.ends_with("steve-idle.webp"),"WASD walks and returns to the idle portrait.")
	await solve_staff_door()
	var output_dir := OS.get_environment("NIGHT_NINE_QA_DIR")
	if not output_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(output_dir)
		var receipt := FileAccess.open(output_dir.path_join("exploration-input.json"),FileAccess.WRITE)
		receipt.store_string(JSON.stringify({"checks":checks,"observations":observations,"failures":failures},"\t")+"\n")
		receipt.close()
	print("Movement input checks: ",checks," failures: ",failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

func solve_staff_door() -> void:
	var campaign: NightCampaign=game.campaign
	while campaign.current().id!="c2_aquarium":
		var scene:=campaign.current()
		campaign.mark_seen(scene.intro)
		for task: Dictionary in scene.tasks:
			if task.actor!="":
				campaign.switch_actor(task.actor)
			campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[]))
			campaign.mark_seen(task.lines)
			if not str(task.get("finding","")).is_empty():
				campaign.mark_seen([task.finding])
		campaign.mark_seen(scene.outro)
		if not campaign.advance():
			check(false,"Prepare the aquarium via a legal campaign history")
			return
	var first: Dictionary = campaign.task_index["c2_aquarium.plan"]
	campaign.mark_seen(campaign.current().intro)
	campaign.choose(first.id,int(first.answer),first.puzzle.solution)
	campaign.mark_seen(first.lines)
	if not str(first.get("finding","")).is_empty():
		campaign.mark_seen([first.finding])
	game._load_stage(false)
	await process_frame
	await process_frame
	var floor_stage: Node2D=game.stage.floor_stage
	var door: Node2D=floor_stage.door_art.staff_door
	var target: Vector2=floor_stage.point([.779,.574])
	check(not door.is_cleared() and not floor_stage.walk_to(target),"Players cannot enter the staff doorway before solving the guard")
	click(game.hotspots[1].get_global_rect().get_center())
	for tick: int in 650:
		if not game.stage.is_walking(): break
		game._process(.025)
	var task: Dictionary=campaign.task_index["c2_aquarium.guard"]
	if game.dialogue_panel.visible:
		check(game.active_line in task.lead,"The guard lead-in plays before the choice")
		game._skip_dialogue()
		await process_frame
	var option: Button
	for button: Button in game.interaction.find_children("*","Button",true,false):
		if button.text==task.options[int(task.answer)]:
			option=button
			break
	check(option!=null,"The guard offers a reachable dialogue choice in the real interaction panel")
	if not option: return
	option.pressed.emit()
	check(game.dialogue_panel.visible and door.open_fraction==0.0,"The guard speaks before players see the door swing")
	game._process(.25)
	check(not door.is_cleared(),"The threshold remains closed during the guard's dialogue")
	for line: int in 30:
		if not game.dialogue_panel.visible: break
		game._next_line()
	check(game.stage.walking_view() and door.open_fraction==0.0,"The camera returns before the visible opening begins")
	game._process(.15)
	check(door.open_fraction>0.0 and not door.is_cleared(),"The door begins swinging before the investigator can cross")
	game._process(.36)
	check(door.open_fraction<.70 and not floor_stage.walk_to(target),"An investigator still cannot enter just before the leaf clears the threshold")
	game._process(.015)
	check(door.is_cleared() and floor_stage.walk_to(target),"A player can enter the newly revealed staff doorway")
	for tick: int in 650:
		if not game.stage.is_walking(): break
		game._process(.025)
	check(floor_stage.bodies[floor_stage.active_actor].body.position.distance_to(target)<.2,"The player arrives on the far side of the opened doorway")
	game._save("manual")
	check(game._load("manual"),"Reload after opening the aquarium")
	floor_stage=game.stage.floor_stage
	door=floor_stage.door_art.staff_door
	check(door.is_cleared() and is_equal_approx(door.open_fraction,1.0) and floor_stage.bodies[floor_stage.active_actor].body.position.distance_to(target)<.2,"A loaded game restores the open leaf and the investigator on the far side together")

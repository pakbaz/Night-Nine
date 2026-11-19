extends SceneTree
## Exercise actual viewport clicks, imported poses, dialogue timing and ground contacts.
var game: Node
var failures: Array[String] = []
var checks := 0
var measurements := {}
var output := ""
var capture := false
# Fingertips measured on the imported 416 x 512 pose sheets.
const FINGERS := {"steve-operate.webp":Vector2(353,214), "nora-operate.webp":Vector2(364,211),
	"steve-kneel.webp":Vector2(277,478), "nora-kneel.webp":Vector2(334,500)}

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures.append(description)
		push_error(description)

func frame(name_: String) -> void:
	if not capture:
		return
	for i: int in 4:
		await process_frame
	RenderingServer.force_draw(false)
	var result := root.get_texture().get_image().save_png(output.path_join(name_ + ".png"))
	check(result == OK,"Save camera frame " + name_)

func click(at: Vector2) -> void:
	var mouse := InputEventMouseMotion.new()
	mouse.position = at
	root.push_input(mouse,true)
	for down: bool in [true,false]:
		var event := InputEventMouseButton.new()
		event.position = at
		event.button_index = MOUSE_BUTTON_LEFT
		event.button_mask = MOUSE_BUTTON_MASK_LEFT if down else 0
		event.pressed = down
		root.push_input(event,true)

func arrive(id: String, intro: bool = false, task_id: String = "") -> void:
	game.campaign.reset()
	while game.campaign.current().id != id:
		var s: Dictionary = game.campaign.current()
		game.campaign.mark_seen(s.intro)
		for task: Dictionary in s.tasks:
			solve(task)
		game.campaign.mark_seen(s.outro)
		if not game.campaign.advance():
			check(false,"Reach " + id)
			return
	if not task_id.is_empty():
		for lead: Variant in game.campaign.current().tasks:
			if lead.id == task_id:
				if not lead.actor.is_empty():
					game.campaign.switch_actor(lead.actor)
				break
			solve(lead)
	if not intro:
		game.campaign.mark_seen(game.campaign.current().intro)
	game._load_stage(intro)
	await process_frame
	await process_frame

func solve(task: Dictionary) -> void:
	if not task.actor.is_empty():
		game.campaign.switch_actor(task.actor)
	game.campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[]))
	game.campaign.mark_seen(task.lines)

func work_at(id: String, action: String, expect_art: bool = true) -> void:
	var task: Dictionary = game.campaign.task_index[id]
	var index: int = game.campaign.current().tasks.find(task)
	var button: Button = game.hotspots[index]
	check(not button.disabled and button.is_visible_in_tree(),"Player can use " + id)
	click(button.get_global_rect().get_center())
	var floor_: Node = game.stage.floor_stage
	check(floor_.pending == id,"Click starts the approach to " + id)
	var elapsed := 0.0
	while floor_.pose_time <= 0 and elapsed < 32 and not floor_.pending.is_empty():
		game.stage.tick_walk(.025,Vector2.ZERO)
		elapsed += .025
	check(floor_.pose_time > 0 and floor_.performance_action == action,"Character performs " + action + " at " + id)
	if floor_.pose_time <= 0:
		return
	var who: Dictionary = floor_.bodies[floor_.active_actor]
	var before: Vector2 = who.body.position
	for i: int in 12:
		game.stage.tick_walk(.025,Vector2.ZERO)
	check(who.body.position.is_equal_approx(before) and absf(who.sprite.rotation) > .001,"Shift weight about stationary feet at " + id)
	var tex_name: String = who.sprite.texture.resource_path.get_file()
	if expect_art:
		check(tex_name == floor_.active_actor + "-" + action + ".webp","Registered action drawing at " + id + " (" + tex_name + ")")
	var key := id.get_slice(".",1)
	var mark: Vector2 = floor_.point(floor_.object_marks[key])
	if not floor_.speaking_partner.is_empty():
		mark = floor_.bodies[floor_.speaking_partner].body.position
	var offset: Vector2 = (mark-before) / floor_.height_at(before)
	check(absf(offset.x)<.018 or who.left==(offset.x<0),"Face the actual contact or interlocutor at " + id)
	var contact: Array = game.stage.floor_directions.get("contact",{}).get(key,[])
	if not contact.is_empty():
		check(mark.distance_to(floor_.point(contact))<.01,"Aim at authored contact for " + id)
	if action == "conversation":
		var other: Dictionary = floor_.bodies[floor_.speaking_partner]
		check(other.left != who.left and absf(offset.x) > .09,"Stand on opposite sides and exchange a look")
	var sprite: Sprite2D = who.sprite
	check(sprite.texture.get_size() == Vector2(416,512),"Keep the imported standing scale through the pose")
	var toes := sprite.position + Vector2(0,256*sprite.scale.y).rotated(sprite.rotation)
	check(toes.length()<.1,"Physical bottom of the pose stays registered to the floor")
	game._process(.001)
	check(button.performing and not game.performance_status.is_empty() and game.status.text == game.performance_status,
		"Expose the working hand and describe the current action during " + id)
	measurements[id] = {"action":action,"asset":tex_name,"contact_in_body_heights":[offset.x,offset.y],"standing_height_art_px":floor_.height_at(before),
		"registered_ground_error":toes.length(),"approach_seconds_simulated":elapsed}
	if FINGERS.has(tex_name):
		var finger: Vector2 = FINGERS[tex_name] - Vector2(208,256)
		if sprite.flip_h:
			finger.x = -finger.x
		var art_hand: Vector2 = before + sprite.position + (finger * sprite.scale).rotated(sprite.rotation)
		var hand_error: float = art_hand.distance_to(mark) / floor_.height_at(before)
		measurements[id].finger_error_in_body_heights = hand_error
		if not contact.is_empty():
			check(hand_error<.14,"Place the working hand at the painted contact for " + id)
	await frame(id.replace(".","-"))
	for i: int in 65:
		if floor_.pose_time<=0:
			break
		game.stage.tick_walk(.025,Vector2.ZERO)
	check(game.selected_task == id and not game.stage.is_walking(),"Finish the action before opening " + id)
	game._process(.001)
	check(not button.performing and game.performance_status.is_empty(),"Restore hotspot labels after " + id)
	check(is_zero_approx(who.sprite.rotation),"Settle to a stationary pose at " + id)

func run() -> void:
	output = OS.get_environment("NIGHT_NINE_QA_DIR")
	if output.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set NIGHT_NINE_QA_DIR and NIGHT_NINE_SAVE_DIR to isolated QA paths.")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output)
	capture = DisplayServer.get_name() != "headless"
	game = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.started = true
	game.menu.hide()
	game.auto_dialogue = false
	await arrive("c3_house",true)
	check(game.stage.floor_dialogue and game.stage.floor_stage.visible,"Open the house scene on both complete standing figures")
	var f: Node = game.stage.floor_stage
	if f.bodies.has("calder"):
		check(f.bodies.calder.sprite.texture.resource_path.ends_with("calder-talk.webp"),"Calder addresses Steve with the imported speaking pose")
		check(f.bodies.steve.left!=f.bodies.calder.left,"Both people turn toward their scene partner")
		await frame("calder-wide")
	else:
		check(false,"Calder's full-body art is present")
	game.stage._process(1.9)
	check(not game.stage.floor_dialogue and game.stage.cast_plane.visible,"Cut to the painted faces after the establishing beat")
	var sheriff: Node = game.stage.actors.calder
	var steve: Node = game.stage.actors.steve
	check(sheriff.role == "speaker" and steve.role=="listener" and steve.voice==null,"Calder speaks while Steve listens")
	var old_look: float = steve.look_side
	game._next_line()
	check(steve.voice==game.voice and sheriff.voice==null and sheriff.role=="listener","Steve replies and Calder receives the next line")
	check(old_look==steve.look_side and sheriff.look_side==-steve.look_side,"Reverse the speaking role without crossing the eye-line")
	game.stage._process(.52)
	check(sheriff.position.distance_to(sheriff.base_ground)>2.0,"Calder changes posture during the listening beat")
	await frame("calder-listens")
	game._skip_dialogue()
	await process_frame
	await work_at("c3_house.crossword","read")
	await arrive("c1_pier",false,"c1_pier.bait")
	game.stage.tick_walk(.13,Vector2.ZERO)
	var agnes: Dictionary = game.stage.floor_stage.bodies.agnes
	check(game.stage.notice.has("agnes") and agnes.sprite.texture.resource_path.ends_with("agnes-greet.webp"),
		"Agnes notices the approaching investigator and acknowledges him")
	game.stage._process(1.05)
	game.stage.tick_walk(.13,Vector2.ZERO)
	check(agnes.sprite.texture.resource_path.ends_with("agnes-idle.webp"),"Agnes settles instead of repeatedly greeting")
	await work_at("c1_pier.bait","conversation",false)
	await arrive("c1_escape",false,"c1_escape.cross")
	await work_at("c1_escape.cross","kneel")
	await arrive("c1_escape",false,"c1_escape.power")
	await work_at("c1_escape.power","operate")
	await arrive("c5_station",false,"c5_station.automation")
	await work_at("c5_station.automation","operate")
	await arrive("i2_nora",false,"i2_nora.pump")
	await work_at("i2_nora.pump","operate")
	await arrive("c7_swap",false,"c7_swap.bus")
	await work_at("c7_swap.bus","operate")
	await arrive("c10_town",false,"c10_town.console")
	await work_at("c10_town.console","operate")
	await arrive("c10_town",false,"c10_town.wind")
	await work_at("c10_town.wind","kneel")
	await arrive("c1_flat",false,"c1_flat.saturday")
	await work_at("c1_flat.saturday","listen")
	await arrive("c9_gallery")
	check(not game.stage.floor_stage.bodies.nora.body.visible,"Keep Nora off her feet until her bed has been released")
	game._choose("c9_gallery.link",0,[])
	game._skip_dialogue()
	game._choose("c9_gallery.talk",0,[])
	var nora: Node = game.stage.actors.nora
	steve = game.stage.actors.steve
	check(nora.appearance=="nora_toward_steve" and steve.appearance=="steve_toward_nora","Select the matched inward-facing art for the live reunion")
	check(steve.look_side>0 and nora.look_side<0 and nora.blocking_plane.scale.x>0,"Keep the two painted profiles looking at each other")
	check(steve.voice==game.voice and nora.voice==null,"Keep the original performance on Steve")
	await frame("reunion-steve")
	game._next_line()
	check(nora.voice==game.voice and steve.voice==null,"Switch the original voice and mouth timing to Nora")
	await frame("reunion-nora")
	var report := {"checks":checks,"failures":failures,"renderer":RenderingServer.get_current_rendering_method(),
		"captured":capture,"measurements":measurements}
	var file := FileAccess.open(output.path_join("social-staging.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  ")+"\n")
	file.close()
	print(JSON.stringify(report))
	await game.drain_audio()
	game.queue_free()
	await process_frame
	await process_frame
	quit(0 if failures.is_empty() else 1)

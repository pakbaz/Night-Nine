extends "res://render/illustrated/room.gd"
## Chapter camera, character and object staging in a shared 1600 by 900 art space.
signal approach_finished(task_id: String)
const FLOOR := preload("exploration_floor.gd")
const SOCIAL := preload("social_direction.gd")
const FLOOR_BOOK := "res://content/illustrated-floor.json"
const ROOM_FOLDER := "res://assets/illustrated/campaign/rooms/"
const MOTION_SHADER := "res://render/illustrated/keyframe_motion.gdshader"
const CHAPTER_FILM := preload("chapter_film.gd")
const FILM_CUES := "res://content/films.json"
const INSERT_FOLDER := "res://assets/illustrated/campaign/inserts/"
const FOREGROUND_FOLDER := "res://assets/illustrated/campaign/foregrounds/"
const SCENE_BOOK := "res://content/illustrated-campaign.json"
const LANDMARK_BOOK := "res://content/illustrated-landmarks.json"
const NEAR_AIR := preload("campaign_air.gdshader")
const OBJECT_EDGE := preload("campaign_prop.gdshader")
const APPEARANCE := {"agnes_original":"agnes", "lyle_copy":"lyle", "rook_copy":"rook", "dale":"pell"}

var scene_record: Dictionary
var directions: Dictionary
var opening: Vector2
var closing_mark: Vector2
var background: Sprite2D
var foreground: Sprite2D
var atmosphere: ColorRect
var curtain: ColorRect
var chapter_frames: Array[TextureRect]=[]
var departure_art_layer: TextureRect
var chapter_film: CHAPTER_FILM
var motion_material: ShaderMaterial
var incoming_frame: TextureRect
var incoming_time:=0.0
var incoming_duration:=.62
var physical_art: Array[Sprite2D] = []
var illustration_insert: Sprite2D
var creatures := {}
var floor_creatures := {}
var active_id := ""
var current_speaker := ""
var shot_clock := 0.0
var retained := ""
var scene_props := {}
var location_landmarks := {}
var high_detail := true
var floor_stage: FLOOR
var floor_directions := {}
var social_scan := 0.0
var notice := {}
var social_pair := PackedStringArray()
var preceding_pair := PackedStringArray()
var last_floor_actor := ""
var floor_dialogue := false
var working_actor := ""

static var direction_book: Dictionary
static var landmark_book: Dictionary
static var floor_book: Dictionary
static var film_book: Dictionary

func build_art(scene: Dictionary) -> void:
	scene_record = scene
	if direction_book.is_empty():
		direction_book = JSON.parse_string(FileAccess.get_file_as_string(SCENE_BOOK))
	if landmark_book.is_empty() and FileAccess.file_exists(LANDMARK_BOOK):
		landmark_book = JSON.parse_string(FileAccess.get_file_as_string(LANDMARK_BOOK))
	directions = direction_book[room_id]
	opening = art_point(directions.opening)
	closing_mark = art_point(directions.closing)
	var file := ROOM_FOLDER+room_id+".webp"
	if ResourceLoader.exists(file):
		background = picture(distant,file,Vector2.ZERO,ART)
	else:
		push_error("Missing room illustration " + file)
	if directions.has("cutaway"):
		var insert_path:=ROOM_FOLDER+str(directions.cutaway.get("file",directions.cutaway.room))+".webp"
		if ResourceLoader.exists(insert_path):
			illustration_insert=picture(distant,insert_path,Vector2.ZERO,ART)
			illustration_insert.hide()
	location_landmarks = landmark_book.get(room_id,{})
	for task: Dictionary in scene.tasks:
		var point: Array = location_landmarks.get(task.id,[])
		if point.size()<2:
			push_error("Missing painted object position: " + task.id)
			point = [.5,.5]
		targets.append(art_point(point))
		var extent:=Vector2(154,110)
		if point.size()>=4:
			extent=(ART*Vector2(point[2],point[3])).clamp(Vector2(78,62),Vector2(370,245))
		hit_sizes.append(extent)
		scene_props[task.id] = targets.back()
	var foreground_path := FOREGROUND_FOLDER+room_id+".webp"
	if floor_book.is_empty():
		floor_book = JSON.parse_string(FileAccess.get_file_as_string(FLOOR_BOOK))
	floor_directions = floor_book.get(room_id,{})
	var wide_file := "res://assets/illustrated/campaign/wide/"+room_id+".webp"
	if background and not floor_directions.is_empty() and (not floor_directions.has("landmarks") or ResourceLoader.exists(wide_file)):
		floor_stage = FLOOR.new()
		floor_stage.room_id = room_id
		distant.add_child(floor_stage)
		floor_stage.configure(floor_directions,scene.actors,background.texture,wide_file,Color.from_string(directions.light,Color.WHITE))
		for task: Dictionary in scene.tasks:
			var key: String = task.id.get_slice(".",1)
			var landmark: Array = floor_directions.get("landmarks",{}).get(key,location_landmarks[task.id])
			floor_stage.object_marks[key] = floor_directions.get("contact",{}).get(key,landmark)
		floor_stage.select_actor(scene.actors[0])
		floor_stage.arrived.connect(func(id: String): approach_finished.emit(id))
	if ResourceLoader.exists(foreground_path):
		foreground = picture(props,foreground_path,Vector2.ZERO,ART)
	if background:
		for i: int in targets.size():
			make_object_layer(i)
	if foreground:
		props.move_child(foreground,-1)
	for role: Dictionary in directions.get("creatures",[]):
		var id: String=role.id
		var folder:=CAST+id
		if not FileAccess.file_exists(folder+"/sprite.json"):
			continue
		var sheet: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(folder+"/sprite.json"))
		var base_path:=folder+"/"+str(sheet.base)
		if not ResourceLoader.exists(base_path):
			continue
		var texture:=load(base_path) as Texture2D
		var performer:=ACTOR.new()
		props.add_child(performer)
		performer.name=id
		var span:=float(role.width)*ART.x/float(texture.get_width())
		var height:=float(sheet.foot_anchor[1])*span
		performer.configure(folder,id,height,art_point(role.foot),Color.WHITE.lerp(Color.from_string(directions.light,Color.WHITE),.14),sheet)
		creatures[id]=performer
		if floor_stage and floor_directions.get("animals",{}).has(id):
			var mark: Dictionary=floor_directions.animals[id]
			var animal:=Node2D.new()
			animal.position=art_point(mark.foot)
			floor_stage.cast.add_child(animal)
			var sprite:=Sprite2D.new()
			sprite.centered=false
			sprite.texture=texture
			sprite.scale=Vector2.ONE*float(mark.width)*ART.x/texture.get_width()
			sprite.position=-Vector2(sheet.foot_anchor[0],sheet.foot_anchor[1])*sprite.scale
			sprite.modulate=Color.WHITE.lerp(Color.from_string(directions.light,Color.WHITE),.14)
			animal.add_child(sprite)
			floor_creatures[id]=animal
	update_inserts()
	var air_plane := distant if directions.has("window") else props
	atmosphere = patch_rect(air_plane,Vector2(-22,-18),ART+Vector2(44,36),NEAR_AIR)
	if directions.has("window"):
		var region: Array=directions.window
		atmosphere.material.set_shader_parameter("window",Vector4(region[0],region[1],region[2],region[3]))
	atmosphere.name="NearAtmosphere"
	atmosphere.material.set_shader_parameter("medium", int(directions.air))
	atmosphere.material.set_shader_parameter("light_color",Color.from_string(directions.light,Color.WHITE))
	atmosphere.material.set_shader_parameter("source",Vector2(directions.opening[0],directions.opening[1]))
	show_cast("")

func art_point(pair: Array) -> Vector2:
	return Vector2(pair[0],pair[1])*ART

func walking_view() -> bool:
	return floor_stage != null and floor_stage.has_actor() and not cinematic and cut_progress < 0.0 and focus < 0

func is_walking() -> bool:
	return floor_stage != null and (not floor_stage.route.is_empty() or floor_stage.pose_time>0.0)

func walk_screen(screen: Vector2) -> bool:
	return walking_view() and frame.get_global_rect().has_point(screen) and floor_stage.walk_to(distant.to_local(screen))

func talk_body_at_screen(screen: Vector2) -> String:
	if not walking_view() or not frame.get_global_rect().has_point(screen):
		return ""
	return floor_stage.body_at(distant.to_local(screen))

func walk_task(id: String) -> bool:
	return walking_view() and floor_stage.approach_task(id)

func select_walker(id: String) -> void:
	if floor_stage:
		floor_stage.select_actor(id)
		update_inserts()

func cancel_walk() -> void:
	if floor_stage:
		floor_stage.cancel()

func tick_walk(delta: float, direction: Vector2) -> void:
	if walking_view() and not paused:
		floor_stage.step(delta,direction)
		animate_prop_contact()
		if walking_view():
			tick_company(delta)

func animate_prop_contact() -> void:
	var active: String = floor_stage.active_actor
	var action: String = floor_stage.performance_action
	if not working_actor.is_empty() and (active != working_actor or action.is_empty()):
		var previous: Dictionary = floor_stage.bodies[working_actor]
		previous.sprite.rotation = 0.0
		previous.sprite.position = Vector2(0,-floor_stage.height_at(previous.body.position) * .5)
		working_actor = ""
	if action.is_empty() or floor_stage.pose_time <= 0:
		return
	working_actor = active
	var progress := clampf(1.0 - floor_stage.pose_time / SOCIAL.hold_for(action),0,1)
	var beat := smoothstep(.02,.34,progress) * (1.0 - smoothstep(.72,1.0,progress))
	var person: Dictionary = floor_stage.bodies[active]
	var turn := -1.0 if person.left else 1.0
	var angle := .010
	match action:
		"operate":
			# The second, smaller accent is the release of the control.
			angle = .020 + .006 * sin(progress * TAU)
		"kneel": angle = .030
		"listen": angle = -.009
		"read": angle = .015
		"observe": angle = .006
	var height: float = floor_stage.height_at(person.body.position)
	var rotation_ := turn * angle * beat
	# Apply the weight shift about the feet; a crouch keeps the same ground
	# contact and reference scale as the preceding standing frame.
	person.sprite.rotation = rotation_
	person.sprite.position = Vector2(0,-height * .5).rotated(rotation_)

func tick_company(delta: float) -> void:
	# A player can pass a companion, turn around, or switch roles at any time.
	# Recheck ordinary personal space at walking speed, with a wider release
	# radius so someone standing on the boundary won't repeatedly greet.
	social_scan -= delta
	var lead: String = floor_stage.active_actor
	if social_scan > 0 and lead == last_floor_actor:
		return
	social_scan = .12
	if lead != last_floor_actor:
		for member: String in notice:
			if floor_stage.bodies.has(member) and member != lead:
				floor_stage.draw_body(member,false)
		notice.clear()
		last_floor_actor = lead
	var feet: Vector2 = floor_stage.bodies[lead].body.position
	var greeting_partner := feet
	var closest := INF
	for member: String in floor_stage.bodies:
		if member == lead or not floor_stage.bodies[member].body.visible:
			continue
		var other: Vector2 = floor_stage.bodies[member].body.position
		var height: float = floor_stage.height_at(other)
		var distance := (feet-other) * Vector2(1,1.9)
		var present := notice.has(member)
		var near := distance.length() < height * (1.85 if present else 1.49)
		if not near:
			if present:
				notice.erase(member)
				floor_stage.draw_body(member,false)
			continue
		if not present:
			notice[member] = clock
		floor_stage.face_toward(member,feet)
		if floor_stage.pose_time > 0 and floor_stage.performance_action == "conversation":
			floor_stage.draw_body(member,false,listener_pose(member))
		elif clock - float(notice[member]) < .83:
			floor_stage.draw_body(member,false,"greet")
		else:
			floor_stage.draw_body(member,false)
		# Leave the lead's navigation and prop eyeline alone. At rest they can
		# meet the gaze of the closest companion who just noticed them.
		if not present and distance.length() < closest:
			greeting_partner = other
			closest = distance.length()
	if closest < INF and not is_walking() and not floor_stage.keyboard_walking and floor_stage.performance_action.is_empty():
		floor_stage.face_toward(lead,greeting_partner)

func listener_pose(id: String) -> String:
	# The investigators' evidence-listening drawing has a hand cupped to the
	# ear. Let them listen face-to-face in their relaxed stance instead.
	return "listen" if floor_stage.bodies[id].poses.has("greet") else ""

func make_object_layer(index: int) -> void:
	# Crop the actual painted prop. Separate near depth allows a small shift when
	# inspecting it, with a soft edge for the nearby table, water or ground.
	var tex_size := background.texture.get_size()
	var extent := hit_sizes[index]*Vector2(1.35,1.36)
	var rectangle := Rect2(targets[index]-extent*.5,extent).intersection(Rect2(Vector2.ZERO,ART))
	var source := Rect2(rectangle.position/ART*tex_size,rectangle.size/ART*tex_size)
	var layer := Sprite2D.new()
	layer.name = "Evidence_" + str(scene_record.tasks[index].id).get_slice(".",1)
	layer.texture=background.texture
	layer.region_enabled=true
	layer.region_rect=source
	layer.centered=false
	layer.scale=ART/tex_size
	var surface := ShaderMaterial.new()
	surface.shader=OBJECT_EDGE
	surface.set_shader_parameter("region",Vector4(source.position.x/tex_size.x,source.position.y/tex_size.y,source.size.x/tex_size.x,source.size.y/tex_size.y))
	layer.material=surface
	# Keep file landmarks in art space, independent of texture resolution.
	layer.position=rectangle.position
	# The reconstructed background fragments share a near plane behind the cast.
	# Occlusion in front of a performer requires an actual transparent silhouette.
	hull.add_child(layer)
	physical_art.append(layer)

func set_quality(profile: String) -> void:
	high_detail = profile != "performance"
	atmosphere.visible = high_detail
	if is_instance_valid(chapter_film):
		chapter_film.action.set_shader_parameter("detail", high_detail)
	if chapter_frames.size()==2:
		set_keyframe_quality()
	for plane: Sprite2D in physical_art:
		plane.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR

func actor_visible(id: String) -> bool:
	var requirement: String = directions.get("reveal_after",{}).get(id,"")
	return id in directions.company and (requirement.is_empty() or requirement in done)

func get_performer(id: String) -> Node2D:
	var authored_appearances: Dictionary=directions.get("appearances",{})
	var appearance: String = authored_appearances.get(id, APPEARANCE.get(id,id))
	if not authored_appearances.has(id) and social_pair.has("nora") and social_pair.has("steve") and room_id in ["c9_gallery","c9_wake","epilogue"]:
		var profile := "steve_toward_nora" if id == "steve" else "nora_toward_steve"
		if FileAccess.file_exists(CAST + profile + "/sprite.json") and ResourceLoader.exists(CAST + profile + "/" + profile + ".webp"):
			appearance = profile
	if actors.has(id):
		if actors[id].appearance == appearance or active_id.is_empty():
			return actors[id]
		actors[id].queue_free()
		actors.erase(id)
		cast_marks.erase(id)
	var folder := CAST+appearance
	if not FileAccess.file_exists(folder+"/sprite.json"):
		return null
	var actor_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(folder+"/sprite.json"))
	if not actor_data.has("base") or not ResourceLoader.exists(folder+"/"+str(actor_data.base)):
		return null
	var anchor: Array = actor_data.foot_anchor
	var eyes_at := Vector2(float(anchor[0]),float(anchor[1])*.20)
	var eye_span := float(anchor[1])*.067
	var eye_list: Array = actor_data.get("eye_centers",[])
	if eye_list.size()==2:
		var a := Vector2(eye_list[0][0],eye_list[0][1])
		var b := Vector2(eye_list[1][0],eye_list[1][1])
		eyes_at = (a+b)*.5
		eye_span = maxf(a.distance_to(b),16.0)
	var side: int = directions.company.find(id)
	var position_x := .37 if side%2==0 else .66
	if room_id=="c9_gallery" and id=="nora":
		position_x=.67
	var eye_target := Vector2(ART.x*position_x,ART.y*(.34 if id in ["helen","nora","agnes","iris"] else .32))
	var scale_factor := clampf(38.0/eye_span,300.0/float(anchor[1]),1520.0/float(anchor[1]))
	var foot_world := eye_target+(Vector2(anchor[0],anchor[1])-eyes_at)*scale_factor
	var performer := ACTOR.new()
	performer.name=id
	cast_plane.add_child(performer)
	var ambient := Color.WHITE.lerp(Color.from_string(directions.light,Color.WHITE),.14)
	performer.configure(folder,appearance,scale_factor*float(anchor[1]),foot_world,ambient,actor_data,str(APPEARANCE.get(id,id)))
	performer.phase = float(posmod(id.hash(),379))/100.0
	actors[id]=performer
	cast_marks[id]=eye_target
	return performer

func show_cast(id: String) -> void:
	var visible_ids: Array[String] = []
	if not id.is_empty() and actor_visible(id):
		visible_ids.append(id)
	social_pair = SOCIAL.dialogue_pair(room_id,active_id,id)
	if active_id == "c9_gallery.out.03" and "c9_gallery.link" in done:
		social_pair = PackedStringArray(["steve","nora"])
	if social_pair.size() == 2:
		for member: String in social_pair:
			if not actor_visible(member) or get_performer(member) == null:
				social_pair.clear()
				break
	for member: String in social_pair:
		if member not in visible_ids:
			visible_ids.append(member)
	var resident: String = directions.get("resident","")
	if not resident.is_empty() and actor_visible(resident) and (id==resident or (id.is_empty() and not walking_view() and not in_cutaway())):
		if resident not in visible_ids:
			visible_ids.append(resident)
	if room_id=="c9_gallery" and "c9_gallery.link" in done and (id in ["steve","nora"] or (id.is_empty() and not walking_view())):
		for partner: String in ["steve","nora"]:
			if partner not in visible_ids:
				visible_ids.append(partner)
	for member: String in visible_ids:
		get_performer(member)
	for member: String in actors.keys():
		var person: Node = actors[member]
		person.visible=member in visible_ids
		if person.visible:
			var body: Sprite2D = person.body
			if not person.has_meta("portrait_origin"):
				person.set_meta("portrait_origin",person.position)
			if not person.has_meta("solo_eyes"):
				person.set_meta("solo_eyes",cast_marks[member])
			if member in social_pair:
				var left := member == social_pair[0]
				var mark := Vector2(ART.x * (.305 if left else .70), float(person.get_meta("solo_eyes").y))
				cast_marks[member] = mark
				person.take_mark(mark,1.0 if left else -1.0,"speaker" if member == id else "listener",clock)
			else:
				person.clear_mark(person.get_meta("portrait_origin"))
				cast_marks[member] = person.get_meta("solo_eyes")
			if not cinematic and not walking_view():
				var lower_edge: float = person.position.y + (body.position.y + body.texture.get_height()) * person.resting_scale.y
				person.position.y += maxf(0.0,ART.y+12.0-lower_edge)
		# Keep the immediately preceding take ready for shot/reverse shot. Returning
		# to exploration releases other incidental portraits in crowded scenes.
		if not person.visible and member!=retained and not (cinematic and member in preceding_pair):
			person.queue_free()
			actors.erase(member)
			cast_marks.erase(member)

func set_focus(index: int) -> void:
	focus=index
	if floor_stage or directions.get("cutaway",{}).has("inspect"):
		update_inserts()
		if not cinematic:
			show_cast("")
	if index<0 and not cinematic and art_ready:
		# Restore the whole clickable canvas in the same beat as the controls.
		# A tight insert can otherwise leave the next object outside the viewport.
		aim=HALF
		zoom=1.028
		transform_planes()

func in_cutaway() -> bool:
	var cutaway: Dictionary=directions.get("cutaway",{})
	if not active_id.is_empty():
		return active_id in cutaway.get("lines",[]) or (cutaway.has("group") and active_id.begins_with(str(cutaway.group)+"."))
	var task_in_view: bool = focus >= 0 and focus < scene_record.tasks.size() and scene_record.tasks[focus].id == cutaway.get("inspect","")
	return task_in_view or (cutaway.has("after") and cutaway.after in done)

func update_inserts() -> void:
	var away := in_cutaway()
	var exploring := walking_view() or floor_dialogue
	if floor_stage:
		floor_stage.visible = exploring
		floor_stage.set_story(done,directions.get("reveal_after",{}))
	if is_instance_valid(illustration_insert):
		illustration_insert.visible=away
	for layer: Sprite2D in physical_art:
		layer.visible=not away and not exploring
	if is_instance_valid(foreground):
		foreground.visible=not away and not (exploring and floor_stage.wide != null)
	for role: Dictionary in directions.get("creatures",[]):
		if creatures.has(role.id):
			var in_shot: bool=not role.has("lines") or active_id in role.lines
			var visible_now: bool=in_shot and (not role.has("after") or role.after in done)
			creatures[role.id].visible=visible_now and not (exploring and floor_creatures.has(role.id))
			if floor_creatures.has(role.id):
				floor_creatures[role.id].visible=visible_now and exploring

func sync_story(completed: Array) -> void:
	done=completed
	update_inserts()
	if dialogue_shot.is_empty():
		show_cast("")

func begin_dialogue(line: Dictionary, voice: AudioStreamPlayer, _take: Dictionary, timing: Dictionary) -> void:
	var id: String = line.speaker
	active_id=line.id
	update_inserts()
	var recorded: bool = line.get("delivery","live")!="live" or line.id in directions.get("off_camera_lines",[])
	var detail: Dictionary=directions.get("detail_shots",{}).get(line.id,{})
	var on_camera := not recorded and detail.is_empty() and actor_visible(id)
	shot_clock=0.0
	current_speaker=id if on_camera else ""
	show_cast(current_speaker)
	cast_plane.visible=detail.is_empty()
	var shot_type := "arrival" if not scene_record.intro.is_empty() and line.id==scene_record.intro.front() else "speaker"
	if recorded or not actors.has(current_speaker):
		shot_type = "arrival" if not scene_record.intro.is_empty() and line.id==scene_record.intro.front() else "insert"
	if shot_type=="speaker" and line.id in scene_record.outro:
		shot_type="farewell"
	dialogue_shot={"speaker":id,"type":shot_type,"recorded":recorded}
	if actors.has(current_speaker):
		actors[current_speaker].speak(voice,timing)
		camera_goal=cast_marks[current_speaker]
		if social_pair.size() == 2:
			# Favor the current speaker without cutting the listener out.
			camera_goal = HALF.lerp(camera_goal,.55)
	else:
		camera_goal=targets[focus] if focus>=0 and focus<targets.size() else (closing_mark if line.id in scene_record.outro else opening)
	if actors.get(current_speaker)==null:
		var inserts: Dictionary=directions.get("inserts",{})
		var group: String=str(line.id).get_basename()
		var mark: Variant=inserts.get(line.id,inserts.get(group))
		if mark is String and scene_props.has(mark):
			camera_goal=scene_props[mark]
		elif mark is Array:
			camera_goal=art_point(mark)
	if not detail.is_empty():
		dialogue_shot.type="detail"
		camera_goal=art_point(detail.target)
		close_scale=float(detail.zoom)
		if detail.get("cut",false):
			zoom=close_scale
			var bounds:=HALF*(1.0-1.0/zoom)
			aim=camera_goal.clamp(HALF-bounds,HALF+bounds)
			transform_planes()
	if shot_type=="arrival":
		aim=HALF.lerp(opening,.22)
		zoom=1.18
	if active_id in SOCIAL.WIDE_LINES and social_pair.size() == 2 and floor_stage:
		var a: Dictionary = floor_stage.bodies.get(social_pair[0],{})
		var b: Dictionary = floor_stage.bodies.get(social_pair[1],{})
		if not a.is_empty() and not b.is_empty() and a.body.visible and b.body.visible:
			floor_dialogue = true
			cast_plane.hide()
			update_inserts()
			floor_stage.face_toward(social_pair[0],b.body.position)
			floor_stage.face_toward(social_pair[1],a.body.position)
			for participant: String in social_pair:
				floor_stage.draw_body(participant,false,"talk" if participant == id else listener_pose(participant))
			aim = HALF
			zoom = 1.028
			transform_planes()

func finish_floor_exchange() -> void:
	if not floor_dialogue:
		return
	for participant: String in social_pair:
		floor_stage.draw_body(participant,false)
	floor_dialogue = false
	cast_plane.show()
	update_inserts()

func end_dialogue() -> void:
	finish_floor_exchange()
	if not social_pair.is_empty():
		preceding_pair = social_pair.duplicate()
	active_id=""
	update_inserts()
	cast_plane.show()
	retained=current_speaker
	current_speaker=""
	super.end_dialogue()
	show_cast("")

func image_layer(texture: Texture2D, label: String) -> TextureRect:
	var layer:=TextureRect.new()
	layer.name=label
	layer.texture=texture
	layer.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
	layer.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_COVERED
	layer.mouse_filter=Control.MOUSE_FILTER_IGNORE
	frame.add_child(layer)
	layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return layer

func show_departure_art(path: String) -> void:
	if is_instance_valid(departure_art_layer) or path.is_empty() or not ResourceLoader.exists(path):
		return
	var painting:=load(path) as Texture2D
	if painting:
		departure_art_layer=image_layer(painting,"DepartureArt")
		departure_art_layer.modulate.a=1.0
		chapter_frames=[departure_art_layer]

func begin_departure_cut() -> void:
	cut_progress=0.0
	show_cast("")
	var authored_departure: String=scene_record.get("departure_art","")
	if not authored_departure.is_empty():
		show_departure_art(authored_departure)
	elif directions.get("chapter_insert",false):
		for suffix: String in ["","-motion"]:
			var path:=INSERT_FOLDER+room_id+suffix+".webp"
			if ResourceLoader.exists(path):
				var painting:=load(path) as Texture2D
				if painting:
					var layer:=image_layer(painting,"ChapterFrame%d"%chapter_frames.size())
					layer.modulate.a=0.0
					chapter_frames.append(layer)
	elif directions.has("departure_painting"):
		var painting := load(INSERT_FOLDER + room_id + ".webp") as Texture2D
		if painting:
			var layer := image_layer(painting, str(directions.departure_painting))
			layer.modulate.a = 0.0
			chapter_frames.append(layer)
	if not chapter_frames.is_empty():
		if chapter_frames.size()==2:
			set_keyframe_quality()
		if film_book.is_empty():
			film_book = JSON.parse_string(FileAccess.get_file_as_string(FILM_CUES))
		if film_book.has(room_id) and ResourceLoader.exists("res://assets/illustrated/campaign/" + str(film_book[room_id].plate) + ".webp"):
			chapter_film = CHAPTER_FILM.new()
			frame.add_child(chapter_film)
			chapter_film.configure(film_book[room_id],high_detail)
		return
	curtain=ColorRect.new()
	curtain.name="FadeToNextScene"
	curtain.color=Color(0.012,0.018,0.024,0)
	curtain.mouse_filter=Control.MOUSE_FILTER_IGNORE
	frame.add_child(curtain)
	curtain.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func set_keyframe_quality() -> void:
	var later:=chapter_frames[1]
	if not high_detail:
		later.material=null
		later.show()
		return
	if not motion_material:
		var field_path:=INSERT_FOLDER+room_id+"-flow.png"
		if not ResourceLoader.exists(field_path) or not ResourceLoader.exists(MOTION_SHADER):
			return
		var field:=load(field_path) as Texture2D
		var blend:=load(MOTION_SHADER) as Shader
		if not field or not blend:
			return
		motion_material=ShaderMaterial.new()
		motion_material.shader=blend
		motion_material.set_shader_parameter("first_image",chapter_frames[0].texture)
		motion_material.set_shader_parameter("motion_vectors",field)
	later.material=motion_material
	later.visible=cut_progress>=.14

func departure_duration() -> float:
	if is_instance_valid(chapter_film):
		return float(chapter_film.record.duration)
	return 3.85 if chapter_frames.size()==2 else (4.4 if chapter_frames.size()==1 else 2.15)

func set_departure_progress(value: float) -> void:
	cut_progress=clampf(value,0.0,1.0)
	if chapter_frames.is_empty():
		curtain.color.a=smoothstep(.68,1.0,cut_progress)
		return
	# Hold the first drawing, then let the moving light, hand or figure travel
	# between two corresponding poses. Keep the final frame for the next room.
	var drawing_time := minf(1.0, cut_progress / .48) if is_instance_valid(chapter_film) and chapter_frames.size()==2 else cut_progress
	var push:=1.0+.036*smoothstep(0.0,1.0,drawing_time) if high_detail else 1.0
	for layer: TextureRect in chapter_frames:
		layer.pivot_offset=frame.size*.5
		layer.scale=Vector2.ONE*push
	chapter_frames[0].modulate.a=1.0 if is_instance_valid(departure_art_layer) else smoothstep(0.0,.14,drawing_time)
	if chapter_frames.size()>1:
		var morph:=smoothstep(.30,.78,drawing_time)
		if chapter_frames[1].material:
			motion_material.set_shader_parameter("progress",morph)
			chapter_frames[1].visible=drawing_time>=.14
			chapter_frames[1].modulate.a=1.0
		else:
			chapter_frames[1].modulate.a=morph
	if is_instance_valid(chapter_film):
		chapter_film.advance(cut_progress)
	if drawing_time>=.14:
		for plane: Node2D in [distant,hull,cast_plane,props]:
			plane.hide()

func outgoing_frame() -> Dictionary:
	if chapter_frames.is_empty():
		return {}
	var last: TextureRect=chapter_frames.back()
	var state := {"texture":last.texture,"scale":last.scale}
	if is_instance_valid(chapter_film) and chapter_film.visible:
		# Keep ownership until another room consumes the pose. Storybooks and
		# flashbacks have no dissolve, so the departing stage must free its film.
		state.film = chapter_film
		state.scale = Vector2.ONE
	return state

func receive_frame(state: Dictionary) -> void:
	incoming_frame=image_layer(state.texture,"IncomingChapterDissolve")
	incoming_frame.pivot_offset=frame.size*.5
	incoming_frame.scale=state.scale
	if state.has("film"):
		state.film.reparent(incoming_frame, false)
		state.film.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	incoming_time=0.0
	incoming_duration=.62 if high_detail else .24

func _process(delta: float) -> void:
	if not art_ready or paused:
		return
	clock+=delta
	shot_clock+=delta
	if is_instance_valid(incoming_frame):
		incoming_time+=delta
		incoming_frame.pivot_offset=frame.size*.5
		incoming_frame.modulate.a=1.0-smoothstep(0.0,incoming_duration,incoming_time)
		if incoming_time>=incoming_duration:
			incoming_frame.queue_free()
			incoming_frame=null
	if not chapter_frames.is_empty() and cut_progress>=.14:
		return
	var target:=HALF
	var magnitude:=1.028
	if floor_dialogue and shot_clock >= 1.76:
		finish_floor_exchange()
	if cut_progress>=0.0:
		target=HALF.lerp(closing_mark,.31)
		magnitude=1.05+.20*smoothstep(0.0,.85,cut_progress)
	elif cinematic and not floor_dialogue and not dialogue_shot.is_empty():
		match str(dialogue_shot.type):
			"arrival":
				var track:=smoothstep(0.0,3.0,shot_clock)
				target=HALF.lerp(opening.lerp(camera_goal,track),.31)
				magnitude=lerpf(1.17,1.26,track)
			"speaker","farewell":
				target=HALF.lerp(camera_goal,.47)
				magnitude=1.26+.024*smoothstep(0.0,4.5,shot_clock)
			"detail":
				target=camera_goal
				magnitude=close_scale
			"insert":
				target=HALF.lerp(camera_goal,.36)
				magnitude=1.16+.055*smoothstep(0.0,3.4,shot_clock)
	elif focus>=0 and focus<targets.size():
		target=HALF.lerp(targets[focus],.31)
		magnitude=1.16
	for id: String in creatures:
		if creatures[id].visible:
			creatures[id].animate(clock)
	move_camera(delta,target,magnitude)
	if background:
		# Clip tiny alignment differences at the prop's feathered perimeter; each
		# painted object's pick surface and near visual follow the same transform.
		for i: int in physical_art.size():
			var layer:=physical_art[i]
			var near_center:=hull.to_local(distant.to_global(targets[i]))
			var offset:=layer.region_rect.size*.5*layer.scale
			layer.position=near_center-offset+pointer*.025
	if high_detail:
		atmosphere.material.set_shader_parameter("seconds",clock)

func project_target(index: int) -> Vector2:
	if walking_view() and floor_stage.wide:
		var mark: Array = floor_directions.landmarks[scene_record.tasks[index].id.get_slice(".",1)]
		return distant.to_global(art_point(mark))
	if index<physical_art.size():
		var object:=physical_art[index]
		return object.to_global(object.region_rect.size*.5)
	return distant.to_global(targets[index])

func hotspot_size(index: int) -> Vector2:
	if walking_view() and floor_stage.wide:
		var mark: Array = floor_directions.landmarks[scene_record.tasks[index].id.get_slice(".",1)]
		return ART*Vector2(mark[2],mark[3])*distant.scale
	return hit_sizes[index]*distant.scale

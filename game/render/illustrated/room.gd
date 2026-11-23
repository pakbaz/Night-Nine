extends Control
## A single illustrated prologue room, in 1600×900 art coordinates.
const ART := Vector2(1600,900)
const HALF := ART * 0.5
const ROOMS := "res://assets/illustrated/rooms/"
const CAST := "res://assets/illustrated/cast/"
const DELEGATE := preload("painted_delegate.gd")
const ACTOR := preload("illustrated_actor.gd")
const WIND := preload("terrace.gdshader")
const RECORDER := preload("recorder.gdshader")
const HULL := preload("boat_depth.gdshader")
const DEPARTURE := preload("departure.gdshader")
const WATER := preload("bay_surface.gdshader")
const UNDERLIGHT := preload("underlight.gdshader")
const GRADE := preload("edge_light.gdshader")
const PIGMENT := preload("pigment.gdshader")

var targets: Array[Vector2] = []
var hit_sizes: Array[Vector2] = []
var actors := {}
var dialogue_shot := {}
var cinematic := false
var style := ""
var frame := Control.new()
var arrival_shade: ColorRect
const ARRIVAL_SECONDS := .9
var distant := Node2D.new()
var hull := Node2D.new()
var cast_plane := Node2D.new()
var props := Node2D.new()
var clock := 0.0
var aim := HALF
var zoom := 1.0
var pointer := Vector2.ZERO
var paused := false
var focus := -1
var grade: ShaderMaterial
var recorder: ShaderMaterial
var dial_material: ShaderMaterial
var water: ShaderMaterial
var tide := 0.0
var playing_recorder := false
var done: Array = []
var night_light := false
var underlight_material: ShaderMaterial
var room_id := ""
var cast_marks := {}
var seats := {}
var gaze_targets := {}
var meeting_recorder_mark := Vector2.ZERO
var seated_gaze := {}
var camera_goal := HALF
var close_scale := 1.18
var art_ready := false
var cut_progress := -1.0
var cut_overlay: ColorRect

func build(scene: Dictionary, profile: String) -> void:
	room_id = scene.id
	style = scene.style
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	frame.name = "PhotoFrame"
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.clip_contents = true
	add_child(frame)
	for plane: Node2D in [distant,hull,cast_plane,props]:
		frame.add_child(plane)
	build_art(scene)
	set_quality(profile)
	grade = ShaderMaterial.new()
	grade.shader = GRADE
	var edge := ColorRect.new()
	edge.name = "CaptionShade"
	edge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	edge.material = grade
	frame.add_child(edge)
	edge.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# Every room fades up from the dark the previous scene faded into.
	arrival_shade = ColorRect.new()
	arrival_shade.name = "ArrivalShade"
	arrival_shade.color = Color(0.012, 0.018, 0.024, 1.0)
	arrival_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(arrival_shade)
	arrival_shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	art_ready = true
	resized.connect(layout)
	layout()

func build_art(_scene: Dictionary) -> void:
	match room_id:
		"p_veyr": build_veyr()
		"p_meeting": build_meeting()
		"p_bay": build_bay()

func set_quality(_profile: String) -> void:
	pass

func picture(parent: Node, file: String, at: Vector2, dimensions: Vector2) -> Sprite2D:
	var image := Sprite2D.new()
	image.name = file.get_file().get_basename()
	image.texture = load(file) as Texture2D
	image.centered = false
	image.position = at
	if image.texture:
		image.scale = dimensions/image.texture.get_size()
	parent.add_child(image)
	return image

func painted_room(file: String) -> void:
	picture(distant,ROOMS+file+".png",Vector2(-24,-13.5),ART*1.03)

func actor_at(actor_id: String, height: float, foot: Vector2, tint: Color, face: Vector2) -> void:
	var person := ACTOR.new()
	person.name = actor_id
	cast_plane.add_child(person)
	person.configure(CAST+actor_id,actor_id,height,foot,tint)
	actors[actor_id] = person
	cast_marks[actor_id] = face

func patch_rect(parent: Node, at: Vector2, dimensions: Vector2, shader: Shader) -> ColorRect:
	var rect := ColorRect.new()
	rect.position = at
	rect.size = dimensions
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var surface := ShaderMaterial.new()
	surface.shader = shader
	rect.material = surface
	parent.add_child(rect)
	return rect

func build_veyr() -> void:
	painted_room("veyr")
	patch_rect(cast_plane,Vector2(-250,798),Vector2(2100,242),WIND)
	actor_at("archivist",1375,Vector2(652,1480),Color.WHITE,Vector2(652,242))
	var surface := ShaderMaterial.new()
	surface.shader = PIGMENT
	for sprite: Node in actors.archivist.get_children():
		sprite.material = surface
	var rail := picture(props,ROOMS+"veyr-recorder.png",Vector2(-10,353),Vector2(1630,543))
	recorder = ShaderMaterial.new()
	recorder.shader = RECORDER
	rail.material = recorder
	# Exact UV landmarks on the meter and the left transport key.
	for uv: Vector2 in [Vector2(.747,.782),Vector2(.576,.694)]:
		targets.append(rail.position + uv * Vector2(1630,543))
	hit_sizes.assign([Vector2(165,89),Vector2(199,106)])

func build_meeting() -> void:
	painted_room("meeting")
	var backdrop: Sprite2D = distant.get_child(0)
	for actor_id: String in ["general_us","general_cn"]:
		var delegate := DELEGATE.new()
		delegate.name = actor_id
		backdrop.add_child(delegate)
		delegate.configure_delegate(actor_id)
		actors[actor_id] = delegate
	cast_marks["general_us"] = Vector2(230,358)
	cast_marks["general_cn"] = Vector2(1395,369)
	actor_at("helen",625,Vector2(754,845),Color("f1ddba"),Vector2(738,299))
	picture(props,ROOMS+"meeting-foreground.png",Vector2(-12,230),Vector2(1624,755))
	targets.assign([Vector2(408,745),Vector2(824,733)])
	hit_sizes.assign([Vector2(195,118),Vector2(190,108)])
	meeting_recorder_mark=Vector2(1260,754)
	seat("helen",false)
	direct_attention()

func build_bay() -> void:
	painted_room("bay")
	water = ShaderMaterial.new()
	water.shader = WATER
	distant.get_child(0).material = water
	picture(hull,ROOMS+"bay-foreground.png",Vector2.ZERO,ART)
	actor_at("frank",559,Vector2(541,747),Color("b9c9d8"),Vector2(507,270))
	actor_at("helen",565,Vector2(1047,762),Color("c2cedc"),Vector2(1019,285))
	var foreground := picture(props,ROOMS+"bay-foreground.png",Vector2.ZERO,ART)
	dial_material = ShaderMaterial.new()
	dial_material.shader = HULL
	foreground.material = dial_material
	build_needle()
	targets.assign([Vector2(595,658),Vector2(1060,654)])
	hit_sizes.assign([Vector2(190,115),Vector2(210,106)])
	seat("frank",false)
	seat("helen",true)
	direct_attention()

func seat(id: String, faces_left: bool) -> void:
	var person: Node2D = actors[id]
	person.prepare_blocking()
	seats[id] = person.position
	person.base_ground = person.position
	person.blocking_plane.scale.x = -1.0 if faces_left else 1.0
	seated_gaze[id] = Vector2.ZERO

func direct_attention(speaker_id: String = "", line_id: String = "") -> void:
	for id: String in seats:
		var person: Node2D = actors[id]
		var mark: Vector2 = cast_marks[id]
		var target: Vector2
		if focus >= 0 and speaker_id.is_empty():
			target = targets[focus]
		elif room_id == "p_meeting":
			if line_id == "p_meeting.record.01":
				target = meeting_recorder_mark
			elif speaker_id == "general_us" or line_id == "p_meeting.terms.01":
				target = cast_marks.general_us
			else:
				target = cast_marks.general_cn
		elif line_id == "p_bay.tune.01":
			target = targets[0]
		elif id == "helen" and line_id == "p_bay.out.01":
			target = targets[1]
		else:
			target = cast_marks.helen if id == "frank" else cast_marks.frank
		var look := (target-mark).normalized()
		person.look_side = signf(look.x)
		person.base_ground = seats[id]
		person.role = "" if speaker_id.is_empty() else ("speaker" if id == speaker_id else "listener")
		person.beat_start = clock
		gaze_targets[id] = look

func animate_seated_gaze(delta: float) -> void:
	for id: String in seats:
		var person: Node = actors[id]
		var look: Vector2 = seated_gaze[id].lerp(gaze_targets[id],1.0-exp(-delta*12.0))
		seated_gaze[id] = look
		if person.eye_shader:
			var local := Vector2(look.x*person.blocking_plane.scale.x*.045,look.y*.026)
			person.eye_shader.set_shader_parameter("eye_travel",local*person.eye_span/person.body.texture.get_size())

func layout() -> void:
	if not art_ready:
		return
	var fit := minf(size.x/ART.x,size.y/ART.y)
	frame.size = ART*fit
	frame.position = (size-frame.size)*.5
	transform_planes()

func transform_planes() -> void:
	var fit := frame.size.x/ART.x
	for plane: Node2D in [distant,hull,cast_plane,props]:
		var depth := .87 if plane == distant else (1.0 if plane == cast_plane else 1.03)
		var scale_factor := 1.0 + (zoom-1.0)*depth
		plane.scale = Vector2.ONE * fit * scale_factor
		plane.position = frame.size*.5 - (HALF+(aim-HALF)*depth)*fit*scale_factor + pointer*(depth-.92)*fit

func begin_departure_cut() -> void:
	cut_progress=0.0
	if room_id in ["p_meeting", "p_bay"]:
		var cutaway := TextureRect.new()
		var is_bay := room_id == "p_bay"
		cutaway.name = "UnderTheGunwale" if is_bay else "SignalExterior"
		cutaway.texture = load(ROOMS + ("bay-underlight.png" if is_bay else "meeting-exterior.png"))
		cutaway.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cutaway.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		cutaway.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		if is_bay:
			underlight_material = ShaderMaterial.new()
			underlight_material.shader = UNDERLIGHT
			cutaway.material = underlight_material
		frame.add_child(cutaway)
		cutaway.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cut_overlay=patch_rect(frame,Vector2.ZERO,frame.size,DEPARTURE)
	cut_overlay.name="RisingLight"
	cut_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cut_overlay.material.set_shader_parameter("scene_kind",["p_veyr","p_meeting","p_bay"].find(room_id))
	if room_id=="p_bay":
		night_light=true

func set_departure_progress(value: float) -> void:
	cut_progress=clampf(value,0.0,1.0)
	if underlight_material:
		underlight_material.set_shader_parameter("progress", cut_progress)
	cut_overlay.material.set_shader_parameter("progress",cut_progress)

func set_focus(index: int) -> void:
	focus = index
	if dialogue_shot.is_empty():
		direct_attention()

func sync_story(completed: Array) -> void:
	done = completed
	if room_id == "p_bay" and "p_bay.tune" in done:
		set_frequency(815)
	if room_id == "p_bay" and "p_bay.message" in done:
		night_light = true

func talk_body_at_screen(screen: Vector2) -> String:
	for id: String in actors:
		if actors[id].hit(screen):
			return id
	return ""

## Frank's radio needle, measured on the 1672 x 941 bay plate: where it pivots, how long it
## is, how far it swings, the glass it sits behind and the glowing scale line it crosses.
const PLATE := Vector2(1672,941)
const NEEDLE_PIVOT := Vector2(524.0,618.5)
const NEEDLE_LENGTH := 64.0
const NEEDLE_SWING := Vector2(-46.0,42.0)
const SCALE_CENTRE_X := 521.0
const DIAL_GLASS := Rect2(Vector2(434,546),Vector2(176,74))
const SCALE_ARC := Vector3(0.002321,-2.5116,1252.20)
## Where the radio's needle points: 0 at 810 kHz, 1 at 820 kHz.
var needle_value := 0.0
var needle_shown := 0.0
var needle: Sprite2D
var needle_shadow: Sprite2D
var dial_light: Sprite2D
var dial_core: Sprite2D

func set_frequency(khz: int) -> void:
	needle_value = clampf((khz-810)/10.0,0.0,1.0)

## The needle's target angle from vertical, in radians.
func needle_angle() -> float:
	return needle_angle_at(needle_value)

func needle_angle_at(value: float) -> float:
	return deg_to_rad(lerpf(NEEDLE_SWING.x, NEEDLE_SWING.y, value))

func needle_pivot_plate() -> Vector2:
	return NEEDLE_PIVOT

func needle_tip_plate(value: float) -> Vector2:
	return NEEDLE_PIVOT+Vector2.UP.rotated(needle_angle_at(value))*NEEDLE_LENGTH

func scale_arc_y(x: float) -> float:
	return SCALE_ARC.x*x*x+SCALE_ARC.y*x+SCALE_ARC.z

## Where the needle crosses the bright upper scale line: the green light sits there.
func dial_light_plate(value: float) -> Vector2:
	var toward := Vector2.UP.rotated(needle_angle_at(value))
	var reach := 20.0
	while reach < NEEDLE_LENGTH:
		var point := NEEDLE_PIVOT+toward*reach
		if point.y <= scale_arc_y(point.x):
			return point
		reach += .25
	return NEEDLE_PIVOT+toward*NEEDLE_LENGTH

func plate_point(point: Vector2) -> Vector2:
	return point*ART/PLATE

## The needle is cut from the painting's own needle (tools/build-bay-needle.py): two
## texture pixels per plate pixel, pivot at the bottom centre. A soft green light rides the
## phosphor scale where the needle crosses it.
func build_needle() -> void:
	var texture_scale := ART/PLATE/2.0
	var additive := CanvasItemMaterial.new()
	additive.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	# A soft halo along the scale and a bright core where the needle crosses it.
	dial_light = Sprite2D.new()
	dial_light.texture = load(ROOMS+"bay-dial-glow.png")
	dial_light.material = additive
	dial_light.modulate = Color(.34,1.0,.30,.95)
	dial_light.scale = ART/PLATE*Vector2(34.0/72.0,13.0/48.0)
	props.add_child(dial_light)
	dial_core = Sprite2D.new()
	dial_core.texture = dial_light.texture
	dial_core.material = additive
	dial_core.modulate = Color(.78,1.0,.66,1.0)
	dial_core.scale = ART/PLATE*Vector2(9.0/72.0,5.0/48.0)
	props.add_child(dial_core)
	var needle_texture: Texture2D = load(ROOMS+"bay-needle.png")
	var pivot := Vector2(needle_texture.get_width()*.5,needle_texture.get_height()-1)
	for shadow: bool in [true,false]:
		var sprite := Sprite2D.new()
		sprite.texture = needle_texture
		sprite.centered = false
		sprite.offset = -pivot
		sprite.scale = texture_scale
		sprite.position = plate_point(NEEDLE_PIVOT+(Vector2(1.2,1.0) if shadow else Vector2.ZERO))
		if shadow:
			sprite.modulate = Color(0,0,0,.3)
			needle_shadow = sprite
		else:
			needle = sprite
		props.add_child(sprite)
	var cap := Sprite2D.new()
	cap.texture = load(ROOMS+"bay-needle-cap.png")
	cap.scale = texture_scale
	cap.position = plate_point(NEEDLE_PIVOT)
	props.add_child(cap)
	needle_shown = needle_value
	place_needle()

func place_needle() -> void:
	if not needle:
		return
	needle.rotation = needle_angle_at(needle_shown)
	needle_shadow.rotation = needle.rotation
	var light := dial_light_plate(needle_shown)
	dial_light.position = plate_point(light)
	dial_light.rotation = atan(2.0*SCALE_ARC.x*light.x+SCALE_ARC.y)
	dial_core.position = dial_light.position
	dial_core.rotation = dial_light.rotation
	# A slow phosphor shimmer, never a flash.
	var shimmer := .92+.08*sin(clock*2.3)
	dial_light.modulate.a = .95*shimmer
	dial_core.modulate.a = shimmer

## The painted plate carries no needle of its own; only the drawn one shows.
func painted_needle_hidden() -> bool:
	var plate: Image = (load(ROOMS + "bay-foreground.png") as Texture2D).get_image()
	var orange := 0
	for y: int in range(527, 612):
		for x: int in range(520, 600):
			var c := plate.get_pixel(x, y)
			if c.r > .59 and c.r > c.g * 1.3 and c.b < .47 and c.g > .2:
				orange += 1
	return orange < 12

func begin_dialogue(line: Dictionary, voice: AudioStreamPlayer, _take: Dictionary, timing: Dictionary) -> void:
	var actor_id: String = line.speaker
	direct_attention(actor_id,line.get("id",""))
	dialogue_shot = {"speaker":actor_id}
	camera_goal = cast_marks.get(actor_id,HALF)
	close_scale = 1.22 if cast_marks.has(actor_id) else 1.06
	if line.get("delivery","live") == "live" and actors.has(actor_id):
		actors[actor_id].speak(voice,timing)
	if room_id == "p_bay" and (line.get("audio","") == "recording.voicemail" or line.get("audio","") == "p_bay.out.02"):
		night_light = true

func end_dialogue() -> void:
	dialogue_shot.clear()
	direct_attention()
	for id: String in seats:
		actors[id].position = seats[id]
	for person: Node in actors.values():
		person.silence()

func set_performance_paused(on: bool) -> void:
	paused = on

func set_recorder_running(on: bool) -> void:
	playing_recorder = on

func fade_arrival(delta: float) -> void:
	if is_instance_valid(arrival_shade):
		arrival_shade.color.a = maxf(0.0, arrival_shade.color.a - delta / ARRIVAL_SECONDS)
		if arrival_shade.color.a <= 0.0:
			arrival_shade.queue_free()
			arrival_shade = null

func _process(delta: float) -> void:
	if not art_ready or paused:
		return
	fade_arrival(delta)
	clock += delta
	animate_seated_gaze(delta)
	var target := HALF
	var magnitude := 1.0
	if cut_progress >= 0.0 and room_id=="p_veyr":
		magnitude=1.13
		target=HALF+Vector2(30,-65)*smoothstep(0.0,.65,cut_progress)
	elif cinematic and not dialogue_shot.is_empty():
		magnitude = close_scale
		target = HALF.lerp(camera_goal,.40)
	elif focus >= 0 and focus < targets.size():
		magnitude = 1.075
		target = HALF.lerp(targets[focus],.18)
	move_camera(delta,target,magnitude)
	if recorder:
		recorder.set_shader_parameter("signal",.45+.48*sin(clock*10.8) if playing_recorder or "p_veyr.levels" in done else .12)
	if room_id == "p_bay":
		# The needle swings to the dial like a real meter: quick, then easing in.
		needle_shown = lerpf(needle_shown,needle_value,1.0-exp(-delta*7.0))
		place_needle()
		tide = lerpf(tide, .9 if night_light else .05,1.0-exp(-delta*.8))
		water.set_shader_parameter("seconds",clock)
		water.set_shader_parameter("shimmer",tide)

func move_camera(delta: float, target: Vector2, magnitude: float) -> void:
	# Keep the edges of the background outside the letterbox at every camera position.
	var extent := HALF*(1.0-1.0/magnitude)
	target = target.clamp(HALF-extent,HALF+extent)
	var blend := 1.0-exp(-delta*3.4)
	aim = aim.lerp(target,blend)
	zoom = lerpf(zoom,magnitude,blend)
	var mouse := (get_local_mouse_position()/size.max(Vector2.ONE)-Vector2(.5,.5)).clamp(-Vector2.ONE,Vector2.ONE)
	pointer = pointer.lerp(mouse*Vector2(27,13),blend)
	transform_planes()
	for person: Node in actors.values():
		person.animate(clock)

func project_target(index: int) -> Vector2:
	return props.to_global(targets[index])

func hotspot_size(index: int) -> Vector2:
	return hit_sizes[index]*props.scale

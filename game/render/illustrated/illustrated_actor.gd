extends Node2D
## Face patches share the neutral illustration's original pixel coordinates.
const EYE_GAZE := preload("portrait_eyes.gdshader")
var manifest: Dictionary
var body: Sprite2D
var eyes: Sprite2D
var mouth: Sprite2D
var resting_scale := Vector2.ONE
var foot := Vector2.ZERO
var voice: AudioStreamPlayer
var cues: Array = []
var last_eye := ""
var last_mouth := ""
var phase := 0.0
var appearance := ""
var base_identity := ""
var blocking_plane: Node2D
var eye_shader: ShaderMaterial
var eye_offset := Vector2.ZERO
var eye_span := 0.0
var eye_line := 0.0
var base_ground := Vector2.ZERO
var look_side := 0.0
var role := ""
var beat_start := 0.0

func configure(folder: String, actor_id: String, height: float, ground: Vector2, tint: Color,
		prepared: Dictionary = {}, identity: String = "") -> void:
	var metadata := folder + "/sprite.json"
	if not prepared.is_empty():
		manifest=prepared
	elif FileAccess.file_exists(metadata):
		manifest = JSON.parse_string(FileAccess.get_file_as_string(metadata))
	else:
		var portrait := load(folder + "/" + actor_id + ".png") as Texture2D
		manifest = {"base":actor_id+".png","foot_anchor":[portrait.get_width()*.5,portrait.get_height()]}
	var baseline: Array = manifest.foot_anchor
	foot = Vector2(baseline[0],baseline[1])
	position = ground
	resting_scale = Vector2.ONE * height / maxf(foot.y,1.0)
	scale = resting_scale
	appearance = actor_id
	base_identity = actor_id if identity.is_empty() else identity
	phase = float(posmod(actor_id.hash(),379))/100.0
	body = Sprite2D.new()
	body.name = "Body"
	body.centered = false
	body.position = -foot
	body.texture = load(folder + "/" + str(manifest.base))
	add_child(body)
	modulate = tint
	if manifest.has("atlas"):
		var atlas := load(folder + "/" + str(manifest.atlas)) as Texture2D
		eyes = patch(atlas)
		mouth = patch(atlas)

func prepare_blocking() -> void:
	if blocking_plane:
		return
	blocking_plane = Node2D.new()
	add_child(blocking_plane)
	for layer: Sprite2D in [body, eyes, mouth]:
		if is_instance_valid(layer):
			layer.reparent(blocking_plane,false)
	var centres: Array = manifest.get("eye_centers",[])
	if centres.size() != 2:
		return
	var first := Vector2(centres[0][0],centres[0][1])
	var second := Vector2(centres[1][0],centres[1][1])
	var pixels := body.texture.get_size()
	eye_offset = (first + second) * .5 - foot
	eye_span = first.distance_to(second)
	eye_shader = ShaderMaterial.new()
	eye_shader.shader = EYE_GAZE
	eye_shader.set_shader_parameter("first_eye",first / pixels)
	eye_shader.set_shader_parameter("second_eye",second / pixels)
	eye_shader.set_shader_parameter("eye_radius",Vector2(.24,.087) * eye_span / pixels)
	body.material = eye_shader

func take_mark(eyes_at: Vector2, toward: float, next_role: String, now: float) -> void:
	prepare_blocking()
	role = next_role
	beat_start = now
	look_side = signf(toward)
	# Keep the original lettering and insignia on the first responders' uniforms.
	var reverse := look_side < 0 and base_identity not in ["calder","pell","lyle","mateo","rook","nora","iris"]
	var facing := -1.0 if reverse else 1.0
	blocking_plane.scale.x = facing
	base_ground = eyes_at - eye_offset * resting_scale * Vector2(facing,1)
	position = base_ground
	eye_line = look_side * facing
	if eye_shader:
		var travel := Vector2(eye_line * .041,0) * eye_span / body.texture.get_size()
		eye_shader.set_shader_parameter("eye_travel",travel)

func clear_mark(ground: Vector2) -> void:
	role = ""
	position = ground
	if blocking_plane:
		blocking_plane.scale.x = 1.0
		blocking_plane.rotation = 0
	if eye_shader:
		eye_shader.set_shader_parameter("eye_travel",Vector2.ZERO)

func patch(atlas: Texture2D) -> Sprite2D:
	var output := Sprite2D.new()
	output.centered = false
	output.texture = atlas
	output.region_enabled = true
	output.hide()
	add_child(output)
	return output

func display_patch(sprite: Sprite2D, frame: String) -> void:
	if not is_instance_valid(sprite):
		return
	var source: Dictionary = manifest.get("frames",{}).get(frame,{})
	sprite.visible = not source.is_empty()
	if not source.is_empty():
		var rect: Array = source.atlas_region
		var origin: Array = source.source_origin
		sprite.region_rect = Rect2(rect[0],rect[1],rect[2],rect[3])
		sprite.position = Vector2(origin[0],origin[1]) - foot

func speak(source: AudioStreamPlayer, timing: Dictionary) -> void:
	voice = source
	cues = timing.get("cues",[])

func silence() -> void:
	voice = null
	cues = []
	display_patch(mouth,"")
	last_mouth = ""

func animate(seconds: float) -> void:
	if is_instance_valid(body):
		var breath := sin(seconds*1.02+phase)
		scale = resting_scale * Vector2(1.0 + breath*0.001, 1.0 + breath*0.0018)
	if not role.is_empty():
		var elapsed := maxf(0.0,seconds - beat_start)
		var beat: float
		if role == "listener":
			# Receive the line, then settle. No repeated nod while a speaker holds.
			beat = smoothstep(.17,.52,elapsed) * (1.0 - smoothstep(.79,1.33,elapsed))
			position = base_ground + Vector2(look_side * 2.8, 4.4) * beat
		else:
			beat = smoothstep(.04,.31,elapsed) * (1.0 - smoothstep(.50,.96,elapsed))
			position = base_ground + Vector2(look_side * 3.3, -.8) * beat
	var blink := fposmod(seconds+phase,4.81)
	var eye_frame := ""
	if blink < 0.084:
		eye_frame = "blink_closed"
	elif blink < 0.141 or blink > 4.761:
		eye_frame = "blink_half"
	if eye_frame != last_eye:
		display_patch(eyes,eye_frame)
		last_eye = eye_frame
	var mouth_frame := ""
	if is_instance_valid(voice) and voice.playing:
		var at := voice.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
		for cue: Dictionary in cues:
			if at < float(cue.start):
				break
			if at < float(cue.end):
				var frame: Variant = manifest.get("cue_frames",{}).get(str(cue.value))
				mouth_frame = str(frame) if frame != null else ""
				break
	if mouth_frame != last_mouth:
		display_patch(mouth,mouth_frame)
		last_mouth = mouth_frame

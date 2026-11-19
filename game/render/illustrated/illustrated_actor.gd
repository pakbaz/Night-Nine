extends Node2D
## Face patches share the neutral illustration's original pixel coordinates.
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

func configure(folder: String, actor_id: String, height: float, ground: Vector2, tint: Color, prepared: Dictionary = {}) -> void:
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
	phase = 0.37 if actor_id == "helen" else 1.19
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

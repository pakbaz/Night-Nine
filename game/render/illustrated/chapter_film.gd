extends TextureRect
## Final shot of a chapter, driven by the same clock as its score and controls.

const ART := "res://assets/illustrated/campaign/"
const ACTION := preload("res://render/illustrated/film_action.gdshader")
var record: Dictionary
var action: ShaderMaterial
var elapsed := 0.0

func configure(cue: Dictionary, high: bool) -> void:
	record = cue
	name = "ChapterAction"
	texture = load(ART + str(cue.plate) + ".webp") as Texture2D
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	action = ShaderMaterial.new()
	action.shader = ACTION
	action.set_shader_parameter("shot", int(cue.shot))
	action.set_shader_parameter("detail", high)
	if cue.has("subject"):
		var subject := load(ART + "films/" + str(cue.subject) + ".webp") as Texture2D
		if subject:
			action.set_shader_parameter("subject_tex", subject)
			action.set_shader_parameter("subject_aspect", float(subject.get_width()) / subject.get_height())
	material = action
	advance(0.0)

func advance(t: float) -> void:
	# In the final coda, return from the fleet's new world to Steve at his mic.
	var year := int(record.shot) == 12
	var start := .07 if year else (.17 if int(record.shot) == 11 else .40)
	var finish := .66 if year else 1.0
	elapsed = clampf(inverse_lerp(start, finish, t), 0, 1)
	modulate.a = smoothstep(start, start + .105, t)
	if year:
		modulate.a *= 1.0 - smoothstep(.58, .73, t)
	visible = modulate.a > .001
	action.set_shader_parameter("progress", elapsed)

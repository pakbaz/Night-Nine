extends VBoxContainer
## Separate the time station and the chime to record the hum between them.
signal tuned
signal submitted(values: Array)
signal draft_changed(draft: Dictionary)
signal dial_moved(frequency: float)
var dial := HSlider.new()
var narrow := CheckButton.new()
var frequency := Label.new()
var description := Label.new()
var record := Button.new()
var choice_box := VBoxContainer.new()
var choices: Array[OptionButton] = []
var players: Array[AudioStreamPlayer] = []
var lock_ready := false
var paused := false
var mode := "bay"
var receiver_data: Dictionary = {}
var target := 815.0
var restoring := false
## Many voices holding one note: the choir under the bay, through the radio's bandwidth.
const HUM := preload("res://assets/audio/effects/ninth_night_loop.wav")

func _ready() -> void:
	add_theme_constant_override("separation",8)
	add_child(frequency)
	add_child(choice_box)
	dial.min_value=810
	dial.max_value=820
	dial.step=1
	dial.value=810
	dial.tooltip_text="Use the arrow keys or drag to tune."
	add_child(dial)
	narrow.text="Narrow bandwidth"
	add_child(narrow)
	description.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	description.custom_minimum_size=Vector2(300,58)
	add_child(description)
	record.text="Record the signal"
	add_child(record)
	for stream: AudioStream in [station(false),station(true),HUM]:
		var player := AudioStreamPlayer.new()
		player.stream=stream
		add_child(player)
		players.append(player)
	dial.value_changed.connect(func(_value: float): retune())
	narrow.toggled.connect(func(_enabled: bool): retune())
	record.pressed.connect(func():
		if not lock_ready:
			return
		if mode == "bay":
			tuned.emit()
		else:
			var values: Array = []
			for choice: OptionButton in choices:
				values.append(choice.selected - 1)
			values.append(_dial_answer())
			submitted.emit(values))
	visibility_changed.connect(set_preview)
	retune()
	set_preview()

func configure(data: Dictionary, progress: Dictionary = {}) -> void:
	for player: AudioStreamPlayer in players:
		player.stop()
	receiver_data = data
	mode = str(data.get("mode", "bay"))
	target = float(data.get("target", 815.0))
	restoring = true
	for child: Node in choice_box.get_children():
		choice_box.remove_child(child)
		child.queue_free()
	choices.clear()
	for row: Dictionary in data.get("choices", []):
		var label := Label.new()
		label.text = str(row.get("label", "Choose"))
		choice_box.add_child(label)
		var choice := OptionButton.new()
		choice.add_item("Choose one")
		for option: String in row.get("options", []):
			choice.add_item(option)
		choice_box.add_child(choice)
		choice.item_selected.connect(func(_index: int): _choice_changed())
		choices.append(choice)
	dial.min_value = float(data.get("min", 810.0))
	dial.max_value = float(data.get("max", 820.0))
	dial.step = float(data.get("step", 1.0))
	narrow.text = str(data.get("narrow_label", "Narrow bandwidth"))
	narrow.visible = bool(data.get("show_narrow", true))
	record.text = str(data.get("action", "Record the signal"))
	var values: Array = progress.get("values", [])
	for index: int in choices.size():
		if index < values.size() and int(values[index]) >= 0:
			choices[index].select(int(values[index]) + 1)
	dial.value = float(progress.get("offset", data.get("start", dial.min_value)))
	narrow.button_pressed = bool(data.get("start_narrow", false))
	restoring = false
	retune()
	set_preview()

func set_preview() -> void:
	for p: AudioStreamPlayer in players:
		if is_visible_in_tree() and not paused:
			if not p.playing:
				p.play()
		else:
			p.stop()

func _exit_tree() -> void:
	for player: AudioStreamPlayer in players:
		player.stop()
		player.stream=null
	players.clear()

func set_paused(on: bool) -> void:
	paused=on
	set_preview()

func retune() -> void:
	if mode != "bay":
		_retune_authored()
		return
	var khz := int(dial.value)
	var width := 1.25 if narrow.button_pressed else 4.8
	var time_gain := .96*exp(-.5*pow((khz-810)/width,2.0))
	var music_gain := .96*exp(-.5*pow((khz-820)/width,2.0))
	var hum_gain := (.94 if narrow.button_pressed else .65)*exp(-.5*pow((khz-815)/1.55,2.0))
	var gains := [time_gain,music_gain,hum_gain]
	for i: int in players.size():
		players[i].volume_db=linear_to_db(maxf(.0001,float(gains[i])))-10.0
	frequency.text="%d kHz" % khz
	lock_ready=narrow.button_pressed and hum_gain>=.74
	record.disabled=not lock_ready
	if lock_ready:
		description.text="Many voices, holding one note. Both stations have dropped away."
	elif time_gain>.4 and music_gain>.4:
		description.text="Time pips and chimes overlap. Under them, something like voices."
	elif hum_gain>.2:
		description.text="Faint voices come through, singing one note under the static."
	else:
		description.text="Regular time pips over static." if time_gain>music_gain else "Two chimes over static."
	dial_moved.emit(khz)

func _retune_authored() -> void:
	var value := float(dial.value)
	var width := float(receiver_data.get("width_narrow", dial.step * 0.75)) if narrow.button_pressed \
		else float(receiver_data.get("width_wide", maxf(dial.step, (dial.max_value - dial.min_value) * 0.35)))
	var signal_gain := .96 * exp(-.5 * pow((value - target) / maxf(width, .0001), 2.0))
	var left_gain := .72 * exp(-.5 * pow((value - dial.min_value) / maxf(width * 1.4, .0001), 2.0))
	var right_gain := .72 * exp(-.5 * pow((value - dial.max_value) / maxf(width * 1.4, .0001), 2.0))
	for i: int in players.size():
		players[i].volume_db = linear_to_db(maxf(.0001, [left_gain, right_gain, signal_gain][i])) - 10.0
	var unit := str(receiver_data.get("unit", ""))
	var decimals := int(receiver_data.get("decimals", 0))
	frequency.text = (String.num(value, decimals) + " " + unit).strip_edges()
	var exact := absf(value - target) <= maxf(dial.step * .25, .0001)
	var choices_ready := choices.all(func(choice: OptionButton): return choice.selected > 0)
	lock_ready = exact and choices_ready and (narrow.button_pressed or not bool(receiver_data.get("require_narrow", false)))
	record.disabled = not lock_ready
	var descriptions: Dictionary = receiver_data.get("descriptions", {})
	var key := _value_key(value)
	if descriptions.has(key):
		description.text = str(descriptions[key])
	elif exact:
		description.text = str(receiver_data.get("target_description", "A clear live reply comes through the static."))
	else:
		description.text = str(receiver_data.get("search_description", "Static and overlapping voices. Keep tuning."))
	dial_moved.emit(value)
	if not restoring:
		_emit_draft()

func _choice_changed() -> void:
	retune()

func _dial_answer() -> int:
	var answers: Array = receiver_data.get("dial_options", [])
	if answers.is_empty():
		return 0
	var best := 0
	var distance := INF
	for index: int in answers.size():
		var next := absf(float(answers[index]) - dial.value)
		if next < distance:
			best = index
			distance = next
	return best

func _emit_draft() -> void:
	var values: Array = []
	for choice: OptionButton in choices:
		values.append(choice.selected - 1)
	draft_changed.emit({"values": values, "offset": dial.value})

func _value_key(value: float) -> String:
	return String.num(value, int(receiver_data.get("decimals", 0)))

static func station(chimes: bool) -> AudioStreamWAV:
	const RATE := 16000
	var bytes := PackedByteArray()
	bytes.resize(RATE*4)
	var random := RandomNumberGenerator.new()
	random.seed=713 if chimes else 182
	for sample: int in RATE*2:
		var time := float(sample)/RATE
		var phase := fmod(time,1.0 if chimes else .5)
		var hz := (523.25 if time<1.0 else 659.25) if chimes else 885.0
		var amplitude := random.randf_range(-.022,.022)
		if chimes:
			# A struck bell: a sharp strike and inharmonic partials that die away at
			# different rates, so the chimes never sound like a voice holding a note.
			var strike := minf(phase/.004,1.0)
			amplitude += .34*strike*(.62*sin(TAU*time*hz)*exp(-phase*6.0)
				+.26*sin(TAU*time*hz*2.756)*exp(-phase*11.0)+.12*sin(TAU*time*hz*5.404)*exp(-phase*19.0))
		else:
			amplitude += sin(TAU*time*hz)*.27*(sin(PI*phase/.16) if phase<.16 else 0.0)
		bytes.encode_s16(sample*2,roundi(32767.0*amplitude*clampf(minf(time,2.0-time)*90.0,0.0,1.0)))
	var wave := AudioStreamWAV.new()
	wave.mix_rate=RATE
	wave.format=AudioStreamWAV.FORMAT_16_BITS
	wave.data=bytes
	wave.loop_mode=AudioStreamWAV.LOOP_FORWARD
	wave.loop_end=RATE*2
	return wave

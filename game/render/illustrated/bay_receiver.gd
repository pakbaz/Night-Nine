extends VBoxContainer
## Separate the time station and the chime to record the hum between them.
signal tuned
signal dial_moved(frequency: int)
var dial := HSlider.new()
var narrow := CheckButton.new()
var frequency := Label.new()
var description := Label.new()
var record := Button.new()
var players: Array[AudioStreamPlayer] = []
var lock_ready := false
var paused := false
## Many voices holding one note: the choir under the bay, through the radio's bandwidth.
const HUM := preload("res://assets/audio/effects/ninth_night_loop.wav")

func _ready() -> void:
	add_theme_constant_override("separation",8)
	add_child(frequency)
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
		player.finished.connect(func(): if is_visible_in_tree() and not paused: player.play())
		add_child(player)
		players.append(player)
	dial.value_changed.connect(func(_value: float): retune())
	narrow.toggled.connect(func(_enabled: bool): retune())
	record.pressed.connect(func(): if lock_ready: tuned.emit())
	visibility_changed.connect(set_preview)
	retune()
	set_preview()

func set_preview() -> void:
	for p: AudioStreamPlayer in players:
		if is_visible_in_tree() and not paused:
			if not p.playing:
				p.play()
		else:
			p.stop()

func set_paused(on: bool) -> void:
	paused=on
	set_preview()

func retune() -> void:
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
		description.text="A steady low hum. Both stations have dropped away."
	elif time_gain>.4 and music_gain>.4:
		description.text="Time pips and chimes overlap. There is a hum beneath them."
	elif hum_gain>maxf(time_gain,music_gain):
		description.text="A low hum comes through, still faint."
	else:
		description.text="Regular time pips over static." if time_gain>music_gain else "Two chimes over static."
	dial_moved.emit(khz)

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

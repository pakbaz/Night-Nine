extends VBoxContainer

signal sent(values: Array)
signal missed(reason: String)

var fader := HSlider.new()
var lamp := Label.new()
var meter := Label.new()
var monitor := AudioStreamPlayer.new()
var keys: Array[Button] = []
var patches: Array = []
var sheet: Dictionary
var effects: Dictionary
var remaining := 0.0
var finished := false
var paused := false

func configure(puzzle: Dictionary, sounds: Dictionary) -> void:
	sheet = puzzle
	effects = sounds
	name = "BroadcastDesk"
	add_child(monitor)
	add_child(lamp)
	lamp.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lamp.add_theme_color_override("font_color", Color("e9c276"))
	add_child(meter)
	add_child(fader)
	fader.max_value = 2
	fader.step = 1
	fader.tooltip_text = "Program level: muted, line, overload. Use the arrow keys."
	fader.value_changed.connect(_level_changed)
	_level_changed(0)
	for channel: String in sheet.channels:
		var key := Button.new()
		key.text = "Send · " + channel
		key.pressed.connect(_send.bind(keys.size()))
		keys.append(key)
		add_child(key)
	visibility_changed.connect(_check_visibility)
	_update_lamp()

func _check_visibility() -> void:
	monitor.stream_paused = paused or not is_visible_in_tree()

func set_paused(on: bool) -> void:
	paused = on
	_check_visibility()

func _level_changed(level: float) -> void:
	meter.text = "PROGRAM FADER   " + str(["MUTED", "LINE", "OVERLOAD"][int(level)])
	monitor.volume_db = [-80.0, -3.0, 0.0][int(level)]

func _process(delta: float) -> void:
	if finished or paused or sheet.is_empty() or not is_visible_in_tree():
		return
	remaining = maxf(0.0, remaining - delta)
	_update_lamp()

func _waiting(cue: Dictionary) -> bool:
	return remaining > 0.0 or (cue.get("monitor", false) and monitor.playing)

func _update_lamp() -> void:
	var cue: Dictionary = sheet.cues[patches.size()]
	lamp.text = str(cue.pending) if _waiting(cue) else str(cue.lamp)

func _send(index: int) -> void:
	if finished or paused or not is_visible_in_tree():
		return
	var cue: Dictionary = sheet.cues[patches.size()]
	if fader.value != 1:
		missed.emit("Bring the program fader to LINE. It is muted." if fader.value == 0 else "The program is clipping. Bring the fader back to LINE.")
	elif _waiting(cue):
		missed.emit(str(cue.pending) + " Hold this cue.")
	elif sheet.channels[index] != cue.send:
		missed.emit(str(cue.wrong))
	else:
		if cue.has("sound"):
			var path: String = effects.get(str(cue.sound).trim_prefix("effect."), {}).get("file", "")
			if path.is_empty() or not ResourceLoader.exists(path):
				missed.emit("The wind reel is missing. Restore the game audio before sending this cue.")
				return
			monitor.stream = load(path) as AudioStream
			monitor.play()
		patches.append(index)
		if patches.size() == sheet.cues.size():
			finished = true
			sent.emit(patches.duplicate())
		else:
			remaining = float(sheet.cues[patches.size()].get("wait", 0))
			_update_lamp()

extends SceneTree

const DESK := preload("res://ui/broadcast_desk.gd")
var faults := PackedStringArray()
var misses := PackedStringArray()
var sent := []

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, message: String) -> void:
	if not ok:
		faults.append(message)
		push_error(message)

func run() -> void:
	var campaign: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	var effects: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/audio/soundscape-manifest.json"))
	for location: Dictionary in campaign.scenes:
		for investigation: Dictionary in location.tasks:
			if not investigation.get("sound_bank", false) and investigation.id != "postcredits.answer":
				continue
			for sound: String in investigation.sounds:
				var clip := load(str(effects[sound.trim_prefix("effect.")].file)) as AudioStreamWAV
				var trace := preload("res://ui/evidence_trace.gd").new()
				trace.configure(clip, clip.get_length())
				check(not trace.envelope.is_empty() and Array(trace.envelope).max() > 0.0,
					str(investigation.id) + " displays samples from " + sound)
				trace.free()
	var scene: Dictionary = campaign.scenes.filter(func(s): return s.id == "c10_live")[0]
	for task: Dictionary in scene.tasks:
		var desk := DESK.new()
		root.add_child(desk)
		desk.configure(task.puzzle, effects)
		desk.sent.connect(func(values): sent.append(values))
		desk.missed.connect(func(reason): misses.append(reason))
		sent.clear()
		misses.clear()
		var first := int(task.puzzle.solution[0])
		var second := int(task.puzzle.solution[1])
		desk.keys[first].pressed.emit()
		check(misses.size() == 1 and desk.patches.is_empty(), task.id + ": muted channel cannot go on air")
		desk.fader.value = 1
		desk.keys[second].pressed.emit()
		check(misses.size() == 2 and desk.patches.is_empty(), task.id + ": wrong channel stays off air")
		desk.keys[first].pressed.emit()
		check(desk.patches == [first] and desk.lamp.text == task.puzzle.cues[1].pending, task.id + ": wait for the outside return")
		desk.keys[second].pressed.emit()
		check(misses.size() == 3 and sent.is_empty(), task.id + ": early send keeps the first cue")
		desk.set_paused(true)
		var time_left := desk.remaining
		desk._process(4)
		check(is_equal_approx(time_left, desk.remaining), task.id + ": the desk pauses with the menu")
		desk.set_paused(false)
		if task.puzzle.cues[1].get("monitor", false):
			check(desk.monitor.playing and desk.monitor.stream.resource_path == effects.veyr_wind.file,
				"The last cue monitors the actual wind reel")
			desk.monitor.seek(desk.monitor.stream.get_length() - 0.12)
			var deadline := Time.get_ticks_msec() + 2500
			while desk.monitor.playing and Time.get_ticks_msec() < deadline:
				await process_frame
		desk._process(4)
		check(desk.lamp.text == task.puzzle.cues[1].lamp, task.id + ": clear lamp waits for return or end of tape")
		desk.keys[second].pressed.emit()
		desk.keys[second].pressed.emit()
		check(sent == [[first, second]], task.id + ": the correct handoff is sent exactly once")
		desk.free()
	print("Broadcast desk: %d failures" % faults.size())
	quit(0 if faults.is_empty() else 1)

extends SceneTree
## Decode every recorded take and check stable clue references in the engine.
var checks := 0
var failures: Array[String] = []

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func _initialize() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/voice-manifest.json"))
	var content: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/campaign.json"))
	var takes: Dictionary = manifest.takes
	var player := preload("res://scripts/campaign.gd").new()
	player.voice_manifest = manifest.duplicate(true)
	player.lipsync_manifest = JSON.parse_string(FileAccess.get_file_as_string("res://content/lipsync-manifest.json"))
	var required: Dictionary = {}
	for line: Dictionary in content.lines.values():
		required[line.audio] = true
	check(takes.size()==required.size(),"Recorded-take inventory matches the current script")
	var private: Dictionary = content.lines["i2_nora.message.01"]
	var replay: Dictionary = content.lines["c9_gallery.out.03"]
	check(private.audio == replay.audio and private.text == replay.text, "Retain one Nora intercom recording from capture to replay")
	check(private.delivery == "private_recording" and replay.delivery == "recorded_playback", "Preserve the final plot's delayed message reveal")
	for id: String in takes:
		var take: Dictionary = takes[id]
		var path: String = take.file
		check(not path.is_empty() and ResourceLoader.exists(path),"Imported voice "+id)
		if path.is_empty() or not ResourceLoader.exists(path):
			continue
		var stream: AudioStream = load(path)
		check(stream!=null and absf(stream.get_length()-float(take.seconds))<0.04,"Decoded duration "+id)
		check(take.get("status","") in ["automated_checks_passed","reviewed"],"Transcript status "+id)
		if take.has("fallback"):
			var selected := player._recording_for(id)
			check(selected.take.file == path and selected.timing.audio_sha256 == take.sha256, "Active voice and mouth cues "+id)
			player.voice_manifest.takes[id].file = "res://missing-recording-for-test.wav"
			var local := player._recording_for(id)
			check(ResourceLoader.exists(local.take.file) and local.take.sha256 == local.timing.audio_sha256,
				"Local voice and matching mouth cues when the preferred asset is absent "+id)
			player.voice_manifest.takes[id].file = path
		stream=null
	for line: Dictionary in content.lines.values():
		check(takes.has(line.audio) and not takes[line.audio].file.is_empty(),"Spoken line coverage "+line.id)
	_check_recording_evidence(content, takes)
	var report := {"checks":checks,"failures":failures,"takes":takes.size(),"dialogue_lines":content.lines.size()}
	player.free()
	print(JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

func _check_recording_evidence(content: Dictionary, takes: Dictionary) -> void:
	var effects: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/audio/soundscape-manifest.json"))
	for scene: Dictionary in content.scenes:
		for task: Dictionary in scene.tasks:
			if not task.has("evidence_labels"):
				continue
			var labels := {}
			for label: String in task.evidence_labels:
				labels[label] = true
			check(labels.size()==task.sounds.size() and labels.size()>=2, "Individually labeled evidence recordings " + task.id)
			for fallback: bool in [false, true]:
				var clips: Array[AudioStreamWAV] = []
				for id: String in task.sounds:
					var take: Dictionary = effects[id.trim_prefix("effect.")] if id.begins_with("effect.") else takes[id]
					if fallback:
						take = take.get("fallback", take)
					clips.append(load(take.file) as AudioStreamWAV)
				var same_take: bool = task.id in ["c4_safe.match", "i1_archive.signals", "c8_beach.second"]
				check((clips[0].data == clips[1].data) == same_take, "Correct deduction from actual PCM " + task.id)
				var traces: Array[PackedFloat32Array] = []
				var longest := 0.0
				for clip: AudioStreamWAV in clips:
					longest=maxf(longest,clip.get_length())
				for clip: AudioStreamWAV in clips:
					var trace := preload("res://ui/evidence_trace.gd").new()
					trace.configure(clip,longest)
					check(trace.envelope.size() == trace.BIN_COUNT and trace.envelope.count(0.0) < trace.BIN_COUNT, "Visible recorded evidence " + task.id)
					traces.append(trace.envelope)
					trace.free()
				check((traces[0] == traces[1]) == same_take, "Silent and audio evidence support the same finding " + task.id)
				if task.id=="c8_lab.lastpage":
					check(clips.size()==3 and clips[2].data!=clips[1].data and traces[2]!=traces[0] and traces[2]!=traces[1], "Distinguish all three Meridian hydrophone reels")
				if task.id == "c2_aquarium.guard":
					for i: int in 2:
						var data := clips[i].data
						var third := data.size() / 3
						var repeated := data.slice(0, third) == data.slice(third, 2 * third) and data.slice(0, third) == data.slice(2 * third)
						check(repeated == (i == 1), "Only the filter corridor repeats one exact loop")

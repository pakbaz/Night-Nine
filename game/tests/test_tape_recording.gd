extends SceneTree
var checks := 0
var failures: Array[String] = []

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func segment(tape: Dictionary, label: String) -> Dictionary:
	for item: Dictionary in tape.segments:
		if item.label == label:
			return item
	return {}

func segment_rms(pcm: PackedByteArray, rate: int, item: Dictionary) -> float:
	var first := roundi(float(item.start) * rate)
	var last := roundi(float(item.end) * rate)
	var energy := 0.0
	for index: int in range(first, last):
		var sample := float(pcm.decode_s16(index * 2)) / 32768.0
		energy += sample * sample
	return sqrt(energy / maxf(1.0, last - first))

func _initialize() -> void:
	var metadata: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string("res://assets/audio/effects/morning-tapes.json"))
	var saturday := load("res://assets/audio/effects/tape-saturday.wav") as AudioStreamWAV
	var sunday := load("res://assets/audio/effects/tape-sunday.wav") as AudioStreamWAV
	var model := NightTapeRecording.new()
	check(model.configure(saturday, sunday, metadata), "Load both deterministic morning tapes")
	if model.samples_a.is_empty() or model.samples_b.is_empty():
		_finish(model, metadata)
		return
	check(saturday.data != sunday.data, "Saturday and Sunday contain different recordings")
	check(model.rate == 48000 and not saturday.stereo and not sunday.stereo,
		"Both tapes are 48 kHz mono PCM16")
	check(model.timeline_end >= 9.0 and model.timeline_end <= 11.5,
		"Widen the timeline for the complete kitchen moment")
	check(model.aligned(-0.35) and model.aligned(-0.34) and model.aligned(-0.36),
		"Accept centisecond input tolerance around the 0.35 second delay")
	check(not model.aligned(-0.33) and not model.aligned(0.35) and not model.aligned(0),
		"Reject shifted and reversed alignment")
	check(not model.aligned(NAN) and not model.aligned(INF), "Reject nonfinite input")
	check(model.playback("missing", 0) == null, "Reject an unknown playback mode")
	var a := model.playback("a", 0)
	var b := model.playback("b", 0)
	var together := model.playback("both", -0.35)
	check(a != null and b != null and together != null, "Build all three playback modes")
	check(a.data != b.data, "Unaligned playback keeps the two tape captures distinct")
	check(together.data != a.data and together.data != b.data,
		"Aligned playback mixes the naturally different voices")
	check(a.mix_rate == 48000 and not a.stereo, "Playback keeps the authored format")
	# Inside the accepted tolerance the tapes click into exact alignment, so identical
	# parts play as one voice instead of two copies a centisecond apart.
	check(model.playback("both", -0.34).data == together.data and model.playback("both", -0.36).data == together.data,
		"An accepted near-alignment plays exactly like the true alignment")
	check(model.playback("both", -0.33).data != together.data, "A rejected offset keeps its own timing")
	check(is_equal_approx(model.effective_offset(-0.34), -0.35) and is_equal_approx(model.effective_offset(0.2), 0.2),
		"Draw and play the effective offset")
	check(model.peaks_a.size() > 1000 and model.peaks_b.size() > 1000,
		"Create independent waveform peaks for both tapes")
	var tapes: Dictionary = metadata.tapes
	for tape_name: String in ["saturday", "sunday"]:
		var tape: Dictionary = tapes[tape_name]
		var seconds := float(tape.seconds)
		check(seconds > 8.0 and seconds < 10.6, tape_name + " stays near the requested tape length")
		for item: Dictionary in tape.segments:
			check(float(item.start) >= 0.0 and float(item.end) > float(item.start)
				and float(item.end) <= seconds, tape_name + " segment " + str(item.label) + " lies inside the audio")
	var sat_ident := segment(tapes.saturday, "Ident")
	var sun_ident := segment(tapes.sunday, "Ident")
	var sat_nora := segment(tapes.saturday, "Nora")
	var sun_nora := segment(tapes.sunday, "Nora")
	var sat_rick := segment(tapes.saturday, "AutoRick")
	var sun_rick := segment(tapes.sunday, "AutoRick")
	var sat_steve := segment(tapes.saturday, "Steve")
	var sun_steve := segment(tapes.sunday, "Steve")
	check(segment_rms(model.pcm_a, model.rate, sat_ident) > 0.02
		and segment_rms(model.pcm_b, model.rate, sun_ident) > 0.02,
		"Both ident segments contain clearly audible signal above the tape noise")
	var ident_waveform_visible := false
	for tape_index: int in 2:
		var item := sat_ident if tape_index == 0 else sun_ident
		var peaks := model.peaks_a if tape_index == 0 else model.peaks_b
		var first_bin := floori(float(item.start) * model.rate / NightTapeRecording.BIN_FRAMES)
		var last_bin := ceili(float(item.end) * model.rate / NightTapeRecording.BIN_FRAMES)
		var tape_visible := false
		for peak_index: int in range(first_bin, mini(last_bin, peaks.size())):
			var peak: Vector2 = peaks[peak_index]
			if maxf(absf(peak.x), absf(peak.y)) > 0.03:
				tape_visible = true
				break
		ident_waveform_visible = tape_visible if tape_index == 0 else ident_waveform_visible and tape_visible
	check(ident_waveform_visible, "The ident produces a visible waveform on both traces")
	check(sat_ident.clean_sha256 == sun_ident.clean_sha256,
		"The ident source is sample-identical after alignment before seeded noise")
	check(sat_nora.clean_sha256 == sun_nora.clean_sha256,
		"Nora's take is sample-identical after alignment before seeded noise")
	check(sat_rick.clean_sha256 != sun_rick.clean_sha256, "AutoRick says different words")
	check(sat_steve.clean_sha256 != sun_steve.clean_sha256, "Steve uses two natural takes")
	check(is_equal_approx(float(sun_ident.start) - float(sat_ident.start), 0.35),
		"Sunday's ident begins exactly 0.35 seconds later")
	var spacing_matches := true
	for index: int in tapes.saturday.segments.size():
		spacing_matches = spacing_matches and is_equal_approx(
			float(tapes.sunday.segments[index].start)
				- float(tapes.saturday.segments[index].start), 0.35)
	check(spacing_matches, "Every segment keeps the same start spacing once aligned")
	check(float(metadata.sunday_steve_cut.seconds) >= 0.6
		and float(metadata.sunday_steve_cut.seconds) <= 1.6,
		"Sunday's energy-detected Morning, Nor cut is plausible")
	check(str(metadata.sunday_steve_cut.method).contains("RMS"),
		"Document the deterministic energy-based Sunday cut")
	check(FileAccess.get_sha256("res://assets/audio/effects/tape-saturday.wav")
		== str(metadata.outputs.saturday.sha256), "Saturday output hash matches metadata")
	check(FileAccess.get_sha256("res://assets/audio/effects/tape-sunday.wav")
		== str(metadata.outputs.sunday.sha256), "Sunday output hash matches metadata")
	var source_hashes_match := true
	for source: Dictionary in metadata.sources.values():
		source_hashes_match = source_hashes_match \
			and FileAccess.get_sha256(str(source.file)) == str(source.sha256)
	check(source_hashes_match, "Every source hash matches the recorded metadata")
	var invalid := AudioStreamWAV.new()
	invalid.format = AudioStreamWAV.FORMAT_8_BITS
	check(not NightTapeRecording.new().configure(invalid, sunday, metadata),
		"Reject a lossy or unsupported tape")
	var invalidated := NightTapeRecording.new()
	invalidated.configure(saturday, sunday, metadata)
	check(not invalidated.configure(invalid, sunday, metadata)
		and invalidated.playback("a", 0) == null,
		"Clear previous tapes when a new source fails validation")
	var rook := load("res://assets/audio/voices/elevenlabs-v4-script-v2/recording.rook.wav") as AudioStreamWAV
	var rook_door := load("res://assets/audio/effects/rook-door.wav") as AudioStreamWAV
	var iris_first := load("res://assets/audio/voices/elevenlabs-v4-script-v2/c6_iris.takes.01.wav") as AudioStreamWAV
	var iris_second := load("res://assets/audio/voices/elevenlabs-v4-script-v2/c6_iris.takes.02.wav") as AudioStreamWAV
	var voicemail := load("res://assets/audio/voices/elevenlabs-v4-script-v2/recording.voicemail.wav") as AudioStreamWAV
	var splice := load("res://assets/audio/voices/elevenlabs-v4-script-v2/recording.saren_splice.wav") as AudioStreamWAV
	var generic := NightTapeRecording.new()
	check(generic.configure_pair(rook,rook_door,{"label_a":"Calder voicemail","label_b":"Safe-house door"})
		and generic.aligned(0.0) and generic.label_b=="SAFE-HOUSE DOOR"
		and generic.samples_a!=generic.samples_b,
		"Compare Rook’s actual take with Steve’s room recording at the door")
	check(generic.configure_pair(iris_first,iris_second,{"label_a":"First reading","label_b":"Second reading"})
		and generic.samples_a.size()!=generic.samples_b.size() and generic.peaks_a!=generic.peaks_b,
		"Compare Iris’s actual takes with the changed internal pause")
	check(generic.configure_pair(voicemail,splice,{"label_a":"Voicemail","label_b":"Saren’s tape"})
		and generic.samples_b.size()<generic.samples_a.size() and generic.playback("both",0.0)!=null,
		"Compare the actual shorter voicemail splice")
	var campaign := NightCampaign.new()
	var iris_puzzle: Dictionary = campaign.task_index["c6_iris.takes"].puzzle
	var iris := NightTapeRecording.new()
	iris.configure_pair(iris_first, iris_second, iris_puzzle)
	check(not iris.alignment_required and is_equal_approx(iris.effective_offset(0.3), 0.3)
		and iris.playback("both", 0.3).data != iris.playback("both", 0.0).data,
		"The slider moves Iris’s second take even though alignment is not scored")
	_finish(model, metadata)

func _finish(model: NightTapeRecording, metadata: Dictionary) -> void:
	var campaign := NightCampaign.new()
	var task: Dictionary = campaign.task_index["c1_flat.compare"]
	check(task.puzzle.recording_a == "res://assets/audio/effects/tape-saturday.wav"
		and task.puzzle.recording_b == "res://assets/audio/effects/tape-sunday.wav",
		"The tape puzzle carries separate Saturday and Sunday recording fields")
	check(task.puzzle.segments == "res://assets/audio/effects/morning-tapes.json",
		"The tape puzzle carries the segment metadata field")
	check(task.puzzle.rows.size() == 4 and task.puzzle.solution.size() == 4
		and int(task.puzzle.solution[0]) == 0 and int(task.puzzle.solution[1]) == 2
		and int(task.puzzle.solution[2]) == 1 and int(task.puzzle.solution[3]) == 0,
		"The tape puzzle solution contains only the four voice rows")
	check(campaign.content.lines["c1_flat.in.04"].display_speaker == "Nora Reyes",
		"Conceal Iris's identity in the first greeting")
	check(campaign.content.lines["c1_pier.door.01"].display_speaker == "Lyle Boone",
		"Conceal Lyle's copy identity at the pier")
	var first_hint := campaign.hint("c1_flat.compare")
	var second_hint := campaign.hint("c1_flat.compare")
	var final_hint := campaign.hint("c1_flat.compare")
	check(not first_hint.contains("0.35") and not second_hint.contains("0.35")
		and not final_hint.contains("0.35"), "Hints guide without giving the numeric answer")
	check(final_hint.contains("ident"), "Final hint names the accessible alignment landmark")
	var report := {
		"checks": checks,
		"failures": failures,
		"saturday_samples": model.samples_a.size(),
		"sunday_samples": model.samples_b.size(),
		"source_count": metadata.get("sources", {}).size(),
		"pcm_identity_verified": failures.is_empty()
	}
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://../tmp/qa"))
	var file := FileAccess.open("res://../tmp/qa/tape-recording-results.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print(JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

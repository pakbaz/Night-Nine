extends SceneTree
var checks := 0
var failures: Array[String] = []
func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func _initialize() -> void:
	var master := load("res://assets/audio/voices/recording.greeting.wav") as AudioStreamWAV
	var model := NightTapeRecording.new()
	check(model.configure(master, 0.2, 0.55), "Load the real mono PCM master")
	if model.samples.is_empty():
		quit(1)
		return
	var before := master.data.duplicate()
	var a := model.playback("a", 0)
	var b := model.playback("b", 0)
	var aligned := model.playback("b", -0.35)
	var together := model.playback("both", -0.35)
	check(a.data != b.data, "Unaligned captures differ in actual PCM timing")
	check(a.data == aligned.data, "Aligned captures match sample for sample")
	check(together.data == a.data, "Aligned combined playback preserves the master amplitude")
	var first := roundi((0.2 - model.timeline_start) * model.rate) * 2
	check(a.data.slice(first, first + before.size()) == before, "Saturday retains every master sample unchanged")
	check(master.data == before, "Comparison never mutates the source recording")
	check(a.mix_rate == 24000 and not a.stereo, "Keep original sample rate and channel layout")
	check(model.aligned(-0.35) and model.aligned(-0.34) and model.aligned(-0.36), "Accept centisecond input tolerance")
	check(not model.aligned(-0.33) and not model.aligned(0.35) and not model.aligned(0), "Reject shifted and reversed alignment")
	check(not model.aligned(NAN) and not model.aligned(INF), "Reject nonfinite input")
	check(model.playback("missing", 0) == null, "Reject an unknown playback mode")
	var invalid := AudioStreamWAV.new()
	invalid.format = AudioStreamWAV.FORMAT_8_BITS
	check(not NightTapeRecording.new().configure(invalid, 0.2, 0.55), "Reject a lossy or unsupported imported master")
	var invalidated := NightTapeRecording.new()
	invalidated.configure(master, 0.2, 0.55)
	check(not invalidated.configure(invalid, 0.2, 0.55) and invalidated.playback("a", 0) == null, "Clear a previous recording when a new source fails validation")
	var registry: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/voice-manifest.json"))
	var active: Dictionary=registry.takes["recording.greeting"]
	var active_audio:=load(str(active.file)) as AudioStreamWAV
	var active_model:=NightTapeRecording.new()
	check(active_model.configure(active_audio,.2,.55),"Import the preferred recorder greeting as mono 16-bit PCM")
	if not active_model.samples.is_empty():
		var first_capture:=active_model.playback("a",0)
		var second_capture:=active_model.playback("b",-.35)
		check(first_capture.data==second_capture.data,"The preferred voice master aligns sample-for-sample")
		var start_sample:=roundi((.2-active_model.timeline_start)*active_model.rate)*2
		check(first_capture.data.slice(start_sample,start_sample+active_audio.data.size())==active_audio.data,"Never resample or normalize the active recording")
		check(active_model.rate==int(active.sample_rate) and active_model.samples.size()==roundi(float(active.seconds)*active_model.rate),"Retain the authored sample rate and duration")
	var campaign := NightCampaign.new()
	check(campaign.content.lines["c1_flat.in.04"].display_speaker == "Nora Reyes", "Conceal Iris's identity in the first greeting")
	check(campaign.content.lines["c1_pier.door.01"].display_speaker == "Lyle Boone", "Conceal Lyle's copy identity at the pier")
	check(campaign.content.lines["c4_safe.in.01"].display_speaker == "Adrian Rook", "Conceal Rook's copy identity before the betrayal")
	check(campaign.content.lines["c6_jail.out.01"].get("display_speaker", "Iris") == "Iris", "Use Iris after she chooses her name")
	var first_hint := campaign.hint("c1_flat.compare")
	var second_hint := campaign.hint("c1_flat.compare")
	var final_hint := campaign.hint("c1_flat.compare")
	check(not first_hint.contains("0.35") and not second_hint.contains("0.35"), "Keep exact timing out of the early hints")
	check(final_hint.contains("-0.35"), "Provide an explicit accessible solution in the final hint")
	var report := {"checks": checks, "failures": failures, "master_samples": model.samples.size(),"preferred_master":active.file,"preferred_samples":active_model.samples.size(),"preferred_rate":active_model.rate, "pcm_identity_verified": failures.is_empty()}
	var file := FileAccess.open("res://../tmp/qa/tape-recording-results.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print(JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

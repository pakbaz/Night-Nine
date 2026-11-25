extends Node
## Exercise the real reunion interaction, recorded audio and staged character controls.
var game: Node
var checks := 0
var failures: Array[String] = []
var report_path := ""
var capture := false
var frames: Array[Dictionary] = []

func _ready() -> void:
	_run.call_deferred()

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func wait_frames(count: int) -> void:
	for index: int in count:
		await get_tree().process_frame

func shot(name_: String) -> void:
	await wait_frames(4)
	RenderingServer.force_draw(false)
	var error := get_viewport().get_texture().get_image().save_png(report_path.path_join(name_ + ".png"))
	check(error == OK, "Saved native shot: " + name_)

func _arrive() -> void:
	game.campaign.reset()
	while game.campaign.current().id != "c9_gallery":
		var scene: Dictionary = game.campaign.current()
		game.campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			var result: Dictionary = game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
			check(result.get("ok", false), "Prepare canonical prerequisite: " + task.id)
			game.campaign.mark_seen(task.lines)
		game.campaign.mark_seen(scene.outro)
		check(game.campaign.advance(), "Prepare scene gate: " + scene.id)
	game.started = true
	game.menu.hide()
	game.auto_dialogue = false
	game._load_stage(true)
	# Chapter cards are timed in story_flow_qa.gd; this check starts at the first line.
	if game.title_card.visible:
		game.title_card.finish_now()

func _run() -> void:
	report_path = OS.get_environment("NIGHT_NINE_QA_DIR")
	if report_path.is_empty():
		report_path = ProjectSettings.globalize_path("res://../tmp/qa/staging")
	DirAccess.make_dir_recursive_absolute(report_path)
	capture = "--staging-capture" in OS.get_cmdline_user_args()
	_arrive()
	await wait_frames(6)
	check(game.stage is Control and game.stage.room_id=="c9_gallery","Load the illustrated reunion stage")
	check(not game.stage.actor_visible("nora"), "Keep Nora's standing portrait absent before release")
	game._skip_dialogue()
	if not capture:
		game._speak(["i2_nora.message.01"], Callable())
		check(not game.voice.playing, "Keep the private message unheard before its later reveal")
		check(game.words.get_parsed_text() == "Nora records a private message for Steve.", "Conceal the private message in early subtitles")
		game._skip_dialogue()
	game._choose("c9_gallery.link", 0, [])
	await wait_frames(3)
	check(not game.stage.actor_visible("nora"), "Keep Nora in the bed until she says she can move")
	game._skip_dialogue()
	check(game.stage.floor_stage.visible and game.stage.floor_stage.bodies.nora.body.visible,
		"Stage Nora beside Steve on the gallery floor after she can move")
	# Count processed frames, which match Movie Maker's written frames one to one.
	# Drawn frames stop counting while a covered window skips drawing.
	var reunion_start_frame := Engine.get_process_frames()
	game._choose("c9_gallery.talk", 0, [])
	await wait_frames(3)
	if not (game.stage.actors.has("steve") and game.stage.actors.has("nora")):
		check(false,"Load Steve and Nora's portrait sheets for the reunion")
		await _finish()
		return
	check(game.active_line == "c9_gallery.talk.01", "Begin Steve's reunion line through the interaction")
	check(game.stage.actors.steve.voice==game.voice, "Bind Steve to the active recording")
	check(game.stage.actors.nora.voice==null, "Keep listener mouth cues clear")
	check(not game.stage.dialogue_shot.is_empty(), "Select authored dialogue camera")
	if capture:
		game.auto_dialogue = true
		var first_frame := reunion_start_frame
		var previous := ""
		while game.dialogue_panel.visible:
			if game.active_line != previous:
				var frame := first_frame if previous.is_empty() else Engine.get_process_frames()
				frames.append({"line": game.active_line, "frame": frame, "from_start": frame - first_frame})
				previous = game.active_line
			await get_tree().process_frame
			if Engine.get_process_frames() - first_frame > 1800:
				check(false, "Reunion capture completed within 60 seconds")
				break
		frames.append({"end_frame": Engine.get_process_frames()})
		await _finish()
		return
	await shot("steve-reunion")
	check(game.words.get_content_height() <= game.words.size.y + 1, "Fit Steve's entire subtitle inside the dialogue panel")
	var person: Node=game.stage.actors.steve
	var limit:=Time.get_ticks_msec()+1000
	while person.last_mouth.is_empty() and game.voice.playing and Time.get_ticks_msec()<limit:
		await get_tree().process_frame
	if game.voice_manifest.get("enabled",true):
		check(person.voice==game.voice and game.voice.playing,"Bind Steve to his approved recording")
	check(person.last_mouth.is_empty() and not person.mouth.visible,"Keep Steve's painted mouth still while he speaks")
	game._pause_audio(true)
	var camera_before: Vector2=game.stage.aim
	var clock_before: float=game.stage.clock
	var shape_before: String=person.last_mouth
	var pose_before: Vector2=person.scale
	await get_tree().create_timer(.18).timeout
	check(game.stage.aim.is_equal_approx(camera_before),"Freeze the illustrated camera while paused")
	check(game.stage.clock==clock_before and person.last_mouth==shape_before,"Freeze expression frames while paused")
	check(person.scale.is_equal_approx(pose_before),"Hold the portrait breathing pose while paused")
	game._pause_audio(false)
	game._save("qa-reunion-interrupted")
	game._load("qa-reunion-interrupted")
	await wait_frames(6)
	check(game.active_line == "c9_gallery.talk.01", "Restore interrupted reunion with the unheard line")
	check(game.stage.actors.nora.visible, "Restore Nora's release state")
	check(game.stage.actors.steve.voice==game.voice, "Restore speech binding after load")
	if game.voice_manifest.get("enabled",true):
		check(game.stage.actors.steve.voice==game.voice and not game.stage.actors.steve.cues.is_empty(),
			"Restore interrupted dialogue with the matching voice timing")
	else:
		check(game.stage.actors.steve.cues.is_empty(), "Keep interrupted text-only dialogue free of stale mouth timing")
	var original_timing: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/lipsync-manifest.json"))
	check(game.lipsync_manifest == original_timing, "Preserve the shared timing manifest across speaker changes and loading")
	game._next_line()
	await wait_frames(5)
	check(game.active_line == "c9_gallery.talk.02", "Advance to Nora's reply")
	check(game.stage.actors.nora.voice==game.voice, "Bind Nora to her recording")
	check(game.stage.actors.steve.voice==null, "Clear Steve's mouth cues on speaker change")
	await shot("nora-reunion")
	check(game.words.get_content_height() <= game.words.size.y + 1, "Fit Nora's entire subtitle inside the dialogue panel")
	game._skip_dialogue()
	await wait_frames(8)
	check(not game.dialogue_panel.visible and game.stage.dialogue_shot.is_empty(), "Restore exploration after skipping")
	for character: Node in game.stage.actors.values():
		check(character.voice==null and character.last_mouth.is_empty(), "Reset lips after skipping "+str(character.name))
	await shot("gallery-exploration")
	game._speak(["c9_gallery.out.03"], Callable())
	await wait_frames(3)
	var replay: Dictionary=game.campaign.content.lines["c9_gallery.out.03"]
	var replay_take: Dictionary=game._recording_for(replay.audio,replay.text).take
	if game.voice_manifest.get("enabled",true):
		check(not replay_take.is_empty() and game.voice.playing and game.voice.stream.resource_path==replay_take.file,
			"Play Nora's approved intercom reveal recording")
	else:
		check(not game.voice.playing, "Keep Nora's revised intercom reveal text-only")
	check(game.stage.dialogue_shot.type=="insert" and game.stage.dialogue_shot.recorded, "Show the listeners during recorded playback")
	check(game.stage.actors.nora.voice==null and game.stage.actors.steve.voice==null, "Keep live mouths neutral during the recording")
	game._skip_dialogue()
	game.campaign.switch_actor("stephen")
	var antenna: Dictionary = game.campaign.task_index["c9_gallery.antenna"]
	game._choose(antenna.id, int(antenna.answer), antenna.get("puzzle",{}).get("solution",[]))
	game._skip_dialogue()
	check(game.campaign.can_leave(), "Resolve every Gallery interaction with staged actors")
	for i: int in 40:
		if not game.dialogue_panel.visible:
			break
		game._next_line()
	check(game.light_remaining>=0.0 and game.cut_skip.visible,"Automatic recap reaches the Gallery departure cut")
	game._advance_scene()
	await wait_frames(3)
	check(game.campaign.current().id != "c9_gallery", "Leave the staged scene through its normal exit")
	check(game.stage.room_id=="c9_wake" and game.stage.background.texture.resource_path.ends_with("/c9_wake.webp"),"Replace the prior Gallery painting on transition")
	await _finish()

func _finish() -> void:
	var result := {"checks": checks, "failures": failures, "renderer": RenderingServer.get_current_rendering_method(),
		"movie_mode": OS.has_feature("movie"), "capture": capture, "frames": frames,
		"physical_audio_output_verified": false, "production_visual_quality_accepted": false}
	var file := FileAccess.open(report_path.path_join("staging-results.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t"))
	file.close()
	print(JSON.stringify(result))
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

extends "res://tests/campaign_input_qa.gd"
## Exercise the production scene loader and clickable paintings using native Godot input.
var details := {}
var screenshots: Array[String] = []
var mouths := {}
var heard_reaction := false
var recordings := {}

func verify_native_line() -> void:
	var line: Dictionary = game.campaign.content.lines[game.active_line]
	var audio_id: String = line.audio
	if not game.voice_manifest.get("enabled",true):
		check(not game.voice.playing and game.line_remaining>=game._reading_time(str(line.get("display_text",line.text)))-.2,
			"Text-only reading time for "+game.active_line)
		return
	var preferred: String = game.voice_manifest.takes[audio_id].file
	var actual: String = game.voice.stream.resource_path if game.voice.stream else ""
	check(actual==preferred and actual.begins_with("res://assets/audio/voices/elevenlabs-v4-script-v2/"),
		"Play the approved recording for "+game.active_line)
	recordings[game.active_line]=actual

func check_speaking_face() -> void:
	verify_native_line()
	var line: Dictionary = game.campaign.content.lines[game.active_line]
	var actor_id: String = line.speaker
	if game.stage.room_id == "p_bay":
		var partner := "helen" if actor_id == "frank" else "frank"
		check(game.stage.actors[partner].role=="listener" and game.stage.actors[partner].voice==null,"Keep the other seated character listening during " + line.id)
		check(game.stage.actors.frank.blocking_plane.scale.x>0 and game.stage.actors.helen.blocking_plane.scale.x<0,"Seat Frank and Helen facing inward")
		if line.id == "p_bay.tune.01":
			check(game.stage.gaze_targets.frank.y>.7 and game.stage.gaze_targets.helen.y>.5,"Watch the tuned receiver together")
		if line.id == "p_bay.out.02":
			check(game.stage.gaze_targets.frank.x>.9 and game.stage.gaze_targets.helen.x<-.9,"Turn attention to each other on Frank’s last line")
	elif game.stage.room_id == "p_meeting" and actor_id.begins_with("general_"):
		var expected := -1.0 if actor_id == "general_us" else 1.0
		check(game.stage.actors.helen.role=="listener" and signf(game.stage.gaze_targets.helen.x)==expected,"Helen follows the delegate who is speaking")
	if mouths.has(actor_id) or not game.stage.actors.has(actor_id) or line.get("delivery","live")!="live":
		return
	if not game.voice_manifest.get("enabled",true):
		return
	var actor: Node = game.stage.actors[actor_id]
	var deadline := Time.get_ticks_msec()+1000
	while Time.get_ticks_msec()<deadline and game.voice.playing:
		if is_instance_valid(actor.mouth) and (actor.mouth.visible or not actor.last_mouth.is_empty()):
			mouths[actor_id]={"line":game.active_line,"frame":actor.last_mouth,"voice_seconds":game.voice.get_playback_position()}
			return
		await get_tree().process_frame

func capture(label: String) -> void:
	for frame: int in 3:
		await get_tree().process_frame
	RenderingServer.force_draw(false)
	var im := get_viewport().get_texture().get_image()
	check(im != null and not im.is_empty(),"Native pixels for "+label)
	if im:
		var path := report_root.path_join(label+".png")
		check(im.save_png(path)==OK,"Write "+label)
		screenshots.append(label+".png")

func jump_to(scene_id: String) -> void:
	game.campaign.reset()
	while game.campaign.current().id != scene_id:
		for task: Dictionary in game.campaign.current().tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		game.campaign.mark_seen(game.campaign.current().intro)
		game.campaign.advance()
	game._load_stage(true)
	await get_tree().process_frame

func wait_for_card() -> void:
	var deadline := Time.get_ticks_msec() + 4000
	while not game.title_card.visible and Time.get_ticks_msec() < deadline:
		await get_tree().process_frame
	check(game.title_card.visible,"Chapter or memory card before "+str(game.campaign.current().id))
	await get_tree().create_timer(.9).timeout
	await capture(str(game.campaign.current().id)+"-card")
	await key(KEY_SPACE)
	deadline = Time.get_ticks_msec() + 4000
	while game.title_card.visible and Time.get_ticks_msec() < deadline:
		await get_tree().process_frame

func _run() -> void:
	Engine.max_fps = 60
	report_root = OS.get_environment("NIGHT_NINE_QA_DIR")
	if report_root.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set an isolated QA capture and save directory.")
		get_tree().quit(1)
		return
	DirAccess.make_dir_recursive_absolute(report_root)
	game.auto_dialogue = false
	await get_tree().create_timer(.3).timeout
	await capture("01-main-menu")
	await click(button("New game",game.menu))
	if game.new_game_confirmation.visible:
		await key(KEY_ENTER,game.new_game_confirmation)
	# The bay opens the game; Veyr closes Interlude 1; Sentinel Point opens Chapter 8.
	var rooms := ["p_bay","p_veyr","p_meeting"]
	for index: int in 3:
		if index == 0:
			check(game.storybook.visible,"The backstory plays before the bay")
			await capture("p_bay-storybook")
			await click(button("Skip story",game.storybook))
		else:
			for attempt: int in 6:
				game.storybook.finish_now()
				game.title_card.finish_now()
				await get_tree().process_frame
			await jump_to(rooms[index])
		await wait_for_card()
		var scene: Dictionary = game.campaign.current()
		var slot: String = scene.id
		check(slot == rooms[index],"Expected room "+slot)
		check(game.stage is Control and game.stage.find_children("*","Node3D",true,false).is_empty(),"Pure illustrated stage "+slot)
		check(game.stage.actors.size() == {"p_bay":2,"p_veyr":1,"p_meeting":3}[slot],"Cast in room "+slot)
		check(game.stage.distant.get_child(0).texture != null,"Loaded room art "+slot)
		for art: Node in game.stage.props.get_children():
			if art is Sprite2D:
				check(art.texture != null,"Loaded foreground "+slot)
		var speaker_ids: Array = []
		while game.dialogue_panel.visible:
			check(not game.words.text.is_empty(),"Show arrival caption "+game.active_line)
			speaker_ids.append(game.active_line)
			await check_speaking_face()
			if speaker_ids.size()==1:
				await get_tree().create_timer(.45).timeout
				await capture(slot+"-arrival")
			await click(button("Continue",game.dialogue_panel))
		await get_tree().create_timer(.55).timeout
		await capture(slot+"-exploration")
		check(game.ambience.playing and game.ambience.stream.resource_path.ends_with("/"+slot+".ogg"),"Location ambience "+slot)
		var hit_locations := {}
		for task: Dictionary in scene.tasks:
			var t: int = scene.tasks.find(task)
			var pin: Button = game.hotspots[t]
			check(pin.is_visible_in_tree() and not pin.disabled,"Enabled evidence "+task.id)
			var position_on_screen: Vector2 = game.stage.project_target(t)
			check(pin.get_global_rect().has_point(position_on_screen),"Painted prop hit test "+task.id)
			hit_locations[task.id] = [snappedf(position_on_screen.x,0.1),snappedf(position_on_screen.y,0.1)]
			await click(pin)
			if game.dialogue_panel.visible:
				check(game.active_line in task.get("lead",[]),"Lead-in before painted puzzle "+task.id)
				while game.dialogue_panel.visible:
					await check_speaking_face()
					speaker_ids.append(game.active_line)
					await click(button("Continue",game.dialogue_panel))
			check(game.selected_task == task.id and game.root.get_node("InteractionPanel").visible,"Clicked authored prop "+task.id)
			if task.id == "p_bay.tune":
				check(game.receiver.record.disabled and game.receiver.players[0].playing,"Receiver starts audibly on the time station")
				game.receiver.dial.grab_focus()
				for step: int in 5:
					await key(KEY_RIGHT)
				await click(game.receiver.narrow)
				check(game.receiver.dial.value==815 and not game.receiver.record.disabled,"Signal isolates at 815 kHz on the narrow band")
				await capture(slot+"-radio")
				await click(game.receiver.record)
			elif task.id == "p_veyr.levels":
				check(button("Apply settings",game.interaction).disabled,"Unselected recorder gain")
				await click(button("−3 dB",game.interaction))
				await click(button("Apply settings",game.interaction))
				check(not task.id in game.campaign.data.done, "Overloading the recorder can be retried")
				await click(button("−6 dB",game.interaction))
				await capture(slot+"-puzzle")
				await click(button("Apply settings",game.interaction))
			elif task.get("puzzle",{}).get("presentation","")=="case_board":
				await solve_case_board(task)
			elif task.has("puzzle"):
				for row_index: int in task.puzzle.rows.size():
					var row: Control = game.puzzle_controls[row_index]
					var choice: Control = row.choices[int(task.puzzle.solution[row_index])]
					(game.interaction.get_parent() as ScrollContainer).ensure_control_visible(choice)
					await get_tree().process_frame
					await click(choice)
				var apply := button("Apply settings",game.interaction)
				(game.interaction.get_parent() as ScrollContainer).ensure_control_visible(apply)
				await get_tree().process_frame
				await click(apply)
			else:
				await click(button("Continue" if task.get("type","")=="beat" else task.options[task.answer],game.interaction))
			check(task.id in game.campaign.data.done,"Saved authored outcome "+task.id)
			while game.dialogue_panel.visible:
				await check_speaking_face()
				if game.active_line=="p_meeting.confess.02":
					await click(button("Continue",game.dialogue_panel))
					heard_reaction=game.reaction_active and game.words.text=="[The delegates share a tired laugh.]"
					check(heard_reaction,"The delegates' group laugh follows their spoken line")
					await capture(slot+"-reaction")
					await click(button("Continue",game.dialogue_panel))
					continue
				speaker_ids.append(game.active_line)
				await click(button("Continue",game.dialogue_panel))
			if index==1 and t==0:
				await click(button("Menu",game.root))
				await click(button("Save game",game.menu))
				await click(button("Load saved game",game.menu))
				check(game.campaign.current().id==slot and task.id in game.campaign.data.done,"Restored illustrated room and solved task")
				if game.menu.visible:
					await click(button("Continue",game.menu))
		check(game.transitioning,"Last finding automatically starts the recap and exit "+slot)
		check(game.cut_skip.visible and game.stage.cut_progress>=0.0,"Running authored departure shot "+slot)
		await get_tree().create_timer(.85).timeout
		await capture(slot+"-last-light")
		if index==1:
			await click(game.cut_skip)
		else:
			var deadline := Time.get_ticks_msec()+roundi((game.cut_duration+1.0)*1000.0)
			while game.campaign.current().id == slot and Time.get_ticks_msec()<deadline:
				await get_tree().process_frame
		details[slot] = {"heard":speaker_ids,"hotspots":hit_locations}
	check(game.campaign.current().id == "c8_lab","Sentinel Point returns to the Meridian laboratory")
	check(game.stage.room_id == "c8_lab" and game.stage is Control,"Chapter 8 continues in the illustrated campaign")
	if game.voice_manifest.get("enabled",true):
		check(not recordings.is_empty(),"Play the approved prologue recordings")
	else:
		check(recordings.is_empty(),"Text-only prologue plays no character recordings")
	check(mouths.is_empty(),"Keep painted mouths still during prologue dialogue")
	var result := {"recordings":recordings,"verified_group_laugh":heard_reaction,"speaking_faces":mouths,"checks":checks,"failures":failures,"scenes":details,"captures":screenshots,"next_scene":game.campaign.current().id,"renderer":RenderingServer.get_current_rendering_method()}
	var output := FileAccess.open(report_root.path_join("prologue-gameplay.json"),FileAccess.WRITE)
	output.store_string(JSON.stringify(result,"  "))
	output.close()
	print(JSON.stringify(result))
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

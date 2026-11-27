extends "res://tests/campaign_input_qa.gd"
## Follow the standard illustrated campaign through the final incoming transmission.
## Every prop and answer is operated through a Control. The only inputs from content
## are the intended investigator and canonical solution, as in a written walkthrough.
var path := ""
var scenes_seen := {}
var takes_seen := {}
var performers_seen := {}
var expressions_seen := {}
var creature_cues := {}
var puzzle_count := 0
var ending_complete := false
var partial_stop := ""
var partial_start := ""
var require_v4 := false
var require_inserts := false
var chapter_inserts := {}
var chapter_checks := {}
var case_boards_played := {}
var captures: Array[String] = []
var frame_samples := {}
var last_frame_usec := 0

func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	if last_frame_usec > 0 and game.started:
		var id: String = game.campaign.current().id
		if not frame_samples.has(id):
			frame_samples[id] = []
		frame_samples[id].append((now - last_frame_usec) / 1000.0)
	last_frame_usec = now

func frame_report() -> Dictionary:
	var report := {}
	for id: String in frame_samples:
		var samples: Array = frame_samples[id]
		samples.sort()
		report[id] = {"frames": samples.size(), "median_ms": samples[samples.size() / 2],
			"p95_ms": samples[int((samples.size() - 1) * .95)], "max_ms": samples.back()}
	return report

func wait_frames(count: int=3) -> void:
	for i: int in count:
		await get_tree().process_frame

func snapshot(name_: String) -> void:
	await wait_frames()
	RenderingServer.force_draw(false)
	var image:=get_viewport().get_texture().get_image()
	check(image!=null and image.get_width()>=850 and image.save_png(path.path_join(name_+".png"))==OK,"Capture illustrated game "+name_)
	captures.append(name_+".png")

func press_control(control: Button) -> void:
	if not is_instance_valid(control):
		check(false,"Expected an available gameplay control in "+str(game.campaign.current().id))
		return
	var holder: Node=control.get_parent()
	while holder and not holder is ScrollContainer:
		holder=holder.get_parent()
	if holder:
		(holder as ScrollContainer).ensure_control_visible(control)
		await wait_frames(2)
	await click(control)

func watch_dialogue(location: String) -> void:
	while game.dialogue_panel.visible and game.campaign.current().id==location and failures.is_empty():
		# RichTextLabel wraps after its caption container has completed layout.
		await wait_frames(2)
		var id: String=game.active_line
		var line: Dictionary=game.campaign.content.lines[id]
		check(not game.words.text.is_empty() and not game.stage.dialogue_shot.is_empty(),"Caption and camera for "+id)
		var delivery_style: Dictionary=game._delivery_style(str(line.get("delivery","live")))
		if not str(delivery_style.label).is_empty():
			check(game.speaker.text.contains(str(delivery_style.label))
				and game.dialogue_panel.get_theme_stylebox("panel").border_color==delivery_style.color,
				"Style and label "+str(line.get("delivery"))+" delivery on "+id)
		if game.campaign.current().has("departure_art") and id in game.campaign.current().outro:
			var departure_layer: TextureRect=game.stage.get("departure_art_layer")
			check(is_instance_valid(departure_layer) and departure_layer.visible
				and departure_layer.texture.resource_path==game.campaign.current().departure_art,
				"Show authored departure art during the outro for "+location)
		check(game.words.get_content_height()<=game.words.size.y+1.0,"Complete subtitle fits on screen for %s (%d/%d)"%[id,game.words.get_content_height(),game.words.size.y])
		var text_only: bool=not game.voice_manifest.get("enabled",true) \
			or str(game.voice_manifest.get("takes",{}).get(line.audio,{}).get("text_hash","")) != str(line.text).sha256_text().substr(0,16)
		if line.get("delivery","live")=="private_recording" or text_only:
			check(not game.voice.playing,"Keep text-only line unheard on "+id)
			check(game.line_remaining>=game._reading_time(str(line.get("display_text",line.text)))-.2,
				"Give text-only caption reading time on "+id)
		else:
			var performance: Dictionary=game._recording_for(line.audio,line.text)
			var take: Dictionary=performance.take
			# Lip sync is retired: later takes carry no mouth cues, and older cues must still match their take.
			check(not take.is_empty() and (performance.timing.is_empty() or take.get("sha256","")==performance.timing.get("audio_sha256","")),"Matching recording for "+id)
			if require_v4:
				check(str(take.file).begins_with("res://assets/audio/voices/elevenlabs-v4/"),"Active v4 recording for "+id)
			check(game.voice.playing and game.voice.stream.resource_path==take.file,"Correct playing take "+id)
			takes_seen[id]=game.voice.stream.resource_path
		if game.stage.has_method("actor_visible"):
			var role: String=game.stage.current_speaker
			if not role.is_empty() and partial_stop.is_empty():
				check(game.stage.actors.has(role),"Load the identity for "+role+" in "+id)
			if game.stage.actors.has(role):
				var actor: Node=game.stage.actors[role]
				check(actor.visible and is_instance_valid(actor.body.texture) and actor.voice==game.voice,"Show and voice the painted "+role)
				if id == "epilogue.in.02":
					check(actor.body.texture.resource_path.ends_with("/iris_epilogue/iris_epilogue.webp"), "Iris speaks with her chosen face in the epilogue")
				performers_seen[role]=true
				if not expressions_seen.has(role) and is_instance_valid(actor.mouth):
					await get_tree().create_timer(.35).timeout
					if not actor.last_mouth.is_empty() or actor.mouth.visible:
						expressions_seen[role]={"line":id,"frame":actor.last_mouth,"seconds":game.voice.get_playback_position()}
			if line.get("delivery","live")!="live":
				for other: Node in game.stage.actors.values():
					check(other.voice==null,"Listeners remain silent during "+id)
			if id=="c1_pier.in.01":
				var painted: Vector2=game.stage.distant.to_global(game.stage.art_point(game.stage.directions.painted_creatures.admiral))
				check(game.stage.dialogue_shot.type=="detail" and not game.stage.frame.get_global_rect().has_point(painted) and game.stage.creatures.admiral.visible,"Keep the original distant sea lion outside Admiral's isolated close-up")
				await get_tree().create_timer(.82).timeout
				await snapshot("c1_pier-admiral")
			if id=="c10_live.out.04":
				check(game.stage.shown_still().ends_with("/c10_live-pier.webp")
					and game.stage.creatures.values().all(func(creature: Node): return not creature.visible),
					"Show Admiral in the pier painting without a duplicate actor in the studio")
			if id=="c6_jail.mail.01":
				check(game.stage.creatures.size()==1 and game.stage.creatures.biscuit.visible,"Biscuit accompanies Pell at the jail")
			for creature: String in game.stage.creatures:
				if game.stage.creatures[creature].visible:
					creature_cues[creature]=id
		if id in ["c1_flat.in.04","c1_flat.saturday.03","c5_station.in.02","c8_beach.in.01","c9_gallery.talk.02","c10_report.out.01","epilogue.in.02"]:
			await get_tree().create_timer(.4).timeout
			await snapshot(id)
		await press_control(button("Continue",game.dialogue_panel))
		if game.active_line==id and game.reaction_active:
			await press_control(button("Continue",game.dialogue_panel))
		if game.active_line==id and game.dialogue_panel.visible:
			check(false,"Advance recorded line "+id)

func operate(task: Dictionary) -> void:
	if task.has("audition_labels"):
		for i: int in task.sounds.size():
			var play := game.interaction.get_node("ReelPlay%d" % i) as Button
			await press_control(play)
			if game.voice_manifest.get("enabled",true):
				var id: String = task.sounds[i]
				var take: Dictionary = game.sound_manifest.get(id.trim_prefix("effect."), {}) if id.begins_with("effect.") else game._recording_for(id).take
				check(game.voice.playing and game.voice.stream.resource_path == str(take.get("file","")), "Preview original recorder cue " + str(i + 1) + " in " + task.id)
			else:
				check(not game.voice.playing,"Keep recorder cue text-only "+str(i+1)+" in "+task.id)
		var reveal := game.interaction.get_node("ReelCaptions") as CheckButton
		await press_control(reveal)
		var captions := game.interaction.get_node("ReelTranscripts") as VBoxContainer
		check(captions.visible and captions.get_child_count() == task.sounds.size(), "Read the actual reel transcripts without audio")
		await press_control(reveal)
	if task.has("evidence_labels") and task.get("puzzle",{}).get("presentation","")!="tape_alignment":
		for index: int in task.sounds.size():
			var listen := game.interaction.get_node("EvidencePlay%d" % index) as Button
			var strip: Control = game.interaction.get_node_or_null("EvidenceTrace%d" % index)
			var transcript: Label=game.interaction.get_node_or_null("EvidenceTranscript%d" % index)
			check(listen.text.contains(task.evidence_labels[index])
				and ((is_instance_valid(strip) and strip.envelope.size()>0)
					or (is_instance_valid(transcript) and transcript.text.contains("Text-only transcript"))),
				"Labeled waveform or text-only evidence for " + task.id)
			await press_control(listen)
			if task.sounds[index].begins_with("effect.") or game.voice_manifest.get("enabled",true):
				check(game.voice.playing and game.voice.stream != null, "Play capture " + str(index + 1) + " for " + task.id)
			else:
				check(not game.voice.playing,"Keep capture text-only "+str(index+1)+" for "+task.id)
		if task.has("clip_captions"):
			var toggle := button("Show sound captions", game.interaction) as CheckButton
			check(is_instance_valid(toggle) and not toggle.button_pressed, "Sound descriptions start hidden for " + task.id)
			await press_control(toggle)
			var captions := game.interaction.get_node("SoundCaptions") as Label
			check(captions.is_visible_in_tree() and captions.text.contains(str(task.clip_captions.back())), "Read sound descriptions for " + task.id)
			await press_control(toggle)
		if task.id == "c2_aquarium.guard":
			await snapshot("c2_aquarium-corridor-evidence")
	if task.id=="p_veyr.levels":
		await press_control(button("6 dB",game.interaction))
		await press_control(button("Apply settings",game.interaction))
	elif task.id=="p_bay.tune":
		game.receiver.dial.grab_focus()
		for pulse: int in 5:
			await key(KEY_RIGHT)
		await press_control(game.receiver.narrow)
		await press_control(game.receiver.record)
	elif task.get("puzzle",{}).get("presentation","")=="tape_alignment":
		var tape: NightTapeCompare=game.tape_compare
		tape.slider.grab_focus()
		var target_steps:=roundi((tape.recording.expected_offset-tape.slider.value)/.01)
		for step: int in absi(target_steps):
			await key(KEY_LEFT if target_steps<0 else KEY_RIGHT)
		check(tape.recording.aligned(tape.slider.value),"Keyboard aligns the two evidence recordings")
		check(tape.row_choices.size()==task.puzzle.rows.size(),"Show every authored comparison row")
		for index: int in tape.row_choices.size():
			tape.row_choices[index].select(int(task.puzzle.solution[index])+1)
		await press_control(button("Play together",tape))
		check(game.voice.playing and game.voice.stream==tape.active_stream,"Play the actual aligned voices")
		await snapshot(str(task.id).replace(".","-")+"-tape-comparison")
		await press_control(button("Record finding",tape))
	elif task.get("puzzle",{}).get("presentation","")=="receiver":
		var investigation_receiver=game.receiver
		var receiver_data: Dictionary=task.puzzle.receiver
		for index: int in investigation_receiver.choices.size():
			investigation_receiver.choices[index].select(int(task.puzzle.solution[index])+1)
		investigation_receiver.dial.value=float(receiver_data.target)
		if bool(receiver_data.get("require_narrow",false)):
			investigation_receiver.narrow.button_pressed=true
		await wait_frames(3)
		check(not investigation_receiver.record.disabled,"Tune the authored receiver for "+task.id)
		await press_control(investigation_receiver.record)
	elif task.get("puzzle",{}).get("presentation","")=="case_board":
		if case_boards_played.is_empty() or task.id=="c8_beach.first":
			await snapshot(str(task.id)+"-case-board")
		await solve_case_board(task)
		var modes: Array=[]
		for sheet: Dictionary in task.puzzle.stages:
			modes.append(sheet.mode)
		case_boards_played[task.id]=modes
	elif task.get("puzzle", {}).get("presentation", "") == "broadcast_desk":
		var desk: Variant=game.interaction.get_node("BroadcastDesk")
		desk.fader.grab_focus()
		await key(KEY_RIGHT)
		for step: int in task.puzzle.cues.size():
			var cue: Dictionary = task.puzzle.cues[step]
			var deadline := Time.get_ticks_msec() + 20000
			while desk.lamp.text != cue.lamp and Time.get_ticks_msec() < deadline:
				await get_tree().process_frame
			check(desk.lamp.text == cue.lamp, "Live return for " + task.id)
			await press_control(desk.keys[int(task.puzzle.solution[step])])
	elif task.has("puzzle"):
		for i: int in task.puzzle.rows.size():
			var row: Control=game.puzzle_controls[i]
			await press_control(row.choices[int(task.puzzle.solution[i])])
			check(row.selected==int(task.puzzle.solution[i]),"Set "+str(task.puzzle.rows[i].label)+" for "+task.id)
		await press_control(button("Apply settings",game.interaction))
	else:
		if task.id=="p_bay.message":
			for wrong_index: int in [1,2]:
				var missed:=button(task.options[wrong_index],game.interaction)
				await press_control(missed)
				check(missed.disabled and game.puzzle_response.text==task.wrong[str(wrong_index)],
					"Disable wrong option and show its reason "+str(wrong_index))
			var offer:=button("Need a hint?",game.interaction)
			check(is_instance_valid(offer) and offer.visible,"Offer hint one after two misses")
			await press_control(offer)
			check(game.puzzle_response.text==task.hints[0] and game.hint_button.text=="Hint 2 of 3",
				"Open hint one only after the player accepts")
		await press_control(button("Continue" if task.get("type","")=="beat" else task.options[task.answer],game.interaction))
		if task.get("sound_bank", false):
			var anchor: String = task.sounds[int(task.answer)].trim_prefix("effect.")
			check(game.effect.playing and game.effect.stream.resource_path == game.sound_manifest[anchor].file,
				"Send the selected recording to the bedside speaker for " + task.id)
	if task.has("puzzle") or task.id=="p_bay.tune":
		puzzle_count+=1

func wait_for_cut(slot: String, progress: float) -> void:
	var deadline:=Time.get_ticks_msec()+int((game.cut_duration+1.5)*1000)
	while game.campaign.current().id==slot and game.stage.cut_progress<progress and Time.get_ticks_msec()<deadline:
		await get_tree().process_frame

func watch_chapter_insert(slot: String) -> void:
	var layers: Array=game.stage.chapter_frames
	var paths: Array[String]=[]
	for layer: TextureRect in layers:
		paths.append(layer.texture.resource_path)
	chapter_inserts[slot]={"frames":paths}

	if require_inserts:
		check(layers.size()==2,"Two authored chapter keyframes for "+slot)
		check(layers.all(func(layer: TextureRect): return layer.material==null),"Show the chapter paintings without morphing them in "+slot)
	var has_film: bool = is_instance_valid(game.stage.chapter_film)
	if require_inserts:
		check(has_film and game.cut_duration>=11.0,"Play the third full-length animated shot in "+slot)
	if has_film:
		var film = game.stage.chapter_film
		chapter_inserts[slot].film = film.texture.resource_path
		chapter_inserts[slot].seconds = game.cut_duration
		check(film.texture.resource_path.ends_with("/"+slot+".webp"),"Use the registered continuation art in "+slot)
	await wait_for_cut(slot,.14 if has_film else .22)
	if OS.get_environment("NIGHT_NINE_QA_CAPTURE_INSERT_FRAMES")=="1":
		await snapshot(slot+"-chapter-first")
	check(layers[0].modulate.a>.99 and not game.stage.cast_plane.visible and not game.stage.props.visible,"Painted chapter insert covers the prior room "+slot)
	if slot=="c1_escape":
		var still: float=game.stage.cut_progress
		await key(KEY_ESCAPE)
		await get_tree().create_timer(.2).timeout
		check(game.menu.visible and absf(game.stage.cut_progress-still)<.018,"Pause the chapter insert")
		await key(KEY_ESCAPE)
	if layers.size()==2:
		await wait_for_cut(slot,.26 if has_film else .54)
		check(layers[1].texture!=layers[0].texture and layers[1].material==null,"Dissolve between two distinct story paintings in "+slot)
		await snapshot(slot+"-chapter-motion")
		await wait_for_cut(slot,.84)
		check(layers[1].modulate.a>.99,"Hold the second drawing in "+slot)
		if has_film:
			var action = game.stage.chapter_film
			check(action.visible and action.modulate.a>.99 and action.elapsed>.65,"Play the new shot over the opening poses in "+slot)
			if action.record.has("subject"):
				check(action.action.get_shader_parameter("subject_tex") is Texture2D,"Composite the independently moving subject in "+slot)
		if OS.get_environment("NIGHT_NINE_QA_CAPTURE_INSERT_FRAMES")=="1":
			await snapshot(slot+"-chapter-last")
	else:
		await snapshot(slot+"-chapter-motion")
	if slot=="c4_escape":
		await press_control(game.cut_skip)
		check(game.campaign.current().id!=slot and not is_instance_valid(game.stage.incoming_frame),"Skip the film directly to gameplay")
		return
	var deadline:=Time.get_ticks_msec()+5000
	while game.campaign.current().id==slot and Time.get_ticks_msec()<deadline:
		await get_tree().process_frame
	if not game._book_before(str(game.campaign.current().id)).is_empty():
		check(game.storybook.visible,"A storybook follows the film in "+slot)
		return
	if str(game.campaign.current().id) in game.PAINTED_NIGHTS:
		# A flashback opens on its own memory card instead of a dissolve.
		check(game.title_card.visible,"A memory card follows the film in "+slot)
		return
	var dissolved: bool=game.campaign.current().id!=slot and is_instance_valid(game.stage.incoming_frame)
	check(dissolved and is_instance_valid(game.stage.background),"Dissolve onto the actual following location "+slot)
	if dissolved:
		check(game.stage.incoming_frame.texture.resource_path==paths.back(),"Carry the same last frame into the following room")
		if has_film:
			check(game.stage.incoming_frame.has_node("ChapterAction"),"Keep the on-screen subject in the dissolve in "+slot)
		await get_tree().create_timer(.7).timeout
		check(not is_instance_valid(game.stage.incoming_frame),"Finish the dissolve and free the chapter media in the following room")

## Storybooks and chapter cards are timed and photographed in story_flow_qa.gd.
## Here they are passed with the same controls a player would use.
func clear_overlays() -> void:
	var deadline := Time.get_ticks_msec() + 12000
	while (game.storybook.visible or game.title_card.visible) and Time.get_ticks_msec() < deadline:
		if game.storybook.visible and game.storybook.closing < 0.0:
			await click(button("Skip story", game.storybook))
		elif game.title_card.visible and game.title_card.closing < 0.0:
			await key(KEY_SPACE)
		await get_tree().process_frame
	check(not game.storybook.visible and not game.title_card.visible, "Pass the story overlay before " + str(game.campaign.current().id))

func verify_room(scene: Dictionary) -> void:
	var slot: String = scene.id
	await clear_overlays()
	if scene.id == "c1_flat":
		var deadline := Time.get_ticks_msec() + 8000
		while not game.dialogue_panel.visible and Time.get_ticks_msec() < deadline:
			await get_tree().process_frame
		check(game.active_line == "c1_flat.in.04", "The kitchen opens with Nora, not the tape")
	var chapter: bool = slot not in game.PAINTED_NIGHTS
	var details: Dictionary={"hits":{},"chapter":scene.chapter,"music":game.score.current_file}
	check(game.stage is Control and game.stage.find_children("*","Node3D",true,false).is_empty(),"Illustrated 2D scene "+slot)
	check(game.stage.targets.size()==scene.tasks.size(),"One mapped surface per task in "+slot)
	if chapter:
		check(is_instance_valid(game.stage.background),"Loaded room painting "+slot)
		if game.stage.background:
			details.art=game.stage.background.texture.resource_path
			check(details.art.ends_with("/"+slot+".webp"),"Dedicated environment painting for "+slot)
		check(game.stage.physical_art.size()==scene.tasks.size(),"Separate painted object crops in "+slot)
		check(game.stage.location_landmarks.size()==scene.tasks.size(),"Registered per-object source landmarks in "+slot)
		check(game.stage.atmosphere.visible,"Near-field atmosphere in "+slot)
		if slot=="c8_beach":
			game.stage.set_quality("performance")
			check(not game.stage.atmosphere.visible and is_instance_valid(game.stage.background.texture),"The lower-cost profile keeps the complete painting")
			game.stage.set_quality("high")
		if partial_stop.is_empty():
			check(game.ambience.playing and game.ambience.stream.resource_path.ends_with("/"+slot+".ogg"),"Play authored location ambience "+slot)
	scenes_seen[slot]=details
	await watch_dialogue(slot)
	await wait_frames()
	if slot=="c1_pier":
		check(not game.stage.creatures.admiral.visible,"Use only the original painted sea lion in the pier wide")
	await snapshot(slot)
	for index: int in scene.tasks.size():
		if not failures.is_empty():
			return
		var task: Dictionary=scene.tasks[index]
		if not task.actor.is_empty() and task.actor!=game.campaign.data.actor:
			for cycle: int in scene.actors.size():
				await key(KEY_Q)
				if game.campaign.data.actor==task.actor:
					break
			check(game.campaign.data.actor==task.actor,"Switch to required investigator "+task.actor)
		var pin: Button=game.hotspots[index]
		var point: Vector2=game.stage.project_target(index)
		var owner_id: String = game._person_for_task(task.id)
		if not owner_id.is_empty() and game.stage.talk_body_visible(owner_id):
			check(not pin.visible, "Person-linked lead hides separate floating marker " + task.id)
			details.hits[task.id]=[snappedf(point.x,.1),snappedf(point.y,.1)]
			var figure: Sprite2D = game.stage.talk_figures[owner_id]
			var click_at := figure.to_global(figure.get_rect().get_center())
			var motion := InputEventMouseMotion.new()
			motion.position = click_at
			get_viewport().push_input(motion, true)
			await wait_frames(1)
			for down: bool in [true, false]:
				var press := InputEventMouseButton.new()
				press.position = click_at
				press.button_index = MOUSE_BUTTON_LEFT
				press.button_mask = MOUSE_BUTTON_MASK_LEFT if down else 0
				press.pressed = down
				get_viewport().push_input(press, true)
			await wait_frames(2)
			check(game.root.get_node("InteractionPanel").visible, "Clicking " + owner_id + " opens their conversation menu")
			await press_control(button(task.title, game.interaction))
		else:
			check(pin.is_visible_in_tree() and not pin.disabled and pin.get_global_rect().has_point(point),"Hitbox on painted object "+task.id)
			details.hits[task.id]=[snappedf(point.x,.1),snappedf(point.y,.1)]
			if task.id=="c3_house.crossword":
				await key(KEY_I)
				check(game.root.get_node("InteractionPanel").visible,"Open keyboard evidence list")
				await key(KEY_SPACE)
			else:
				await click(pin)
		if game.stage.has_method("is_walking") and game.stage.is_walking():
			var deadline := Time.get_ticks_msec()+20000
			while game.stage.is_walking() and Time.get_ticks_msec()<deadline:
				await get_tree().process_frame
		if game.dialogue_panel.visible:
			check(game.active_line in task.get("lead",[]),"Lead-in starts before the puzzle for "+task.id)
			await watch_dialogue(slot)
			for lead_line: String in task.get("lead",[]):
				check(lead_line in game.campaign.data.seen,"Remember lead-in line "+lead_line)
		check(game.selected_task==task.id and (game.tape_compare.visible or game.root.get_node("InteractionPanel").visible),"Open from physical object "+task.id)
		if task.has("art"):
			var evidence_art: TextureRect=game.get("task_art")
			check(is_instance_valid(evidence_art) and evidence_art.is_visible_in_tree()
				and evidence_art.texture.resource_path==task.art,
				"Show framed task art without replacing the puzzle for "+task.id)
		if not failures.is_empty():
			return
		await operate(task)
		check(task.id in game.campaign.data.done,"Canonical evidence entered from real controls "+task.id)
		if task.has("art"):
			var finding_art: TextureRect=game.get("task_art")
			check(game.dialogue_panel.visible and is_instance_valid(finding_art) and finding_art.is_visible_in_tree(),
				"Keep task art visible through the finding for "+task.id)
		if task.id=="c9_gallery.link":
			check(not game.stage.actor_present("nora"),"Nora stays in the bed until she says she can move")
		if task.id=="c6_iris.takes":
			await press_control(button("Menu",game.root))
			await press_control(button("Save game",game.menu))
			var last_line: String=game.active_line
			await press_control(button("Load saved game",game.menu))
			check(game.campaign.current().id==slot and task.id in game.campaign.data.done and game.active_line==last_line,"Restore the same chapter task and interrupted speech")
		await watch_dialogue(slot)
		if task.id=="c9_gallery.link":
			check(game.stage.actor_visible("nora"),"Nora appears after the uncoupling")
		var finding: String=task.get("finding","")
		if not finding.is_empty():
			check(finding in game.campaign.data.seen,"Play the finding before returning control for "+task.id)
		if task.id == "c1_flat.control":
			check("c1_flat.in.01" not in game.campaign.data.seen and game.campaign.can_leave(),
				"Finish Chapter 1's kitchen without listening to the optional voicemail")
		if task.id == "c1_flat.compare" and failures.is_empty():
			await exercise_notebook()
	check(game.transitioning,"The cleared scene starts its recap and departure automatically from "+slot)
	for recap_line: String in scene.get("recap",[]):
		check(recap_line in game.campaign.data.seen,"Play scene recap before departure "+recap_line)
	check(game.light_remaining>=0 and game.cut_skip.visible,"Authored terminal shot "+slot)
	if scene.has("departure_art"):
		var departure_layer: TextureRect=game.stage.get("departure_art_layer")
		check(is_instance_valid(departure_layer) and departure_layer.visible
			and departure_layer.texture.resource_path==scene.departure_art,
			"Authored departure art takes priority in the cut for "+slot)
	details.departure_music=game.score.current_file
	if slot in ["c1_pier", "epilogue", "one_year"]:
		var story_layers: Array = game.stage.chapter_frames
		check(story_layers.size() == 1, "Present the original story painting in " + slot)
		if story_layers.size() == 1:
			await wait_for_cut(slot, .22)
			check(story_layers[0].texture.resource_path.ends_with("/" + slot + ".webp") and story_layers[0].modulate.a > .99, "Reveal the full painting in " + slot)
			await snapshot(slot + "-story-cut")
			if slot in ["epilogue","one_year"] and require_inserts:
				var coda = game.stage.chapter_film
				# The film now lasts whole bars of its music, within four percent of its drawn length.
				check(is_instance_valid(coda) and game.cut_duration>=12.5, "Time the ending film in " + slot)
				if is_instance_valid(coda):
					await wait_for_cut(slot,.53)
					check(coda.modulate.a>.99 and coda.elapsed>.35, "Play the coda's action in " + slot)
					await snapshot(slot+"-coda")
					if slot=="one_year":
						await wait_for_cut(slot,.78)
						check(not coda.visible,"Return from the new world to Steve before the credits")
	if chapter and game.stage.directions.get("chapter_insert",false) and not scene.has("departure_art"):
		if slot=="c3_archive" and not game.stage.chapter_frames.is_empty():
			await key(KEY_ESCAPE)
			await press_control(button("Save game",game.menu))
			await press_control(button("Load saved game",game.menu))
			check(game.campaign.current().id==slot and game.light_remaining>=0 and game.stage.chapter_frames.size()==2,"Restore a save made during the archive departure film")
		if not game.stage.chapter_frames.is_empty():
			await watch_chapter_insert(slot)
			return
		check(not require_inserts,"An authored chapter insert is present in "+slot)
	if chapter and slot in ["c1_escape","c9_choir","postcredits"]:
		await get_tree().create_timer(.90).timeout
		await snapshot(slot+"-departure")
	await press_control(game.cut_skip)
	await wait_frames(2)
	if slot == "one_year":
		check(game.credits_panel.visible and game.campaign.current().id == slot, "See the credits before Shaw receives the final signal")
		await press_control(game.credits_return)
		await wait_frames(2)
		check(game.title_card.visible and game.title_card.kicker.text == "After the credits", "Title the final transmission after the credits")
		await clear_overlays()
		check(game.campaign.current().id == "postcredits" and game.dialogue_panel.visible, "Continue from credits to the final transmission")

func inspect_credits(parent: Node, save_picture: bool) -> void:
	await press_control(button("Credits",parent))
	check(game.credits_panel.visible,"Open the original game credits")
	for credit: String in ["[b]Original story (written 25 years ago):[/b]\nS3PehR","[b]Built using[/b]\nGodot Game Engine","[b]Original Writing, Creative Decisions and Music Composition:[/b]\nSepehr Pakbaz","[b]Script Writing, Narration and Game Programming:[/b]\nClaude Opus 5.5\nGemini 4 Neon\nGitHub Copilot Fusion","[b]Artworks, Characters:[/b]\nGPT Image 2.6","[b]Music Generation:[/b]\nGoogle Lyria 3.5","[b]Voices:[/b]\nElevenLabs 4","[b]Code Deployment, Testing and hosting:[/b]\nGitHub","[b]Game hosting[/b]\nCloudflare Pages"]:
		check(game.credits_body.text.contains(credit),"Show the approved credit for " + credit)
	if save_picture:
		await get_tree().create_timer(.83).timeout
		await snapshot("credits")
	await press_control(game.credits_toggle)
	check(game.showing_notices and game.credits_body.text==FileAccess.get_file_as_string("res://LICENSES.txt") and game.credits_body.text.contains("Godot Engine contributors"),"Open the complete bundled third-party notices")
	await key(KEY_ESCAPE)
	check(game.credits_panel.visible and not game.showing_notices,"Return from notices to the credits")
	await press_control(game.credits_return)
	check(not game.credits_panel.visible and parent.is_visible_in_tree(),"Return to the caller of the credits")

func start_section(id: String) -> void:
	# Isolated art review uses the same validated task journal as a player save.
	while game.campaign.current().id!=id:
		var scene: Dictionary=game.campaign.current()
		game.campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			var solved: Dictionary=game.campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[]))
			check(solved.ok,"Prepare authored prerequisite "+task.id)
			game.campaign.mark_seen(task.lines)
		game.campaign.mark_seen(scene.outro)
		if not game.campaign.advance() or game.campaign.data.finished:
			check(false,"Unknown requested review room "+id)
			return
	game.started=true
	game.menu.hide()
	game._load_stage(true)

func exercise_notebook() -> void:
	# Recreate the save fields used by the original illustrated release.
	var legacy: Dictionary = game.campaign.data.duplicate(true)
	legacy.erase("walk_positions")
	legacy.erase("notebook")
	check(game.saves.write_slot("manual", legacy), "Accept an original schema-2 save")
	await press_control(button("Menu", game.root))
	await press_control(button("Load saved game", game.menu))
	check(game.campaign.data.notebook.marks.is_empty() and game.campaign.current().id == "c1_flat", "Open a legacy manual save with a fresh casebook")
	await press_control(button("Notebook", game.root))
	var book: Control = game.casebook
	await press_control(book.tabs["Hypotheses"])
	var cross := book.sheet.find_child("tape_fault_struck", true, false) as Button
	var keep := book.sheet.find_child("misheard_open", true, false) as Button
	check(book.case_ids == ["greeting"] and book.sheet.find_child("stand_in_open", true, false) == null, "Only mundane explanations are available before physical evidence")
	await press_control(cross)
	await press_control(keep)
	check(game.campaign.data.notebook.marks.get("tape_fault") == "struck" and game.campaign.data.notebook.marks.get("misheard") == "open", "Independently cross out and retain theories")
	await click(book.note)
	for letter in "Test fresh tape":
		var event := InputEventKey.new()
		event.keycode = letter.to_upper().unicode_at(0)
		event.physical_keycode = event.keycode
		event.unicode = letter.unicode_at(0)
		event.pressed = true
		game.get_viewport().push_input(event, true)
		event = event.duplicate()
		event.pressed = false
		game.get_viewport().push_input(event, true)
	await wait_frames(2)
	if game.campaign.data.notebook.notes.get("greeting") != "Test fresh tape":
		print("Notebook input check ", JSON.stringify({"text":book.note.text, "has_focus":book.note.has_focus(), "editing":book.note.is_editing(), "state":game.campaign.data.notebook.notes}))
	check(game.campaign.data.notebook.notes.get("greeting") == "Test fresh tape", "Write a personal theory through text input")
	await snapshot("c1_flat-hypothesis-notebook")
	await press_control(book.tabs["Evidence"])
	check(book.archive.text.contains("Sunday") and not book.archive.text.contains("aquarium work order"), "Only collected evidence is readable")
	await press_control(book.tabs["Transcript"])
	check(book.archive.text.contains("sleepyhead"), "Notebook retains the reached dialogue transcript")
	await press_control(button("Return to the scene", game.journal))
	var autosave: Dictionary = game.saves.read_slot("autosave")
	check(autosave.get("state", {}).get("notebook", {}).get("notes", {}).get("greeting") == "Test fresh tape", "Persist the written note when closing the notebook")
	await press_control(button("Menu", game.root))
	await press_control(button("Save game", game.menu))
	await press_control(button("Load saved game", game.menu))
	await press_control(button("Notebook", game.root))
	await press_control(book.tabs["Hypotheses"])
	keep = book.sheet.find_child("tape_fault_open", true, false) as Button
	check(book.note.text == "Test fresh tape" and game.campaign.data.notebook.marks.get("tape_fault") == "struck", "Restore the player's theory and mark through a manual load")
	await press_control(keep)
	check(game.campaign.data.notebook.marks.get("tape_fault") == "open", "Reopen an explanation after reconsidering it")
	await press_control(button("Return to the scene", game.journal))

func _run() -> void:
	Engine.max_fps=60
	var isolated:=OS.get_environment("NIGHT_NINE_SAVE_DIR")
	report_root=OS.get_environment("NIGHT_NINE_QA_DIR")
	if report_root.is_empty() or isolated.is_empty():
		push_error("Use isolated NIGHT_NINE_QA_DIR and NIGHT_NINE_SAVE_DIR for this walkthrough.")
		get_tree().quit(1)
		return
	path=report_root.path_join("campaign-render")
	DirAccess.make_dir_recursive_absolute(path)
	partial_stop=OS.get_environment("NIGHT_NINE_QA_STOP_AT")
	require_v4=OS.get_environment("NIGHT_NINE_QA_EXPECT_V4")=="1"
	require_inserts=OS.get_environment("NIGHT_NINE_QA_EXPECT_INSERTS")=="1"
	game.auto_dialogue=false
	await wait_frames()
	partial_start=OS.get_environment("NIGHT_NINE_QA_START_AT")
	await inspect_credits(game.menu,false)
	if partial_start.is_empty():
		await press_control(button("New game",game.menu))
		if game.new_game_confirmation.visible:
			await key(KEY_ENTER,game.new_game_confirmation)
	else:
		start_section(partial_start)
	var start_index: int=game.campaign.data.scene
	for scene: Dictionary in game.campaign.content.scenes.slice(start_index):
		print("Walking illustrated room ",scene.id)
		var before_checks: int = checks
		check(game.campaign.current().id==scene.id,"Sequential room "+scene.id)
		await verify_room(scene)
		chapter_checks[scene.chapter] = int(chapter_checks.get(scene.chapter,0)) + checks - before_checks
		if not failures.is_empty() or scene.id==partial_stop:
			break
	if failures.is_empty() and (partial_stop.is_empty() or game.campaign.data.finished):
		ending_complete=game.campaign.data.finished and game.end_card.visible
		check(ending_complete,"The postcredits signal leads to the ending")
		for role: String in performers_seen:
			check(not expressions_seen.has(role),"Keep the painted mouth still for the speaking "+role)
		if partial_start.is_empty():
			for creature: String in ["admiral","biscuit","wick"]:
				check(creature_cues.has(creature),"Stage "+creature+" in a canonical scene")
		var final_save: Dictionary = game.saves.read_slot("autosave")
		var saved_ending: bool = final_save.get("state", {}).get("finished", false)
		if not saved_ending:
			push_error("Ending autosave: write=%s, live=%s, read=%s, recovered=%s, scene=%s" % [
				game.saves.last_error, game.campaign.validate(game.campaign.data),
				final_save.get("error", ""), final_save.get("recovered", false),
				final_save.get("state", {}).get("scene_id", "")])
		check(saved_ending,"Persist the final campaign state")
		check(game._load("autosave") and game.campaign.data.finished and game.end_card.visible,"Restore the completed game and end card")
		await snapshot("ending")
		await inspect_credits(game.end_card,true)
		await press_control(button("Read the notebook and transcript",game.end_card))
		await press_control(game.casebook.tabs["Transcript"])
		check(game.journal.visible and game.casebook.archive.text.contains("Hello. We heard the singing."),"Read the completed notebook and final transcript")
	var unique_streams: Dictionary={}
	for path_played: String in takes_seen.values():
		unique_streams[path_played]=true
	if require_v4 and partial_start.is_empty() and partial_stop.is_empty():
		check(unique_streams.size()==game.voice_manifest.takes.size(),"Play all distinct preferred cast takes through the standard audio player")
	var result:={"checks":checks,"chapter_checks":chapter_checks,"case_boards":case_boards_played,"failures":failures,"scenes":scenes_seen.size(),"locations":scenes_seen,"played_lines":takes_seen.size(),"distinct_streams":unique_streams.size(),
		"recorded_takes":takes_seen,"chapter_inserts":chapter_inserts,"required_inserts":require_inserts,"required_v4":require_v4,"on_camera":performers_seen.keys(),"face_frames":expressions_seen,"creature_cues":creature_cues,"instrument_puzzles":puzzle_count,"finished":ending_complete,"partial_stop":partial_stop,"partial_start":partial_start,"captures":captures,
		"renderer":RenderingServer.get_current_rendering_method(),"audio_driver":AudioServer.get_driver_name(),
		"frame_times":frame_report()}
	var file:=FileAccess.open(path.path_join("results.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(result,"  "));file.close()
	print("Walkthrough: ",checks," checks; ",failures.size()," failures; ",scenes_seen.size()," rooms.")
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

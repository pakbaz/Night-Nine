extends SceneTree
var checks := 0
var failures: Array[String] = []

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)

func _scene_index(state: NightCampaign, id: String) -> int:
	for i: int in state.content.scenes.size():
		if state.content.scenes[i].id == id:
			return i
	return -1

func _check_story_shape(state: NightCampaign) -> void:
	var scenes: Array = state.content.scenes
	check(scenes[0].id == "p_bay" and scenes[1].id == "c1_flat", "Open on the bay with Steve's parents, then Chapter 1")
	check(_scene_index(state, "p_veyr") == _scene_index(state, "i1_archive") + 1 and scenes[_scene_index(state, "p_veyr")].chapter == "Interlude 1", "Veyr closes the Archivist's interlude")
	check(_scene_index(state, "p_meeting") + 1 == _scene_index(state, "c8_lab") and scenes[_scene_index(state, "p_meeting")].chapter == "Chapter 8", "Sentinel Point opens Chapter 8 as Helen's notebook is read")
	var previous := ""
	for scene: Dictionary in scenes:
		if scene.chapter != previous:
			check(scene.has("card") and scene.card.has("chapter") and not str(scene.card.chapter.title).is_empty(), "Chapter card for " + str(scene.chapter))
		previous = scene.chapter
	for id: String in ["p_veyr", "p_meeting", "one_year"]:
		check(scenes[_scene_index(state, id)].get("card", {}).has("page"), "Time-jump page for " + id)
	var books: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/storybook.json")).books
	var music: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/music.json"))
	for key: String in ["opening", "aftermath", "after"]:
		var book: Dictionary = books[key]
		check(_scene_index(state, str(book.before)) >= 0, "Storybook " + key + " leads into a real scene")
		check(ResourceLoader.exists(str(book.music.file)), "Storybook " + key + " has its music")
		var last := -1.0
		for panel: Dictionary in book.panels:
			check(ResourceLoader.exists(str(panel.image)), "Storybook picture " + str(panel.image))
			check(float(panel.bar) > last and float(panel.bar) < float(book.end_bar), "Storybook panels run in bar order in " + key)
			last = float(panel.bar)
			for line: Dictionary in panel.lines:
				check(float(line.bar) >= float(panel.bar) and not str(line.text).contains("—"), "Caption sits inside its panel in " + key)
				check(ResourceLoader.exists(str(line.get("narration", ""))), "Recorded narration for: " + str(line.text))
	check(str(books.opening.before) == str(scenes[0].id), "The opening storybook comes first")
	for group: Dictionary in music.chapters.values():
		for track: Dictionary in group.values():
			check(float(track.get("bpm", 0)) >= 60.0 and float(track.get("bpm", 0)) <= 120.0, "Bar grid for " + str(track.file))
	for id: String in music.departures:
		check(_scene_index(state, id) >= 0, "Departure music belongs to a scene " + id)
	for scene: Dictionary in scenes:
		if scene.id != "postcredits":
			var plan: Dictionary = music.scene_music.get(scene.id, {})
			check(ResourceLoader.exists(str(plan.get("file", ""))), "Planned music for " + str(scene.id))
	check(music.scene_music.c1_flat.file.ends_with("tape-anomaly.mp3") and music.scene_music.c10_live.file == music.title.file, "Tape Anomaly for the tapes; the main title for the finale")

func _check_migration() -> void:
	var old_order: Array = NightCampaign.ORDER_V1
	var probe := NightCampaign.new()
	# A player who had reached Chapter 4 under the old order keeps their place.
	var at_c4 := probe.data.duplicate(true)
	at_c4.content = "campaign-1"
	at_c4.scene = old_order.find("c4_safe")
	at_c4.actor = "steve"
	for i: int in old_order.find("c4_safe"):
		for scene: Dictionary in probe.content.scenes:
			if scene.id == old_order[i]:
				for task: Dictionary in scene.tasks:
					at_c4.done.append(task.id)
				at_c4.seen.append_array(scene.intro)
	at_c4.hints = {"p_meeting.terms": 2}
	check(probe.validate(at_c4).is_empty() and probe.restore(at_c4), "Accept a campaign-1 save from Chapter 4")
	check(probe.current().id == "c4_safe" and probe.data.content == probe.content.version, "Keep the Chapter 4 position under the new order")
	check(not probe.data.done.has("p_meeting.terms") and probe.data.done.has("p_veyr.levels") and not probe.data.hints.has("p_meeting.terms"), "Replay Sentinel Point later, keep the finished Veyr memory")
	# A player inside the old three-night prologue starts again at the bay.
	var in_prologue := NightCampaign.new().data.duplicate(true)
	in_prologue.content = "campaign-1"
	in_prologue.scene = 1
	in_prologue.actor = "helen"
	in_prologue.done = ["p_veyr.shield", "p_veyr.levels", "p_veyr.record"]
	check(probe.restore(in_prologue) and probe.current().id == "p_bay" and probe.data.done.is_empty() and probe.data.actor == "frank", "Old prologue saves begin at the bay")

func _initialize() -> void:
	var state := NightCampaign.new()
	check(state.content.scenes.size()==34,"Every authored location is present")
	check(state.content.lines["c2_ship.command.01"].audio=="recording.release"
		and state.content.lines["c2_ship.escape.01"].audio=="recording.release",
		"The captured release command and its replay share one exact recording")
	check(state.validate(state.data).is_empty(),"Fresh state validates")
	check(not state.mark_theory("greeting","stand_in","open"), "The notebook cannot enter a future theory")
	var forged: Dictionary = state.data.duplicate(true)
	forged.notebook.marks["stand_in"] = "open"
	check(not state.validate(forged).is_empty(), "Reject future notebook marks from a save")
	forged = state.data.duplicate(true)
	forged.notebook.notes["greeting"] = "Too early."
	check(not state.validate(forged).is_empty(), "Reject notes on an unreached case")
	var wake_index := int(state.task_scene["c9_wake.rook"])
	check("nora" in state.content.scenes[wake_index].actors and state.task_index["c9_wake.rook"].actor == "nora" and state.task_index["c9_wake.agnes"].actor == "nora", "Nora can direct the Chapter 9 sleeper rescues after Iris releases her")
	check(not state.advance(),"Cannot skip an unresolved opening")
	_check_story_shape(state)
	_check_migration()
	check(not state.switch_actor("saren"),"Cannot switch to an unavailable actor")
	var ids: Dictionary={}
	for scene: Dictionary in state.content.scenes:
		check(not ids.has(scene.id),"Unique scene "+scene.id)
		ids[scene.id]=true
		for task: Dictionary in scene.tasks:
			check(task.answer>=0 and task.answer<task.options.size(),"Valid answer "+task.id)
			for required: String in task.requires:
				check(state.task_index.has(required),"Known prerequisite "+required)
			for line: String in task.lines:
				check(state.content.lines.has(line),"Known spoken line "+line)
	# Exhaust every valid task order per scene, including wrong answers and actor changes.
	for scene_index: int in range(state.content.scenes.size()):
		var frontier: Array[Dictionary]=[state.data.duplicate(true)]
		var visited: Dictionary={}
		var terminal: Dictionary={}
		while not frontier.is_empty():
			var candidate: Dictionary=frontier.pop_back()
			var sorted_done: Array=candidate.done.duplicate()
			sorted_done.sort()
			var key:=JSON.stringify(sorted_done)
			if visited.has(key):
				continue
			visited[key]=true
			check(state.restore(candidate),"Reachable state restores")
			if state.can_leave():
				terminal=candidate
				continue
			var exits:=0
			for task: Dictionary in state.current().tasks:
				state.restore(candidate)
				if not state.available(task.id):
					continue
				exits+=1
				state.restore(candidate)
				if not task.actor.is_empty():
					state.switch_actor(task.actor)
				var before:=JSON.stringify(state.data)
				# Epilogue visits have one action and nothing to get wrong.
				if task.options.size() > 1:
					var bad: int=(int(task.answer)+1)%task.options.size()
					check(not state.choose(task.id,bad).ok,"Wrong answer rejected "+task.id)
					check(JSON.stringify(state.data)==before,"Wrong answer preserves recoverable state")
				else:
					check(task.id.begins_with("epilogue."),"Only epilogue visits have a single action "+task.id)
				var solution: Array=task.get("puzzle",{}).get("solution",[]).duplicate()
				if task.has("puzzle"):
					check(not state.choose(task.id,int(task.answer)).ok,"Puzzle cannot bypass settings "+task.id)
					var invalid: Array=solution.duplicate()
					invalid[0]=float(invalid[0])+0.5
					check(not state.choose(task.id,int(task.answer),invalid).ok,"Reject fractional settings "+task.id)
					for i: int in range(solution.size()):
						solution[i]=int(solution[i])
				check(state.choose(task.id,int(task.answer),solution).ok,"Correct approach succeeds "+task.id)
				check(not state.choose(task.id,int(task.answer)).ok,"Completed task is idempotent")
				frontier.append(state.data.duplicate(true))
			check(exits>0,"No reachable dead end in "+state.current().id)
		check(not terminal.is_empty(),"Scene has a complete solution")
		state.restore(terminal)
		check(state.advance(),"Advance completed scene")
		check(state.validate(state.data).is_empty(),"Progress remains valid")
	check(state.data.finished,"Full campaign reaches post-credits completion")
	check(state.mark_theory("greeting", "grief", "struck") and state.mark_theory("greeting", "grief", "open"), "Earlier case marks remain reversible through the ending")
	check(state.write_case_note("greeting", "Ask about the cough.") and state.validate(state.data).is_empty(), "Validate a personal notebook after credits")
	check(not state.write_case_note("greeting", "x".repeat(NightCampaign.NOTE_LIMIT + 1)), "Bound custom notes")
	forged = state.data.duplicate(true)
	forged.notebook.notes["greeting"] = {"bad":"entry"}
	check(not state.validate(forged).is_empty(), "Reject a malformed journal even when the case is unlocked")
	forged = state.data.duplicate(true)
	forged.erase("notebook")
	forged.erase("walk_positions")
	check(state.restore(forged) and state.data.notebook.marks.is_empty() and state.data.finished, "Read original schema-2 saves without losing progress")
	check(state.data.done.size()==state.task_index.size(),"Every puzzle solved")
	var bad_state: Dictionary=state.data.duplicate(true)
	bad_state.done.pop_front()
	check(not state.validate(bad_state).is_empty(),"Reject missing earlier puzzle")
	bad_state=state.data.duplicate(true)
	bad_state.done.append("invented")
	check(not state.validate(bad_state).is_empty(),"Reject unknown journal entry")
	bad_state=state.data.duplicate(true)
	bad_state.hints={"p_veyr.record":2.5}
	check(not state.validate(bad_state).is_empty(),"Reject fractional hint counter")
	var directory:=OS.get_environment("NIGHT_NINE_SAVE_DIR").path_join("campaign-test-"+str(OS.get_process_id()))
	var saves:=NightSaves.new(directory,state.validate)
	check(saves.write_slot("full",state.data),"Save complete campaign")
	check(saves.read_slot("full").get("ok",false),"Reload complete campaign")
	check(not saves.write_slot("../escape",state.data),"Reject save path traversal")
	check(saves.write_slot("full",state.data),"Preserve previous good backup")
	var file:=FileAccess.open(directory.path_join("full.json"),FileAccess.WRITE)
	file.store_string("broken")
	file.close()
	check(saves.read_slot("full").get("recovered",false),"Recover backup after interrupted/corrupt save")
	var exported: Dictionary = saves.export_slot("full")
	check(exported.get("ok", false) and exported.get("recovered", false), "Export the last valid save when the primary file is corrupt")
	check(saves.import_slot("imported", exported.text), "Import a portable backup into a separate slot")
	var imported: Dictionary = saves.read_slot("imported")
	check(imported.get("ok", false) and imported.state.finished and imported.state.done == state.data.done, "Portable backup retains completed campaign progress")
	var original_import: String = FileAccess.get_file_as_string(directory.path_join("imported.json"))
	var envelope: Dictionary = JSON.parse_string(exported.text)
	envelope.payload = "{}"
	check(not saves.import_slot("imported", JSON.stringify(envelope)), "Reject a backup with altered contents and an unchanged checksum")
	envelope.payload = JSON.stringify(bad_state)
	envelope.sha256 = str(envelope.payload).sha256_text()
	check(not saves.import_slot("imported", JSON.stringify(envelope)), "Reject invalid campaign state even with a valid backup checksum")
	envelope.payload = "null"
	envelope.sha256 = str(envelope.payload).sha256_text()
	check(not saves.import_slot("imported", JSON.stringify(envelope)), "Reject a backup whose valid JSON payload is not an object")
	check(not saves.import_slot("imported", "{broken"), "Reject malformed backup JSON")
	check(not saves.import_slot("imported", "x".repeat(NightSaves.MAX_BYTES + 1)), "Reject an oversized imported backup")
	check(FileAccess.get_file_as_string(directory.path_join("imported.json")) == original_import, "Rejected imports preserve the existing save")
	var result:={"checks":checks,"failures":failures,"scenes":state.content.scenes.size(),"puzzles":state.task_index.size(),"all_orders_explored":true}
	var output:=FileAccess.open("res://../tmp/qa/campaign-core-results.json",FileAccess.WRITE)
	output.store_string(JSON.stringify(result,"\t"))
	output.close()
	print(JSON.stringify(result))
	quit(0 if failures.is_empty() else 1)

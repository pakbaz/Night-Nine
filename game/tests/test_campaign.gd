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
	var narration: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/narration.json"))
	var voice: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/voice-manifest.json"))
	var music: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/music.json"))
	var narration_enabled: bool = bool(narration.get("enabled",true))
	check(narration_enabled == bool(voice.get("enabled",true)), "Storybook and dialogue voice activation match")
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
				check(str(line.get("narration","")).is_empty() != narration_enabled, "Narration follows the approved voice gate: " + str(line.text))
				check(not str(line.text).is_empty() and (str(line.get("narration","")).is_empty()
					or ResourceLoader.exists(str(line.narration))),"Caption does not depend on recorded narration: "+str(line.text))
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
	check(music.scene_music.c1_flat.file == music.chapters["Chapter 1"].theme.file and music.scene_music.c1_pier.file.ends_with("tape-anomaly.mp3") and music.scene_music.c10_live.file == music.title.file, "The Chapter 1 theme for the morning, Tape Anomaly on the pier; the main title for the finale")

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
	var v093: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/v0.9.3-save.json"))
	check(probe.restore(v093), "Load a v0.9.3 save fixture")
	check(probe.current().id == "p_bay" and probe.data.done.is_empty() and probe.data.seen.is_empty(), "Drop removed ids and fall back to the chapter start")

func _check_script_v2_runtime() -> void:
	var state := NightCampaign.new()
	var flat_index := _scene_index(state, "c1_flat")
	state.data.scene = flat_index
	state.data.scene_id = "c1_flat"
	var gated: Dictionary
	for topic: Dictionary in state.current().get("talk", []):
		if not str(topic.get("after", "")).is_empty():
			gated = topic
			break
	check(not gated.is_empty(), "Chapter 1 includes task-gated small talk")
	check(gated not in state.available_talk("iris"), "Small talk waits for its scene task")
	state.data.done = [gated.after]
	var topics: Array = state.available_talk("iris")
	check(gated in topics, "Small talk unlocks after its scene task")
	check(not state.talk_heard(gated), "A topic is unheard before its lines play")
	state.mark_seen(gated.lines)
	check(state.talk_heard(gated), "A topic is heard after all its lines play")
	state.data.scene = 0
	state.data.scene_id = state.content.scenes[0].id
	state.data.done = []
	var lead_id := "c1_flat.control"
	var lead: Array = state.unseen_lead(lead_id)
	check(not lead.is_empty(), "A new lead exposes its lead-in lines")
	state.mark_seen(lead)
	check(state.unseen_lead(lead_id).is_empty(), "A lead-in plays only once per save")
	check(state.perspective_name("p_veyr.levels") == "The Archivist", "Background labels use the scene point of view")
	check(state.perspective_name("c9_gallery.antenna") == "Stephen", "Background labels use the task actor")
	check(state.lock_reason("p_bay.message") == "Solve “Frank’s radio” first", "Locked leads name the prerequisite")
	state.data.scene = _scene_index(state, "p_bay")
	state.data.actor = "frank"
	var task: Dictionary = state.task_index["p_bay.message"]
	state.data.done = ["p_bay.tune"]
	var miss: Dictionary = state.choose(task.id, 1)
	check(not miss.ok and miss.reason == task.wrong["1"], "Wrong choices use their authored reason")
	check(not miss.offer_hint and int(state.data.misses[task.id]) == 1, "The first miss records recoverable progress")
	miss = state.choose(task.id, 2)
	check(miss.offer_hint and int(state.data.misses[task.id]) == 2, "Two misses offer hint one without revealing it")
	for level: int in 3:
		state.hint(task.id)
	check(not state.answer_available(task.id), "Hint three alone does not reveal the answer")
	state.choose(task.id, 1)
	check(not state.answer_available(task.id), "One later miss keeps the answer hidden")
	state.choose(task.id, 2)
	check(state.answer_available(task.id), "Two misses after hint three offer the separate answer")
	check(state.reveal_answer(task.id) and state.answer_text(task.id).contains(task.options[int(task.answer)]), "Answer reveal is explicit and persistent")
	var solved: Dictionary = state.choose(task.id, int(task.answer))
	check(solved.ok and solved.finding == task.finding, "A solved task returns its finding line")

func _check_storybook_caption_cleanup() -> void:
	var STORYBOOK := load("res://ui/storybook.gd")
	var book = STORYBOOK.new()
	root.add_child(book)
	var old_label := Label.new()
	old_label.text = "Opening line"
	book.caption_box.add_child(old_label)
	book.captions.append(old_label)
	book.caption_times.append(0.0)
	book._clear_captions()
	check(book.captions.is_empty() and book.caption_box.get_child_count() == 0,
		"Story opening removes old caption nodes immediately")
	book.queue_free()

## A stalled frame can hide the music clock and then return it behind the free-running
## fallback. The book must not jump ahead, fall back, and narrate a caption a second time.
func _check_storybook_clock_hitch() -> void:
	var fake := GDScript.new()
	fake.source_code = "extends Node\nvar current_file := \"\"\nvar at := 0.0\n" \
		+ "func play_story(file: String, _bar: float, _keep: bool) -> bool:\n\tcurrent_file = file\n\treturn true\n" \
		+ "func track_for_file(file: String) -> Dictionary:\n\treturn {\"file\": file, \"bpm\": 75.0, \"beat\": 0.0}\n" \
		+ "func bar_length(_track: Dictionary) -> float:\n\treturn 3.2\n" \
		+ "func bar_time(_track: Dictionary, bar: float) -> float:\n\treturn bar * 3.2\n" \
		+ "func position() -> float:\n\treturn at\n" \
		+ "func seek(seconds: float) -> void:\n\tat = seconds\n"
	fake.reload()
	var score: Node = fake.new()
	root.add_child(score)
	var STORYBOOK := load("res://ui/storybook.gd")
	var book = STORYBOOK.new()
	root.add_child(book)
	book.set_process(false)
	var narrated: Array[String] = []
	book.narrate.connect(func(line: Dictionary): narrated.append(str(line.text)))
	book.play({"title": "Opening", "music": {"file": "res://opening.mp3", "bar": 0}, "end_bar": 8,
		"panels": [
			{"bar": 0, "image": "res://icon.png", "lines": [
				{"bar": .25, "text": "Bellwether.", "seconds": 1.0},
				{"bar": 1.5, "text": "Six thousand people.", "seconds": 1.0}]},
			{"bar": 3.5, "image": "res://icon.png", "lines": [
				{"bar": 3.75, "text": "I'm Steve Mercer.", "seconds": 1.0}]}]}, score)
	while score.at < 5.5:
		score.at += .05
		book._process(.05)
	check(narrated == ["Bellwether.", "Six thousand people."], "The opening narrates its first page in order")
	# The music clock is unavailable for one long, stalled frame, then resumes where it was.
	score.at = -1.0
	book._process(6.0)
	score.at = 5.6
	for i: int in 20:
		score.at += .05
		book._process(.05)
	check(narrated.count("Six thousand people.") == 1, "A stalled frame never narrates an opening line twice")
	check(book.index == 0, "A stalled frame does not turn the page before the music reaches it")
	book.queue_free()
	score.queue_free()

## Two captions that appear while Steve is still speaking are both narrated, in order, and
## the last picture holds until his final line ends instead of cutting it with the music.
func _check_storybook_narrates_every_caption() -> void:
	var fake := GDScript.new()
	fake.source_code = "extends Node\nvar current_file := \"\"\nvar at := 0.0\nvar faded := false\n" \
		+ "func play_story(file: String, _bar: float, _keep: bool) -> bool:\n\tcurrent_file = file\n\treturn true\n" \
		+ "func track_for_file(file: String) -> Dictionary:\n\treturn {\"file\": file, \"bpm\": 75.0, \"beat\": 0.0}\n" \
		+ "func bar_length(_track: Dictionary) -> float:\n\treturn 3.2\n" \
		+ "func bar_time(_track: Dictionary, bar: float) -> float:\n\treturn bar * 3.2\n" \
		+ "func position() -> float:\n\treturn at\n" \
		+ "func seek(seconds: float) -> void:\n\tat = seconds\n" \
		+ "func fade_out(_seconds: float) -> void:\n\tfaded = true\n\tcurrent_file = \"\"\n"
	fake.reload()
	var score: Node = fake.new()
	root.add_child(score)
	var book = load("res://ui/storybook.gd").new()
	root.add_child(book)
	book.set_process(false)
	var narrated: Array[String] = []
	var closed := [false]
	book.narrate.connect(func(line: Dictionary): narrated.append(str(line.text)))
	book.finished.connect(func(): closed[0] = true)
	book.play({"title": "Aftermath", "music": {"file": "res://aftermath.mp3", "bar": 0}, "end_bar": 2,
		"panels": [{"bar": 0, "image": "res://icon.png", "lines": [
			{"bar": .1, "text": "A long first line.", "seconds": 4.0},
			{"bar": .5, "text": "So now I am home.", "seconds": 1.5},
			{"bar": .5, "text": "This is the story.", "seconds": 1.5}]}]}, score)
	var held_past_music := false
	var clock := 0.0
	while not closed[0] and clock < 20.0:
		clock += .05
		if not score.faded:
			score.at += .05
		book._process(.05)
		held_past_music = held_past_music or (clock > 6.6 and book.visible and book.closing < 0.0)
	check(narrated == ["A long first line.", "So now I am home.", "This is the story."], "Narrate every caption on a page, in order")
	check(held_past_music and score.faded, "Hold the last picture until the final line ends, and fade the music")
	check(closed[0] and clock > 7.4, "Close the book after the final line")
	book.queue_free()
	score.queue_free()

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
	_check_script_v2_runtime()
	_check_storybook_caption_cleanup()
	_check_storybook_clock_hitch()
	_check_storybook_narrates_every_caption()
	check(not state.switch_actor("saren"),"Cannot switch to an unavailable actor")
	var ids: Dictionary={}
	for scene: Dictionary in state.content.scenes:
		check(not ids.has(scene.id),"Unique scene "+scene.id)
		ids[scene.id]=true
		for task: Dictionary in scene.tasks:
			if task.has("art"):
				check(ResourceLoader.exists(task.art), "Imported task art " + task.id)
			check(task.answer>=0 and task.answer<task.options.size(),"Valid answer "+task.id)
			for required: String in task.requires:
				check(state.task_index.has(required),"Known prerequisite "+required)
			for line: String in task.lines:
				check(state.content.lines.has(line),"Known spoken line "+line)
		if scene.has("departure_art"):
			check(ResourceLoader.exists(scene.departure_art), "Imported departure art " + scene.id)
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
				var before_done: Array=state.data.done.duplicate()
				# Script-v2 beats have one Continue action and nothing to get wrong.
				if task.options.size() > 1:
					var bad: int=(int(task.answer)+1)%task.options.size()
					check(not state.choose(task.id,bad).ok,"Wrong answer rejected "+task.id)
					check(state.data.done==before_done and int(state.data.misses.get(task.id,0))>=1,"Wrong answer preserves progress and records the miss")
				else:
					check(task.get("type","")=="beat","Only authored beats have a single action "+task.id)
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

extends SceneTree

var errors: Array[String] = []
var checks := 0
var visited: Array = []
var shown_lines := {}

func _initialize() -> void:
	call_deferred("verify")

func expect(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		errors.append(message)
		push_error(message)

func check_dialogue(game: Node, ids: Array) -> void:
	for id: String in ids:
		var line: Dictionary = game.campaign.content.lines[id]
		expect(game.dialogue_panel.visible and game.active_line == id, "Presented line " + id)
		expect(game.words.text == line.get("display_text", line.text), "Subtitle " + id)
		if line.get("delivery", "live") != "private_recording":
			var record: Dictionary = game._recording_for(line.audio)
			expect(game.voice.playing and game.voice.stream.resource_path == record.take.file, "Recording " + id)
		shown_lines[id] = true
		game._next_line()

func verify() -> void:
	if OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set NIGHT_NINE_SAVE_DIR to a new temporary directory before running this test.")
		quit(2)
		return
	var game: Node = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue=false
	game._new_game()
	var checkpoint: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/checkpoint.json"))
	var count: int = game.campaign.content.scenes.size()
	expect(count==int(checkpoint.scenes),"Manifest room count")
	var last_id: String = ""
	for index: int in count:
		var scene: Dictionary = game.campaign.current()
		last_id=scene.id
		expect(scene.id==game.campaign.content.scenes[index].id,"Room order "+scene.id)
		expect(game.stage.room_id==scene.id and game.stage.art_ready,"Loaded stage "+scene.id)
		expect(game.ambience.playing and game.ambience.stream.resource_path.ends_with("/"+scene.id+".ogg"),"Authored room ambience "+scene.id)
		if scene.chapter!="Prologue":
			expect(game.stage.background!=null and game.stage.background.texture!=null,"Painted background "+scene.id)
		expect(game.hotspots.size()==scene.tasks.size(),"Clickable evidence "+scene.id)
		expect(game.dialogue_panel.visible and game.active_line==scene.intro[0],"Playable arrival "+scene.id)
		expect(game.voice.playing,"Arrival audio "+scene.id)
		check_dialogue(game, scene.intro)
		for task: Dictionary in scene.tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
				game._refresh()
			var solution: Array=task.get("puzzle",{}).get("solution",[])
			game._inspect(task.id)
			for step: int in 400:
				if not game.stage.has_method("is_walking") or not game.stage.is_walking():
					break
				game._process(.05)
			expect(game.selected_task==task.id,"Inspect "+task.id)
			game._choose(task.id,int(task.answer),solution)
			expect(task.id in game.campaign.data.done,"Resolve "+task.id)
			check_dialogue(game, task.lines)
		expect(game.campaign.can_leave(),"Departure gate "+scene.id)
		game._depart()
		expect(game.transitioning and game.dialogue_panel.visible,"Departure performance "+scene.id)
		check_dialogue(game, scene.outro)
		expect(game.light_remaining > 0.0, "Departure cut started " + scene.id)
		game._process(game.cut_duration * 0.5)
		expect(is_equal_approx(game.stage.cut_progress, 0.5), "Departure midpoint " + scene.id)
		if scene.chapter != "Prologue" and game.stage.directions.get("chapter_insert", false):
			expect(game.stage.chapter_frames.size() == 2, "Chapter keyframes " + scene.id)
			expect(game.stage.motion_material != null, "Chapter motion field " + scene.id)
		game._process(game.cut_duration)
		if scene.id == "one_year":
			expect(game.credits_panel.visible and game.campaign.current().id == "one_year","Credits before the transmission")
			game._close_credits()
		visited.append(scene.id)
		await process_frame
	expect(game.campaign.data.finished and game.end_card.visible,"Terminal card after "+last_id)
	expect(last_id==checkpoint.ending,"Reached this checkpoint’s last room")
	var correct_card := false
	var message := "The End" if last_id=="postcredits" else ("Prologue checkpoint complete" if last_id=="p_bay" else "Chapter %d checkpoint complete" % str(checkpoint.tag).get_slice("-",1).to_int())
	for label: Node in game.end_card.find_children("*","Label",true,false):
		correct_card=correct_card or label.text==message
	expect(correct_card,"Displayed terminal title "+message)
	expect(game.campaign.validate(game.campaign.data).is_empty(),"Final save validity")
	expect(shown_lines.size() == int(checkpoint.lines), "Every dialogue line presented")
	game._save("manual")
	expect(game._load("manual") and game.campaign.data.finished and game.end_card.visible,"Reload terminal save")
	game._open_credits()
	expect(game.credits_panel.visible and "GPT Image" in game.credits_body.text,"View production credits")
	game._show_credits_page(true)
	expect("Godot Engine contributors" in game.credits_body.text,"View engine and dependency notices")
	game._close_credits()
	game._open_journal()
	game.casebook.tabs["Transcript"].pressed.emit()
	expect(game.journal.visible and game.casebook.archive.visible and game.casebook.archive.text.length()>100,
		"Read completed notebook and transcript")
	await game.drain_audio()
	var report={"checks":checks,"rooms":visited,"tasks":game.campaign.data.done.size(),"lines":shown_lines.size(),"ending":last_id,"errors":errors}
	print("NIGHT_NINE_CHECKPOINT_QA ",JSON.stringify(report))
	quit(0 if errors.is_empty() else 1)

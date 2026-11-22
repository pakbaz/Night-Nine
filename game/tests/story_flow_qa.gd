extends Node
## Play the opening and ending in the real renderer: storybooks, chapter cards,
## flashback pages and the music cues that time them. Saves screenshots.
var game: Node
var checks := 0
var failures: Array[String] = []
var report_root := ""
var shots: Array[String] = []
var timing := []
var narrated := 0
var opening_mix_checked := false
var silent_lines: Array = []
var fates: Array = []
## Frames longer than a quarter second, with where the music was. A throttled or
## background window shows up here, so a timing failure can be told apart from a bug.
var hitches: Array = []
var longest_frame := 0.0

func _ready() -> void:
	# Keep the test window out of the way so it is not closed by accident; the
	# screenshots force a render, so they work while minimized.
	if not OS.get_environment("NIGHT_NINE_QA_MINIMIZE").is_empty():
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	_run.call_deferred()

func _process(delta: float) -> void:
	longest_frame = maxf(longest_frame, delta)
	if delta > .25 and game != null:
		hitches.append({"seconds": snappedf(delta, .01), "music_seconds": snappedf(game.score.position(), .01), "storybook": game.storybook.visible, "book_index": game.storybook.index})

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func verify_opening_mix() -> void:
	opening_mix_checked = true
	check(game.storybook.visible and game.voice.playing, "Play the opening narration over the storybook")
	check(game.score.current_file.ends_with("prologue-theme.mp3"), "Keep opening music under the narration")
	check(game.score.duck_db <= -13.9, "Lower opening music under the voice")
	if game.score.active_index >= 0:
		var deck: AudioStreamPlayer = game.score.players[game.score.active_index]
		check(deck.playing and deck.volume_db > game.score.SILENT_DB, "Keep the opening music audible while ducked")
	else:
		check(false, "Keep the opening music deck active")
	check(game.voice.volume_linear > 0.0, "Keep the opening voice audible")

func capture(label: String) -> void:
	for frame: int in 3:
		await get_tree().process_frame
	RenderingServer.force_draw(false)
	var image := get_viewport().get_texture().get_image()
	check(image != null and not image.is_empty(), "Pixels for " + label)
	if image:
		image.save_png(report_root.path_join(label + ".png"))
		shots.append(label + ".png")

func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout

func until(condition: Callable, seconds: float) -> bool:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < deadline:
		if condition.call():
			return true
		await get_tree().process_frame
	return condition.call()

## Storybook pictures may change on a half bar; both are on the beat.
func on_bar(label: String, track: Dictionary, seconds: float, half: bool = false) -> void:
	var bar: float = game.score.bar_length(track) * (.5 if half else 1.0)
	var offset := fposmod(seconds - float(track.beat), bar)
	var error := minf(offset, bar - offset)
	timing.append({"event": label, "music_seconds": snappedf(seconds, .001), "off_bar_by": snappedf(error, .001)})
	check(error < .2, label + " lands on a bar line (" + str(snappedf(error, .01)) + " s away)")

func finish_dialogue() -> void:
	for i: int in 40:
		if not game.dialogue_panel.visible:
			return
		game._skip_dialogue()
		await get_tree().process_frame

## Let departure lines end normally, so the departure film and its music play.
func finish_departure() -> void:
	for i: int in 40:
		if not game.dialogue_panel.visible:
			return
		game._next_line()
		await get_tree().process_frame

func solve_scene() -> void:
	for task: Dictionary in game.campaign.current().tasks:
		if not task.actor.is_empty():
			game.campaign.switch_actor(task.actor)
		var result: Dictionary = game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		check(result.ok, "Solve " + str(task.id))
		game.campaign.mark_seen(task.lines)
	game._refresh()

func jump_to(scene_id: String) -> void:
	# Reach a later scene by solving everything before it, then arrive as a player would.
	game.campaign.reset()
	while game.campaign.current().id != scene_id:
		for task: Dictionary in game.campaign.current().tasks:
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			game.campaign.choose(task.id, int(task.answer), task.get("puzzle", {}).get("solution", []))
		game.campaign.mark_seen(game.campaign.current().get("context", []) + game.campaign.current().intro)
		game.campaign.advance()
	game._load_stage(true)

func watch_book(prefix: String, natural_panels: int) -> void:
	var book: Dictionary = game.storybook.book
	var track: Dictionary = game.storybook.track
	check(game.storybook.visible and game.storybook.music_driven, prefix + " storybook plays over its music")
	var panels: Array = book.panels
	for i: int in panels.size():
		if i < natural_panels:
			# Let the music turn the page, and measure where it does. A book that
			# was already showing its first picture is measured from its second.
			var already: bool = game.storybook.index == i
			var arrived: bool = await until(func(): return game.storybook.index == i, 40.0)
			check(arrived, prefix + " reaches panel " + str(i))
			if not already:
				on_bar(prefix + " panel " + str(i), track, game.score.position(), true)
				# Landing on a bar line is not enough: it has to be this panel's own bar.
				var own: float = game.storybook._time_of(float(panels[i].bar))
				check(absf(game.score.position() - own) < .25, prefix + " panel " + str(i) + " turns on its own bar (" + str(snappedf(game.score.position() - own, .01)) + " s off)")
		else:
			check(game.storybook.index == i - 1, prefix + " is on panel " + str(i - 1) + " when the QA turns the page")
			game.storybook.next()
			await until(func(): return game.storybook.index == i, 3.0)
		if i + 1 == panels.size():
			# Capture the last picture where it settles, just before the book closes.
			await until(func(): return game.score.position() >= game.storybook.end_time - .9 or not game.storybook.visible, 20.0)
			check(game.storybook.visible and game.storybook.closing < 0.0, prefix + " holds its last picture to the end")
		else:
			await wait(4.8)
		await capture("%s-%02d" % [prefix, i + 1])
	# The last picture holds until Steve's final line ends, which can outlast the music.
	await until(func(): return not game.storybook.visible, 14.0)
	for entry: Dictionary in game.storybook.narration_log:
		fates.append(entry.merged({"book": prefix}))

func _run() -> void:
	report_root = OS.get_environment("NIGHT_NINE_QA_DIR")
	if report_root.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set isolated QA and save directories.")
		get_tree().quit(2)
		return
	DirAccess.make_dir_recursive_absolute(report_root)
	# A wall-clock limit, not a frame count: a covered window can run thousands of
	# frames a second and would hit a frame cap long before the story ends.
	get_tree().create_timer(900.0, true, false, true).timeout.connect(func():
		failures.append("Story flow timed out after 15 minutes")
		var report := FileAccess.open(report_root.path_join("story-flow.json"), FileAccess.WRITE)
		report.store_string(JSON.stringify({"checks": checks, "failures": failures, "narration": fates, "hitches": hitches}, "  ") + "\n")
		report.close()
		get_tree().quit(3))
	game.auto_dialogue = false
	await wait(.5)
	await capture("00-title")
	# The QA drives the game by calls; real clicks and keys must not turn pages.
	get_viewport().gui_disable_input = true
	# Connected after the game's own handler, so the clip must already be playing.
	game.storybook.narrate.connect(func(line: Dictionary):
		if game.voice.playing and str(game.voice.stream.resource_path) == str(line.get("narration", "")):
			narrated += 1
		else:
			silent_lines.append({"text": line.text, "narration": line.get("narration", ""), "music_seconds": snappedf(game.score.position(), .01), "book_index": game.storybook.index})
		if str(line.get("narration", "")).ends_with("/book.opening.5.1.wav"):
			get_tree().create_timer(.2).timeout.connect(verify_opening_mix))
	game._new_game()
	await get_tree().process_frame
	check(game.storybook.visible and game.campaign.current().id == "p_bay", "New game opens with the backstory, before the bay")
	check(game.score.current_file.ends_with("prologue-theme.mp3"), "The backstory plays over the Three Nights theme")
	await watch_book("01-opening", 2)
	check(opening_mix_checked, "Check the opening narration and music mix")
	check(await until(func(): return game.title_card.visible, 3.0), "The prologue card follows the backstory")
	check(game.score.current_file.ends_with("prologue-bgm.mp3"), "The bay brings in its own music under the card")
	await wait(1.6)
	await capture("02-prologue-card")
	await until(func(): return not game.title_card.visible, 12.0)
	check(game.dialogue_panel.visible and game.active_line == "p_bay.in.01", "Frank speaks first after the card")
	await capture("03-bay-arrival")
	await finish_dialogue()
	check(game.status.text.contains("radio"), "The first scene explains where to click")
	await capture("04-bay-play")
	solve_scene()
	game._depart()
	await finish_departure()
	check(game.light_remaining > 0.0 and game.score.current_file.ends_with("prologue-theme.mp3"), "The light rises on the Three Nights theme")
	on_bar("Bay departure", game.score.current_track, game.score.position())
	check(absf(game.cut_duration - 3.0 * game.score.bar_length(game.score.current_track)) < .01, "The rising light lasts three bars")
	await wait(4.0)
	await capture("05-bay-departure")
	check(await until(func(): return game.storybook.visible, 9.0), "The aftermath follows the rising light")
	await watch_book("06-aftermath", 2)
	check(await until(func(): return game.title_card.visible, 3.0) and game.campaign.current().id == "c1_flat", "Chapter 1 opens with its card")
	check(game.title_card.goal.text.contains("mother") and game.title_card.goal.text.contains("voicemail"), "The Chapter 1 card states Steve's revised goal")
	await wait(1.6)
	await capture("07-chapter-1-card")
	var bar_start: float = game.score.position()
	await until(func(): return not game.title_card.visible or game.title_card.closing >= 0.0, 14.0)
	on_bar("Chapter 1 card ends", game.score.current_track, game.score.position())
	timing.append({"event": "Chapter 1 card length", "seconds": snappedf(game.score.position() - bar_start, .01)})
	await until(func(): return not game.title_card.visible, 3.0)
	await capture("08-chapter-1-arrival")
	await finish_dialogue()
	# Flashback pages.
	jump_to("p_veyr")
	check(game.title_card.visible and game.title_card.kicker.text.contains("Archivist"), "Veyr arrives as the Archivist's memory")
	check(game.score.current_file.ends_with("prologue-bgm.mp3"), "Veyr keeps the Three Nights music inside the interlude")
	await wait(1.6)
	await capture("09-veyr-card")
	game.title_card.finish_now()
	await finish_dialogue()
	await capture("10-veyr-play")
	jump_to("p_meeting")
	check(game.title_card.visible and game.title_card.kicker.text == "Chapter 8", "Chapter 8 opens with its card")
	await wait(1.6)
	await capture("11-chapter-8-card")
	check(await until(func(): return game.title_card.page == 1, 12.0) and game.title_card.title.text.contains("Sentinel Point"), "Then the notebook page dates the flashback")
	await wait(1.6)
	await capture("12-sentinel-page")
	game.title_card.finish_now()
	await finish_dialogue()
	# Ending.
	jump_to("epilogue")
	check(game.title_card.visible and game.title_card.kicker.text == "Epilogue", "The epilogue opens with its card")
	check(game.score.current_file.ends_with("epilogue-bgm.mp3"), "The epilogue opens on its original Epilogue BGM")
	await wait(1.6)
	await capture("13-epilogue-card")
	game.title_card.finish_now()
	await finish_dialogue()
	for task: Dictionary in game.campaign.current().tasks:
		check(task.options.size() == 1, "Epilogue visit needs no puzzle: " + str(task.id))
	game._inspect_on_arrival(game.campaign.current().tasks[0].id)
	await wait(.4)
	await capture("14-epilogue-visit")
	game.root.get_node("InteractionPanel").hide()
	solve_scene()
	game._depart()
	await finish_departure()
	check(game.score.current_file.ends_with("prologue-theme.mp3"), "Lanterns on the water bring back the Three Nights theme")
	on_bar("Epilogue departure", game.score.current_track, game.score.position())
	await wait(7.0)
	await capture("15-lanterns")
	check(await until(func(): return game.storybook.visible, 9.0), "The closing storybook follows the lanterns")
	await watch_book("16-after", 2)
	check(await until(func(): return game.title_card.visible, 10.0) and game.campaign.current().id == "one_year", "One year later arrives with its page")
	await wait(1.6)
	check(game.score.current_file.ends_with("chapter-01-bgm.mp3"), "One year later returns to the warm Chapter 1 morning theme")
	await capture("17-one-year-card")
	game.title_card.finish_now()
	await finish_dialogue()
	await capture("18-one-year")
	check(narrated > 0 and silent_lines.is_empty(), "Reached storybook captions use their approved recordings")
	check(fates.all(func(f: Dictionary): return f.fate != "audio_error"), "Storybook narration reports no audio errors")
	var file := FileAccess.open(report_root.path_join("story-flow.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify({"checks": checks, "failures": failures, "timing": timing, "silent_lines": silent_lines, "narration": fates, "longest_frame": snappedf(longest_frame, .001), "hitches": hitches, "screenshots": shots}, "  ") + "\n")
	file.close()
	print("Story flow: ", checks, " checks, ", failures.size(), " failures")
	await game.drain_audio()
	get_tree().quit(0 if failures.is_empty() else 1)

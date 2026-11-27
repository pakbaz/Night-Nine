extends SceneTree

const STAGE := preload("res://render/illustrated/campaign_room.gd")
var checks := 0
var failures: Array[String] = []
var campaign := NightCampaign.new()

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		failures.append(message)
		push_error(message)

func scene(id: String) -> Dictionary:
	for entry: Dictionary in campaign.content.scenes:
		if entry.id == id:
			return entry
	assert(false, "Unknown test scene " + id)
	return {}

func run() -> void:
	for id: String in ["c7_swap", "epilogue", "c1_escape"]:
		var outgoing := STAGE.new()
		root.add_child(outgoing)
		outgoing.build(scene(id), "high")
		outgoing.begin_departure_cut()
		outgoing.set_departure_progress(.9)
		var film: Node = outgoing.chapter_film
		check(is_instance_valid(film) and film.visible, "Play the departing film in " + id)
		var state := outgoing.outgoing_frame()
		check(state.get("film") == film, "Retain the final animated pose in " + id)
		var incoming: STAGE
		if id == "c1_escape":
			incoming = STAGE.new()
			root.add_child(incoming)
			incoming.build(scene("c2_aquarium"), "high")
			incoming.receive_frame(state)
		outgoing.queue_free()
		await process_frame
		await process_frame
		if is_instance_valid(incoming):
			check(is_instance_valid(film) and film.get_parent() == incoming.incoming_frame,
				"Transfer the film to the next room's dissolve")
			incoming._process(1.0)
			await process_frame
			await process_frame
			check(not is_instance_valid(film), "Release the film after its dissolve")
			incoming.queue_free()
		else:
			check(not is_instance_valid(film), "Release the film when no room consumes it: " + id)
		if is_instance_valid(film):
			film.free()
		await process_frame
	# A film that leads into a storybook or a title card ends on black, as those open on black;
	# a bridge inside a chapter stays bright so the next room dissolves out of it.
	for leaving_case: Array in [["c1_escape", true], ["c1_flat", false]]:
		var leaving := STAGE.new()
		root.add_child(leaving)
		leaving.build(scene(leaving_case[0]), "high")
		leaving.opens_dark = leaving_case[1]
		leaving.begin_departure_cut()
		leaving.set_departure_progress(.5)
		var halfway: float = leaving.curtain.color.a if is_instance_valid(leaving.curtain) else 0.0
		leaving.set_departure_progress(1.0)
		var ending: float = leaving.curtain.color.a if is_instance_valid(leaving.curtain) else 0.0
		if leaving_case[1]:
			check(halfway < .05 and ending > .99 and leaving.curtain.get_index() == leaving.frame.get_child_count() - 1,
				"End the " + str(leaving_case[0]) + " film on black before the next chapter opens")
		else:
			check(ending < .01, "Keep the " + str(leaving_case[0]) + " bridge bright for the next room's dissolve")
		if is_instance_valid(leaving.chapter_film):
			leaving.chapter_film.free()
		leaving.queue_free()
		await process_frame
	var report := {"checks": checks, "failures": failures}
	var directory := OS.get_environment("NIGHT_NINE_QA_DIR")
	if not directory.is_empty():
		DirAccess.make_dir_recursive_absolute(directory)
		var file := FileAccess.open(directory.path_join("animation-handoff.json"), FileAccess.WRITE)
		file.store_string(JSON.stringify(report, "  ") + "\n")
	print(JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

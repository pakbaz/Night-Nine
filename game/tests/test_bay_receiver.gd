extends SceneTree
## Frank's radio: one needle that sweeps with the dial, and the choir's hum between the stations.
var failures: Array[String] = []
var checks := 0

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures.append(description)
		push_error(description)

func frames(count: int) -> void:
	for i: int in count:
		await process_frame

## Brightest orange pixel per row of the radio window, as the needle sits in the rendered frame.
func needle_tip(image: Image, window: Rect2i) -> Vector2:
	var best := Vector2(-1, -1)
	for y: int in range(window.position.y, window.end.y):
		for x: int in range(window.position.x, window.end.x):
			var c := image.get_pixel(x, y)
			if c.r > .72 and c.g > .3 and c.g < .7 and c.b < .35 and c.r > c.g * 1.35:
				return Vector2(x, y)
	return best

func run() -> void:
	var output := OS.get_environment("NIGHT_NINE_QA_DIR")
	if output.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Set isolated QA and save directories.")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output)
	var game: Node = load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue = false
	await frames(2)
	game.started = true
	game.menu.hide()
	var campaign = game.campaign
	campaign.reset()
	campaign.mark_seen(campaign.current().get("context", []) + campaign.current().intro)
	game._load_stage(false)
	await frames(6)
	while game.dialogue_panel.visible:
		game._next_line()
		await frames(1)
	var stage = game.stage
	# The receiver panel itself: one hum, the choir's loop, behind the stations.
	game._open_task("p_bay.tune")
	await frames(4)
	var receiver = game.receiver
	check(receiver != null, "Frank's radio opens")
	if receiver == null:
		quit(1)
		return
	check(receiver.players[2].stream.resource_path.ends_with("ninth_night_loop.wav"), "Between the stations the radio plays the choir's hum")
	# The chime station is struck bells (inharmonic partials), not a voice-like held tone.
	var chimes: AudioStreamWAV = receiver.station(true)
	var bell := 0.0
	var voice_like := 0.0
	var count := chimes.data.size() / 2
	for i: int in range(0, mini(count, 16000)):
		var t := float(i) / chimes.mix_rate
		var v := chimes.data.decode_s16(i * 2) / 32768.0
		bell += v * sin(TAU * 523.25 * 2.756 * t)
		voice_like += v * sin(TAU * 523.25 * 2.0 * t)
	check(absf(bell) > absf(voice_like) * 3.0, "The chime station rings like a bell, so the singing is only at 815 kHz")
	# What the panel says matches what plays: voices, not a tone.
	receiver.dial.value = 815
	receiver.narrow.button_pressed = true
	await frames(2)
	check(receiver.lock_ready and "voices" in receiver.description.text, "Locked on, the radio describes voices holding one note (%s)" % receiver.description.text)
	receiver.narrow.button_pressed = false
	receiver.dial.value = 813
	await frames(2)
	check("voices" in receiver.description.text or "sing" in receiver.description.text, "Near the hum, the radio hints at voices (%s)" % receiver.description.text)
	# One needle: the painted needle is gone and a drawn one moves with the dial.
	var tips: Array[float] = []
	for khz: int in [810, 815, 820]:
		receiver.dial.value = khz
		await frames(6)
		check(is_equal_approx(stage.needle_value, (khz - 810) / 10.0), "The needle follows the dial at %d kHz" % khz)
		tips.append(stage.needle_angle())
	check(tips[0] < tips[1] and tips[1] < tips[2], "The needle sweeps one way across the scale as the dial turns (%s)" % str(tips))
	check(absf(tips[2] - tips[0]) > deg_to_rad(40.0), "The needle crosses most of the scale, not a sliver of it")
	check(stage.painted_needle_hidden(), "The painting's own needle is painted out, so only one needle shows")
	var receipt := FileAccess.open(output.path_join("bay-receiver.json"), FileAccess.WRITE)
	receipt.store_string(JSON.stringify({"checks": checks, "failures": failures}, "\t") + "\n")
	receipt.close()
	print("Bay receiver checks: ", checks, " failures: ", failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

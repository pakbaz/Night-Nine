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
	var hum_stream: AudioStreamWAV = receiver.players[2].stream
	check(hum_stream.loop_mode == AudioStreamWAV.LOOP_FORWARD and hum_stream.loop_end > 0,
		"The choir hum loops continuously instead of ending after one pass")
	# Fast tuning back and forth past the 5.25s clip length must never silence the hum.
	for step: int in 36:
		receiver.dial.value = 810 + (step % 11)
		receiver.narrow.button_pressed = (step % 4) >= 2
		await frames(1)
	receiver.dial.value = 815
	receiver.narrow.button_pressed = true
	await create_timer(5.6).timeout
	check(receiver.players[0].playing and receiver.players[1].playing and receiver.players[2].playing,
		"All three receiver audio layers keep playing after rapid tuning past one loop cycle")
	check(receiver.players[2].volume_db > -25.0,
		"The choir hum stays audible at 815 kHz after rapid tuning")
	receiver.narrow.button_pressed = false
	receiver.dial.value = 810
	await frames(2)
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
	# The needle is the painting's own needle: its texture, its size, centred under the scale.
	check(stage.needle != null and stage.needle.texture.resource_path.ends_with("bay-needle.png"),
		"The swinging needle is cut from the painting's own needle")
	check(absf(stage.needle_pivot_plate().x - stage.SCALE_CENTRE_X) < 2.0, "The needle pivots dead-centre under the painted scale axis")
	check(stage.dial_aperture != null and stage.dial_aperture.clip_children == CanvasItem.CLIP_CHILDREN_ONLY
		and stage.dial_glass_overlay != null and stage.dial_glass_overlay.texture.resource_path.ends_with("bay-dial-glass.png"),
		"The needle sits recessed behind the dial bezel and glass overlay")
	for value: float in [0.0, 0.5, 1.0]:
		var tip: Vector2 = stage.needle_tip_plate(value)
		check(stage.DIAL_GLASS.has_point(tip), "At %.1f the needle's tip stays behind the dial glass (%s)" % [value, str(tip)])
	check(absf(rad_to_deg(stage.needle_angle_at(0.5)) - stage.SCALE_CENTRE_TILT_DEG) < 0.6,
		"At 815 kHz the needle lies cleanly along the painted centre tick")
	# The green light rides the scale with the needle.
	var lights: Array[Vector2] = []
	for value: float in [0.0, 0.5, 1.0]:
		lights.append(stage.dial_light_plate(value))
	check(lights[0].x < lights[1].x and lights[1].x < lights[2].x, "The green light moves along the scale with the dial")
	check(lights.all(func(point: Vector2): return absf(point.y - stage.scale_arc_y(point.x)) < 2.0), "The green light sits on the glowing scale line")
	receiver.dial.value = 815
	await frames(90)
	check(absf(stage.needle.rotation - stage.needle_angle()) < deg_to_rad(1.0), "The needle settles where the dial points")
	var submitted:={"values":[]}
	receiver.submitted.connect(func(values: Array): submitted.values=values)
	receiver.configure({
		"mode":"drift","min":3.51,"max":3.61,"step":.05,"target":3.61,
		"unit":"MHz","decimals":2,"require_narrow":true,
		"choices":[{"label":"Battery","options":["RED","GREY","BLUE"]}],
		"dial_options":[3.51,3.56,3.61],
		"descriptions":{"3.61":"Gull’s call sign resolves through the static."}
	})
	receiver.choices[0].select(3)
	receiver.dial.value=3.61
	receiver.narrow.button_pressed=true
	await frames(2)
	check(not receiver.record.disabled and receiver.frequency.text=="3.61 MHz","Reuse the receiver for Frank’s slipped dial")
	receiver.record.pressed.emit()
	check(submitted.values==[2,2],"Submit the battery and corrected club frequency")
	receiver.configure({
		"mode":"relay","min":0,"max":2,"step":1,"target":2,"require_narrow":true,
		"dial_options":[0,1,2],
		"descriptions":{"0":"OFFICIAL · heavy jamming.","2":"MARSH · west wind, then dropping."}
	})
	check(receiver.description.text.contains("jamming"),"Hear the official channel’s jammer")
	receiver.dial.value=2
	receiver.narrow.button_pressed=true
	await frames(2)
	check(receiver.description.text.contains("MARSH") and not receiver.record.disabled,"Isolate Marsh’s changing field report")
	var receipt := FileAccess.open(output.path_join("bay-receiver.json"), FileAccess.WRITE)
	receipt.store_string(JSON.stringify({"checks": checks, "failures": failures}, "\t") + "\n")
	receipt.close()
	print("Bay receiver checks: ", checks, " failures: ", failures)
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

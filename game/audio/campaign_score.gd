extends Node
## Play the original MP3s on two streaming decks. Only the current and outgoing
## recordings stay in memory. A chapter keeps its transport between locations.
const BOOK := "res://content/music.json"
const TARGET_LUFS := {"title":-17.0, "theme":-18.0, "bgm":-24.0}
const SILENT_DB := -80.0
const CLUE_DB := -64.0

var manifest := {}
var players: Array[AudioStreamPlayer] = []
var active_index := -1
var current_file := ""
var cue := "silence"
var chapter := ""
var volume := .85:
	set(value):
		volume = clampf(value,0.0,1.0)
		apply_levels()
var duck_db := 0.0
var duck_target_db := 0.0
var powers := PackedFloat32Array([0.0,0.0])
var starting_power := PackedFloat32Array([0.0,0.0])
var trim := PackedFloat32Array([0.0,0.0])
var elapsed := 0.0
var duration := 0.0
var film_paused := false

func _ready() -> void:
	if FileAccess.file_exists(BOOK):
		manifest = JSON.parse_string(FileAccess.get_file_as_string(BOOK))
	for i: int in 2:
		var player := AudioStreamPlayer.new()
		player.name = "MusicDeck%d" % (i+1)
		# Avoid decoding two entire long recordings as PCM samples in the browser.
		player.playback_type = AudioServer.PLAYBACK_TYPE_STREAM
		player.volume_db = SILENT_DB
		add_child(player)
		players.append(player)

func play_title() -> bool:
	return select_track(manifest.get("title",{}),"title","")

func play_chapter(chapter_id: String) -> bool:
	return select_track(manifest.get("chapters",{}).get(chapter_id,{}).get("bgm",{}),"bgm",chapter_id)

func play_theme(chapter_id: String) -> bool:
	return select_track(manifest.get("chapters",{}).get(chapter_id,{}).get("theme",{}),"theme",chapter_id)

func select_track(track: Dictionary, kind: String, chapter_id: String) -> bool:
	var path: String = track.get("file","")
	if path.is_empty() or players.is_empty():
		silence()
		return false
	if current_file == path and active_index >= 0:
		return true
	# If the player reverses a transition, bring the still-playing deck back
	# without restarting it. Otherwise replace the quieter deck.
	var next := -1
	for i: int in players.size():
		if players[i].stream and players[i].stream.resource_path == path:
			next = i
			break
	if next < 0:
		if not ResourceLoader.exists(path):
			silence()
			return false
		var stream := load(path) as AudioStreamMP3
		if not stream:
			silence()
			return false
		next = 0 if powers[0] <= powers[1] else 1
		var player := players[next]
		player.stop()
		player.stream = stream
		stream.loop = true
		player.volume_db = SILENT_DB
		powers[next] = 0.0
		player.play(clampf(float(track.get("entry_seconds",0.0)),0.0,maxf(0.0,stream.get_length()-.1)))
	current_file = path
	chapter = chapter_id
	cue = kind
	active_index = next
	trim[next] = clampf(float(TARGET_LUFS[kind]) - float(track.get("lufs",-16.0)),-24.0,6.0)
	begin_fade(.52 if kind == "theme" else .93)
	return true

func silence() -> void:
	if active_index < 0:
		return
	current_file = ""
	chapter = ""
	cue = "silence"
	active_index = -1
	begin_fade(.10)

func begin_fade(seconds: float) -> void:
	starting_power = powers.duplicate()
	elapsed = 0.0
	duration = seconds

func set_mix(speech: bool, evidence: bool, menu_open: bool) -> void:
	var target := CLUE_DB if evidence else (-10.0 if speech else (-4.0 if menu_open else 0.0))
	if target == duck_target_db:
		return
	duck_target_db = target
	# Some evidence starts with a tiny click. Clear the score before that
	# first sample, then ease it back after the listener closes the evidence.
	if evidence:
		duck_db = target
		apply_levels()

func pause_film(on: bool) -> void:
	if on == film_paused:
		return
	film_paused = on
	for player: AudioStreamPlayer in players:
		player.stream_paused = on

func _process(delta: float) -> void:
	if film_paused:
		return
	var changed := false
	if elapsed < duration:
		elapsed = minf(elapsed+delta,duration)
		var t := smoothstep(0.0,duration,elapsed)
		for i: int in players.size():
			powers[i] = lerpf(starting_power[i],1.0 if i == active_index else 0.0,t)
			if elapsed >= duration and i != active_index:
				players[i].stop()
				players[i].stream = null
		changed = true
	if not is_equal_approx(duck_db,duck_target_db):
		var rate := 120.0 if duck_target_db < duck_db else 52.0
		duck_db = move_toward(duck_db,duck_target_db,rate*delta)
		changed = true
	if changed:
		apply_levels()

func apply_levels() -> void:
	for i: int in players.size():
		var weight := volume * sqrt(maxf(0.0,powers[i]))
		if weight > 0.0:
			players[i].volume_db = maxf(SILENT_DB,trim[i] + duck_db + linear_to_db(weight))
		else:
			players[i].volume_linear = 0.0

func stop_all() -> void:
	for i: int in players.size():
		players[i].stop()
		players[i].stream = null
		powers[i] = 0.0
	duration = 0.0
	current_file = ""
	cue = "silence"
	chapter = ""
	active_index = -1

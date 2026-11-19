extends Node
## Play the original MP3s on two streaming decks. Only the current and outgoing
## recordings stay in memory. A chapter keeps its transport between locations.
const BOOK := "res://content/music.json"
const TARGET_LUFS := {"title":-17.0, "theme":-18.0, "bgm":-24.0, "scene":-22.0, "story":-18.0, "credits":-17.0}
## Longer fades let one piece hand over to the next on a bar line.
const FADE_SECONDS := {"title":2.0, "theme":1.2, "bgm":2.4, "scene":2.4, "story":1.6, "credits":1.6}
const SILENT_DB := -80.0
const CLUE_DB := -64.0

var manifest := {}
var players: Array[AudioStreamPlayer] = []
var active_index := -1
var current_file := ""
var current_track := {}
var cue := "silence"
var chapter := ""
var volume := .85:
	set(value):
		volume = clampf(value,0.0,1.0)
		apply_levels()
var duck_db := 0.0
var duck_target_db := 0.0
## Chapter cards lift the music while they are up, then it settles under the scene.
var lift_db := 0.0
var lift_target_db := 0.0
## Location music rides up through its quietest passages, like a mixer on the fader.
const FLOOR_BELOW_TARGET := 7.0
const MAX_RIDE_DB := 9.0
var ride_db := 0.0
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

## Each location's music comes from the plan in music.json: a chapter's first
## location plays its theme, later ones its BGM, and flashbacks keep Three Nights.
func play_scene(scene: Dictionary) -> bool:
	var planned: Dictionary = manifest.get("scene_music",{}).get(scene.get("id",""),{})
	if planned.is_empty():
		return select_track(manifest.get("chapters",{}).get(scene.get("chapter",""),{}).get("bgm",{}),"bgm",scene.get("chapter",""))
	var kind := "bgm" if planned.get("role","bgm") == "bgm" else "scene"
	return select_track(planned,kind,scene.get("chapter",""),float(planned.get("entry_seconds",0.0)))

## The main title carries on from the last film into the credits.
func play_credits() -> bool:
	var cue: Dictionary = manifest.get("credits",{})
	if cue.is_empty():
		return play_theme("Epilogue")
	return select_track(cue,"credits","")

## The short Epilogue theme plays once under the end card.
func play_finale() -> bool:
	var cue: Dictionary = manifest.get("finale",{})
	if cue.is_empty():
		silence()
		return false
	return select_track(cue,"theme","",0.0)

func play_theme(chapter_id: String) -> bool:
	return select_track(manifest.get("chapters",{}).get(chapter_id,{}).get("theme",{}),"theme",chapter_id)

## Start the music for a departure film and return its length in whole bars,
## or 0 when the departure keeps the current music.
func play_departure(scene_id: String, chapter_id: String, chapter_ending: bool, minimum: float) -> float:
	var cue: Dictionary = manifest.get("departures",{}).get(scene_id,{})
	if not cue.is_empty():
		# A departure can move within the music already playing; start it on a fresh deck and crossfade.
		if not select_track(cue,"theme",chapter_id,bar_time(cue,float(cue.bar)),true):
			return 0.0
		return float(cue.bars) * bar_length(cue)
	if not chapter_ending:
		return 0.0
	var theme: Dictionary = manifest.get("chapters",{}).get(chapter_id,{}).get("theme",{})
	if theme.is_empty():
		return 0.0
	var bar := bar_length(theme)
	var entry := float(theme.get("entry_seconds",0.0))
	var start := bar_time(theme, maxf(0.0,roundf((entry-float(theme.get("beat",0.0)))/bar))) if theme.has("bpm") else entry
	# Chapter films return to the theme at its loudest stretch.
	if theme.has("climax_bar"):
		start = bar_time(theme, float(theme.climax_bar))
	if not select_track(theme,"theme",chapter_id,start,true):
		return 0.0
	if not theme.has("bpm"):
		return maxf(minimum,8.0)
	# Round up to whole bars, trimming at most a few percent, so a film is never rushed.
	return maxf(2.0,ceilf(maxf(minimum,8.0)/bar - .12)) * bar

## Storybooks either start a recording on a bar, or continue it.
func play_story(file: String, bar: float, keep_playing: bool) -> bool:
	var track := track_for_file(file)
	if track.is_empty():
		return false
	var start := bar_time(track,bar)
	if keep_playing and current_file == file and active_index >= 0:
		if position() < start - .25:
			seek(start)
		return true
	return select_track(track,"story","",start)

func track_for_file(file: String) -> Dictionary:
	if manifest.get("title",{}).get("file","") == file:
		return manifest.title
	for track: Dictionary in manifest.get("extras",{}).values():
		if track.get("file","") == file:
			return track
	for group: Dictionary in manifest.get("chapters",{}).values():
		for track: Dictionary in group.values():
			if track.get("file","") == file:
				return track
	return {}

func bar_length(track: Dictionary) -> float:
	return 240.0 / maxf(1.0,float(track.get("bpm",74.0)))

func bar_time(track: Dictionary, bar: float) -> float:
	return float(track.get("beat",0.0)) + bar * bar_length(track)

## The current bar grid, for title cards that last whole bars.
func active_bar_length() -> float:
	return bar_length(current_track) if current_track.has("bpm") else 0.0

func position() -> float:
	if active_index < 0 or not players[active_index].playing:
		return -1.0
	# Correct for the time since the last mix, but never by more than one buffer:
	# a stalled mixer under heavy load must not make the clock jump ahead.
	return players[active_index].get_playback_position() + minf(AudioServer.get_time_since_last_mix(), .05)

func seek(seconds: float) -> void:
	if active_index >= 0 and players[active_index].stream:
		players[active_index].seek(clampf(seconds,0.0,maxf(0.0,players[active_index].stream.get_length()-.1)))

func select_track(track: Dictionary, kind: String, chapter_id: String, start: float = -1.0, fresh: bool = false) -> bool:
	var path: String = track.get("file","")
	if path.is_empty() or players.is_empty():
		silence()
		return false
	if current_file == path and active_index >= 0 and not fresh:
		return true
	# If the player reverses a transition, bring the still-playing deck back
	# without restarting it. Otherwise replace the quieter deck.
	var next := -1
	if not fresh:
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
		if fresh and next == active_index:
			next = 1 - active_index
		var player := players[next]
		player.stop()
		player.stream = stream
		stream.loop = bool(track.get("loop", true))
		player.volume_db = SILENT_DB
		powers[next] = 0.0
		var from := start if start >= 0.0 else float(track.get("entry_seconds",0.0))
		player.play(clampf(from,0.0,maxf(0.0,stream.get_length()-.1)))
	elif start >= 0.0 and kind != "bgm":
		players[next].seek(clampf(start,0.0,maxf(0.0,players[next].stream.get_length()-.1)))
	current_file = path
	current_track = track
	chapter = chapter_id
	cue = kind
	if next != active_index:
		ride_db = 0.0
	active_index = next
	trim[next] = clampf(float(TARGET_LUFS[kind]) - float(track.get("lufs",-16.0)),-24.0,6.0)
	begin_fade(float(FADE_SECONDS[kind]))
	return true

func silence() -> void:
	if active_index < 0:
		return
	current_file = ""
	current_track = {}
	chapter = ""
	cue = "silence"
	active_index = -1
	begin_fade(.10)

## Let a storybook's last bar ring out instead of cutting it.
func fade_out(seconds: float) -> void:
	if active_index < 0:
		return
	current_file = ""
	current_track = {}
	chapter = ""
	cue = "silence"
	active_index = -1
	begin_fade(seconds)

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

func _ride_target() -> float:
	if cue not in ["bgm", "scene"] or not current_track.has("bar_loudness") or active_index < 0:
		return 0.0
	var at := position()
	var loud: Array = current_track.bar_loudness
	if at < 0.0 or loud.is_empty():
		return ride_db
	var bar := int(floor((at - float(current_track.get("beat", 0.0))) / bar_length(current_track)))
	var looping: bool = players[active_index].stream is AudioStreamMP3 and players[active_index].stream.loop
	var next := posmod(bar + 1, loud.size()) if looping else clampi(bar + 1, 0, loud.size() - 1)
	# Read the louder of this bar and the next, so the fader is already down when a loud passage arrives.
	var louder := maxf(float(loud[clampi(bar, 0, loud.size() - 1)]), float(loud[next]))
	var heard := louder + float(TARGET_LUFS[cue]) - float(current_track.get("lufs", -16.0))
	var floor_lufs := float(TARGET_LUFS[cue]) - FLOOR_BELOW_TARGET
	return clampf(floor_lufs - heard, 0.0, MAX_RIDE_DB)

func set_lift(db: float) -> void:
	lift_target_db = db

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
	var ride_target := _ride_target()
	if not is_equal_approx(ride_db,ride_target):
		# Rise slowly through a quiet passage, and come down fast before a loud one.
		ride_db = move_toward(ride_db,ride_target,(1.5 if ride_target > ride_db else 9.0)*delta)
		changed = true
	if not is_equal_approx(lift_db,lift_target_db):
		# Rise quickly with the card, settle gently as the scene begins.
		lift_db = move_toward(lift_db,lift_target_db,(8.0 if lift_target_db > lift_db else 2.5)*delta)
		changed = true
	if changed:
		apply_levels()

func apply_levels() -> void:
	for i: int in players.size():
		var weight := volume * sqrt(maxf(0.0,powers[i]))
		if weight > 0.0:
			var ride := ride_db if i == active_index else 0.0
			players[i].volume_db = maxf(SILENT_DB,trim[i] + duck_db + lift_db + ride + linear_to_db(weight))
		else:
			players[i].volume_linear = 0.0

func stop_all() -> void:
	for i: int in players.size():
		players[i].stop()
		players[i].stream = null
		powers[i] = 0.0
	duration = 0.0
	current_file = ""
	current_track = {}
	cue = "silence"
	chapter = ""
	active_index = -1

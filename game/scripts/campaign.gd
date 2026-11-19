extends Node
## Native point-and-click campaign. Dialogue and voices share immutable line IDs.
var campaign := NightCampaign.new()
var saves: NightSaves
const ILLUSTRATED_STAGE := preload("res://render/illustrated/room.gd")
const CHAPTER_STAGE := preload("res://render/illustrated/campaign_room.gd")
const BAY_RECEIVER := preload("res://render/illustrated/bay_receiver.gd")
var receiver: Control
const PROP_BUTTON := preload("res://render/illustrated/prop_button.gd")
var stage: Variant
var root: Control
var title: Label
var objective: Label
var status: Label
var speaker: Label
var words: RichTextLabel
var interaction: VBoxContainer
var dialogue_panel: PanelContainer
var menu: PanelContainer
var journal: PanelContainer
var journal_text: RichTextLabel
var actor: OptionButton
const LIGHT_BEAT := 2.15
var light_remaining := -1.0
var cut_duration := LIGHT_BEAT
var skipping_departure := false
var object_list: Button
var end_card: PanelContainer
var credits_panel: ColorRect
var credits_title: Label
var credits_body: RichTextLabel
var credits_toggle: Button
var credits_return: Button
var credits_prior_focus: Control
var showing_notices:=false
var cut_skip: Button
var next_button: Button
var hotspots: Array[Button] = []
var voice: AudioStreamPlayer
var ambience: AudioStreamPlayer
var effect: AudioStreamPlayer
var sound_manifest: Dictionary = {}
var new_game_confirmation: ConfirmationDialog
var queue: Array = []
var queue_done: Callable
var voice_manifest: Dictionary = {}
var lipsync_manifest: Dictionary = {}
var selected_task := ""
var settings := ConfigFile.new()
var profile := "high"
var started := false
var transitioning := false
var auto_dialogue := true
var line_remaining := 0.0
var active_line := ""
var save_root := ""
const SETTING_ROW := preload("res://ui/setting_row.gd")
var puzzle_controls: Array[SETTING_ROW] = []
var closing := false
var tape_playback := false
var tape_compare: NightTapeCompare

func _ready() -> void:
	save_root = NightDesktop.new().save_root().path_join("campaign")
	saves = NightSaves.new(save_root,campaign.validate)
	settings.load(save_root.path_join("settings.cfg"))
	profile = settings.get_value("graphics","profile","high")
	if profile not in ["high","performance"]:
		profile = "high"
	voice_manifest = JSON.parse_string(FileAccess.get_file_as_string("res://content/voice-manifest.json"))
	lipsync_manifest = JSON.parse_string(FileAccess.get_file_as_string("res://content/lipsync-manifest.json"))
	sound_manifest = JSON.parse_string(FileAccess.get_file_as_string("res://assets/audio/soundscape-manifest.json"))
	voice = AudioStreamPlayer.new()
	voice.finished.connect(_after_spoken_line)
	add_child(voice)
	ambience = AudioStreamPlayer.new()
	ambience.volume_db = -24
	add_child(ambience)
	effect = AudioStreamPlayer.new()
	effect.volume_db = -10
	add_child(effect)
	_build_ui()
	_load_stage(false)
	menu.show()
	var previous := saves.read_slot("autosave")
	_status("Continue your saved game, or begin with the three playable prologue scenes." if previous.get("ok",false) else "Begin a new game. Click objects to investigate; use the notebook for collected evidence.")
	get_tree().auto_accept_quit = false

func _theme() -> Theme:
	var theme := Theme.new()
	theme.default_font_size = 20
	for type: String in ["Label","Button","RichTextLabel","OptionButton","CheckButton"]:
		theme.set_color("font_color",type,Color("e9e5d7"))
	for state: String in ["normal","hover","pressed","focus"]:
		var box := StyleBoxFlat.new()
		box.bg_color = Color("16333d") if state == "normal" else Color("31545b")
		box.border_color = Color("59787c")
		box.set_border_width_all(1)
		box.set_corner_radius_all(5)
		box.content_margin_left = 16
		box.content_margin_right = 16
		box.content_margin_top = 10
		box.content_margin_bottom = 10
		theme.set_stylebox(state,"Button",box)
		theme.set_stylebox(state,"OptionButton",box)
	return theme

func _panel(parent: Node) -> PanelContainer:
	var p := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.025,0.065,0.078,0.97)
	style.border_color = Color("647b77")
	style.set_border_width_all(1)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(22)
	p.add_theme_stylebox_override("panel",style)
	parent.add_child(p)
	return p

func _label(parent: Node, text: String, size: int = 20) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size",size)
	parent.add_child(l)
	return l

func _button(parent: Node, text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(action)
	b.focus_mode = Control.FOCUS_ALL
	parent.add_child(b)
	return b

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = _theme()
	layer.add_child(root)
	var heading := VBoxContainer.new()
	heading.position = Vector2(42,32)
	heading.custom_minimum_size.x = 830
	root.add_child(heading)
	title = _label(heading,"NIGHT NINE",30)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.custom_minimum_size.x = 830
	objective = _label(heading,"",20)
	objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	objective.modulate = Color("c4cdc3")
	var toolbar := HBoxContainer.new()
	toolbar.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	toolbar.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	toolbar.offset_left = -552
	toolbar.offset_right = -42
	toolbar.offset_top = 32
	toolbar.alignment = BoxContainer.ALIGNMENT_END
	root.add_child(toolbar)
	actor = OptionButton.new()
	actor.custom_minimum_size.x = 210
	actor.tooltip_text = "Switch investigator [Q]"
	actor.item_selected.connect(func(i: int): campaign.switch_actor(campaign.current().actors[i]); _refresh())
	toolbar.add_child(actor)
	_button(toolbar,"Notebook",_open_journal)
	_button(toolbar,"Menu",func(): menu.show(); _pause_audio(true))
	status = _label(root,"",18)
	status.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	status.offset_left = 42
	status.offset_top = -42
	status.offset_right = -42
	status.offset_bottom = -10
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dialogue_panel = _panel(root)
	dialogue_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	dialogue_panel.offset_left = 180
	dialogue_panel.offset_right = -180
	dialogue_panel.offset_top = -315
	dialogue_panel.offset_bottom = -65
	var dialog := VBoxContainer.new()
	dialogue_panel.add_child(dialog)
	speaker = _label(dialog,"",20)
	speaker.modulate = Color("e7b781")
	words = RichTextLabel.new()
	words.custom_minimum_size.y = 115
	words.size_flags_vertical = Control.SIZE_EXPAND_FILL
	words.bbcode_enabled = false
	words.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	words.clip_contents = true
	words.add_theme_font_size_override("normal_font_size",25)
	dialog.add_child(words)
	var controls := HBoxContainer.new()
	dialog.add_child(controls)
	_button(controls,"Continue  [Space]",_next_line)
	_button(controls,"Skip scene",_skip_dialogue)
	var auto := CheckButton.new()
	auto.text = "Auto-advance"
	auto.button_pressed = true
	auto.toggled.connect(func(on: bool): auto_dialogue=on)
	controls.add_child(auto)
	dialogue_panel.hide()
	var interact_panel := _panel(root)
	interact_panel.name = "InteractionPanel"
	interact_panel.position = Vector2(42,150)
	interact_panel.size = Vector2(440,720)
	var scroll := ScrollContainer.new()
	scroll.follow_focus=true
	scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size=Vector2(390,650)
	interact_panel.add_child(scroll)
	interaction = VBoxContainer.new()
	interaction.custom_minimum_size.x = 360
	interaction.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	scroll.add_child(interaction)
	interact_panel.hide()
	tape_compare = NightTapeCompare.new()
	root.add_child(tape_compare)
	tape_compare.play_requested.connect(func(stream: AudioStreamWAV):
		effect.stop()
		voice.stop()
		voice.stream = stream
		voice.play()
		tape_playback = true)
	tape_compare.stop_requested.connect(func(): voice.stop(); tape_playback = false)
	tape_compare.finding_requested.connect(func(values: Array): _choose(tape_compare.task_id, int(campaign.task_index[tape_compare.task_id].answer), values))
	tape_compare.hint_requested.connect(func():
		tape_compare.feedback.text = campaign.hint(tape_compare.task_id)
		_save("autosave"))
	tape_compare.closed.connect(func():
		if is_instance_valid(stage):
			stage.set_focus(-1))
	object_list = _button(root,"Objects  [I]",_open_objects)
	object_list.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	object_list.offset_left=42
	object_list.offset_right=213
	object_list.offset_top=-110
	object_list.offset_bottom=-60
	object_list.hide()
	next_button = _button(root,"Leave this location",_depart)
	next_button.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	next_button.offset_left = -350
	next_button.offset_top = -110
	next_button.offset_right = -40
	next_button.offset_bottom = -60
	next_button.hide()
	cut_skip = _button(root,"Continue  [Space]",_advance_scene)
	cut_skip.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	cut_skip.offset_left = -250
	cut_skip.offset_right = -44
	cut_skip.offset_top = -91
	cut_skip.offset_bottom = -45
	cut_skip.hide()
	_build_menu()
	journal = _panel(root)
	journal.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	journal.offset_left=170
	journal.offset_top=110
	journal.offset_right=-170
	journal.offset_bottom=-90
	var jbox := VBoxContainer.new()
	journal.add_child(jbox)
	_label(jbox,"FRANK’S RECORDER / STEVE’S NOTEBOOK",26)
	journal_text = RichTextLabel.new()
	journal_text.size_flags_vertical=Control.SIZE_EXPAND_FILL
	journal_text.bbcode_enabled = false
	jbox.add_child(journal_text)
	_button(jbox,"Return to the scene",func(): journal.hide(); _pause_audio(false))
	journal.hide()
	end_card=_panel(root)
	end_card.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	end_card.offset_left=-295
	end_card.offset_right=295
	end_card.offset_top=-360
	end_card.offset_bottom=-90
	var credits:=VBoxContainer.new()
	credits.alignment=BoxContainer.ALIGNMENT_CENTER
	credits.add_theme_constant_override("separation",12)
	end_card.add_child(credits)
	_label(credits,"NIGHT NINE",44).horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
	_label(credits,"Chapter 2 checkpoint complete",23).horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
	_button(credits,"Read the notebook and transcript",_open_journal)
	_button(credits,"Credits",_open_credits)
	end_card.hide()
	root.move_child(end_card,0)
	_build_credits()

func _open_objects() -> void:
	if not started or campaign.data.finished or dialogue_panel.visible or transitioning or menu.visible or journal.visible or tape_compare.visible:
		return
	stage.set_focus(-1)
	(interaction.get_parent() as ScrollContainer).scroll_vertical=0
	for child: Node in interaction.get_children():
		interaction.remove_child(child)
		child.queue_free()
	_label(interaction,"Objects at this location",25)
	var first: Button
	for task: Dictionary in campaign.current().tasks:
		var lead:=_button(interaction,task.title,func(): _inspect(task.id))
		lead.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
		lead.disabled=not campaign.available(task.id) and task.id not in campaign.data.done
		if not lead.disabled and not first:
			first=lead
	_button(interaction,"Return to the scene",func(): root.get_node("InteractionPanel").hide(); object_list.grab_focus.call_deferred())
	root.get_node("InteractionPanel").show()
	if first:
		first.grab_focus()

func _build_menu() -> void:
	menu = _panel(root)
	menu.position = Vector2(62,126)
	menu.size = Vector2(470,720)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation",12)
	menu.add_child(box)
	_label(box,"NIGHT NINE",42)
	_label(box,"An original adventure in Bellwether",20)
	_button(box,"Continue",_continue)
	_button(box,"New game",_request_new_game)
	new_game_confirmation = ConfirmationDialog.new()
	new_game_confirmation.title = "Begin a new game?"
	new_game_confirmation.dialog_text = "Replace your autosave and begin again? Your manual save will remain available."
	new_game_confirmation.confirmed.connect(_new_game)
	root.add_child(new_game_confirmation)
	_button(box,"Save game",func(): _save("manual"); _status("Game saved." if saves.last_error.is_empty() else saves.last_error))
	_button(box,"Load saved game",func(): _load("manual"))
	var quality := OptionButton.new()
	quality.add_item("Graphics: High")
	quality.add_item("Graphics: Performance")
	quality.select(0 if profile=="high" else 1)
	quality.item_selected.connect(func(i: int):
		profile="high" if i==0 else "performance"
		if is_instance_valid(stage):
			stage.set_quality(profile)
		settings.set_value("graphics","profile",profile)
		_save_settings())
	box.add_child(quality)
	var fullscreen := CheckButton.new()
	fullscreen.text="Fullscreen"
	fullscreen.toggled.connect(func(on: bool): DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if on else DisplayServer.WINDOW_MODE_WINDOWED))
	box.add_child(fullscreen)
	_label(box,"Voice volume",18)
	var volume := HSlider.new()
	volume.min_value=0
	volume.max_value=1
	volume.step=0.01
	volume.value=float(settings.get_value("audio","voice",0.9))
	voice.volume_db=linear_to_db(volume.value)
	volume.value_changed.connect(func(value: float): voice.volume_db=linear_to_db(value); settings.set_value("audio","voice",value); _save_settings())
	box.add_child(volume)
	_label(box,"Click an object, or press I to choose from a list. Tab moves focus. Space advances dialogue.",16).autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	_button(box,"Credits",_open_credits)
	_button(box,"Quit",_quit)

func _build_credits() -> void:
	credits_panel=ColorRect.new()
	credits_panel.name="Credits"
	credits_panel.color=Color(.008,.017,.023,.83)
	credits_panel.mouse_filter=Control.MOUSE_FILTER_STOP
	root.add_child(credits_panel)
	credits_panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var card:=_panel(credits_panel)
	card.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	card.offset_left=155
	card.offset_right=-155
	card.offset_top=108
	card.offset_bottom=-100
	var box:=VBoxContainer.new()
	box.add_theme_constant_override("separation",22)
	card.add_child(box)
	credits_title=_label(box,"Credits",36)
	credits_body=RichTextLabel.new()
	credits_body.size_flags_vertical=Control.SIZE_EXPAND_FILL
	credits_body.focus_mode=Control.FOCUS_ALL
	credits_body.selection_enabled=true
	box.add_child(credits_body)
	var actions:=HBoxContainer.new()
	box.add_child(actions)
	credits_toggle=_button(actions,"Third-party notices",func(): _show_credits_page(not showing_notices))
	credits_return=_button(actions,"Return",_close_credits)
	credits_return.focus_next=credits_return.get_path_to(credits_body)
	credits_body.focus_previous=credits_body.get_path_to(credits_return)
	credits_panel.hide()

func _show_credits_page(notices: bool) -> void:
	showing_notices=notices
	credits_title.text="Third-party notices" if notices else "Night Nine / Credits"
	credits_body.bbcode_enabled=not notices
	if notices:
		credits_body.text=FileAccess.get_file_as_string("res://LICENSES.txt")
	else:
		credits_body.text="[font_size=29]Original story and characters[/font_size]\nPakbaz\n\n[font_size=29]Production tools[/font_size]\n\n[b]Paintings and chapter animation keyframes[/b]\nGPT Image\n\n[b]Character dialogue audio[/b]\nElevenLabs v4 through Higgsfield\n\n[b]Game engine[/b]\nGodot Engine"
	credits_toggle.text="Back to credits" if notices else "Third-party notices"
	credits_body.scroll_to_line(0)

func _open_credits() -> void:
	credits_prior_focus=get_viewport().gui_get_focus_owner()
	_show_credits_page(false)
	credits_panel.show()
	_pause_audio(true)
	credits_toggle.grab_focus()

func _close_credits() -> void:
	credits_panel.hide()
	_pause_audio(menu.visible or journal.visible)
	if is_instance_valid(credits_prior_focus) and credits_prior_focus.is_visible_in_tree():
		credits_prior_focus.grab_focus()

func _continue() -> void:
	if started:
		menu.hide()
		_pause_audio(false)
		return
	if not _load("autosave"):
		_new_game()

func _request_new_game() -> void:
	if started or saves.read_slot("autosave").get("ok",false):
		new_game_confirmation.popup_centered(Vector2i(560,180))
	else:
		_new_game()

func _new_game() -> void:
	# New Game deliberately preserves the manual slot.
	campaign.reset()
	started=true
	menu.hide()
	_load_stage(true)
	_save("autosave")

func _load(slot: String) -> bool:
	var result := saves.read_slot(slot)
	if not result.get("ok",false):
		_status(result.get("error","Save unavailable."))
		return false
	if not campaign.restore(result.state):
		_status("The save failed validation.")
		return false
	started=true
	menu.hide()
	_load_stage(false)
	_status("Recovered the previous valid save." if result.get("recovered",false) else "Game loaded.")
	return true

func _save(slot: String) -> void:
	if started and not saves.write_slot(slot,campaign.data):
		_status("Could not save: "+saves.last_error)

func _save_settings() -> void:
	DirAccess.make_dir_recursive_absolute(save_root)
	settings.save(save_root.path_join("settings.cfg"))

func _load_stage(play_intro: bool) -> void:
	light_remaining=-1.0
	skipping_departure=false
	cut_skip.hide()
	actor.get_parent().show()
	_pause_audio(false)
	tape_compare.reset_task()
	voice.stop()
	effect.stop()
	queue.clear()
	active_line=""
	queue_done=Callable()
	selected_task=""
	dialogue_panel.hide()
	_dialogue_layout(false)
	root.get_node("InteractionPanel").hide()
	transitioning=false
	for button: Button in hotspots:
		button.queue_free()
	hotspots.clear()
	if is_instance_valid(stage):
		remove_child(stage)
		stage.queue_free()
	var prologue: bool = campaign.current().chapter == "Prologue"
	stage = ILLUSTRATED_STAGE.new() if prologue else CHAPTER_STAGE.new()
	add_child(stage)
	stage.build(campaign.current(),profile)
	if started:
		_status("Click a marked object to investigate.")
	actor.clear()
	for id: String in campaign.current().actors:
		actor.add_item(campaign.content.cast[id])
	for i: int in range(campaign.current().tasks.size()):
		var task: Dictionary = campaign.current().tasks[i]
		var b := PROP_BUTTON.new()
		b.text = task.title
		b.pressed.connect(func(): _inspect(task.id))
		root.add_child(b)
		b.add_theme_font_size_override("font_size",17)
		hotspots.append(b)
		root.move_child(b,0)
	_refresh()
	var audio_path: String = "res://assets/audio/ambience/"+campaign.current().style+".wav"
	var atmosphere_folder := "ambience-prologue" if prologue else "ambience-campaign"
	var authored := "res://assets/audio/"+atmosphere_folder+"/"+str(campaign.current().id)+".ogg"
	if ResourceLoader.exists(authored):
		audio_path=authored
	ambience.volume_db = -12.0 if audio_path.ends_with(".ogg") else -24.0
	if started and ResourceLoader.exists(audio_path):
		if ambience.stream==null or ambience.stream.resource_path!=audio_path:
			ambience.stop()
			ambience.stream=load(audio_path)
			if ambience.stream is AudioStreamOggVorbis:
				ambience.stream.loop = true
			elif ambience.stream is AudioStreamWAV:
				ambience.stream.loop_mode=AudioStreamWAV.LOOP_FORWARD
				ambience.stream.loop_end=int(ambience.stream.get_length()*ambience.stream.mix_rate)
		if not ambience.playing:
			ambience.play()
	else:
		ambience.stop()
	if play_intro:
		_speak(campaign.current().intro,Callable())
	elif started and not campaign.data.finished:
		_resume_dialogue()
	end_card.visible=campaign.data.finished
	if campaign.data.finished:
		title.get_parent().hide()
		_status("Chapter 2 checkpoint complete. Your notebook and transcript are available.")

func _resume_dialogue() -> void:
	# Resume unheard dialogue after a save during an arrival or completed interaction.
	var pending: Array=[]
	for id: String in campaign.current().intro:
		if id not in campaign.data.seen:
			pending.append(id)
	for task_id: String in campaign.data.done:
		if campaign.task_scene[task_id]!=int(campaign.data.scene):
			continue
		for id: String in campaign.task_index[task_id].lines:
			if id not in campaign.data.seen:
				pending.append(id)
	var departing := false
	for id: String in campaign.current().outro:
		departing=departing or id in campaign.data.seen
	if departing and campaign.can_leave():
		transitioning=true
		for id: String in campaign.current().outro:
			if id not in campaign.data.seen:
				pending.append(id)
		_speak(pending,_end_departure_dialogue)
	elif not pending.is_empty():
		_speak(pending,Callable())

func _refresh() -> void:
	if is_instance_valid(stage):
		stage.sync_story(campaign.data.done)
	var s := campaign.current()
	title.text=s.chapter.to_upper()+"  /  "+s.title
	objective.text=s.objective
	actor.select(s.actors.find(campaign.data.actor))
	actor.disabled=s.actors.size()==1
	actor.visible=s.actors.size()>1
	for i: int in range(hotspots.size()):
		var task: Dictionary=s.tasks[i]
		var complete: bool=task.id in campaign.data.done
		hotspots[i].text=("✓ " if complete else "")+task.title
		hotspots[i].modulate=Color("8aa498") if complete else Color.WHITE
		hotspots[i].disabled=not complete and not campaign.available(task.id)
	next_button.visible=started and campaign.can_leave() and not campaign.data.finished and not dialogue_panel.visible and not transitioning
	next_button.text="Finish" if int(campaign.data.scene)==campaign.content.scenes.size()-1 else "Leave this location"

func _inspect(id: String) -> void:
	if not started or dialogue_panel.visible or menu.visible or journal.visible or transitioning:
		return
	selected_task=id
	(interaction.get_parent() as ScrollContainer).scroll_vertical=0
	puzzle_controls.clear()
	var task: Dictionary=campaign.task_index[id]
	stage.set_focus(campaign.current().tasks.find(task))
	if id in campaign.data.done:
		root.get_node("InteractionPanel").hide()
		_status(task.note)
		_speak(task.lines,Callable())
		return
	if task.get("puzzle", {}).get("presentation", "") == "tape_alignment":
		root.get_node("InteractionPanel").hide()
		var take: Dictionary = _recording_for(task.puzzle.recording).take
		var master := load(str(take.get("file", ""))) as AudioStreamWAV
		if not tape_compare.open_task(id, master, voice, task.puzzle):
			_status(tape_compare.recording.error)
		return
	for child: Node in interaction.get_children():
		interaction.remove_child(child)
		child.queue_free()
	_label(interaction,task.title,25)
	var prompt:=_label(interaction,task.prompt,19)
	prompt.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	prompt.custom_minimum_size.x=355
	if id == "p_bay.tune":
		receiver = BAY_RECEIVER.new()
		receiver.tuned.connect(func(): _choose(id,int(task.answer)))
		receiver.dial_moved.connect(stage.set_frequency)
		interaction.add_child(receiver)
	elif task.has("puzzle"):
		var instruction:=_label(interaction,task.puzzle.instruction,17)
		instruction.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
		instruction.custom_minimum_size.x=355
		if id == "p_veyr.levels":
			_recorder_gain(id, task)
		else:
			for row: Dictionary in task.puzzle.rows:
				_label(interaction,row.label,17)
				var selector:=SETTING_ROW.new()
				selector.configure(row.label,row.options)
				interaction.add_child(selector)
				puzzle_controls.append(selector)
			_button(interaction,"Apply settings",func():
				var values: Array=[]
				for selector: SETTING_ROW in puzzle_controls:
					values.append(selector.selected)
				_choose(id,int(task.answer),values))
	# Stable, nontrivial answer positions without changing saved IDs or authored solutions.
	var order: Array[int]=[]
	for i: int in range(task.options.size()):
		order.append(i)
	var rng:=RandomNumberGenerator.new()
	rng.seed=hash(id)
	for i: int in range(order.size()-1,0,-1):
		var j:=rng.randi_range(0,i)
		var old:=order[i]
		order[i]=order[j]
		order[j]=old
	for index: int in order:
		if task.has("puzzle") or id == "p_bay.tune":
			break
		var b:=_button(interaction,task.options[index],func(): _choose(id,index))
		b.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
		b.custom_minimum_size.x=355
	for audio_id: String in task.sounds:
		var caption: String = campaign.content.get("sound_labels",{}).get(audio_id,"Listen to recording")
		_button(interaction,caption,func():
			if _play_audio(audio_id)<=0.0:
				_status("Restore the missing recording from the game download, then reopen this location."))
	_button(interaction,"Hint",func(): _status(campaign.hint(id)); _save("autosave"))
	_button(interaction,"Back",func(): root.get_node("InteractionPanel").hide(); stage.set_focus(-1))
	root.get_node("InteractionPanel").show()
	if interaction.get_child_count()>2 and interaction.get_child(2) is Button:
		interaction.get_child(2).grab_focus()

func _recorder_gain(id: String, task: Dictionary) -> void:
	var row: Dictionary = task.puzzle.rows[0]
	_label(interaction, row.label, 17)
	var bank := GridContainer.new()
	bank.columns = 2
	interaction.add_child(bank)
	var gain := ButtonGroup.new()
	for option: String in row.options:
		var setting := Button.new()
		setting.text = option
		setting.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		setting.toggle_mode = true
		setting.button_group = gain
		bank.add_child(setting)
	var apply := _button(interaction, "Apply settings", func():
		var index := gain.get_buttons().find(gain.get_pressed_button())
		_choose(id, int(task.answer), [index]))
	apply.disabled = true
	gain.pressed.connect(func(_setting: BaseButton): apply.disabled = false)
	bank.get_child(0).grab_focus()

func _choose(id: String, answer: int, puzzle_input: Array = []) -> void:
	var result:=campaign.choose(id,answer,puzzle_input)
	if not result.ok:
		_status(result.reason)
		return
	root.get_node("InteractionPanel").hide()
	if tape_compare.visible:
		tape_compare.close()
	_status(campaign.task_index[id].note)
	_save("autosave")
	_refresh()
	_speak(result.lines,Callable())

func _speak(ids: Array, after: Callable) -> void:
	effect.stop()
	queue=ids.duplicate()
	queue_done=after
	stage.cinematic=true
	dialogue_panel.show()
	next_button.hide()
	_next_line()

func _after_spoken_line() -> void:
	if active_line.is_empty() or not dialogue_panel.visible:
		return
	var reaction: Dictionary = campaign.content.lines[active_line].get("reaction", {})
	if not reaction.is_empty() and _play_effect(str(reaction.sound)) > 0:
		stage.end_dialogue()
		speaker.text = ""
		words.text = reaction.caption

func _next_line() -> void:
	if not active_line.is_empty() and campaign.content.lines[active_line].has("reaction"):
		effect.stop()
	voice.stop()
	stage.end_dialogue()
	if not active_line.is_empty():
		campaign.mark_seen([active_line])
		active_line=""
	if queue.is_empty():
		dialogue_panel.hide()
		stage.cinematic=false
		stage.set_focus(-1)
		_dialogue_layout(false)
		var callback:=queue_done
		queue_done=Callable()
		_save("autosave")
		_refresh()
		if callback.is_valid():
			callback.call()
		return
	var id: String=queue.pop_front()
	var line: Dictionary=campaign.content.lines[id]
	active_line=id
	var delivery: String = line.get("delivery", "live")
	speaker.text=str(line.get("display_speaker", campaign.content.cast[line.speaker])).to_upper() + ("  /  INTERCOM RECORDING" if delivery == "recorded_playback" else "")
	words.text=line.get("display_text", line.text)
	var recording := _recording_for(line.audio)
	var duration:=0.0 if delivery == "private_recording" else _play_audio(line.audio, recording.take)
	stage.begin_dialogue(line, voice, recording.take, recording.timing)
	_dialogue_layout(not stage.dialogue_shot.is_empty())
	var cue: String = line.get("cue","")
	if not cue.is_empty():
		duration=maxf(duration,_play_effect(cue))
	line_remaining=maxf(duration+0.6,2.5+words.text.length()/20.0)

func _dialogue_layout(staged: bool) -> void:
	var scene := campaign.current()
	var show_dateline: bool = staged and active_line in scene.intro
	actor.visible=not staged and scene.actors.size()>1 and not campaign.data.finished
	title.get_parent().visible = not staged or show_dateline
	objective.visible = not staged
	if show_dateline:
		title.text = scene.place
	status.visible = not staged
	dialogue_panel.offset_left = 140 if staged else 180
	dialogue_panel.offset_right = -140 if staged else -180
	dialogue_panel.offset_top = -240 if staged else -315
	dialogue_panel.offset_bottom = -40 if staged else -65
	words.custom_minimum_size.y = 60 if staged else 115

func _recording_for(id: String) -> Dictionary:
	var take: Dictionary = voice_manifest.get("takes", {}).get(id, {})
	var timing: Dictionary = lipsync_manifest.get("takes", {}).get(id, {})
	if take.has("fallback") and not ResourceLoader.exists(take.file):
		take = take.fallback
		timing = take.timing
	return {"take": take, "timing": timing}

func _play_audio(id: String, take: Dictionary = {}) -> float:
	voice.stop()
	tape_playback = id.begins_with("recording.") or id.begins_with("effect.")
	if id.begins_with("effect."):
		take=sound_manifest.get(id.trim_prefix("effect."),{})
	elif take.is_empty():
		take = _recording_for(id).take
	var path: String=take.get("file","")
	if path.is_empty() or not ResourceLoader.exists(path):
		return 0.0
	var stream:=load(path) as AudioStream
	if not stream:
		return 0.0
	voice.stream=stream
	voice.play()
	return voice.stream.get_length()

func _play_effect(id: String) -> float:
	effect.stop()
	var path: String=sound_manifest.get(id,{}).get("file","")
	if path.is_empty() or not ResourceLoader.exists(path):
		return 0.0
	var stream:=load(path) as AudioStream
	if not stream:
		return 0.0
	effect.stream=stream
	effect.play()
	return effect.stream.get_length()

func _skip_dialogue() -> void:
	if transitioning:
		skipping_departure=true
	effect.stop()
	campaign.mark_seen(queue)
	queue.clear()
	_next_line()

func _depart() -> void:
	if campaign.data.finished or not campaign.can_leave() or transitioning or dialogue_panel.visible:
		return
	transitioning=true
	root.get_node("InteractionPanel").hide()
	_speak(campaign.current().outro,_end_departure_dialogue)

func _end_departure_dialogue() -> void:
	if skipping_departure:
		_advance_scene()
		return
	stage.begin_departure_cut()
	cut_duration=stage.departure_duration() if stage.has_method("departure_duration") else LIGHT_BEAT
	light_remaining=cut_duration
	title.get_parent().hide()
	actor.get_parent().hide()
	status.hide()
	cut_skip.show()

func _advance_scene(dissolve: bool=false) -> void:
	var last_frame: Dictionary={}
	if dissolve and stage.has_method("outgoing_frame"):
		last_frame=stage.outgoing_frame()
	if campaign.advance():
		_save("autosave")
		_load_stage(not campaign.data.finished)
		if not last_frame.is_empty() and stage.has_method("receive_frame"):
			stage.receive_frame(last_frame)

func _open_journal() -> void:
	var text := "COLLECTED EVIDENCE\n\n"
	for id: String in campaign.data.done:
		text += "• "+campaign.task_index[id].note+"\n\n"
	text += "\nCONVERSATION TRANSCRIPT\n\n"
	var transcript_ids: Array=campaign.data.seen.duplicate()
	if not active_line.is_empty() and active_line not in transcript_ids:
		transcript_ids.append(active_line)
	for id: String in transcript_ids:
		var line: Dictionary=campaign.content.lines[id]
		text += str(line.get("display_speaker", campaign.content.cast[line.speaker]))+": "+str(line.get("display_text", line.text))+"\n\n"
	journal_text.text=text
	journal.show()
	_pause_audio(true)

func _pause_audio(on: bool) -> void:
	if is_instance_valid(receiver):
		receiver.set_paused(on)
	voice.stream_paused=on
	ambience.stream_paused=on
	effect.stream_paused=on
	if is_instance_valid(tape_compare):
		tape_compare.set_paused(on)
	if is_instance_valid(stage):
		stage.set_performance_paused(on)

func _process(delta: float) -> void:
	if not is_instance_valid(stage):
		return
	if light_remaining>=0.0:
		cut_skip.visible=not menu.visible and not journal.visible
	if light_remaining>=0.0 and not menu.visible and not journal.visible:
		light_remaining=maxf(0.0,light_remaining-delta)
		stage.set_departure_progress(1.0-light_remaining/cut_duration)
		if light_remaining<=0.0:
			_advance_scene(true)
			return
	stage.set_recorder_running(tape_playback and voice.playing and not voice.stream_paused)
	for i: int in range(hotspots.size()):
		hotspots[i].size = stage.hotspot_size(i)
		hotspots[i].position = stage.project_target(i)-hotspots[i].size*.5
		hotspots[i].visible=started and not campaign.data.finished and not transitioning and not dialogue_panel.visible and not menu.visible and not journal.visible and not tape_compare.visible and not root.get_node("InteractionPanel").visible
	object_list.visible = started and not campaign.data.finished and not dialogue_panel.visible and not transitioning and not menu.visible and not journal.visible and not tape_compare.visible and not root.get_node("InteractionPanel").visible
	if dialogue_panel.visible and not menu.visible and not journal.visible and auto_dialogue:
		line_remaining-=delta
		if line_remaining<=0 and not voice.playing and not effect.playing:
			_next_line()

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if credits_panel.visible:
			if event.keycode==KEY_ESCAPE:
				if showing_notices:
					_show_credits_page(false)
				else:
					_close_credits()
			get_viewport().set_input_as_handled()
			return
		if event.keycode==KEY_ESCAPE:
			if journal.visible:
				journal.hide()
				_pause_audio(false)
			else:
				menu.visible=not menu.visible
				_pause_audio(menu.visible)
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_SPACE and light_remaining>=0.0 and not menu.visible and not journal.visible:
			_advance_scene()
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_SPACE and dialogue_panel.visible and not menu.visible and not journal.visible:
			_next_line()
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_Q and object_list.visible and campaign.current().actors.size()>1:
			var investigators: Array=campaign.current().actors
			var next: int=(investigators.find(campaign.data.actor)+1)%investigators.size()
			campaign.switch_actor(investigators[next])
			_refresh()
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_I and object_list.visible:
			_open_objects()
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_J and not menu.visible:
			_open_journal()

func _status(message: String) -> void:
	status.text=message

func _notification(what: int) -> void:
	if what==NOTIFICATION_WM_CLOSE_REQUEST:
		_quit()

func _exit_tree() -> void:
	shutdown_audio()

func shutdown_audio() -> void:
	for player: AudioStreamPlayer in [voice,ambience,effect]:
		if is_instance_valid(player):
			player.stream_paused=false
			player.stop()
			player.stream=null

func drain_audio() -> void:
	shutdown_audio()
	# The mixer releases stopped WAV playbacks on its own thread. Allow the
	# deferred release cycle to finish even during a heavily loaded render test.
	await get_tree().create_timer(0.5).timeout

func _quit() -> void:
	if closing:
		return
	closing=true
	_save("autosave")
	dialogue_panel.hide()
	await drain_audio()
	get_tree().quit()

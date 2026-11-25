extends VBoxContainer

signal edited
var campaign: NightCampaign
var pages := OptionButton.new()
var case_scroll := ScrollContainer.new()
var sheet := VBoxContainer.new()
var archive := RichTextLabel.new()
var tabs: Dictionary = {}
var case_ids: Array[String] = []
var selected_case := ""
var tab := "Hypotheses"
var evidence := ""
var transcript := ""
var note: LineEdit
var save_delay := Timer.new()
const CROSS_REACTIONS := {
	"grief": "Steve, in the margin: Missing them changes what I fear. It does not change what the recorder caught.",
	"just_agnes": "Steve, in the margin: I want this to be true. Wanting it is not evidence."
}
const AGNES_ACKNOWLEDGMENT := "Steve, in the margin: At the booth, Agnes caught me rereading this page. She only smiled. Took you long enough, Steven."

func _ready() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	var navigation := HBoxContainer.new()
	add_child(navigation)
	var group := ButtonGroup.new()
	for caption: String in ["Hypotheses", "Evidence", "Transcript"]:
		var button := Button.new()
		button.text = caption
		button.toggle_mode = true
		button.button_group = group
		button.pressed.connect(_show_tab.bind(caption))
		navigation.add_child(button)
		tabs[caption] = button
	add_child(pages)
	pages.item_selected.connect(_select_page)
	add_child(case_scroll)
	case_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	case_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	case_scroll.follow_focus = true
	sheet.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sheet.add_theme_constant_override("separation", 9)
	case_scroll.add_child(sheet)
	add_child(archive)
	archive.size_flags_vertical = Control.SIZE_EXPAND_FILL
	archive.selection_enabled = true
	archive.bbcode_enabled = false
	archive.add_theme_font_size_override("normal_font_size", 19)
	save_delay.one_shot = true
	save_delay.wait_time = 0.4
	save_delay.timeout.connect(func(): edited.emit())
	add_child(save_delay)
	visibility_changed.connect(func():
		if not is_visible_in_tree() and not save_delay.is_stopped():
			save_delay.stop()
			edited.emit())

func open_book(state: NightCampaign, evidence_text: String, transcript_text: String) -> void:
	campaign = state
	evidence = evidence_text
	transcript = transcript_text
	pages.clear()
	var latest := "" if case_ids.is_empty() else str(case_ids.back())
	case_ids.clear()
	for id: String in campaign.content.get("notebook_cases", {}):
		if not campaign.available_theories(id, campaign.data.done).is_empty():
			case_ids.append(id)
			pages.add_item(campaign.content.notebook_cases[id].title)
	if case_ids.is_empty():
		selected_case = ""
	else:
		if selected_case not in case_ids or latest != case_ids.back():
			selected_case = case_ids.back()
		pages.select(case_ids.find(selected_case))
	_show_tab(tab if not case_ids.is_empty() else "Evidence", false)
	if not case_ids.is_empty():
		_draw_page()

func _show_tab(next: String, remember: bool = true) -> void:
	if remember:
		tab = next
	tabs[next].set_pressed_no_signal(true)
	for key: String in tabs:
		if key != next:
			tabs[key].set_pressed_no_signal(false)
	var investigating := next == "Hypotheses"
	pages.visible = investigating and not case_ids.is_empty()
	case_scroll.visible = pages.visible
	archive.visible = not case_scroll.visible
	if next == "Evidence":
		archive.text = evidence
	elif next == "Transcript":
		archive.text = transcript
	else:
		archive.text = "No open investigation yet."

func _select_page(index: int) -> void:
	selected_case = case_ids[index]
	_draw_page()

func _line(parent: Control, caption: String) -> Label:
	var line := Label.new()
	line.text = caption
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(line)
	return line

func _draw_page() -> void:
	for child: Node in sheet.get_children():
		sheet.remove_child(child)
		child.queue_free()
	case_scroll.scroll_vertical = 0
	var page: Dictionary = campaign.content.notebook_cases[selected_case]
	if selected_case == "penhallow" and campaign.current().id == "c10_town" \
			and bool(campaign.data.notebook.get("flags", {}).get("just_agnes_early", false)):
		var acknowledgment := _line(sheet, AGNES_ACKNOWLEDGMENT)
		acknowledgment.name = "AgnesAcknowledgment"
		acknowledgment.modulate = Color("d9c69b")
	for theory: Dictionary in campaign.available_theories(selected_case, campaign.data.done):
		var entry := VBoxContainer.new()
		sheet.add_child(entry)
		var row := HBoxContainer.new()
		entry.add_child(row)
		var statement := RichTextLabel.new()
		statement.bbcode_enabled = true
		statement.fit_content = true
		statement.scroll_active = false
		statement.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		statement.add_theme_font_size_override("normal_font_size", 19)
		row.add_child(statement)
		var mark: String = campaign.data.notebook.marks.get(theory.id, "")
		_set_statement(statement, theory.text, mark)
		var buttons := ButtonGroup.new()
		buttons.allow_unpress = true
		for action: String in ["open", "struck"]:
			var button := Button.new()
			button.name = str(theory.id) + "_" + action
			button.text = "Keep open" if action == "open" else "Cross out"
			button.toggle_mode = true
			button.button_group = buttons
			button.set_pressed_no_signal(mark == action)
			button.pressed.connect(_mark.bind(theory, action, button, statement))
			row.add_child(button)
		if CROSS_REACTIONS.has(str(theory.id)):
			var reaction := _line(entry, str(CROSS_REACTIONS[theory.id]))
			reaction.name = "Reaction_" + str(theory.id)
			reaction.modulate = Color("aeb8ad")
			reaction.visible = mark == "struck"
	if not page.clues.is_empty():
		_line(sheet, "Evidence in hand").modulate = Color("e7b781")
		for id: String in page.clues:
			if id in campaign.data.done:
				_line(sheet, "• " + campaign.task_index[id].note)
	_line(sheet, "My note").modulate = Color("e7b781")
	note = LineEdit.new()
	note.name = "CaseNote"
	note.max_length = NightCampaign.NOTE_LIMIT
	note.placeholder_text = "Write a theory or a question to follow up."
	note.text = campaign.data.notebook.notes.get(selected_case, "")
	note.text_changed.connect(_edit_note.bind(selected_case))
	note.text_submitted.connect(func(_text: String): note.release_focus())
	sheet.add_child(note)

func _set_statement(label: RichTextLabel, statement: String, mark: String) -> void:
	label.clear()
	if mark == "struck":
		label.push_strikethrough()
	label.add_text(statement)
	if mark == "struck":
		label.pop()

func _mark(theory: Dictionary, action: String, button: Button, label: RichTextLabel) -> void:
	var value := action if button.button_pressed else ""
	if campaign.mark_theory(selected_case, theory.id, value):
		_set_statement(label, theory.text, value)
		var reaction := label.get_parent().get_parent().get_node_or_null("Reaction_" + str(theory.id)) as Label
		if reaction:
			reaction.visible = value == "struck"
		if theory.id == "just_agnes" and value == "struck" and _before_scene("c10_town"):
			campaign.data.notebook.flags["just_agnes_early"] = true
		edited.emit()

func _before_scene(id: String) -> bool:
	var target := -1
	for index: int in campaign.content.scenes.size():
		if campaign.content.scenes[index].id == id:
			target = index
			break
	return target >= 0 and int(campaign.data.scene) < target

func _edit_note(value: String, id: String) -> void:
	if campaign.write_case_note(id, value):
		save_delay.start()

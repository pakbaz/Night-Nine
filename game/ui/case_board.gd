extends VBoxContainer
## One case file, with a bank of movable evidence shared by mouse and keyboard.
signal draft_changed(draft: Dictionary)
signal submitted(values: Array)
signal hint_requested
signal closed

const INK := Color("f1ead8")
const MUTED := Color("b7c3b9")
const GOLD := Color("e9c276")
const TEAL := Color("72bdb4")
const MODE_LABEL := {"order":"Timeline","match":"Evidence match","route":"Route map"}
var task_id := ""
var stages: Array
var draft: Dictionary
var selected := -1
var stage_index := 0
var pieces: Array[Button] = []
var slots: Array[Button] = []
var lane: VBoxContainer
var bank: VBoxContainer
var step_label: Label
var prompt: Label
var response: Label
var confirm: Button
var lines: BoardLines

class EvidenceButton extends Button:
	var tile := -1
	var position_id := -1
	var board: VBoxContainer
	func _get_drag_data(_at: Vector2) -> Variant:
		var value: int = tile if position_id == -1 else int(board.draft.placements[board.stage_index][position_id])
		if value < 0:
			return null
		var preview := Label.new()
		preview.text = str(board.stages[board.stage_index].pieces[value])
		preview.modulate = Color("ffe1a4")
		set_drag_preview(preview)
		return {"case":board.get_instance_id(),"piece":value}
	func _can_drop_data(_at: Vector2, payload: Variant) -> bool:
		if position_id < 0 or not payload is Dictionary or payload.get("case") != board.get_instance_id():
			return false
		var value: Variant=payload.get("piece")
		return value is int and value>=0 and value<board.pieces.size()
	func _drop_data(_at: Vector2, payload: Variant) -> void:
		board.place(int(payload.piece),position_id)

class BoardLines extends Control:
	var mode := ""
	var slots: Array[Button] = []
	var pieces: Array[Button] = []
	var placements: Array = []
	const THREADS := [Color("72bdb4"),Color("e9c276"),Color("b4a4d1"),Color("d69474"),Color("92b9dc")]
	func _draw() -> void:
		var previous := Vector2.ZERO
		for i: int in slots.size():
			var b := slots[i]
			if not is_instance_valid(b) or b.size.y < 1:
				continue
			var point := Vector2(b.global_position.x-global_position.x-12.0,b.global_position.y-global_position.y+b.size.y*.5)
			var color := Color("e9c276") if int(placements[i]) >= 0 else Color("627774")
			if mode != "match" and i:
				draw_line(previous,Vector2(previous.x,point.y),color,2.0,true)
				draw_line(Vector2(previous.x,point.y),point,color,2.0,true)
			if mode == "match":
				var tile := int(placements[i])
				if tile >= 0:
					var origin := pieces[tile].get_global_rect()
					var start := Vector2(origin.end.x,origin.get_center().y)-global_position
					var bend := lerpf(start.x,point.x,.25+.1*tile)
					color=THREADS[tile]
					draw_polyline(PackedVector2Array([start,Vector2(bend,start.y),Vector2(bend,point.y),point]),color,2.0,true)
					draw_circle(point,3.0,color,true,-1,true)
				else:
					draw_line(point-Vector2(6,0),point+Vector2(4,0),color,2.0,true)
			else:
				draw_circle(point,4.0,color,true,-1,true)
			previous=point

func configure(id: String, title: String, puzzle: Dictionary, progress: Dictionary) -> void:
	task_id = id
	stages = puzzle.stages
	draft = progress.duplicate(true)
	stage_index = int(draft.stage)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation",12)
	var headline := HBoxContainer.new()
	add_child(headline)
	var heading := label_at(headline,title,30,INK)
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	step_label = label_at(headline,"",17,GOLD)
	step_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	step_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	label_at(self,puzzle.instruction,18,MUTED)
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation",24)
	add_child(body)
	var notes_panel := PanelContainer.new()
	var paper := StyleBoxFlat.new()
	paper.bg_color=Color("d9d2ba")
	paper.border_color=Color("9c926e")
	paper.set_border_width_all(1)
	paper.set_content_margin_all(14)
	notes_panel.add_theme_stylebox_override("panel",paper)
	notes_panel.custom_minimum_size.x=330
	body.add_child(notes_panel)
	var notes_column:=VBoxContainer.new()
	notes_panel.add_child(notes_column)
	label_at(notes_column,"Case notes",21,Color("403a2d"))
	var scroll:=ScrollContainer.new()
	scroll.custom_minimum_size.y=345
	scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	scroll.focus_mode=Control.FOCUS_ALL
	notes_column.add_child(scroll)
	var notes:=column(scroll,0)
	notes.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	for item: String in puzzle.evidence:
		var rule := HSeparator.new()
		rule.modulate=Color("655b42")
		notes.add_child(rule)
		label_at(notes,item,18,Color("242b28"))
	bank = column(body,285)
	var right := column(body,432)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	prompt = label_at(right,"",20,INK)
	var graph := PanelContainer.new()
	graph.add_theme_stylebox_override("panel",StyleBoxEmpty.new())
	right.add_child(graph)
	lines = BoardLines.new()
	lines.mouse_filter = Control.MOUSE_FILTER_IGNORE
	graph.add_child(lines)
	lane = VBoxContainer.new()
	lane.add_theme_constant_override("separation",7)
	graph.add_child(lane)
	lane.resized.connect(func(): lines.queue_redraw())
	response = label_at(self,"",17,GOLD)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation",10)
	add_child(actions)
	confirm = button_at(actions,"","CheckBoard",func(): check_step())
	button_at(actions,"Clear this step","ClearBoard",func(): clear_step())
	button_at(actions,"Hint","BoardHint",func(): hint_requested.emit())
	button_at(actions,"Back to scene","CloseBoard",func(): closed.emit())
	build_step()

func label_at(parent: Node,value: String,font_size: int,color: Color) -> Label:
	var item := Label.new()
	item.text = value
	item.add_theme_font_size_override("font_size",font_size)
	item.add_theme_color_override("font_color",color)
	item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(item)
	return item

func column(parent: Node,width: int) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.custom_minimum_size.x = width
	box.add_theme_constant_override("separation",8)
	parent.add_child(box)
	return box

func button_at(parent: Node,caption: String,id: String,action: Callable) -> Button:
	var button := Button.new()
	button.name = id
	button.text = caption
	button.add_theme_font_size_override("font_size",17)
	button.pressed.connect(action)
	parent.add_child(button)
	return button

func evidence_button(parent: Node,id: String) -> EvidenceButton:
	var b := EvidenceButton.new()
	b.name=id
	b.board=self
	b.alignment=HORIZONTAL_ALIGNMENT_LEFT
	b.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	b.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	b.custom_minimum_size.y=44
	b.add_theme_font_size_override("font_size",17)
	parent.add_child(b)
	return b

func empty(box: Node) -> void:
	for child: Node in box.get_children():
		box.remove_child(child)
		child.queue_free()

func build_step() -> void:
	empty(bank)
	empty(lane)
	pieces.clear()
	slots.clear()
	selected=-1
	var stage: Dictionary=stages[stage_index]
	step_label.text="%s   •   %d / %d" % [MODE_LABEL[stage.mode],stage_index+1,stages.size()]
	prompt.text=stage.prompt
	label_at(bank,"Evidence pieces",20,TEAL)
	var order: Array=range(stage.pieces.size())
	var rng := RandomNumberGenerator.new()
	rng.seed=hash(task_id + str(stage_index))
	for i: int in range(order.size()-1,0,-1):
		var other:=rng.randi_range(0,i)
		var temp: int=order[i]
		order[i]=order[other]
		order[other]=temp
	var same := true
	for i: int in order.size():
		same = same and int(order[i])==int(stage.answer[i])
	if same:
		order.append(order.pop_front())
	pieces.resize(order.size())
	for index: int in order:
		var tile:=evidence_button(bank,"Piece%d"%index)
		tile.tile=index
		tile.text=stage.pieces[index]
		tile.pressed.connect(pick.bind(index))
		pieces[index]=tile
	for i: int in stage.slots.size():
		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left",34+(i%2)*34 if stage.mode=="route" else 20)
		lane.add_child(margin)
		var node:=evidence_button(margin,"Slot%d"%i)
		node.position_id=i
		node.pressed.connect(press_slot.bind(i))
		node.item_rect_changed.connect(lines.queue_redraw)
		slots.append(node)
	lines.mode=stage.mode
	lines.slots=slots
	lines.pieces=pieces
	lines.placements=draft.placements[stage_index]
	lines.queue_redraw.call_deferred()
	confirm.text="Record finding" if stage_index==stages.size()-1 else "Check this step"
	response.text="Select a piece, then a destination. You can also drag pieces between positions."
	refresh_tiles()
	if not pieces.is_empty():
		pieces[order[0]].grab_focus.call_deferred()

func refresh_tiles() -> void:
	var stage: Dictionary=stages[stage_index]
	var row: Array=draft.placements[stage_index]
	for i: int in pieces.size():
		var used:=row.find(i)
		pieces[i].modulate=GOLD if selected==i else (MUTED if used>=0 else Color.WHITE)
		pieces[i].tooltip_text=stage.pieces[i] if used<0 else "Placed at "+str(stage.slots[used])
	for i: int in slots.size():
		var tile:=int(row[i])
		var prefix: String="%d. "%(i+1) if stage.mode=="order" else ""
		slots[i].text=prefix+str(stage.slots[i])+"\n"+(str(stage.pieces[tile]) if tile>=0 else "Choose evidence")
		slots[i].modulate=GOLD if tile>=0 and tile==selected else (TEAL if tile>=0 else Color.WHITE)
		slots[i].tooltip_text=slots[i].text
	lines.queue_redraw()

func pick(index: int) -> void:
	selected=index
	response.text="Place “%s” on the board." % stages[stage_index].pieces[index]
	refresh_tiles()

func press_slot(index: int) -> void:
	if selected>=0:
		place(selected,index)
	elif int(draft.placements[stage_index][index])>=0:
		pick(int(draft.placements[stage_index][index]))
	else:
		response.text="Choose an evidence piece first."

func place(tile: int, target: int) -> void:
	var row: Array=draft.placements[stage_index]
	var previous:= -1
	for i: int in row.size():
		if int(row[i])==tile:
			previous=i
	if previous>=0:
		row[previous]=row[target]
	row[target]=tile
	selected=-1
	response.text="Placed at "+str(stages[stage_index].slots[target])+"."
	draft_changed.emit(draft)
	refresh_tiles()

func clear_step() -> void:
	draft.placements[stage_index].fill(-1)
	selected=-1
	response.text="This step is clear."
	draft_changed.emit(draft)
	refresh_tiles()

func check_step() -> void:
	var stage: Dictionary=stages[stage_index]
	var row: Array=draft.placements[stage_index]
	var matches:=0
	for i: int in row.size():
		if int(row[i])<0:
			response.text="Place a piece at “%s” before checking." % stage.slots[i]
			return
		if int(row[i])==int(stage.answer[i]):
			matches+=1
	if matches!=row.size():
		response.text="%d of %d placements fit the evidence. Recheck the case notes or ask for a hint." % [matches,row.size()]
		return
	if stage_index+1 < stages.size():
		stage_index+=1
		draft.stage=stage_index
		draft_changed.emit(draft)
		build_step()
	else:
		var values: Array=[]
		for entries: Array in draft.placements:
			values.append_array(entries)
		submitted.emit(values)

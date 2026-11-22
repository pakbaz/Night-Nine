extends SceneTree
## Exercise the authored board, a saved in-progress deduction, and the previous save format.
var game: Node
var failures: Array[String]=[]
var checks:=0
var destination: String
var examples:= {}
var case_count:=0
var stage_count:=0
var placement_count:=0
var decoy_count:=0
var layouts := []

func _initialize() -> void:
	run.call_deferred()

func check(ok: bool,text: String) -> void:
	checks+=1
	if not ok:
		failures.append(text)
		push_error(text)

func frames(n: int=2) -> void:
	for i: int in n:
		await process_frame

func mouse(control: Control) -> void:
	var scroll:=game.interaction.get_parent() as ScrollContainer
	scroll.ensure_control_visible(control)
	await frames()
	var at: Vector2=control.get_global_transform_with_canvas()*(control.size*.5)
	var motion:=InputEventMouseMotion.new()
	motion.position=at
	root.push_input(motion,true)
	for down: bool in [true,false]:
		var click:=InputEventMouseButton.new()
		click.position=at
		click.button_index=MOUSE_BUTTON_LEFT
		click.button_mask=MOUSE_BUTTON_MASK_LEFT if down else 0
		click.pressed=down
		root.push_input(click,true)
	await frames()

func enter(control: Control) -> void:
	control.grab_focus()
	for down: bool in [true,false]:
		var k:=InputEventKey.new()
		k.keycode=KEY_ENTER
		k.physical_keycode=KEY_ENTER
		k.pressed=down
		root.push_input(k,true)
	await frames()

func drag(source: Control, target: Control) -> void:
	var start: Vector2=source.get_global_transform_with_canvas()*(source.size*.5)
	var end: Vector2=target.get_global_transform_with_canvas()*(target.size*.5)
	var ev:=InputEventMouseMotion.new()
	ev.position=start
	root.push_input(ev,true)
	var down:=InputEventMouseButton.new()
	down.position=start
	down.button_index=MOUSE_BUTTON_LEFT
	down.button_mask=MOUSE_BUTTON_MASK_LEFT
	down.pressed=true
	root.push_input(down,true)
	var previous:=start
	for index: int in range(1,6):
		var move:=InputEventMouseMotion.new()
		move.position=start.lerp(end,index/5.0)
		move.relative=move.position-previous
		previous=move.position
		move.button_mask=MOUSE_BUTTON_MASK_LEFT
		root.push_input(move,true)
		await frames()
	var up:=InputEventMouseButton.new()
	up.position=end
	up.button_index=MOUSE_BUTTON_LEFT
	up.pressed=false
	root.push_input(up,true)
	await frames()

func fresh_room(id: String, board: bool = true) -> void:
	game.campaign.reset()
	var task_scene: int=game.campaign.task_scene[id]
	for i: int in range(task_scene+1):
		var scene: Dictionary=game.campaign.current()
		game.campaign.mark_seen(scene.intro)
		for task: Dictionary in scene.tasks:
			if task.id==id:
				break
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			check(game.campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[])).ok,"Reach exhibit "+str(task.id))
			game.campaign.mark_seen(task.lines)
			if not str(task.get("finding","")).is_empty():
				game.campaign.mark_seen([task.finding])
		if i!=task_scene:
			game.campaign.mark_seen(scene.outro)
			game.campaign.advance()
	var wanted: String=game.campaign.task_index[id].actor
	if not wanted.is_empty():
		game.campaign.switch_actor(wanted)
	game.campaign.mark_seen(game.campaign.task_index[id].get("lead",[]))
	game.started=true
	game.menu.hide()
	game._load_stage(false)
	check(game._can_explore() and game.campaign.available(id),"Board task is available to inspect "+id)
	game._inspect_on_arrival(id)
	await frames(4)
	if board:
		check(game.case_board.is_visible_in_tree(),"Open the case at "+id)

func record_view(mode: String,board: Control) -> void:
	if examples.has(mode) or DisplayServer.get_name()=="headless":
		return
	await frames(3)
	var panel: Rect2=game.root.get_node("InteractionPanel").get_global_rect()
	check(root.get_visible_rect().encloses(panel),"Keep the "+mode+" board on screen")
	check(panel.encloses(board.confirm.get_global_rect()),"Show the "+mode+" confirmation button")
	RenderingServer.force_draw(false)
	var name_:=mode+"-case-board.png"
	check(root.get_texture().get_image().save_png(destination.path_join(name_))==OK,"Capture "+mode)
	examples[mode]=name_

func review_layouts() -> void:
	var scroll:=game.interaction.get_parent() as ScrollContainer
	var images:=OS.get_environment("NIGHT_NINE_CASEBOARD_ALL_FRAMES")=="1" and DisplayServer.get_name()!="headless"
	if images:
		DirAccess.make_dir_recursive_absolute(destination.path_join("boards"))
	for child: Node in game.interaction.get_children():
		game.interaction.remove_child(child)
		child.queue_free()
	for task: Dictionary in game.campaign.task_index.values():
		if task.get("puzzle",{}).get("presentation","")!="case_board":
			continue
		for index: int in task.puzzle.stages.size():
			var board:=preload("res://ui/case_board.gd").new()
			var progress: Dictionary=game.campaign.board_draft(task.id)
			progress.stage=index
			game.interaction.add_child(board)
			board.configure(task.id,task.title,task.puzzle,progress,task.goal,task.background,game.campaign.perspective_name(task.id))
			await frames(3)
			var name_: String="%s-%d" % [task.id,index+1]
			check(board.goal.text == task.goal and board.background.text == task.background, "Show goal and background on " + name_)
			check(board.hint_button.text.begins_with("Hint 1 of 3"), "Number the board hint on " + name_)
			check(board.knowledge.get_line_count()==1 and board.knowledge.size.x>=300 and board.background.size.x>=300,"Read the knowledge heading and background across the board on "+name_)
			var numbered: bool=board.notes.size()==task.puzzle.evidence.size()
			for n: int in board.notes.size():
				numbered=numbered and board.notes[n].text==str(task.puzzle.evidence[n]) and board.note_numbers[n].text==str(n+1) and board.notes[n].size.x>=250
			check(numbered,"Number every case note at a readable width on "+name_)
			var steps: int=task.puzzle.stages.size()
			check(board.step_label.text==("Step %d of %d" % [index+1,steps] if steps>1 else "") and board.step_label.visible==(steps>1),"Readable step counter on "+name_)
			var fit:=true
			for dimensions: Vector2i in [Vector2i(960,600),Vector2i(1280,720)]:
				root.size=dimensions
				game._investigation_size(true)
				await frames(3)
				var panel: Rect2=game.root.get_node("InteractionPanel").get_global_rect()
				for control: Control in [board.goal,board.background,board.pieces[-1],board.slots[-1],board.confirm,board.hint_button]:
					scroll.ensure_control_visible(control)
					await frames()
					var visible:=panel.intersects(control.get_global_rect()) if control==board.background else panel.encloses(control.get_global_rect())
					fit=fit and visible
					check(visible,"Reach every board control at %dx%d for %s" % [dimensions.x,dimensions.y,name_])
			layouts.append({"task":task.id,"step":index+1,"mode":task.puzzle.stages[index].mode,"fits":fit})
			if images:
				RenderingServer.force_draw(false)
				root.get_texture().get_image().save_png(destination.path_join("boards").path_join(name_+".png"))
			game.interaction.remove_child(board)
			board.queue_free()
	root.size=Vector2i(1600,900)
	game._investigation_size(true)

func wrong_row(stage: Dictionary) -> Array:
	# Right in the first two places, wrong everywhere else.
	var row: Array=[int(stage.answer[0]),int(stage.answer[1])]
	var spare: Array=[]
	for piece: int in range(stage.pieces.size()):
		if piece not in row:
			spare.append(piece)
	for i: int in range(2,stage.answer.size()):
		for piece: int in spare:
			if piece!=int(stage.answer[i]):
				row.append(piece)
				spare.erase(piece)
				break
	return row

func settings_rows(id: String) -> void:
	var task: Dictionary=game.campaign.task_index[id]
	var solution: Array=task.puzzle.solution
	var wrong_values: Array=solution.duplicate()
	wrong_values[1]=(int(solution[1])+1)%task.puzzle.rows[1].options.size()
	var expected: Array[bool]=[]
	for i: int in solution.size():
		expected.append(i!=1)
	check(game.campaign.settings_marks(id,solution).count(true)==solution.size(),"Mark every right setting")
	check(game.campaign.settings_marks(id,wrong_values)==expected,"Mark each setting row right or wrong")
	check(game.campaign.settings_marks(id,[]).count(false)==solution.size() and game.campaign.settings_marks(id,["x",NAN]).count(true)==0,"Treat missing or invalid settings as wrong")
	await fresh_room(id,false)
	var rows: Array=game.puzzle_controls
	check(rows.size()==solution.size(),"Show every settings row")
	var shown:=true
	for i: int in rows.size():
		shown=shown and rows[i].choices.size()==task.puzzle.rows[i].options.size() and rows[i].title.text.contains(str(task.puzzle.rows[i].label))
	check(shown,"Show every choice on its row")
	var background: Node=game.interaction.find_child("Background",true,false)
	var boxed:=background==null
	var holder: Node=background.get_parent() if background else null
	while holder and holder!=game.interaction:
		boxed=boxed or holder is ScrollContainer
		holder=holder.get_parent()
	check(not boxed and background.text==task.background,"Show the whole background, not a small scroll box")
	var apply: Button
	for child: Node in game.interaction.get_children():
		if child is Button and child.text=="Apply settings":
			apply=child
	var misses: int=int(game.campaign.data.misses.get(id,0))
	await mouse(apply)
	check(int(game.campaign.data.misses.get(id,0))==misses and game.puzzle_response.text.contains("Pick a choice"),"Ask for every row before applying")
	for i: int in rows.size():
		await mouse(rows[i].choices[int(wrong_values[i])])
	check(rows[0].selected==int(solution[0]) and rows[0].choices[int(solution[0])].button_pressed,"Pick a setting with the mouse")
	await mouse(apply)
	check(int(game.campaign.data.misses.get(id,0))==misses+1,"A wrong setting still records a miss")
	check(game.puzzle_response.text.begins_with("%d of %d rows are right." % [rows.size()-1,rows.size()]),"Count the right rows")
	var marked:=true
	for i: int in rows.size():
		marked=marked and rows[i].mark_state==("wrong" if i==1 else "right") and rows[i].mark.kind==rows[i].mark_state
	check(marked,"Mark each row right or wrong after applying")
	rows[0].choose((int(solution[0])+1)%rows[0].choices.size())
	check(rows[0].selected==int(solution[0]),"A right row stays locked")
	await mouse(rows[1].choices[int(solution[1])])
	check(rows[1].mark_state=="","Changing a wrong row clears its cross")
	await mouse(apply)
	check(id in game.campaign.data.done,"Apply the fixed settings")

func run() -> void:
	destination=OS.get_environment("NIGHT_NINE_QA_DIR")
	if destination.is_empty() or OS.get_environment("NIGHT_NINE_SAVE_DIR").is_empty():
		push_error("Use isolated save and QA directories for board tests.")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(destination)
	game=load("res://scenes/campaign.tscn").instantiate()
	root.add_child(game)
	game.auto_dialogue=false
	for task: Dictionary in game.campaign.task_index.values():
		var p: Dictionary=task.get("puzzle",{})
		if p.get("presentation","")=="case_board":
			case_count+=1
			stage_count+=p.stages.size()
			placement_count+=p.solution.size()
			var merged: Array=[]
			for row: Dictionary in p.stages:
				check(row.slots.size()>=1 and row.slots.size()<=5,"Board stage uses one to five slots "+str(task.id))
				check(row.pieces.size()>=row.slots.size(),"Board has enough pieces "+str(task.id))
				var piece_ids := {}
				for piece: String in row.pieces:
					piece_ids[piece]=true
				check(piece_ids.size()==row.pieces.size(),"Board piece ids are unique "+str(task.id))
				var used := {}
				for answer: int in row.answer:
					check(answer>=0 and answer<row.pieces.size(),"Board answer names an existing piece "+str(task.id))
					used[answer]=true
				check(used.size()==row.slots.size(),"One distinct answer per board slot "+str(task.id))
				decoy_count+=row.pieces.size()-row.slots.size()
				merged.append_array(row.answer)
			check(merged==p.solution,"Canonical finding for "+str(task.id))
	check(case_count==23 and stage_count==30 and placement_count==92,"Campaign packages the revised board inventory")
	check(decoy_count==29,"Campaign packages authored decoy pieces")
	await fresh_room("c1_pier.bait")
	var id: String=game.case_board.task_id
	var board: Control=game.case_board
	var legacy: Dictionary=game.campaign.data.duplicate(true)
	legacy.erase("case_boards")
	check(game.campaign.restore(legacy) and game.campaign.data.case_boards.is_empty(),"Open a previous-version save without drafts")
	check(board.knowledge.text=="What %s knows" % game.campaign.perspective_name(id) and board.knowledge.get_line_count()==1 and board.knowledge.size.x>=300,"Show the knowledge heading on one line")
	check(board.background.is_visible_in_tree() and board.background.size.x>=300 and board.background.size.y>=20 and board.background.get_visible_line_count()==board.background.get_line_count(),"Show the whole background paragraph")
	check(board.find_children("*","ScrollContainer",true,false).is_empty(),"Show every case note without an inner scroll box")
	check(board.guide.size()==3 and board.guide_labels[0].text.contains("Pick a card") and board.guide_labels[2].text.contains("Check"),"Spell out the three steps")
	check(board.slot_state(0)=="empty" and board.slots[0].value.text=="Drop a card here","Show an empty place clearly")
	board.pick(0)
	check(board.piece_state(0)=="selected" and board.slot_state(0)=="invite" and board.active_step==1,"Highlight the picked card and invite a place")
	board.pick(0)
	check(board.piece_state(0)=="free" and board.active_step==0,"Pick the same card again to put it down")
	await mouse(board.confirm)
	check(board.response.text.contains("Put a card in") and board.marks.is_empty(),"Explain the first empty position")
	await drag(board.pieces[2],board.slots[2])
	check(int(board.draft.placements[0][2])==2,"Drag an exhibit onto the timeline")
	await mouse(board.find_child("ClearBoard",true,false))
	await enter(board.pieces[0])
	await enter(board.slots[0])
	check(int(board.draft.placements[0][0])==0,"Place evidence with the keyboard")
	await mouse(board.pieces[1])
	await mouse(board.slots[1])
	await mouse(board.slots[0])
	await mouse(board.slots[1])
	check(int(board.draft.placements[0][0])==1 and int(board.draft.placements[0][1])==0,"Swap two placed pieces")
	await mouse(board.find_child("BoardHint",true,false))
	check(board.response.text==game.campaign.task_index[id].hints[0],"Read an authored hint")
	game._save("manual")
	var before: Dictionary=game.campaign.board_draft(id)
	var corrupted: Dictionary=game.campaign.data.duplicate(true)
	corrupted.case_boards[id].placements[0][1]=1
	check(not game.campaign.validate(corrupted).is_empty(),"Reject duplicate pieces in saved cases")
	await mouse(board.find_child("ClearBoard",true,false))
	check(int(board.draft.placements[0][0])==-1,"Clear the current stage")
	check(game._load("manual"),"Restore from the real manual save")
	game._inspect_on_arrival(id)
	await frames(3)
	board=game.case_board
	check(JSON.stringify(before)==JSON.stringify(board.draft),"Restore puzzle placements after a manual load")
	await mouse(board.find_child("CloseBoard",true,false))
	game._inspect_on_arrival(id)
	await frames(2)
	board=game.case_board
	check(int(board.draft.placements[0][0])==1,"Reopen the same incomplete board")
	var stage: Dictionary=board.stages[0]
	var wrong: Array=wrong_row(stage)
	for i: int in stage.slots.size():
		await mouse(board.pieces[int(wrong[i])])
		await mouse(board.slots[i])
	var total: int=stage.slots.size()
	var misses: int=int(game.campaign.data.misses.get(id,0))
	await mouse(board.confirm)
	check(int(game.campaign.data.misses.get(id,0))==misses+1,"A wrong check still records a miss")
	check(board.stage_index==0 and board.response.text.begins_with("2 of %d are right." % total),"Count the right placements")
	check(board.marks.size()==total,"Mark every placement after a check")
	var marked:=true
	for i: int in total:
		marked=marked and board.slot_state(i)==("right" if i<2 else "wrong") and board.slots[i].mark.kind==("right" if i<2 else "wrong")
	check(marked,"Draw a check on right places and a cross on wrong ones")
	check(board.piece_state(int(stage.answer[0]))=="locked" and board.piece_state(int(wrong[2]))=="placed","Lock the right cards only")
	await drag(board.pieces[int(stage.answer[0])],board.slots[2])
	check(int(board.draft.placements[0][0])==int(stage.answer[0]) and int(board.draft.placements[0][2])==int(wrong[2]),"A locked card cannot be dragged")
	await mouse(board.slots[0])
	await mouse(board.slots[2])
	check(int(board.draft.placements[0][0])==int(stage.answer[0]) and board.selected!=int(stage.answer[0]),"A locked place cannot be picked up")
	board.selected=-1
	await mouse(board.pieces[int(wrong[2])])
	check(board.selected==int(wrong[2]),"Pick up a flagged card")
	await mouse(board.slots[1])
	check(int(board.draft.placements[0][1])==int(stage.answer[1]) and board.slot_state(1)=="right","A locked place keeps its card")
	board.selected=-1
	await drag(board.slots[2],board.slots[3] if total>3 else board.slots[1])
	check(board.slot_state(2)!="wrong","Moving a flagged card clears its cross")
	await mouse(board.find_child("CloseBoard",true,false))
	game._inspect_on_arrival(id)
	await frames(3)
	board=game.case_board
	check(board.slot_state(0)=="right" and board.slot_state(1)=="right","Keep right cards locked after reopening")
	await mouse(board.find_child("ClearBoard",true,false))
	check(int(board.draft.placements[0][0])==int(stage.answer[0]) and int(board.draft.placements[0][2])==-1 and board.slot_state(2)=="empty","Clearing keeps the right cards")
	for row: Dictionary in board.stages:
		for i: int in row.answer.size():
			await mouse(board.pieces[int(row.answer[i])])
			await mouse(board.slots[i])
			if i==1:
				await record_view(row.mode,board)
		await mouse(board.confirm)
		if board.stage_index==1 and not game.dialogue_panel.visible:
			check(game._load("autosave"),"Reload between two board stages")
			game._inspect_on_arrival(id)
			await frames(3)
			board=game.case_board
			check(board.stage_index==1,"Resume on the second stage")
	check(id in game.campaign.data.done and not game.campaign.data.case_boards.has(id),"Record the finding and remove the completed draft")
	legacy=game.campaign.data.duplicate(true)
	legacy.erase("case_boards")
	check(game.campaign.restore(legacy) and id in game.campaign.data.done,"Preserve historical findings without replaying a board")
	await fresh_room("c7_swap.map")
	var route_stage: Dictionary=game.case_board.stages[0]
	for i: int in route_stage.answer.size():
		await mouse(game.case_board.pieces[int(route_stage.answer[i])])
		await mouse(game.case_board.slots[i])
	await mouse(game.case_board.confirm)
	check(game.case_board.stage_index==1,"Advance to the authored route stage")
	for i: int in 2:
		await mouse(game.case_board.pieces[int(game.case_board.stages[1].answer[i])])
		await mouse(game.case_board.slots[i])
	await record_view("route",game.case_board)
	await review_layouts()
	await settings_rows("c1_escape.power")
	var out:=FileAccess.open(destination.path_join("case-boards.json"),FileAccess.WRITE)
	out.store_string(JSON.stringify({"checks":checks,"failures":failures,"boards":case_count,"stages":stage_count,"placements":placement_count,"decoys":decoy_count,"screens":examples,"layouts":layouts},"  ")+"\n")
	out.close()
	print("Case boards: ",checks," checks, ",failures.size()," failures, ",case_count," cases")
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

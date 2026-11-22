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

func fresh_room(id: String) -> void:
	game.campaign.reset()
	var task_scene: int=game.campaign.task_scene[id]
	for i: int in range(task_scene+1):
		var scene: Dictionary=game.campaign.current()
		game.campaign.mark_seen(scene.get("context", []) + scene.intro)
		for task: Dictionary in scene.tasks:
			if task.id==id:
				break
			if not task.actor.is_empty():
				game.campaign.switch_actor(task.actor)
			check(game.campaign.choose(task.id,int(task.answer),task.get("puzzle",{}).get("solution",[])).ok,"Reach exhibit "+str(task.id))
			game.campaign.mark_seen(task.lines)
		if i!=task_scene:
			game.campaign.mark_seen(scene.outro)
			game.campaign.advance()
	var wanted: String=game.campaign.task_index[id].actor
	if not wanted.is_empty():
		game.campaign.switch_actor(wanted)
	game.started=true
	game.menu.hide()
	game._load_stage(false)
	game._inspect_on_arrival(id)
	await frames(4)
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
	var panel: Rect2=game.root.get_node("InteractionPanel").get_global_rect()
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
			board.configure(task.id,task.title,task.puzzle,progress)
			scroll.scroll_vertical=0
			await frames(3)
			var name_: String="%s-%d" % [task.id,index+1]
			var fit: bool=panel.encloses(board.confirm.get_global_rect()) and panel.encloses(board.slots[-1].get_global_rect()) and panel.encloses(board.pieces[-1].get_global_rect())
			check(fit,"Fit all board controls for "+name_)
			layouts.append({"task":task.id,"step":index+1,"mode":task.puzzle.stages[index].mode,"fits":fit})
			if images:
				RenderingServer.force_draw(false)
				root.get_texture().get_image().save_png(destination.path_join("boards").path_join(name_+".png"))
			game.interaction.remove_child(board)
			board.queue_free()

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
				merged.append_array(row.answer)
			check(merged==p.solution,"Canonical finding for "+str(task.id))
	check(case_count>=32 and stage_count>=80,"Campaign includes all authored multi-stage boards")
	await fresh_room("c1_pier.bait")
	var id: String=game.case_board.task_id
	var board: Control=game.case_board
	var legacy: Dictionary=game.campaign.data.duplicate(true)
	legacy.erase("case_boards")
	check(game.campaign.restore(legacy) and game.campaign.data.case_boards.is_empty(),"Open a previous-version save without drafts")
	await mouse(board.confirm)
	check(board.response.text.contains("Place a piece"),"Explain the first empty position")
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
	for i: int in stage.slots.size():
		await mouse(board.pieces[(int(stage.answer[i])+1)%stage.pieces.size()])
		await mouse(board.slots[i])
	await mouse(board.confirm)
	check(board.stage_index==0 and board.response.text.contains("placements fit"),"Explain an incorrect completed board")
	await mouse(board.find_child("ClearBoard",true,false))
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
	await fresh_room("c4_escape.van")
	for i: int in 2:
		await mouse(game.case_board.pieces[int(game.case_board.stages[0].answer[i])])
		await mouse(game.case_board.slots[i])
	await record_view("route",game.case_board)
	await review_layouts()
	var out:=FileAccess.open(destination.path_join("case-boards.json"),FileAccess.WRITE)
	out.store_string(JSON.stringify({"checks":checks,"failures":failures,"boards":case_count,"stages":stage_count,"placements":placement_count,"screens":examples,"layouts":layouts},"  ")+"\n")
	out.close()
	print("Case boards: ",checks," checks, ",failures.size()," failures, ",case_count," cases")
	await game.drain_audio()
	quit(0 if failures.is_empty() else 1)

extends Node2D
## Feet, paths and perspective are measured on the painted 1600 × 900 stage.
signal arrived(task_id: String)

const ART := Vector2(1600.0,900.0)
const WALK := "res://assets/illustrated/campaign/walk/"
const CONTACT_SHADOW := preload("contact_shadow.gdshader")
const IDLE_FRAME := 2
const GROUND := preload("ground_navigation.gd")
const SOCIAL := preload("social_direction.gd")
const STORY_DOOR := preload("story_door.gd")
var navigation := GROUND.new()
var door_art := {}
var blockers: Array = []
var solids: Array = []
var story: Array = []
var navigation_key := -1
var room_id := ""
var performance_action := ""
var speaking_partner := ""
var authored_marks := {}
var desired_foot := Vector2.ZERO
var polygon := PackedVector2Array()
var depth: Array
var approach: Dictionary
var listen_tasks: Array
var object_marks := {}
var bodies := {}
var playable: Array
var active_actor := ""
var route := PackedVector2Array()
var pending := ""
var phase := 0.0
var pose_time := 0.0
var marker: Node2D
var marker_alpha := 0.0
var keyboard_walking := false
var wide: Sprite2D
var steps: AudioStreamPlayer2D
var footfalls: Array[AudioStream] = []

func configure(room: Dictionary, roles: Array, plate: Texture2D, wide_file: String, tint: Color) -> void:
	configure_navigation(room)
	approach = room.approach
	listen_tasks = room.get("listen",[])
	var surface: String = room.get("surface", "timber")
	for side: int in 2:
		var foot_file := "res://assets/audio/steps/%s-%d.wav" % [surface, side]
		if ResourceLoader.exists(foot_file):
			footfalls.append(load(foot_file))
	steps = AudioStreamPlayer2D.new()
	steps.max_distance = 3600
	steps.attenuation = .4
	add_child(steps)
	if ResourceLoader.exists(wide_file):
		wide = Sprite2D.new()
		wide.centered = false
		wide.texture = load(wide_file)
		wide.scale = ART / wide.texture.get_size()
		add_child(wide)
		plate = wide.texture
	for record: Dictionary in room.get("doors",[]):
		var door := STORY_DOOR.new()
		add_child(door)
		door.configure(record,plate,room_id,ART,record.opens_after in story)
		door_art[record.blocker]=door
	var cast := Node2D.new()
	cast.y_sort_enabled = true
	marker = Node2D.new()
	add_child(marker)
	marker.draw.connect(draw_marker)
	add_child(cast)
	playable = roles.duplicate()
	var marks: Dictionary = room.spawn.duplicate()
	marks.merge(room.get("residents",{}))
	authored_marks = marks
	for id: String in marks:
		var path := WALK + id + ".webp"
		var idle_file := WALK + id + "-idle.webp"
		if not ResourceLoader.exists(path) and not ResourceLoader.exists(idle_file):
			continue
		var body := Node2D.new()
		body.name = id
		body.position = point(marks[id])
		cast.add_child(body)
		var shadow := Sprite2D.new()
		var white := PlaceholderTexture2D.new()
		white.size = Vector2(1,1)
		shadow.texture = white
		var shade := ShaderMaterial.new()
		shade.shader = CONTACT_SHADOW
		shadow.material = shade
		body.add_child(shadow)
		var sprite := Sprite2D.new()
		var sheet: Texture2D = load(path) if ResourceLoader.exists(path) else null
		var idle: Texture2D = load(idle_file) if ResourceLoader.exists(idle_file) else null
		sprite.modulate = Color.WHITE.lerp(tint,.11)
		body.add_child(sprite)
		var poses := {}
		for kind: String in ["reach","listen","read","kneel","operate","greet","talk","toward","away"]:
			var pose_file := WALK + id + "-" + kind + ".webp"
			if ResourceLoader.exists(pose_file):
				poses[kind] = load(pose_file)
		bodies[id] = {"body":body,"sprite":sprite,"shadow":shadow,"sheet":sheet,"idle":idle,"poses":poses,"left":false,"facing":"side"}
		draw_body(id,false)
	for layer: Dictionary in room.get("occluders",[]):
		var occluder := Polygon2D.new()
		occluder.position.y = float(layer.behind_y)*ART.y
		var outlines := points(layer.polygon)
		var local := PackedVector2Array()
		var uv := PackedVector2Array()
		for corner: Vector2 in outlines:
			local.append(corner-occluder.position)
			uv.append(corner / ART * plate.get_size())
		occluder.polygon = local
		occluder.uv = uv
		occluder.texture = plate
		cast.add_child(occluder)

	repair_positions({})

func point(pair: Array) -> Vector2:
	return Vector2(pair[0],pair[1])*ART

func points(pairs: Array) -> PackedVector2Array:
	var result := PackedVector2Array()
	for pair: Array in pairs:
		result.append(point(pair))
	return result

func select_actor(id: String) -> void:
	if id != active_actor:
		cancel()
		active_actor = id
		navigation_key = -1

func has_actor() -> bool:
	return bodies.has(active_actor)

func configure_navigation(room: Dictionary) -> void:
	polygon = points(room.polygon)
	depth = room.depth
	blockers = room.get("blockers",[])
	update_solids([])

func update_solids(completed: Array) -> void:
	solids.clear()
	for item: Dictionary in blockers:
		var open: bool=item.has("opens_after") and item.opens_after in completed
		if open and door_art.has(item.id):
			open=door_art[item.id].is_cleared()
		if not open:
			solids.append(points(item.polygon))
	navigation_key = -1

func set_story(completed: Array, reveal_after: Dictionary) -> void:
	var changed := story!=completed
	if changed:
		story=completed.duplicate()
		for item: Dictionary in blockers:
			if door_art.has(item.id):
				door_art[item.id].set_unlocked(item.opens_after in completed)
		update_solids(story)
	for id: String in bodies:
		var show_person: bool = not reveal_after.has(id) or reveal_after[id] in completed
		if bodies[id].body.visible!=show_person:
			bodies[id].body.visible = show_person
			changed=true
	if changed:
		repair_positions({})

func sync_navigation() -> bool:
	var neighbours := PackedVector2Array()
	for id: String in bodies:
		if id!=active_actor and bodies[id].body.visible:
			neighbours.append(bodies[id].body.position)
	var key := hash([active_actor,neighbours])
	if key==navigation_key and navigation.mesh!=null:
		return false
	navigation.bake(polygon,depth,solids,neighbours)
	navigation_key=key
	return true

func repair_positions(saved: Dictionary) -> void:
	var occupied := PackedVector2Array()
	var placement_order: Array[String] = []
	for id: String in bodies:
		if id not in playable:
			placement_order.append(id)
	for id: String in playable:
		if bodies.has(id):
			placement_order.append(id)
	for id: String in placement_order:
		var body: Node2D = bodies[id].body
		var saved_foot: Array = saved.get(id,[])
		var target := point(saved_foot) if saved_foot.size()>=3 else body.position
		if id not in playable:
			target=point(authored_marks[id])
		navigation.bake(polygon,depth,solids,occupied)
		var settled := navigation.closest(target)
		if saved_foot.size()>=3:
			var anchor := navigation.closest(point(authored_marks[id]))
			if anchor.is_finite() and settled.is_finite() and navigation.path(anchor,settled).is_empty():
				settled=anchor
			bodies[id].left = saved_foot[2]
			bodies[id].facing = saved_foot[3] if saved_foot.size()==4 else "side"
		if settled.is_finite():
			body.position=settled
		if body.visible:
			occupied.append(body.position)
		draw_body(id,false)
	navigation_key=-1

func cancel() -> void:
	route.clear()
	pending = ""
	performance_action = ""
	speaking_partner = ""
	pose_time = 0.0
	keyboard_walking = false
	marker_alpha = 0.0
	marker.hide()
	if has_actor():
		draw_body(active_actor,false)

func height_at(at: Vector2) -> float:
	var t := clampf(inverse_lerp(depth[0],depth[2],at.y/ART.y),0.0,1.0)
	return lerpf(depth[1],depth[3],t)*ART.y

func draw_body(id: String, walking: bool, pose: String = "") -> void:
	var person: Dictionary = bodies[id]
	var sprite: Sprite2D = person.sprite
	var height := height_at(person.body.position)
	var poses: Dictionary = person.poses
	var still: Texture2D = poses.get(pose)
	if not still and pose in ["operate","kneel"]:
		still=poses.get("reach")
	var strip: Texture2D = poses.get(person.facing)
	var columns := 1
	var rows := 1
	var cell := 0
	if strip and pose.is_empty() and person.facing!="side":
		sprite.texture=strip
		columns=4
		cell=int(phase*.5)%4 if walking else 1
	elif not walking and (still or person.idle):
		sprite.texture=still if still else person.idle
	else:
		sprite.texture=person.sheet
		columns=4
		rows=2
		cell=int(phase)%8 if walking else IDLE_FRAME
	sprite.hframes=columns
	sprite.vframes=rows
	sprite.frame=cell
	var cell_height := float(sprite.texture.get_height())/rows
	sprite.scale=Vector2.ONE*height/cell_height
	sprite.flip_h=person.left and not (strip and pose.is_empty() and person.facing!="side")
	sprite.position=Vector2(0,-height*.5)
	person.shadow.scale = Vector2(.37,.066)*height
	person.shadow.position = Vector2(-.012,-.008)*height

func on_floor(at: Vector2) -> bool:
	sync_navigation()
	return navigation.contains(at)

func clear_segment(a: Vector2, b: Vector2) -> bool:
	sync_navigation()
	return navigation.clear(a,b)

func path_to(start: Vector2, finish: Vector2) -> PackedVector2Array:
	sync_navigation()
	return navigation.path(start,finish)

func start_path(next: PackedVector2Array, task: String, partner: String = "") -> bool:
	if next.is_empty():
		return false
	if route.is_empty():
		phase=0.0
	route=next
	keyboard_walking=false
	desired_foot=next[-1]
	pose_time=0.0
	performance_action=""
	speaking_partner=partner
	pending=task
	marker.position=desired_foot
	marker_alpha=1.0
	marker.show()
	marker.queue_redraw()
	return true

func walk_to(at: Vector2, task: String = "") -> bool:
	if not has_actor() or not bodies[active_actor].body.visible:
		return false
	sync_navigation()
	var distance := clampf(height_at(at)*.19,24.0,75.0)
	return start_path(navigation.nearby_path(bodies[active_actor].body.position,at,distance),task)

func approach_task(id: String) -> bool:
	var partner := SOCIAL.task_partner(room_id,id,active_actor)
	if bodies.has(partner) and bodies[partner].body.visible:
		return walk_to_person(partner,id)
	var target: Array = approach.get(id.get_slice(".",1),[])
	return target.size()==2 and walk_to(point(target),id)

func walk_to_person(id: String, task: String) -> bool:
	if not has_actor() or not bodies.has(id) or id==active_actor or not bodies[id].body.visible:
		return false
	sync_navigation()
	var foot: Vector2 = bodies[id].body.position
	var from: Vector2 = bodies[active_actor].body.position
	var spacing := clampf(height_at(foot)*.45,50.0,220.0)
	var best := PackedVector2Array()
	var least := INF
	for factor: float in [1.0,.82,1.22]:
		for side: int in 12:
			var offset := Vector2.from_angle(side*TAU/12.0)*Vector2(1.0,.52)*spacing*factor
			var landing := foot+offset
			var sightline := PackedVector2Array([landing,foot])
			if not Geometry2D.clip_polyline_with_polygon(sightline,polygon).is_empty():
				continue
			var candidate := navigation.path(from,landing)
			if candidate.is_empty():
				continue
			# Favour side-by-side staging and avoid speaking through a solid prop.
			var blocked := false
			for solid: PackedVector2Array in solids:
				if not Geometry2D.intersect_polyline_with_polygon(sightline,solid).is_empty():
					blocked=true
					break
			if blocked:
				continue
			var cost := absf(offset.normalized().y)*spacing*.70 + absf(1.0-factor)*spacing*1.6
			var last := from
			for step_: Vector2 in candidate:
				cost+=last.distance_to(step_)
				last=step_
			if cost<least:
				best=candidate
				least=cost
	return start_path(best,task,id)

func finish_person_now(id: String, task: String) -> bool:
	if not walk_to_person(id,task):
		return false
	finish_route(task)
	return true

func finish_now(id: String) -> bool:
	if not approach_task(id):
		return false
	finish_route(id)
	return true

func finish_route(id: String) -> void:
	var partner := speaking_partner
	var landing := route[-1]
	cancel()
	bodies[active_actor].body.position=landing
	speaking_partner=partner
	gaze_at_task(id)
	draw_body(active_actor,false)

func face_toward(id: String, art_point: Vector2) -> void:
	if not bodies.has(id):
		return
	var person: Dictionary = bodies[id]
	var offset: Vector2 = art_point-person.body.position
	if absf(offset.x)>4.0:
		person.left=offset.x<0.0
	person.facing="side"
	draw_body(id,false)

func gaze_at_task(id: String) -> void:
	if not has_actor():
		return
	if bodies.has(speaking_partner) and bodies[speaking_partner].body.visible:
		face_toward(active_actor,bodies[speaking_partner].body.position)
		face_toward(speaking_partner,bodies[active_actor].body.position)
	elif object_marks.has(id.get_slice(".",1)):
		face_toward(active_actor,point(object_marks[id.get_slice(".",1)]))

func face_motion(person: Dictionary, motion: Vector2) -> void:
	if motion.length_squared()<.0001:
		return
	var ratio := absf(motion.y)*1.9/maxf(absf(motion.x),.001)
	var threshold := .96 if person.facing!="side" else 1.35
	var requested := ("toward" if motion.y>0 else "away") if ratio>threshold else "side"
	person.facing = requested if person.poses.has(requested) else "side"
	if absf(motion.x)>.002:
		person.left = motion.x<0.0

func draw_marker() -> void:
	var oval := PackedVector2Array()
	for i: int in 31:
		var a := TAU * i / 30.0
		oval.append(Vector2(cos(a)*11.0,sin(a)*4.0))
	marker.draw_polyline(oval,Color(.93,.82,.58,.69),1.7,true)

func step(delta: float, direction: Vector2) -> void:
	for gate: Node2D in door_art.values():
		var previously_clear: bool=gate.is_cleared()
		gate.advance(delta,is_visible_in_tree())
		if previously_clear!=gate.is_cleared():
			update_solids(story)
	if not has_actor():
		return
	var person: Dictionary = bodies[active_actor]
	var changed := sync_navigation()
	if changed and not navigation.contains(person.body.position):
		repair_positions({})
		sync_navigation()
	if changed and not route.is_empty():
		if not speaking_partner.is_empty():
			if not walk_to_person(speaking_partner,pending):
				cancel()
		else:
			route=navigation.path(person.body.position,desired_foot)
			if route.is_empty():
				cancel()
	if pose_time>0.0 and direction==Vector2.ZERO:
		pose_time = maxf(0.0,pose_time-delta)
		if pose_time==0.0:
			var completed := pending
			performance_action=""
			pending = ""
			draw_body(active_actor,false)
			arrived.emit(completed)
		return
	var body: Node2D = person.body
	var height := height_at(body.position)
	var speed := height*.77
	if direction!=Vector2.ZERO:
		route.clear()
		pending = ""
		speaking_partner = ""
		performance_action = ""
		pose_time = 0.0
		keyboard_walking = true
		marker.hide()
		var motion := direction.normalized()*Vector2(1.0,.62)*speed*delta
		route = navigation.slide(body.position,motion)
		if route.is_empty():
			draw_body(active_actor,false)
	elif keyboard_walking:
		keyboard_walking = false
		draw_body(active_actor,false)
	if route.is_empty():
		return
	var time_left := delta
	var travelled := 0.0
	while time_left > 0 and not route.is_empty():
		var movement := route[0]-body.position
		var remaining := movement.length()
		var pace := speed * lerpf(1.0,.62,absf(movement.normalized().y))
		var distance := minf(pace*time_left,remaining)
		face_motion(person,movement)
		body.position = body.position.move_toward(route[0],distance)
		travelled += distance
		time_left -= distance/pace
		if distance>=remaining:
			body.position=route[0]
			route.remove_at(0)
		else:
			break
	var previous_step := floori(phase / 4)
	phase += travelled / (height*.09)
	var next_step := floori(phase / 4)
	if next_step != previous_step and footfalls.size() == 2 and is_visible_in_tree():
		steps.position = body.position
		steps.stream = footfalls[next_step % 2]
		steps.pitch_scale = 1.10 if active_actor == "nora" else (.95 if active_actor == "pell" else 1.0)
		steps.volume_db = lerpf(-24.0, -15.0, clampf(height / 560.0, 0.0, 1.0))
		steps.play()
	draw_body(active_actor,not route.is_empty() or (direction!=Vector2.ZERO and travelled>0.0))
	marker_alpha = maxf(0.0,marker_alpha-delta*1.5)
	marker.modulate.a = marker_alpha
	if route.is_empty():
		marker.hide()
		if not pending.is_empty():
			gaze_at_task(pending)
			performance_action=SOCIAL.action_for(room_id,pending,listen_tasks)
			pose_time=SOCIAL.hold_for(performance_action)
			draw_body(active_actor,false,SOCIAL.pose_for(performance_action))

func snapshot() -> Dictionary:
	var result := {}
	for id: String in playable:
		if not bodies.has(id):
			continue
		var foot: Vector2 = bodies[id].body.position/ART
		result[id] = [foot.x,foot.y,bodies[id].left]
		if bodies[id].facing!="side":
			result[id].append(bodies[id].facing)
	return result

func restore(saved: Dictionary) -> void:
	for item: Dictionary in blockers:
		if door_art.has(item.id):
			door_art[item.id].snap_unlocked(item.opens_after in story)
	update_solids(story)
	repair_positions(saved)

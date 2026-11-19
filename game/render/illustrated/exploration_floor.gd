extends Node2D
## Feet, paths and perspective are measured on the painted 1600 × 900 stage.
signal arrived(task_id: String)

const ART := Vector2(1600.0,900.0)
const WALK := "res://assets/illustrated/campaign/walk/"
const CONTACT_SHADOW := preload("contact_shadow.gdshader")
const IDLE_FRAME := 2
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
	polygon = points(room.polygon)
	depth = room.depth
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
	var cast := Node2D.new()
	cast.y_sort_enabled = true
	marker = Node2D.new()
	add_child(marker)
	marker.draw.connect(draw_marker)
	add_child(cast)
	playable = roles.duplicate()
	var marks: Dictionary = room.spawn.duplicate()
	marks.merge(room.get("residents",{}))
	for id: String in marks:
		var path := WALK + id + ".webp"
		if not ResourceLoader.exists(path):
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
		var sheet := load(path) as Texture2D
		var idle_file := WALK + id + "-idle.webp"
		var idle: Texture2D = load(idle_file) if ResourceLoader.exists(idle_file) else null
		sprite.modulate = Color.WHITE.lerp(tint,.11)
		body.add_child(sprite)
		var poses := {}
		for kind: String in ["reach","listen"]:
			var pose_file := WALK + id + "-" + kind + ".webp"
			if ResourceLoader.exists(pose_file):
				poses[kind] = load(pose_file)
		bodies[id] = {"body":body,"sprite":sprite,"shadow":shadow,"sheet":sheet,"idle":idle,"poses":poses,"left":false}
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

func has_actor() -> bool:
	return bodies.has(active_actor)

func set_story(completed: Array, reveal_after: Dictionary) -> void:
	for id: String in bodies:
		# A switching role can represent a later reveal in the same location.
		bodies[id].body.visible = not reveal_after.has(id) or reveal_after[id] in completed

func cancel() -> void:
	route.clear()
	pending = ""
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
	var idle: Texture2D = person.poses.get(pose,person.idle)
	var sheet: Texture2D = person.sheet
	if not walking and idle:
		sprite.hframes = 1
		sprite.vframes = 1
		sprite.texture = idle
		sprite.frame = 0
	else:
		sprite.texture = sheet
		sprite.hframes = 4
		sprite.vframes = 2
		sprite.frame = int(phase) % 8 if walking else IDLE_FRAME
	var cell_height := sheet.get_height()/2.0
	if not walking and idle:
		cell_height = idle.get_height()
	sprite.scale = Vector2.ONE*height/cell_height
	sprite.flip_h = person.left
	sprite.position = Vector2(0,-height*.5)
	person.shadow.scale = Vector2(.37,.066)*height
	person.shadow.position = Vector2(-.012,-.008)*height

func on_floor(at: Vector2) -> bool:
	if Geometry2D.is_point_in_polygon(at,polygon):
		return true
	for i: int in polygon.size():
		if Geometry2D.get_closest_point_to_segment(at,polygon[i],polygon[(i+1)%polygon.size()]).distance_squared_to(at)<.16:
			return true
	return false

func clear_segment(a: Vector2, b: Vector2) -> bool:
	if a.distance_squared_to(b)<.16:
		return true
	var axis := b-a
	var crossings: Array[float] = [0.0,1.0]
	for i: int in polygon.size():
		var start := polygon[i]
		var finish := polygon[(i+1)%polygon.size()]
		var hit: Variant = Geometry2D.segment_intersects_segment(a,b,start,finish)
		if hit != null:
			crossings.append((Vector2(hit)-a).dot(axis)/axis.length_squared())
		# A collinear boundary can start or end partway along the candidate edge.
		for vertex: Vector2 in [start,finish]:
			var t := (vertex-a).dot(axis)/axis.length_squared()
			if t>0.0 and t<1.0 and (a+axis*t).distance_squared_to(vertex)<.16:
				crossings.append(t)
	crossings.sort()
	for i: int in range(1,crossings.size()):
		if not on_floor(a.lerp(b,(crossings[i-1]+crossings[i])*.5)):
			return false
	return true

func path_to(start: Vector2, finish: Vector2) -> PackedVector2Array:
	if not on_floor(finish):
		return PackedVector2Array()
	if clear_segment(start,finish):
		return PackedVector2Array([finish])
	var vertices := PackedVector2Array([start,finish])
	vertices.append_array(polygon)
	var graph := AStar2D.new()
	for i: int in vertices.size():
		graph.add_point(i,vertices[i])
		for j: int in range(i):
			if clear_segment(vertices[i],vertices[j]):
				graph.connect_points(i,j)
	var path := graph.get_point_path(0,1)
	if not path.is_empty():
		path.remove_at(0)
	return path

func walk_to(at: Vector2, task: String = "") -> bool:
	if not has_actor() or not bodies[active_actor].body.visible:
		return false
	var next := path_to(bodies[active_actor].body.position,at)
	if next.is_empty():
		return false
	if route.is_empty():
		phase = 0.0
	route = next
	pose_time = 0.0
	pending = task
	marker.position = at
	marker_alpha = 1.0
	marker.show()
	marker.queue_redraw()
	return true

func approach_task(id: String) -> bool:
	var target: Array = approach.get(id.get_slice(".",1),[])
	return target.size()==2 and walk_to(standing_spot(point(target)),id)

func standing_spot(at: Vector2) -> Vector2:
	var height := height_at(at)
	var alternatives: Array[Vector2] = [at,at+Vector2(height*.21,0),at-Vector2(height*.21,0),at+Vector2(0,height*.11),at-Vector2(0,height*.11)]
	for candidate: Vector2 in alternatives:
		if not on_floor(candidate):
			continue
		var occupied := false
		for id: String in bodies:
			if id==active_actor or not bodies[id].body.visible:
				continue
			var delta: Vector2 = (bodies[id].body.position-candidate).abs()
			if delta.x<height*.16 and delta.y<height*.075:
				occupied = true
				break
		if not occupied:
			return candidate
	return at

func finish_now(id: String) -> void:
	if has_actor() and approach.has(id.get_slice(".",1)):
		var body: Node2D = bodies[active_actor].body
		var target := standing_spot(point(approach[id.get_slice(".",1)]))
		cancel()
		if absf(body.position.x-target.x)>1.0:
			bodies[active_actor].left = target.x<body.position.x
		body.position = target
		face_object(id)
		draw_body(active_actor,false)

func face_object(id: String) -> void:
	var name_ := id.get_slice(".",1)
	if not object_marks.has(name_):
		return
	var body: Node2D = bodies[active_actor].body
	var offset := point(object_marks[name_]).x-body.position.x
	if absf(offset)>ART.x*.02:
		bodies[active_actor].left = offset<0.0

func draw_marker() -> void:
	var oval := PackedVector2Array()
	for i: int in 31:
		var a := TAU * i / 30.0
		oval.append(Vector2(cos(a)*11.0,sin(a)*4.0))
	marker.draw_polyline(oval,Color(.93,.82,.58,.69),1.7,true)

func step(delta: float, direction: Vector2) -> void:
	if not has_actor():
		return
	var person: Dictionary = bodies[active_actor]
	if pose_time>0.0 and direction==Vector2.ZERO:
		pose_time = maxf(0.0,pose_time-delta)
		if pose_time==0.0:
			var completed := pending
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
		pose_time = 0.0
		keyboard_walking = true
		marker.hide()
		var motion := direction.normalized()*Vector2(1.0,.62)*speed*delta
		var next := body.position + motion
		if on_floor(next) and clear_segment(body.position,next):
			route = PackedVector2Array([next])
		else:
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
		var pace := speed * lerpf(1.0,.62,absf(movement.normalized().y))
		var distance := minf(pace*time_left,movement.length())
		if absf(movement.x)>1.0:
			person.left = movement.x<0.0
		body.position = body.position.move_toward(route[0],distance)
		travelled += distance
		time_left -= distance/pace
		if body.position.distance_squared_to(route[0])<.01:
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
			face_object(pending)
			var pose := "listen" if pending.get_slice(".",1) in listen_tasks else "reach"
			if person.poses.has(pose):
				pose_time = .34
				draw_body(active_actor,false,pose)
			else:
				var id := pending
				pending = ""
				arrived.emit(id)

func snapshot() -> Dictionary:
	var result := {}
	for id: String in playable:
		if not bodies.has(id):
			continue
		var foot: Vector2 = bodies[id].body.position/ART
		result[id] = [foot.x,foot.y,bodies[id].left]
	return result

func restore(saved: Dictionary) -> void:
	for id: String in bodies:
		if saved.has(id) and on_floor(point(saved[id])):
			bodies[id].body.position = point(saved[id])
			bodies[id].left = saved[id][2]
			draw_body(id,false)

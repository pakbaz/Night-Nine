extends SceneTree

const FLOOR := preload("res://render/illustrated/exploration_floor.gd")
var checks := 0
var errors: Array[String] = []

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		errors.append(description)
		push_error(description)

func _initialize() -> void:
	var state := NightCampaign.new()
	var rooms: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/illustrated-floor.json"))
	var scenes := {}
	for s: Dictionary in state.content.scenes:
		scenes[s.id] = s
	for id: String in rooms:
		var layout: Dictionary = rooms[id]
		var stage := FLOOR.new()
		stage.configure_navigation(layout)
		check(stage.depth[0]<stage.depth[2] and stage.depth[1]<stage.depth[3],id+" valid perspective")
		var scene: Dictionary = scenes[id]
		for role: String in scene.actors:
			check(layout.spawn.has(role),id+" spawn for "+role)
		for role: String in layout.spawn:
			check(role in scene.actors,id+" registered investigator "+role)
			var start := stage.point(layout.spawn[role])
			check(stage.on_floor(start),id+" safe spawn for "+role)
			for task: Dictionary in scene.tasks:
				var key: String = str(task.id).get_slice(".",1)
				check(layout.approach.has(key),task.id+" staged approach")
				if not layout.approach.has(key):
					continue
				var end := stage.point(layout.approach[key])
				var route := stage.path_to(start,end)
				check(not route.is_empty(),task.id+" reachable by "+role)
				var last := start
				for next: Vector2 in route:
					check(stage.clear_segment(last,next),task.id+" route inside painted floor")
					last = next
				if not route.is_empty():
					check(last.distance_to(end)<.1,task.id+" reaches the marked object")
				if layout.has("landmarks"):
					check(layout.landmarks.get(key,[]).size()==4,task.id+" has a wide painting hitbox")
		stage.free()
	var bent := FLOOR.new()
	bent.polygon = PackedVector2Array([Vector2(0,0),Vector2(150,0),Vector2(150,35),Vector2(35,35),Vector2(35,150),Vector2(0,150)])
	check(not bent.clear_segment(Vector2(130,20),Vector2(20,130)),"Avoid a concave corner")
	check(bent.path_to(Vector2(130,20),Vector2(20,130)).size()>1,"Route around the occluding corner")
	check(bent.path_to(Vector2(20,20),Vector2(110,110)).is_empty(),"Ignore clicks on scenery")
	bent.free()
	var legacy := state.data.duplicate(true)
	legacy.erase("walk_positions")
	check(state.restore(legacy) and state.data.walk_positions.is_empty(),"Read an existing save without foot positions")
	var corrupt := state.data.duplicate(true)
	corrupt.walk_positions = {"archivist":[1.5,.4,false]}
	check(not state.validate(corrupt).is_empty(),"Reject an offscreen saved position")
	corrupt.walk_positions = {"archivist":[.5,.4,false,"upside-down"]}
	check(not state.validate(corrupt).is_empty(),"Reject an unknown saved facing")
	print("Floor checks: ",checks,"; authored rooms: ",rooms.size(),"; failures: ",errors.size())
	quit(0 if errors.is_empty() else 1)

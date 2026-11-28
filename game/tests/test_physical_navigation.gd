extends SceneTree

const FLOOR := preload("res://render/illustrated/exploration_floor.gd")
const STAGE := preload("res://render/illustrated/campaign_room.gd")
const ART := Vector2(1600,900)
var checks := 0
var failures: Array[String] = []
var last_arrival := ""
var coverage := {}
var movement_trace := {}

func check(ok: bool, description: String) -> void:
	checks+=1
	if not ok:
		failures.append(description)
		push_error(description)

func _initialize() -> void:
	run.call_deferred()

func run() -> void:
	var fixture := {
		"polygon":[[.04,.08],[.96,.08],[.96,.94],[.04,.94]], "depth":[.08,.32,.94,.32],
		"spawn":{"steve":[.18,.51],"stephen":[.44,.77]}, "approach":{"lever":[.64,.52],"far":[.85,.5]},
		"blockers":[{"id":"table","polygon":[[.38,.40],[.55,.40],[.55,.62],[.38,.62]]},
			{"id":"door","polygon":[[.71,.05],[.725,.05],[.725,.96],[.71,.96]],"opens_after":"test.lever"}]}
	var floor_stage := FLOOR.new()
	root.add_child(floor_stage)
	floor_stage.room_id="test"
	var plate := PlaceholderTexture2D.new()
	plate.size=ART
	floor_stage.configure(fixture,["steve","stephen"],plate,"res://missing-field-art.webp",Color.WHITE)
	floor_stage.select_actor("steve")
	var body: Node2D=floor_stage.bodies.steve.body
	var other: Node2D=floor_stage.bodies.stephen.body
	var start:=body.position
	var end := floor_stage.point([.62,.50])
	check(not floor_stage.clear_segment(start,end),"A straight click crosses the tabletop")
	var route := floor_stage.path_to(start,end)
	check(route.size()>=2,"Click navigation bends around the solid table")
	var last:=start
	for part: Vector2 in route:
		check(floor_stage.clear_segment(last,part),"The whole routed segment clears the table with room for the feet")
		last=part
	check(not floor_stage.on_floor(floor_stage.point([.38,.49])-Vector2(6,0)),"Shoe clearance extends beyond the painted edge")
	check(floor_stage.walk_to(floor_stage.point([.383,.49])),"Clicking just inside furniture finds an accessible edge")
	check(floor_stage.route[-1].x<.38*ART.x,"The marker stops in front of the near table edge")
	floor_stage.cancel()
	check(not floor_stage.walk_to(floor_stage.point([.85,.5])),"A closed door prevents a route into the far room")
	check(not floor_stage.finish_now("test.far") and body.position==start,"Keyboard evidence access also respects the closed door")
	floor_stage.step(6.0,Vector2.RIGHT)
	check(body.position.x<.38*ART.x and body.position.x>start.x+100,"A long WASD frame reaches the table without tunneling")
	var before:=body.position
	floor_stage.step(.55,Vector2(1,.48))
	check(body.position.y>before.y+10 and body.position.x<.38*ART.x,"WASD slides along the table edge")
	body.position=floor_stage.point([.20,.77])
	var beyond:=floor_stage.point([.64,.77])
	check(not floor_stage.clear_segment(body.position,beyond),"Another character occupies real personal space")
	check(floor_stage.walk_to(beyond) and floor_stage.route.size()>1,"Clicks route around a standing companion")
	other.position=floor_stage.point([.52,.73])
	var min_gap:=INF
	for frame: int in 300:
		floor_stage.step(.024,Vector2.ZERO)
		min_gap=minf(min_gap,((body.position-other.position)*floor_stage.navigation.FLATTEN).length())
		if floor_stage.route.is_empty():
			break
	check(body.position.distance_to(beyond)<.5 and min_gap>=floor_stage.navigation.radius(other.position)*3.3,
		"A moving companion triggers replanning with shoe clearance throughout")
	check(floor_stage.walk_to_person("stephen","test.hello"),"A character interaction finds a reachable nearby stance")
	for tick: int in 300:
		if floor_stage.route.is_empty():
			break
		floor_stage.step(.08,Vector2.ZERO)
	check(floor_stage.route.is_empty() and body.position.distance_to(other.position)>35 and floor_stage.bodies.steve.left==(body.position.x>other.position.x),
		"The investigators face each other across a speaking distance")
	floor_stage.set_story(["test.lever"],{})
	check(floor_stage.finish_now("test.far") and body.position.x>.725*ART.x,"After the registered event, direct access can pass the opened door")
	floor_stage.set_story([],{})
	floor_stage.restore({"steve":[.45,.50,true]})
	check(floor_stage.on_floor(body.position) and not Geometry2D.is_point_in_polygon(body.position,floor_stage.points(fixture.blockers[0].polygon)),
		"An older save inside newly solid furniture returns to accessible ground")
	floor_stage.restore({"steve":[.85,.5,false]})
	check(body.position.x<.71*ART.x,"An old save beyond a newly closed threshold resumes on the reachable side")
	floor_stage.restore({"steve":[.18,.70,false]})
	floor_stage.step(.23,Vector2.UP)
	floor_stage.step(.01,Vector2.ZERO)
	var sheet: Sprite2D=floor_stage.bodies.steve.sprite
	check(sheet.texture.resource_path.ends_with("steve-away.webp") and sheet.hframes==4 and not sheet.flip_h,
		"Depth travel retains an unmirrored away stance when the investigator stops")
	var saved := floor_stage.snapshot()
	floor_stage.step(.23,Vector2.DOWN)
	check(sheet.texture.resource_path.ends_with("steve-toward.webp"),"Moving toward the camera selects its own painted cycle")
	floor_stage.restore(saved)
	check(sheet.texture.resource_path.ends_with("steve-away.webp") and sheet.frame==1,"Saving and restoring retains the depth-facing stance")
	var rooms: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/illustrated-floor.json"))
	var campaign := NightCampaign.new()
	var n_solids:=0
	var n_doors:=0
	for id: String in rooms:
		var layout: Dictionary=rooms[id]
		var isolated:=FLOOR.new()
		isolated.configure_navigation(layout)
		for solid: Dictionary in layout.get("blockers",[]):
			n_solids+=1
			if solid.has("after"):
				check(campaign.task_index.has(solid.after),"Registered story event exists for "+str(solid.id))
			if not solid.has("opens_after"):
				continue
			n_doors+=1
			check(campaign.task_index.has(solid.opens_after),"Registered story event exists for "+str(solid.id))
			check_door(isolated,layout,solid,id)
		isolated.free()
	floor_stage.free()
	verify_props(rooms)
	verify_ship_attendant(rooms.c2_ship)
	verify_gallery_aisle(rooms.i2_nora)
	verify_campaign(campaign,rooms)
	var result := {"rooms":coverage,"movement_trace":movement_trace,"registered_blockers":n_solids,
		"story_gates":n_doors,"checks":checks,"failures":failures}
	var destination := OS.get_environment("NIGHT_NINE_QA_DIR")
	if not destination.is_empty():
		DirAccess.make_dir_recursive_absolute(destination)
		var output := FileAccess.open(destination.path_join("physical-navigation.json"),FileAccess.WRITE)
		output.store_string(JSON.stringify(result,"\t")+"\n")
		output.close()
	print("Physical navigation: ",checks," checks, ",n_solids," registered blockers, ",n_doors," story doors, ",failures.size()," failures.")
	quit(0 if failures.is_empty() else 1)

## Painted furniture is solid where it meets the floor, and nobody stands in front of a
## prop at a depth where the occluder would still paint the prop over them.
const PROP_SOLID := {
	"c2_ship":[[.50,.74],[.46,.745],[.545,.74]],
	"c4_safe":[[.19,.89]],
	"c7_gate":[[.615,.66],[.60,.635]],
	"c10_report":[[.83,.79]],
	"epilogue":[[.93,.86],[.10,.85]],
	"c8_lab":[[.07,.92],[.935,.90]],
}
const PROP_CLEAR := {
	"c2_ship":[[.56,.79],[.62,.76]],
	"c4_safe":[[.20,.915]],
	"c7_gate":[[.66,.67]],
	"c10_report":[[.82,.855]],
	"epilogue":[[.83,.74]],
	"c8_lab":[[.12,.90],[.90,.90]],
}

func verify_props(rooms: Dictionary) -> void:
	for id: String in rooms:
		var layout: Dictionary=rooms[id]
		var isolated := FLOOR.new()
		isolated.configure_navigation(layout)
		isolated.sync_navigation()
		for spot: Array in PROP_SOLID.get(id,[]):
			check(not isolated.on_floor(isolated.point(spot)),id+" keeps feet off the painted prop at "+str(spot))
		for spot: Array in PROP_CLEAR.get(id,[]):
			check(isolated.on_floor(isolated.point(spot)),id+" leaves open floor at "+str(spot))
		var marks: Dictionary=layout.spawn.duplicate()
		marks.merge(layout.get("residents",{}))
		marks.merge(layout.get("approach",{}))
		for mark: String in marks:
			var at: Vector2=isolated.point(marks[mark])
			check(isolated.navigation.closest(at).distance_to(at)<14.0,id+" authors "+mark+" on open floor, not inside a prop")
		isolated.free()

## Once Steve is out of the chair the attendant argues at the speaker column, so Steve
## creeps along the front of the room instead of walking through or behind them.
func verify_ship_attendant(layout: Dictionary) -> void:
	var isolated := FLOOR.new()
	isolated.configure_navigation(layout)
	var spot: Vector2 = isolated.point([.51,.79])
	isolated.update_solids(["c2_ship.command"])
	isolated.sync_navigation()
	check(isolated.on_floor(spot),"c2_ship leaves the floor by the column open while the attendant is at the chair")
	isolated.update_solids(["c2_ship.command","c2_ship.escape"])
	isolated.sync_navigation()
	check(not isolated.on_floor(spot),"c2_ship keeps Steve out of the attendant arguing at the column")
	check(not isolated.on_floor(isolated.point([.51,.775])),"c2_ship leaves no gap between the attendant and the column")
	var chair: Vector2 = isolated.point(layout.approach.escape)
	for mark: String in ["nora","intake"]:
		check(not isolated.navigation.path(chair,isolated.point(layout.approach[mark])).is_empty(),
			"c2_ship lets Steve creep from the chair to the "+mark+" past the attendant")
	var hatch: Array = layout.approach.intake
	check(hatch[0] < .40 and hatch[1] > .88,"c2_ship puts the intake hatch in the floor in front of Nora's capsule")
	isolated.free()

## Until Nora has timed the guard, the open aisle past the pods is in his sight, so
## she stays on the pod side; once he is through the far door the pump side opens.
func verify_gallery_aisle(layout: Dictionary) -> void:
	var isolated := FLOOR.new()
	isolated.configure_navigation(layout)
	var pods: Vector2 = isolated.point(layout.spawn.nora)
	isolated.update_solids([])
	isolated.sync_navigation()
	check(not isolated.navigation.path(pods,isolated.point(layout.approach.patrol)).is_empty(),"i2_nora lets Nora reach the corridor to time the guard")
	for mark: String in ["pump","message"]:
		check(isolated.navigation.path(pods,isolated.point(layout.approach[mark])).is_empty(),
			"i2_nora keeps Nora on the pod side of the aisle before she has timed the guard ("+mark+")")
	isolated.update_solids(["i2_nora.patrol"])
	isolated.sync_navigation()
	for mark: String in ["pump","message"]:
		check(not isolated.navigation.path(pods,isolated.point(layout.approach[mark])).is_empty(),
			"i2_nora opens the aisle once the guard is through the far door ("+mark+")")
	isolated.free()

func check_door(floor_stage: Node2D, layout: Dictionary, door: Dictionary, room: String) -> void:
	var outline: PackedVector2Array=floor_stage.points(door.polygon)
	var box := Rect2(outline[0],Vector2.ZERO)
	for vertex: Vector2 in outline:
		box=box.expand(vertex)
	box=box.grow(18.0)
	floor_stage.update_solids([])
	floor_stage.sync_navigation()
	var closed_points := PackedVector2Array()
	for ix: int in 17:
		for iy: int in 17:
			var spot := box.position+box.size*Vector2(ix,iy)/16.0
			if not floor_stage.navigation.contains(spot):
				closed_points.append(spot)
	floor_stage.update_solids([door.opens_after])
	floor_stage.sync_navigation()
	var entry: Vector2=floor_stage.point(layout.spawn.values()[0])
	var newly_reachable := false
	for spot: Vector2 in closed_points:
		if not floor_stage.navigation.path(entry,spot).is_empty():
			newly_reachable=true
			break
	check(newly_reachable,room+" opens reachable painted ground at "+str(door.id))

func verify_campaign(campaign: NightCampaign, layouts: Dictionary) -> void:
	var before_scene: Array = []
	for scene: Dictionary in campaign.content.scenes:
		if layouts.has(scene.id):
			var stage := STAGE.new()
			root.add_child(stage)
			stage.build(scene,"high")
			check(stage.floor_stage!=null,scene.id+" has its imported exploration painting and floor")
			if stage.floor_stage==null:
				stage.free()
				continue
			if scene.id=="c6_jail":
				verify_jail_staging(stage)
			stage.approach_finished.connect(func(id: String): last_arrival=id)
			# An object the story brings in later (the sound truck at the gate) has no marker until then.
			for i: int in scene.tasks.size():
				var waits: String = str(stage.directions.get("hotspot_after",{}).get(str(scene.tasks[i].id).get_slice(".",1),""))
				if waits.is_empty():
					continue
				stage.sync_story(before_scene)
				check(not stage.hotspot_in_view(i),str(scene.tasks[i].id)+" has no marker before "+waits)
				stage.sync_story(before_scene+[waits])
				check(stage.hotspot_in_view(i),str(scene.tasks[i].id)+" is marked once "+waits+" is done")
			var room_results := {}
			var room_trace := {}
			for id: String in scene.actors:
				stage.select_walker(id)
				var completed := before_scene.duplicate()
				stage.sync_story(completed)
				var floor_stage: Node2D=stage.floor_stage
				var reached: Array = []
				var actor_trace := {}
				for i: int in scene.tasks.size():
					var task: Dictionary=scene.tasks[i]
					var label := str(task.id)+" via "+id
					if stage.in_transit():
						check(stage.hotspot_in_view(i) and stage.frame.get_global_rect().has_point(stage.project_target(i)),
							label+" can be selected aboard the moving vehicle")
						check(not stage.walk_task(task.id) and not floor_stage.visible,label+" cannot walk back into the bay")
						reached.append(task.id)
						completed.append(task.id)
						stage.sync_story(completed)
						continue
					# A walker the story keeps out of sight (Steve under the sound desk at the
					# gate) cannot walk until the story brings them out.
					if not floor_stage.bodies[id].body.visible:
						check(not stage.walk_task(task.id),label+" cannot walk while "+id+" is out of sight")
						reached.append(task.id)
						completed.append(task.id)
						stage.sync_story(completed)
						continue
					# While a story layer holds the lead in place (Steve strapped into the
					# scan chair), objects open directly and nobody walks.
					if not stage.walking_view() and stage.active_layers().any(func(layer: Dictionary): return not layer.get("walking",true)):
						check(not stage.walk_task(task.id),label+" opens without walking while "+id+" is held in place")
						reached.append(task.id)
						completed.append(task.id)
						stage.sync_story(completed)
						continue
					check(stage.walking_view() and floor_stage.visible,label+" visible walking floor for "+id)
					check(stage.frame.get_global_rect().has_point(stage.project_target(i)),label+" target in camera")
					last_arrival=""
					var started := stage.walk_task(task.id)
					check(started,label+" registers a physical route")
					var route_clear := true
					var route_start: Vector2=floor_stage.bodies[id].body.position
					for waypoint: Vector2 in floor_stage.route:
						route_clear=route_clear and floor_stage.clear_segment(route_start,waypoint)
						route_start=waypoint
					check(route_clear,label+" planned segments clear props and standing characters")
					var on_ground := true
					var acted := false
					var min_peer_margin := INF
					var trace: Array = []
					var initial_foot: Vector2=floor_stage.bodies[id].body.position
					trace.append([roundf(initial_foot.x/ART.x*10000.0)/10000.0,
						roundf(initial_foot.y/ART.y*10000.0)/10000.0])
					for frame: int in 650:
						if not stage.is_walking():
							break
						stage.tick_walk(.025,Vector2.ZERO)
						var foot: Vector2=floor_stage.bodies[id].body.position
						on_ground=on_ground and floor_stage.on_floor(foot)
						for peer: String in floor_stage.bodies:
							if peer==id or not floor_stage.bodies[peer].body.visible:
								continue
							var peer_foot: Vector2=floor_stage.bodies[peer].body.position
							var gap: float=((foot-peer_foot)*floor_stage.navigation.FLATTEN).length()
							min_peer_margin=minf(min_peer_margin,gap-floor_stage.navigation.radius(peer_foot)*3.3)
						trace.append([roundf(foot.x/ART.x*10000.0)/10000.0,
							roundf(foot.y/ART.y*10000.0)/10000.0])
						acted=acted or not floor_stage.performance_action.is_empty()
					check(on_ground,label+" feet clear solids and other people throughout")
					if min_peer_margin<INF:
						check(min_peer_margin>=-.5,label+" keeps personal space from every standing character")
					check(acted and last_arrival==task.id,label+" action and arrival callback")
					actor_trace[task.id]={"frames":trace.size()-1,"points":trace,
						"route_clear":route_clear,
						"minimum_peer_margin":min_peer_margin if min_peer_margin<INF else -1.0}
					if scene.id=="c8_beach":
						var guest: Dictionary=floor_stage.bodies.get("saren",{})
						var lead: Dictionary=floor_stage.bodies[id]
						check(not guest.is_empty() and guest.body.visible and guest.sprite.texture.resource_path.ends_with("saren-idle.webp")
							and floor_stage.speaking_partner=="saren" and lead.left!=guest.left
							and absf(guest.body.position.x-lead.body.position.x)>.12*floor_stage.height_at(guest.body.position),
							label+" finishes facing the standing Prefect across a speaking distance")
					if last_arrival==task.id:
						reached.append(task.id)
					stage.set_focus(i)
					check(not floor_stage.visible,label+" shows the evidence painting")
					completed.append(task.id)
					stage.sync_story(completed)
					stage.set_focus(-1)
					if stage.in_transit():
						check(stage.illustration_insert.is_visible_in_tree() and not floor_stage.visible,label+" boards the vehicle")
					elif stage.active_layers().any(func(layer: Dictionary): return not layer.get("walking",true)):
						check(not stage.walking_view() and not floor_stage.visible,label+" leaves the room with "+id+" held by the story")
					else:
						check(floor_stage.visible,label+" returns to exploration")
				room_results[id]=reached
				room_trace[id]=actor_trace
			stage.free()
			coverage[scene.id]=room_results
			movement_trace[scene.id]=room_trace
		for task: Dictionary in scene.tasks:
			before_scene.append(task.id)

func verify_jail_staging(stage: STAGE) -> void:
	var floor_stage: Node2D=stage.floor_stage
	var cell: Vector2=floor_stage.point(floor_stage.approach.crossword)
	check(floor_stage.point(floor_stage.object_marks.crossword).x-cell.x>floor_stage.height_at(cell)*.15,
		"Steve can look into the cell from beside the door and leave the central bars visible")
	check(not floor_stage.bodies.has("stephen"),"Steve visits the Sheriff's office alone")
	var dog: Node2D=stage.floor_creatures.biscuit
	var sprite: Sprite2D=dog.get_child(0)
	var animal_height := sprite.scale.y*sprite.texture.get_height()
	check(dog.get_parent()==floor_stage.cast and dog.visible and not stage.creatures.biscuit.visible,
		"Biscuit shares the investigators' depth sorting on the wide painting")
	check(animal_height<floor_stage.height_at(dog.position)*.40 and not floor_stage.on_floor(dog.position),
		"Biscuit sits at a dog's scale with an occupied spot on the jail floor")
	stage.set_focus(0)
	check(not dog.visible and stage.creatures.biscuit.visible,"The detail painting keeps the close-up of Biscuit")
	stage.set_focus(-1)

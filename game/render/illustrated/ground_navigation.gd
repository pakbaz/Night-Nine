extends RefCounted
## Bake the silhouettes at shoe level in ground coordinates. The y stretch turns a
## perspective ellipse into a circle for collision margins and personal space.
const FLATTEN := Vector2(1.0, 2.65)
const METRIC_EPSILON := .28
const RING_POINTS := 12
var footprint_depth: Array = []
var mesh: NavigationPolygon
var graph := AStar2D.new()
var faces: Array[PackedVector2Array] = []
var bounds: Array[Rect2] = []
var portals := {}
var edges: Array[PackedVector2Array] = []
var floor_outline := PackedVector2Array()

func radius(at: Vector2) -> float:
	if footprint_depth.size()!=4:
		return 0.0
	var t := clampf(inverse_lerp(footprint_depth[0],footprint_depth[2],at.y/900.0),0.0,1.0)
	return clampf(lerpf(footprint_depth[1],footprint_depth[3],t)*900.0*.05,4.0,30.0)

func circle(center: Vector2, width: float) -> PackedVector2Array:
	var ring := PackedVector2Array()
	for i: int in RING_POINTS:
		ring.append(center*FLATTEN + Vector2.from_angle(float(i)*TAU/RING_POINTS)*width)
	return ring

func metric(points: PackedVector2Array) -> PackedVector2Array:
	var transformed := PackedVector2Array()
	for p: Vector2 in points:
		transformed.append(p*FLATTEN)
	return transformed

func add_edge_clearance(source: NavigationMeshSourceGeometryData2D, line: PackedVector2Array) -> void:
	if footprint_depth.size()!=4:
		return
	for i: int in line.size():
		var a := line[i]
		var b := line[(i+1)%line.size()]
		var caps := circle(a,radius(a))
		caps.append_array(circle(b,radius(b)))
		var hull := Geometry2D.convex_hull(caps)
		hull.resize(hull.size()-1)
		source.add_obstruction_outline(hull)

func bake(outline: PackedVector2Array, depth: Array, solids: Array, people: PackedVector2Array) -> void:
	floor_outline = outline
	footprint_depth = depth
	var source := NavigationMeshSourceGeometryData2D.new()
	source.add_traversable_outline(metric(outline))
	add_edge_clearance(source,outline)
	for solid: PackedVector2Array in solids:
		source.add_obstruction_outline(metric(solid))
		add_edge_clearance(source,solid)
	for foot: Vector2 in people:
		# Allow for two stances, including the shoulders of a nearby companion.
		source.add_obstruction_outline(circle(foot,radius(foot)*3.5))
	mesh = NavigationPolygon.new()
	mesh.agent_radius = 0.0
	NavigationServer2D.bake_from_source_geometry_data(mesh,source)
	edges.clear()
	faces.clear()
	bounds.clear()
	portals.clear()
	graph.clear()
	var vertices := mesh.vertices
	var owners := {}
	for i: int in mesh.get_polygon_count():
		var indices := mesh.get_polygon(i)
		var face := PackedVector2Array()
		var center := Vector2.ZERO
		var box := Rect2(vertices[indices[0]],Vector2.ZERO)
		for j: int in indices.size():
			var a := indices[j]
			var b := indices[(j+1)%indices.size()]
			face.append(vertices[a])
			center += vertices[a]
			box = box.expand(vertices[a])
			var key := Vector2i(mini(a,b),maxi(a,b))
			if not owners.has(key):
				owners[key] = []
			owners[key].append(i)
		faces.append(face)
		bounds.append(box.grow(METRIC_EPSILON))
		graph.add_point(i,center/indices.size())
	for key: Vector2i in owners:
		var edge := PackedVector2Array([vertices[key.x],vertices[key.y]])
		var adjoining: Array = owners[key]
		if adjoining.size()==1:
			edges.append(edge)
		elif adjoining.size()==2:
			var a: int = adjoining[0]
			var b: int = adjoining[1]
			graph.connect_points(a,b)
			var heading := graph.get_point_position(b)-graph.get_point_position(a)
			if heading.cross(edge[0]-edge[1])<0.0:
				edge.reverse()
			portals[Vector2i(a,b)] = edge
			portals[Vector2i(b,a)] = PackedVector2Array([edge[1],edge[0]])

func containing_face(p: Vector2) -> int:
	for i: int in faces.size():
		if not bounds[i].has_point(p):
			continue
		if Geometry2D.is_point_in_polygon(p,faces[i]):
			return i
		# A clipped portal or edge can be rounded by a few hundredths of a pixel.
		for j: int in faces[i].size():
			var a := faces[i][j]
			var b := faces[i][(j+1)%faces[i].size()]
			if Geometry2D.get_closest_point_to_segment(p,a,b).distance_squared_to(p)<.0004:
				return i
	return -1

func closest(art: Vector2) -> Vector2:
	var p := art*FLATTEN
	if containing_face(p)>=0:
		return art
	var nearest := Vector2.INF
	var best := INF
	for edge: PackedVector2Array in edges:
		var candidate := Geometry2D.get_closest_point_to_segment(p,edge[0],edge[1])
		var distance := p.distance_squared_to(candidate)
		if distance<best:
			best = distance
			nearest = candidate
	return nearest/FLATTEN

func contains(art: Vector2) -> bool:
	return containing_face(art*FLATTEN)>=0

func clear(a: Vector2, b: Vector2) -> bool:
	if not contains(a) or not contains(b):
		return false
	var start := a*FLATTEN
	var finish := b*FLATTEN
	var delta := finish-start
	var length_sq := delta.length_squared()
	if length_sq < METRIC_EPSILON*METRIC_EPSILON:
		return true
	var crossings: Array[float] = [0.0,1.0]
	for edge: PackedVector2Array in edges:
		var hit: Variant = Geometry2D.segment_intersects_segment(start,finish,edge[0],edge[1])
		if hit != null:
			crossings.append(clampf((Vector2(hit)-start).dot(delta)/length_sq,0.0,1.0))
	crossings.sort()
	for i: int in range(1,crossings.size()):
		if not contains(a.lerp(b,(crossings[i-1]+crossings[i])*.5)):
			return false
	return true

func path(a: Vector2, b: Vector2) -> PackedVector2Array:
	if not contains(a) or not contains(b):
		return PackedVector2Array()
	if clear(a,b):
		return PackedVector2Array([b])
	var ids := graph.get_id_path(containing_face(a*FLATTEN),containing_face(b*FLATTEN))
	if ids.is_empty():
		return PackedVector2Array()
	var gates: Array[PackedVector2Array] = []
	for i: int in range(1,ids.size()):
		gates.append(portals[Vector2i(ids[i-1],ids[i])])
	gates.append(PackedVector2Array([b*FLATTEN,b*FLATTEN]))
	var route := funnel(a*FLATTEN,gates)
	if route.is_empty():
		return portal_path(a,gates)
	var previous := a
	for step: Vector2 in route:
		if not clear(previous,step):
			# Collinear portals can collapse onto the same point. The centres of
			# successive portals always lie inside the same convex face.
			return portal_path(a,gates)
		previous = step
	return route

func funnel(apex: Vector2, gates: Array[PackedVector2Array]) -> PackedVector2Array:
	var result := PackedVector2Array()
	var left := apex
	var right := apex
	var li := 0
	var ri := 0
	var i := 0
	var iterations := 0
	while i<gates.size():
		iterations+=1
		if iterations>gates.size()*gates.size()+2:
			return PackedVector2Array()
		var l := gates[i][0]
		var r := gates[i][1]
		if (right-apex).cross(r-apex)>=0.0:
			if right.is_equal_approx(apex) or (left-apex).cross(r-apex)<0.0:
				right=r
				ri=i
			else:
				result.append(left/FLATTEN)
				apex=left
				right=apex
				i=li+1
				continue
		if (left-apex).cross(l-apex)<=0.0:
			if left.is_equal_approx(apex) or (right-apex).cross(l-apex)>0.0:
				left=l
				li=i
			else:
				result.append(right/FLATTEN)
				apex=right
				left=apex
				i=ri+1
				continue
		i+=1
	var end := gates[-1][0]/FLATTEN
	if result.is_empty() or not result[-1].is_equal_approx(end):
		result.append(end)
	return result

func portal_path(a: Vector2, gates: Array[PackedVector2Array]) -> PackedVector2Array:
	var stops := PackedVector2Array()
	for gate: PackedVector2Array in gates:
		stops.append((gate[0]+gate[1])*.5/FLATTEN)
	var result := PackedVector2Array()
	var start := a
	var i := 0
	while i<stops.size():
		var j := stops.size()-1
		while j>i and not clear(start,stops[j]):
			j-=1
		if not clear(start,stops[j]):
			return PackedVector2Array()
		start=stops[j]
		result.append(start)
		i=j+1
	return result

func nearby_path(from: Vector2, desired: Vector2, tolerance: float) -> PackedVector2Array:
	var nearest := closest(desired)
	if not nearest.is_finite() or nearest.distance_to(desired)>tolerance:
		return PackedVector2Array()
	var first := path(from,nearest)
	if not first.is_empty() or contains(desired):
		return first
	# At a blocked click, the closest boundary may belong to the far side of
	# a closed threshold. Try only nearby pieces physically reachable from here.
	var candidates: Array[Vector2] = []
	for edge: PackedVector2Array in edges:
		var foot := Geometry2D.get_closest_point_to_segment(desired*FLATTEN,edge[0],edge[1])/FLATTEN
		if foot.distance_to(desired)<=tolerance:
			candidates.append(foot)
	candidates.sort_custom(func(a: Vector2,b: Vector2): return desired.distance_squared_to(a)<desired.distance_squared_to(b))
	for candidate: Vector2 in candidates:
		var alternative := path(from,candidate)
		if not alternative.is_empty():
			return alternative
	return PackedVector2Array()

func safe_fraction(from: Vector2, motion: Vector2) -> float:
	if clear(from,from+motion):
		return 1.0
	var low := 0.0
	var high := 1.0
	for i: int in 13:
		var middle := (low+high)*.5
		if clear(from,from+motion*middle):
			low = middle
		else:
			high = middle
	return low

func slide(from: Vector2, motion: Vector2) -> PackedVector2Array:
	var part := safe_fraction(from,motion)
	var contact := from + motion*part
	var result := PackedVector2Array()
	if contact.distance_squared_to(from)>.0025:
		result.append(contact)
	if part>=1.0:
		return result
	var remainder := (1.0-part)*motion*FLATTEN
	var best := contact
	var best_progress := 0.0
	for edge: PackedVector2Array in edges:
		var near := Geometry2D.get_closest_point_to_segment(contact*FLATTEN,edge[0],edge[1])
		if near.distance_to(contact*FLATTEN)>2.0:
			continue
		var tangent := (edge[1]-edge[0]).normalized()
		var along := (tangent*tangent.dot(remainder))/FLATTEN
		var candidate := contact + along*safe_fraction(contact,along)
		var progress := (candidate-contact).dot(motion.normalized())
		if progress>best_progress:
			best = candidate
			best_progress = progress
	if best.distance_squared_to(contact)>.0025:
		result.append(best)
	return result

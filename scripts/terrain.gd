extends Node3D

const Sites := preload("res://scripts/sites.gd")
const Air := preload("res://scripts/air.gd")

const SIZE := 2816.0
const CELL := 2.0
const N := 1408
const HALF := SIZE / 2.0
const DIR := "res://assets/gen/terrain/"
const TEX := "res://assets/gen/tex/"
const BUCKET := 32.0

static var heights := PackedFloat32Array()
static var meta := {}
static var track := PackedVector3Array()
static var track_at := PackedFloat32Array()
static var river := PackedVector3Array()
static var height_tex: ImageTexture
static var _track_buckets := {}

var near_mesh: MeshInstance3D
var mid_mesh: MeshInstance3D
var far_mesh: MeshInstance3D
var near_mat: ShaderMaterial
var far_mat: ShaderMaterial
var hide_all := false


static func load_data() -> void:
	if not heights.is_empty():
		return
	var bytes := FileAccess.get_file_as_bytes(DIR + "height.bin")
	heights = bytes.to_float32_array()
	height_tex = ImageTexture.create_from_image(Image.create_from_data(N + 1, N + 1, false, Image.FORMAT_RF, bytes))
	meta = JSON.parse_string(FileAccess.get_file_as_string(DIR + "meta.json"))
	track = _points(FileAccess.get_file_as_bytes(DIR + "track.bin").to_float32_array())
	river = _points(FileAccess.get_file_as_bytes(DIR + "river.bin").to_float32_array())
	track_at.resize(track.size())
	var run := 0.0
	for i in track.size():
		if i > 0:
			run += Vector2(track[i].x - track[i - 1].x, track[i].z - track[i - 1].z).length()
		track_at[i] = run
		var key := Vector2i(floori(track[i].x / BUCKET), floori(track[i].z / BUCKET))
		var bucket: PackedInt32Array = _track_buckets.get(key, PackedInt32Array())
		bucket.append(i)
		_track_buckets[key] = bucket


static func _points(f: PackedFloat32Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	out.resize(f.size() / 3)
	for i in out.size():
		out[i] = Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2])
	return out


static func height(x: float, z: float) -> float:
	var fx := clampf((x + HALF) / CELL, 0.0, N - 0.001)
	var fz := clampf((z + HALF) / CELL, 0.0, N - 0.001)
	var i := int(fx)
	var j := int(fz)
	var tx := fx - i
	var tz := fz - j
	var n := N + 1
	var a := lerpf(heights[j * n + i], heights[j * n + i + 1], tx)
	var b := lerpf(heights[(j + 1) * n + i], heights[(j + 1) * n + i + 1], tx)
	return lerpf(a, b, tz)


static func on_ground(p: Vector2, lift := 0.0) -> Vector3:
	return Vector3(p.x, height(p.x, p.y) + lift, p.y)


static func normal(x: float, z: float) -> Vector3:
	var e := CELL
	return Vector3(height(x - e, z) - height(x + e, z), 2.0 * e, height(x, z - e) - height(x, z + e)).normalized()


static func track_index(x: float, z: float) -> int:
	var key := Vector2i(floori(x / BUCKET), floori(z / BUCKET))
	var best := -1
	var best_d := 1e12
	for dj in range(-2, 3):
		for di in range(-2, 3):
			var k := key + Vector2i(di, dj)
			if not _track_buckets.has(k):
				continue
			for i: int in _track_buckets[k]:
				var d := (track[i].x - x) * (track[i].x - x) + (track[i].z - z) * (track[i].z - z)
				if d < best_d:
					best_d = d
					best = i
	return best


static func track_distance(x: float, z: float) -> float:
	var i := track_index(x, z)
	if i < 0:
		return 9999.0
	return Vector2(track[i].x - x, track[i].z - z).length()


static func track_point(meters: float) -> Vector3:
	var i := track_at.bsearch(clampf(meters, 0.0, track_at[track_at.size() - 1]))
	return track[mini(i, track.size() - 1)]


static func track_length() -> float:
	return track_at[track_at.size() - 1]


static func track_meters_near(x: float, z: float) -> float:
	var best := 0
	var best_d := 1e12
	for i in track.size():
		var d := (track[i].x - x) * (track[i].x - x) + (track[i].z - z) * (track[i].z - z)
		if d < best_d:
			best_d = d
			best = i
	return track_at[best]


static func water_level(x: float, z: float) -> float:
	var level := -INF
	var ponds: Array = meta.get("foot_water", [])
	for i in mini(Sites.FOOTPRINTS.size(), ponds.size()):
		var f: Array = Sites.FOOTPRINTS[i]
		var rel := (Vector2(x, z) - (f[0] as Vector2)).rotated(f[1])
		if Vector2(rel.x / (Sites.FOOT_WIDTH * 0.62), rel.y / (Sites.FOOT_LENGTH * 0.62)).length() < 1.0:
			level = maxf(level, ponds[i])
	var best := 72.25
	for p in river:
		var d := (p.x - x) * (p.x - x) + (p.z - z) * (p.z - z)
		if d < best:
			best = d
			level = maxf(level, p.y)
	return level


static func footprint_factor(x: float, z: float) -> float:
	var best := 9.0
	for f: Array in Sites.FOOTPRINTS:
		var rel := (Vector2(x, z) - (f[0] as Vector2)).rotated(f[1])
		var e := Vector2(rel.x / (Sites.FOOT_WIDTH * 0.5), rel.y / (Sites.FOOT_LENGTH * 0.5)).length()
		best = minf(best, e)
	return best


func _ready() -> void:
	load_data()
	_build_collision()
	_build_meshes()


func _build_collision() -> void:
	var body := StaticBody3D.new()
	body.name = "Ground"
	var shape := HeightMapShape3D.new()
	shape.map_width = N + 1
	shape.map_depth = N + 1
	shape.map_data = heights
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.scale = Vector3(CELL, 1.0, CELL)
	body.add_child(cs)
	add_child(body)
	var edge := HALF - 40.0
	for side in 4:
		var wall := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(SIZE, 800.0, 4.0)
		wall.shape = box
		wall.position = Vector3(0, 200, edge).rotated(Vector3.UP, side * PI * 0.5)
		wall.rotation.y = side * PI * 0.5
		body.add_child(wall)


func _material(far: bool) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/terrain.gdshader")
	m.set_shader_parameter("height_map", height_tex)
	m.set_shader_parameter("control_map", load(DIR + "control.png"))
	m.set_shader_parameter("tint_map", load(DIR + "tint.png"))
	m.set_shader_parameter("normal_map", load(DIR + "normal.png"))
	m.set_shader_parameter("ground_albedo", load(TEX + "ground_albedo.png"))
	m.set_shader_parameter("ground_nrh", load(TEX + "ground_nrh.png"))
	m.set_shader_parameter("map_size", SIZE)
	m.set_shader_parameter("cell", CELL)
	m.render_priority = -2
	if far:
		m.set_shader_parameter("far_sink", 14.0)
		m.set_shader_parameter("canopy", 17.0)
		m.render_priority = 0
	return m


func _ring(verts: PackedVector3Array, uv2: PackedVector2Array, idx: PackedInt32Array, step: float, inner: float, outer: float, next_step: float) -> void:
	var n := int(round(outer * 2.0 / step))
	var base := verts.size()
	var side := n + 1
	for j in side:
		var z := -outer + j * step
		for i in side:
			var x := -outer + i * step
			verts.append(Vector3(x, 0.0, z))
			var off := Vector2.ZERO
			if next_step > 0.0:
				var on_x_edge := i == 0 or i == n
				var on_z_edge := j == 0 or j == n
				if on_x_edge and fposmod(z, next_step) > 0.01:
					off = Vector2(0.0, step)
				elif on_z_edge and fposmod(x, next_step) > 0.01:
					off = Vector2(step, 0.0)
			uv2.append(off)
	for j in n:
		var z := -outer + j * step
		for i in n:
			var x := -outer + i * step
			if inner > 0.0 and x >= -inner and x + step <= inner and z >= -inner and z + step <= inner:
				continue
			var a := base + j * side + i
			idx.append(a)
			idx.append(a + 1)
			idx.append(a + side)
			idx.append(a + 1)
			idx.append(a + side + 1)
			idx.append(a + side)


func _build_meshes() -> void:
	var verts := PackedVector3Array()
	var uv2 := PackedVector2Array()
	var idx := PackedInt32Array()
	_ring(verts, uv2, idx, 2.0, 0.0, 96.0, 4.0)
	_ring(verts, uv2, idx, 4.0, 96.0, 224.0, 8.0)
	near_mat = _material(false)
	near_mesh = _instance(verts, uv2, idx, near_mat, AABB(Vector3(-224, -20, -224), Vector3(448, 500, 448)))
	near_mesh.name = "GroundNear"

	verts = PackedVector3Array()
	uv2 = PackedVector2Array()
	idx = PackedInt32Array()
	_ring(verts, uv2, idx, 8.0, 224.0, 480.0, 0.0)
	mid_mesh = _instance(verts, uv2, idx, near_mat, AABB(Vector3(-480, -20, -480), Vector3(960, 500, 960)))
	mid_mesh.name = "GroundMid"

	verts = PackedVector3Array()
	uv2 = PackedVector2Array()
	idx = PackedInt32Array()
	_ring(verts, uv2, idx, 16.0, 0.0, HALF, 0.0)
	far_mesh = _instance(verts, uv2, idx, _material(true), AABB(Vector3(-HALF, -20, -HALF), Vector3(SIZE, 500, SIZE)))
	far_mesh.name = "GroundFar"
	far_mat = far_mesh.material_override


func _instance(verts: PackedVector3Array, uv2: PackedVector2Array, idx: PackedInt32Array, mat: ShaderMaterial, box: AABB) -> MeshInstance3D:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV2] = uv2
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.custom_aabb = box
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	return mi


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var p := cam.global_position
	near_mesh.position = Vector3(floorf(p.x / 8.0) * 8.0, 0.0, floorf(p.z / 8.0) * 8.0)
	mid_mesh.position = near_mesh.position
	var deep := p.y < Air.MIST_FROM - 30.0 and not hide_all
	mid_mesh.visible = not deep and not hide_all
	far_mesh.visible = not deep and not hide_all

extends Node3D

const Terrain := preload("res://scripts/terrain.gd")
const MeshLib := preload("res://scripts/meshlib.gd")
const Air := preload("res://scripts/air.gd")

const NEAR_CELLS := 3
const FAR_CELLS_MIST := 11
const FAR_CELLS_CLEAR := 30
const FADE_FROM := 30.0
const FADE_TO := 41.0
const TRUNK := 0.0125
const ROW := 20

var cell := 16.0
var cells := 0
var starts := PackedInt32Array()
var counts := PackedInt32Array()
var tops := PackedFloat32Array()
var kinds := PackedInt32Array()
var buf := PackedFloat32Array()
var near: Array[MultiMesh] = []
var far: MultiMesh
var near_mat: ShaderMaterial
var far_mat: ShaderMaterial
var at_cell := Vector2i(1 << 20, 1 << 20)
var at_level := -1
var trunks := {}
var _order: Array[Vector2i] = []
var _order_d2 := PackedInt32Array()


func _ready() -> void:
	var data := FileAccess.get_file_as_bytes(Terrain.DIR + "trees.bin")
	cells = data.decode_u32(4)
	var total := data.decode_u32(8)
	cell = data.decode_float(12)
	var at := 16
	var n := cells * cells * 4
	starts = data.slice(at, at + n).to_int32_array()
	at += n
	counts = data.slice(at, at + n).to_int32_array()
	at += n
	tops = data.slice(at, at + n).to_float32_array()
	at += n
	kinds = data.slice(at, at + n * 4).to_int32_array()
	at += n * 4
	buf = data.slice(at, at + total * ROW * 4).to_float32_array()

	var r := FAR_CELLS_CLEAR
	for dj in range(-r, r + 1):
		for di in range(-r, r + 1):
			if di * di + dj * dj <= r * r:
				_order.append(Vector2i(di, dj))
	_order.sort_custom(func(a: Vector2i, b: Vector2i) -> bool: return a.length_squared() < b.length_squared())
	_order_d2.resize(_order.size())
	for i in _order.size():
		_order_d2[i] = _order[i].length_squared()

	var albedo: TextureLayered = load(Terrain.TEX + "tree_albedo.png")
	var nrh: TextureLayered = load(Terrain.TEX + "tree_nrh.png")
	near_mat = ShaderMaterial.new()
	near_mat.shader = preload("res://shaders/tree.gdshader")
	near_mat.set_shader_parameter("tree_albedo", albedo)
	near_mat.set_shader_parameter("tree_nrh", nrh)
	near_mat.render_priority = -3
	far_mat = ShaderMaterial.new()
	far_mat.shader = preload("res://shaders/tree_far.gdshader")
	far_mat.set_shader_parameter("tree_albedo", albedo)
	var shape: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/gen/mesh/tree_far.json"))
	far_mat.set_shader_parameter("band", PackedFloat32Array(shape.band))
	var hw: Array = shape.half_width
	far_mat.set_shader_parameter("half_width", Vector4(hw[0], hw[1], hw[2], hw[3]))
	far_mat.render_priority = -1
	for m: ShaderMaterial in [near_mat, far_mat]:
		m.set_shader_parameter("fade_from", FADE_FROM)
		m.set_shader_parameter("fade_to", FADE_TO)
	var group := Node3D.new()
	group.name = "TreesNear"
	add_child(group)
	for kind in 4:
		near.append(_multimesh(MeshLib.load_mesh("res://assets/gen/mesh/tree_near_%d.hmesh" % kind, true).mesh, near_mat, "Kind%d" % kind, group))
	far = _multimesh(MeshLib.load_mesh("res://assets/gen/mesh/tree_far.hmesh").mesh, far_mat, "TreesFar", self)


func _multimesh(mesh: Mesh, mat: ShaderMaterial, node_name: String, parent: Node) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = mesh
	mm.custom_aabb = AABB(Vector3(-Terrain.HALF, -50, -Terrain.HALF), Vector3(Terrain.SIZE, 600, Terrain.SIZE))
	var mmi := MultiMeshInstance3D.new()
	mmi.name = node_name
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.custom_aabb = mm.custom_aabb
	parent.add_child(mmi)
	return mm


func _gather(center: Vector2i, radius: int, above := -1e9) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	var r2 := radius * radius
	for i in _order.size():
		if _order_d2[i] > r2:
			break
		var c := center + _order[i]
		if c.x < 0 or c.y < 0 or c.x >= cells or c.y >= cells:
			continue
		var k := c.y * cells + c.x
		var n := counts[k]
		if n == 0 or tops[k] < above:
			continue
		out.append_array(buf.slice(starts[k] * ROW, (starts[k] + n) * ROW))
	return out


func _gather_kind(center: Vector2i, radius: int, kind: int) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	var r2 := radius * radius
	for i in _order.size():
		if _order_d2[i] > r2:
			break
		var c := center + _order[i]
		if c.x < 0 or c.y < 0 or c.x >= cells or c.y >= cells:
			continue
		var k := c.y * cells + c.x
		var n := kinds[k * 4 + kind]
		if n == 0:
			continue
		var from := starts[k]
		for j in kind:
			from += kinds[k * 4 + j]
		out.append_array(buf.slice(from * ROW, (from + n) * ROW))
	return out


func _fill(mm: MultiMesh, data: PackedFloat32Array) -> void:
	mm.instance_count = data.size() / ROW
	if not data.is_empty():
		mm.buffer = data


func warm(point: Vector3, _radius := 0.0) -> void:
	var c := Vector2i(floori((point.x + Terrain.HALF) / cell), floori((point.z + Terrain.HALF) / cell))
	var level := 0
	if point.y > Air.MIST_FROM + 12.0:
		level = 2
	elif point.y > Air.MIST_FROM - 30.0:
		level = 1
	if c == at_cell and level == at_level:
		return
	var near_moved := c != at_cell
	at_cell = c
	at_level = level
	if near_moved:
		for kind in 4:
			_fill(near[kind], _gather_kind(c, NEAR_CELLS, kind))
		trunks.clear()
	match level:
		0:
			_fill(far, _gather(c, FAR_CELLS_MIST))
		1:
			_fill(far, _gather(c, 18))
		_:
			_fill(far, _gather(c, FAR_CELLS_CLEAR, Air.MIST_FROM - 6.0))


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		warm(cam.global_position)


func _cell_trunks(c: Vector2i) -> PackedVector3Array:
	if trunks.has(c):
		return trunks[c]
	var out := PackedVector3Array()
	if c.x >= 0 and c.y >= 0 and c.x < cells and c.y < cells:
		var from := starts[c.y * cells + c.x]
		for k in counts[c.y * cells + c.x]:
			var o := (from + k) * ROW
			var tall := buf[o + 5]
			var kind := buf[o + 16]
			out.append(Vector3(buf[o + 3], buf[o + 11], tall * (0.07 if kind > 2.5 else TRUNK * 1.15)))
	trunks[c] = out
	return out


func push_out(pos: Vector3, body_radius := 0.35) -> Vector3:
	var c := Vector2i(floori((pos.x + Terrain.HALF) / cell), floori((pos.z + Terrain.HALF) / cell))
	var p := Vector2(pos.x, pos.z)
	for dj in range(-1, 2):
		for di in range(-1, 2):
			for t: Vector3 in _cell_trunks(c + Vector2i(di, dj)):
				var d := Vector2(p.x - t.x, p.y - t.y)
				var reach := t.z + body_radius
				var len2 := d.length_squared()
				if len2 < reach * reach and len2 > 0.000001:
					p = Vector2(t.x, t.y) + d / sqrt(len2) * reach
	return Vector3(p.x, pos.y, p.y)


func nearest_trunk(point: Vector3, min_height := 12.0) -> Vector3:
	var c := Vector2i(floori((point.x + Terrain.HALF) / cell), floori((point.z + Terrain.HALF) / cell))
	var best := Vector3.ZERO
	var best_d := 1e12
	for dj in range(-1, 2):
		for di in range(-1, 2):
			for t: Vector3 in _cell_trunks(c + Vector2i(di, dj)):
				if t.z < min_height * TRUNK:
					continue
				var d := (t.x - point.x) * (t.x - point.x) + (t.y - point.z) * (t.y - point.z)
				if d < best_d:
					best_d = d
					best = t
	return best

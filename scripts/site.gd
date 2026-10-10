extends Node3D

const MeshLib := preload("res://scripts/meshlib.gd")
const DIR := "res://assets/gen/sites/"

static var _mat: ShaderMaterial
static var _decal_mat: ShaderMaterial

var info := {}
var key := ""
var body: StaticBody3D
var shown: MeshInstance3D
var glows: Array[Dictionary] = []


static func material() -> ShaderMaterial:
	if _mat == null:
		_mat = ShaderMaterial.new()
		_mat.shader = preload("res://shaders/structure.gdshader")
		_mat.set_shader_parameter("structure_albedo", load("res://assets/gen/tex/structure_albedo.png"))
		_mat.set_shader_parameter("structure_nrh", load("res://assets/gen/tex/structure_nrh.png"))
		_mat.set_shader_parameter("blotch", load("res://assets/gen/tex/film_grain.png"))
		_mat.render_priority = -2
	return _mat


static func decal_material() -> ShaderMaterial:
	if _decal_mat == null:
		_decal_mat = ShaderMaterial.new()
		_decal_mat.shader = preload("res://shaders/decal.gdshader")
		_decal_mat.set_shader_parameter("sheet", load("res://assets/gen/tex/decals.png"))
	return _decal_mat


func setup(site_name: String, air: Node = null) -> bool:
	var text := FileAccess.get_file_as_string(DIR + site_name + ".json")
	if text == "":
		push_warning("no such place: " + site_name)
		return false
	info = JSON.parse_string(text)
	key = site_name
	name = site_name.capitalize().replace(" ", "")
	var o: Array = info.origin
	position = Vector3(o[0], o[1], o[2])
	rotation.y = info.yaw
	var lo: Array = info.box[0]
	var hi: Array = info.box[1]
	var box := AABB(Vector3(lo[0], lo[1], lo[2]), Vector3(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
	shown = MeshInstance3D.new()
	shown.name = "Built"
	shown.mesh = MeshLib.load_mesh(DIR + site_name + ".hmesh").mesh
	shown.material_override = material()
	shown.custom_aabb = box
	shown.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var far: float = info.get("see_from", 340.0)
	if far > 0.0:
		shown.visibility_range_end = far + box.size.length() * 0.5
	add_child(shown)
	if info.get("decals", false):
		var d := MeshInstance3D.new()
		d.name = "Pictures"
		d.mesh = MeshLib.load_mesh(DIR + site_name + "_decals.hmesh").mesh
		d.material_override = decal_material()
		d.custom_aabb = box
		d.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		d.visibility_range_end = minf(shown.visibility_range_end, 160.0 + box.size.length() * 0.5) if far > 0.0 else 0.0
		add_child(d)
	body = StaticBody3D.new()
	body.name = "Solid"
	var shape := CollisionShape3D.new()
	var tri: ConcavePolygonShape3D = MeshLib.load_mesh(DIR + site_name + "_col.hmesh").mesh.create_trimesh_shape()
	tri.backface_collision = true
	shape.shape = tri
	body.add_child(shape)
	add_child(body)
	if air:
		for g: Dictionary in info.get("glows", []):
			var p: Array = g.pos
			var c: Array = g.color
			glows.append(air.add_glow(Vector3(p[0], p[1], p[2]), g.reach, Color(c[0], c[1], c[2]), g.energy))
	return true


func mark(spot: String) -> Vector3:
	var m: Dictionary = info.get("marks", {}).get(spot, {})
	if m.is_empty():
		return Vector3.ZERO
	var p: Array = m.pos
	return Vector3(p[0], p[1], p[2])


func mark_yaw(spot: String) -> float:
	return info.get("marks", {}).get(spot, {}).get("yaw", 0.0)


func has_mark(spot: String) -> bool:
	return info.get("marks", {}).has(spot)

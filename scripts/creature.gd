extends Node3D

const MeshLib := preload("res://scripts/meshlib.gd")
const DIR := "res://assets/gen/creatures/"

var skeleton: Skeleton3D
var mesh: MeshInstance3D
var mat: ShaderMaterial
var bone := {}
var rest := {}
var _info := {}
var _floats := PackedFloat32Array()
var _heads: Array[Vector3] = []

const MAX_BONES := 28

static var _all := {}


static func catalogue() -> Dictionary:
	if _all.is_empty():
		var text := FileAccess.get_file_as_string(DIR + "creatures.json")
		if text != "":
			_all = JSON.parse_string(text)
	return _all


func setup(body_name: String) -> bool:
	var data := MeshLib.load_mesh(DIR + body_name + ".hmesh", false, true)
	if data.is_empty():
		return false
	_info = catalogue().get(body_name, {})
	skeleton = Skeleton3D.new()
	skeleton.name = "Bones"
	add_child(skeleton)
	var heads := _heads
	for b: Dictionary in data.bones:
		var i := skeleton.add_bone(b.name)
		skeleton.set_bone_parent(i, b.parent)
		skeleton.set_bone_rest(i, b.rest)
		bone[b.name] = i
		var head: Vector3 = (b.rest as Transform3D).origin
		if b.parent >= 0:
			head += heads[b.parent]
		heads.append(head)
		rest[b.name] = head
	skeleton.reset_bone_poses()
	mesh = MeshInstance3D.new()
	mesh.name = "Body"
	mesh.mesh = data.mesh
	add_child(mesh)
	_floats.resize(MAX_BONES * 12)
	mat = ShaderMaterial.new()
	mat.shader = preload("res://shaders/skin.gdshader")
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if _info.has("box"):
		var lo: Array = _info.box[0]
		var hi: Array = _info.box[1]
		var size := Vector3(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
		var reach := maxf(size.y, maxf(size.x, size.z)) * 1.2
		mesh.custom_aabb = AABB(Vector3(-reach, lo[1] - reach * 0.3, -reach), Vector3(reach * 2.0, size.y + reach * 0.6, reach * 2.0))
	push()
	return true


func push() -> void:
	var n := skeleton.get_bone_count()
	for i in n:
		var t: Transform3D = skeleton.get_bone_global_pose(i) * Transform3D(Basis(), -(_heads[i]))
		var b := t.basis
		var o := i * 12
		_floats[o] = b.x.x
		_floats[o + 1] = b.y.x
		_floats[o + 2] = b.z.x
		_floats[o + 3] = t.origin.x
		_floats[o + 4] = b.x.y
		_floats[o + 5] = b.y.y
		_floats[o + 6] = b.z.y
		_floats[o + 7] = t.origin.y
		_floats[o + 8] = b.x.z
		_floats[o + 9] = b.y.z
		_floats[o + 10] = b.z.z
		_floats[o + 11] = t.origin.z
	mat.set_shader_parameter("bones", _floats)


func has(bone_name: String) -> bool:
	return bone.has(bone_name)


func turn(bone_name: String, x := 0.0, y := 0.0, z := 0.0) -> void:
	if bone.has(bone_name):
		skeleton.set_bone_pose_rotation(bone[bone_name], Quaternion.from_euler(Vector3(x, y, z)))


func turn_q(bone_name: String, q: Quaternion) -> void:
	if bone.has(bone_name):
		skeleton.set_bone_pose_rotation(bone[bone_name], q)


func shift(bone_name: String, by: Vector3) -> void:
	if bone.has(bone_name):
		var i: int = bone[bone_name]
		skeleton.set_bone_pose_position(i, skeleton.get_bone_rest(i).origin + by)


func where(bone_name: String) -> Vector3:
	if not bone.has(bone_name):
		return global_position
	return global_transform * skeleton.get_bone_global_pose(bone[bone_name]).origin


func aim(bone_name: String, child: String, dir: Vector3) -> void:
	var i: int = bone[bone_name]
	var rest_dir: Vector3 = ((rest[child] as Vector3) - (rest[bone_name] as Vector3)).normalized()
	var q := Quaternion(rest_dir, dir.normalized())
	var parent := skeleton.get_bone_parent(i)
	var pb := skeleton.get_bone_global_pose(parent).basis if parent >= 0 else Basis()
	skeleton.set_bone_pose_rotation(i, (pb.inverse() * Basis(q)).get_rotation_quaternion())


func level(bone_name: String, extra := Basis()) -> void:
	var i: int = bone[bone_name]
	var parent := skeleton.get_bone_parent(i)
	var pb := skeleton.get_bone_global_pose(parent).basis if parent >= 0 else Basis()
	skeleton.set_bone_pose_rotation(i, (pb.inverse() * extra).get_rotation_quaternion())


func head_of(bone_name: String) -> Vector3:
	return skeleton.get_bone_global_pose(bone[bone_name]).origin


func reach(upper: String, lower: String, tip: String, target: Vector3, pole: Vector3) -> void:
	var a := head_of(upper)
	var l1: float = ((rest[lower] as Vector3) - (rest[upper] as Vector3)).length()
	var l2: float = ((rest[tip] as Vector3) - (rest[lower] as Vector3)).length()
	var to := target - a
	var d := clampf(to.length(), absf(l1 - l2) + 0.001, l1 + l2 - 0.001)
	var dir := to.normalized()
	var along := (l1 * l1 - l2 * l2 + d * d) / (2.0 * d)
	var off := sqrt(maxf(l1 * l1 - along * along, 0.0))
	var side := pole - dir * pole.dot(dir)
	side = side.normalized() if side.length() > 0.0001 else dir.cross(Vector3.RIGHT).normalized()
	var joint := a + dir * along + side * off
	aim(upper, lower, joint - a)
	aim(lower, tip, (a + dir * d) - joint)


func at_rest() -> void:
	skeleton.reset_bone_poses()


func carried(bone_name: String, rest_point: Vector3) -> Vector3:
	var i: int = bone[bone_name]
	return global_transform * (skeleton.get_bone_global_pose(i) * (rest_point - _heads[i]))


func set_param(key: String, value: Variant) -> void:
	mat.set_shader_parameter(key, value)

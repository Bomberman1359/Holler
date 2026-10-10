extends Node3D

const Terrain := preload("res://scripts/terrain.gd")
const MeshLib := preload("res://scripts/meshlib.gd")

const KINDS := [
	{"mesh": "cover_fern", "channel": 0, "spacing": 1.6, "reach": 28.0, "size": Vector2(0.75, 1.35), "sway": 1.0, "sink": 0.06},
	{"mesh": "cover_grass", "channel": 1, "spacing": 1.0, "reach": 18.0, "size": Vector2(0.7, 1.4), "sway": 1.6, "sink": 0.02},
	{"mesh": "cover_rock", "channel": 2, "spacing": 3.0, "reach": 36.0, "size": Vector2(0.4, 1.7), "sway": 0.0, "sink": 0.12},
]

var layers: Array[Dictionary] = []


func _ready() -> void:
	var cover: Texture2D = load(Terrain.DIR + "cover.png")
	if cover == null:
		return
	for k: Dictionary in KINDS:
		var path := "res://assets/gen/mesh/%s.hmesh" % k.mesh
		if not FileAccess.file_exists(path):
			continue
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://shaders/cover.gdshader")
		mat.set_shader_parameter("height_map", Terrain.height_tex)
		mat.set_shader_parameter("cover_map", cover)
		mat.set_shader_parameter("map_size", Terrain.SIZE)
		mat.set_shader_parameter("cell", Terrain.CELL)
		mat.set_shader_parameter("spacing", k.spacing)
		mat.set_shader_parameter("reach", k.reach)
		mat.set_shader_parameter("channel", k.channel)
		mat.set_shader_parameter("size_min", (k.size as Vector2).x)
		mat.set_shader_parameter("size_max", (k.size as Vector2).y)
		mat.set_shader_parameter("sway", k.sway)
		mat.set_shader_parameter("sink", k.sink)
		mat.render_priority = -3
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = MeshLib.load_mesh(path).mesh
		var step: float = k.spacing
		var reach: float = k.reach
		var n := int(ceil(reach / step))
		var slots := PackedVector3Array()
		for j in range(-n, n + 1):
			for i in range(-n, n + 1):
				if Vector2(i, j).length() * step <= reach + step:
					slots.append(Vector3(i * step, 0.0, j * step))
		mm.instance_count = slots.size()
		for s in slots.size():
			mm.set_instance_transform(s, Transform3D(Basis(), slots[s]))
		mm.custom_aabb = AABB(Vector3(-reach - 4.0, -400.0, -reach - 4.0), Vector3(reach * 2.0 + 8.0, 1200.0, reach * 2.0 + 8.0))
		var mmi := MultiMeshInstance3D.new()
		mmi.name = String(k.mesh).capitalize().replace(" ", "")
		mmi.multimesh = mm
		mmi.material_override = mat
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.custom_aabb = mm.custom_aabb
		add_child(mmi)
		layers.append({"node": mmi, "step": step})


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var at := cam.global_position
	for l: Dictionary in layers:
		var step: float = l.step
		(l.node as Node3D).global_position = Vector3(snappedf(at.x, step), 0.0, snappedf(at.z, step))

extends MultiMeshInstance3D

const LIFE := 20.0

var age := 0.0
var _mat: ShaderMaterial


static func spawn(world: Node3D, pos: Vector3, spread := 34.0, size := 26.0, count := 22) -> Node3D:
	var d := MultiMeshInstance3D.new()
	d.set_script(load("res://scripts/dust.gd"))
	world.add_child(d)
	d.global_position = pos
	d._build(spread, size, count)
	return d


func _build(spread: float, size: float, count: int) -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2(2, 2)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = quad
	mm.instance_count = count
	for i in count:
		var a := randf() * TAU
		var r := spread * sqrt(randf())
		mm.set_instance_transform(i, Transform3D(Basis(), Vector3(cos(a) * r, randf_range(1.0, size * 0.3), sin(a) * r)))
		mm.set_instance_color(i, Color(1, 1, 1, 1))
		mm.set_instance_custom_data(i, Color(randf() * 1.2, randf_range(3.0, 9.0) * size / 26.0, size * randf_range(0.5, 1.0), randf()))
	multimesh = mm
	_mat = ShaderMaterial.new()
	_mat.shader = preload("res://shaders/dust.gdshader")
	_mat.set_shader_parameter("life", LIFE - 2.0)
	_mat.render_priority = 6
	material_override = _mat
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	custom_aabb = AABB(Vector3(-spread * 3.0, -20, -spread * 3.0), Vector3(spread * 6.0, size * 6.0, spread * 6.0))


func _process(delta: float) -> void:
	age += delta
	_mat.set_shader_parameter("age", age)
	if age > LIFE:
		queue_free()

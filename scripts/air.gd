extends Node3D

const MIST_THICK := 0.017
const MIST_THIN := 0.0011
const MIST_FROM := 128.0
const MIST_TO := 176.0
const MOON := Vector3(0.70, 0.41, -0.585)

var env: Environment
var moon: DirectionalLight3D
var sky: MeshInstance3D
var sky_mat: ShaderMaterial
var lamp: SpotLight3D
var density_scale := 1.0
var _density_now := 1.0
var day := false
var look := ""
var _sky_now := Vector3.ZERO
var _glows: Array[Dictionary] = []

const LAMP_COLOR := Vector3(1.0, 0.86, 0.64)
const LAMP_ENERGY := 8.0
const LAMP_REACH := 34.0
const LAMP_OUTER := 31.0
const LAMP_INNER := 13.0
const LAMP_DROOP := 7.0
const SKY := Vector3(0.36, 0.44, 0.62)
const MOON_COLOR := Vector3(0.62, 0.72, 0.95)
const LOOKS := {
	"grey": {"mist": Color(0.36, 0.38, 0.39), "up": Color(0.44, 0.46, 0.48), "top": Color(0.52, 0.54, 0.56), "sun": Vector3(0.62, 0.60, 0.56),
			"sky": Vector3(0.50, 0.52, 0.55), "density": 0.45, "overcast": 1.0},
	"dusk": {"mist": Color(0.15, 0.16, 0.18), "up": Color(0.20, 0.21, 0.24), "top": Color(0.28, 0.28, 0.31), "sun": Vector3(0.17, 0.16, 0.17),
			"sky": Vector3(0.22, 0.24, 0.28), "density": 0.6, "overcast": 0.9},
	"moon": {"mist": Color(0.115, 0.135, 0.17), "up": Color(0.18, 0.21, 0.265), "top": Color(0.26, 0.30, 0.37), "sun": Vector3(0.21, 0.245, 0.32),
			"sky": Vector3(0.16, 0.195, 0.275), "density": 0.55, "overcast": 0.0},
}


func _ready() -> void:
	day = Shots.day
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.025, 0.035)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.36, 0.44, 0.62)
	env.ambient_light_energy = 0.16
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_white = 4.0
	env.fog_enabled = true
	env.fog_light_color = Color(0.07, 0.085, 0.11)
	env.fog_density = MIST_THICK * 0.8
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	moon = DirectionalLight3D.new()
	moon.light_color = Color(0.62, 0.72, 0.95)
	moon.light_energy = 0.12
	moon.shadow_enabled = false
	add_child(moon)
	moon.look_at_from_position(Vector3.ZERO, -MOON.normalized(), Vector3.UP)

	sky = MeshInstance3D.new()
	sky.name = "Sky"
	var dome := SphereMesh.new()
	dome.radius = 2600.0
	dome.height = 5200.0
	dome.radial_segments = 32
	dome.rings = 16
	sky.mesh = dome
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = preload("res://shaders/sky.gdshader")
	sky_mat.set_shader_parameter("cloud_noise", _noise_texture())
	sky_mat.render_priority = 20
	sky.material_override = sky_mat
	sky.custom_aabb = AABB(Vector3(-1e5, -1e5, -1e5), Vector3(2e5, 2e5, 2e5))
	sky.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sky)

	lamp = SpotLight3D.new()
	lamp.name = "Lamp"
	lamp.light_energy = 0.0
	lamp.shadow_enabled = false
	add_child(lamp)

	_set_colors()
	_push(1.0)
	var rs := RenderingServer
	rs.global_shader_parameter_set("moon_dir", MOON.normalized())
	rs.global_shader_parameter_set("mist_far", 2400.0)
	rs.global_shader_parameter_set("lamp_cone", Vector4(0, 0, -1, 0))
	rs.global_shader_parameter_set("lamp_at", Vector3.ZERO)
	rs.global_shader_parameter_set("lamp_light", Vector4(LAMP_COLOR.x * LAMP_ENERGY, LAMP_COLOR.y * LAMP_ENERGY, LAMP_COLOR.z * LAMP_ENERGY, LAMP_REACH))
	_push_glows()
	_push_light(0.0, 1.0)


func _set_colors() -> void:
	var rs := RenderingServer
	if day:
		rs.global_shader_parameter_set("mist_color", Color(0.55, 0.62, 0.70))
		rs.global_shader_parameter_set("mist_up", Color(0.6, 0.68, 0.8))
		rs.global_shader_parameter_set("mist_top", Color(0.7, 0.75, 0.82))
		rs.global_shader_parameter_set("mist_glow", Color(0, 0, 0))
		env.ambient_light_color = Color(1, 1, 1)
		env.ambient_light_energy = 0.9
		env.background_color = Color(0.55, 0.65, 0.8)
		moon.light_color = Color(1, 0.97, 0.9)
		moon.light_energy = 1.3
		sky.visible = false
		return
	sky_mat.set_shader_parameter("overcast", 0.0)
	if look != "":
		var l: Dictionary = LOOKS[look]
		rs.global_shader_parameter_set("mist_color", l.mist)
		rs.global_shader_parameter_set("mist_up", l.up)
		rs.global_shader_parameter_set("mist_top", l.top)
		rs.global_shader_parameter_set("mist_glow", Color(0, 0, 0) if l.overcast > 0.0 else Color(0.20, 0.225, 0.27))
		sky_mat.set_shader_parameter("overcast", l.overcast)
		sky_mat.set_shader_parameter("overcast_color", l.top)
		return
	rs.global_shader_parameter_set("mist_color", Color(0.105, 0.125, 0.16))
	rs.global_shader_parameter_set("mist_up", Color(0.16, 0.19, 0.245))
	rs.global_shader_parameter_set("mist_top", Color(0.25, 0.29, 0.36))
	rs.global_shader_parameter_set("mist_glow", Color(0.20, 0.225, 0.27))


func set_look(l: String) -> void:
	look = l
	_set_colors()
	_push(_density_now)
	if look != "":
		var d: Dictionary = LOOKS[look]
		var rs := RenderingServer
		var sun: Vector3 = d.sun
		var sk: Vector3 = d.sky
		rs.global_shader_parameter_set("moon_light", Vector4(sun.x, sun.y, sun.z, 0))
		rs.global_shader_parameter_set("sky_light", Vector4(sk.x, sk.y, sk.z, 0))
		rs.global_shader_parameter_set("ground_light", Vector4(sk.x * 0.5, sk.y * 0.5, sk.z * 0.5, 0))
		var cone: Vector4 = Vector4(0, 0, -1, 0)
		rs.global_shader_parameter_set("lamp_cone", cone)


func _push(scale: float) -> void:
	var thick := MIST_THICK * scale * (0.12 if day else 1.0) * (float(LOOKS[look].density) if look != "" else 1.0)
	RenderingServer.global_shader_parameter_set("mist_layer", Vector4(thick, MIST_THIN, MIST_FROM, MIST_TO))
	env.fog_density = thick * 0.8


func _push_light(up: float, sky_gain: float) -> void:
	var rs := RenderingServer
	if day:
		rs.global_shader_parameter_set("moon_light", Vector4(1.25, 1.2, 1.1, 0))
		rs.global_shader_parameter_set("sky_light", Vector4(0.75, 0.8, 0.9, 0))
		rs.global_shader_parameter_set("ground_light", Vector4(0.42, 0.42, 0.4, 0))
		return
	var m := MOON_COLOR * lerpf(0.10, 0.42, up)
	rs.global_shader_parameter_set("moon_light", Vector4(m.x, m.y, m.z, 0))
	var s := SKY * lerpf(0.19, 0.27, up) * sky_gain
	rs.global_shader_parameter_set("sky_light", Vector4(s.x, s.y, s.z, 0))
	rs.global_shader_parameter_set("ground_light", Vector4(s.x * 0.45, s.y * 0.45, s.z * 0.45, 0))


func add_glow(at: Vector3, reach: float, color: Color, energy := 1.0) -> Dictionary:
	var g := {"at": at, "reach": reach, "light": Vector3(color.r, color.g, color.b) * energy, "on": true}
	_glows.append(g)
	return g


func clear_glow(g: Dictionary) -> void:
	_glows.erase(g)


func _push_glows(eye := Vector3.ZERO) -> void:
	var rs := RenderingServer
	var live: Array[Dictionary] = []
	for g in _glows:
		if g.on and (g.at as Vector3).distance_to(eye) < float(g.reach) + 220.0:
			live.append(g)
	if live.size() > 3:
		live.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
			return (a.at as Vector3).distance_squared_to(eye) < (b.at as Vector3).distance_squared_to(eye))
	for i in 3:
		if i < live.size():
			var g := live[i]
			var at: Vector3 = g.at
			var light: Vector3 = g.light
			rs.global_shader_parameter_set("glow%d_at" % i, Vector4(at.x, at.y, at.z, g.reach))
			rs.global_shader_parameter_set("glow%d_light" % i, Vector4(light.x, light.y, light.z, 0))
		else:
			rs.global_shader_parameter_set("glow%d_at" % i, Vector4(0, 0, 0, 0))


func _noise_texture() -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	n.frequency = 0.012
	n.fractal_octaves = 4
	var t := NoiseTexture2D.new()
	t.width = 256
	t.height = 256
	t.seamless = true
	t.noise = n
	return t


static func above(y: float) -> float:
	return smoothstep(MIST_FROM, MIST_TO + 20.0, y)


func density_at(y: float) -> float:
	var thick := MIST_THICK * _density_now
	return MIST_THIN + (thick - MIST_THIN) * clampf((MIST_TO - y) / (MIST_TO - MIST_FROM), 0.0, 1.0)


func _process(delta: float) -> void:
	if absf(_density_now - density_scale) > 0.001:
		_density_now = move_toward(_density_now, density_scale, delta * 0.08)
		_push(_density_now)
	if day:
		return
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var rs := RenderingServer
	if look != "":
		_push_glows(cam.global_position)
		return
	var on: bool = Game.lamp_on and not Game.scope_on and not Game.in_title
	var want := cam.global_transform * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(-LAMP_DROOP)), Vector3(0.24, -0.2, 0.05))
	if lamp.global_position.distance_to(want.origin) > 3.0:
		lamp.global_transform = want
	else:
		lamp.global_transform = Transform3D(lamp.global_basis.slerp(want.basis, minf(delta * 11.0, 1.0)), want.origin)
	var aim := -lamp.global_basis.z
	rs.global_shader_parameter_set("lamp_cone", Vector4(aim.x, aim.y, aim.z, 1.0 if on else 0.0))
	rs.global_shader_parameter_set("lamp_at", lamp.global_position)
	rs.global_shader_parameter_set("lamp_shape", Vector4(cos(deg_to_rad(LAMP_OUTER)), cos(deg_to_rad(LAMP_INNER)), density_at(lamp.global_position.y), 0))
	var up := above(cam.global_position.y)
	var gain := 14.0 if Game.scope_on else 1.0
	_sky_now.x = move_toward(_sky_now.x, gain, delta * 60.0)
	_push_light(up, _sky_now.x)
	_push_glows(cam.global_position)

extends Node3D

const Terrain := preload("res://scripts/terrain.gd")
const Creature := preload("res://scripts/creature.gd")

const CAMERA_AT := 168.0
const LOOK_AHEAD := 70.0
const FAR := 22.0
const NEAR := 9.0
const BODY := "watcher_smile"
const TALL := 3.1

const CALM := {
	"stand": {"head": Vector3(0.05, 0.0, 0.25), "arm_l": Vector3(0.03, 0, -0.05), "arm_r": Vector3(0.03, 0, 0.05), "fore_l": Vector3(0.08, 0, 0), "fore_r": Vector3(0.08, 0, 0)},
	"askew": {"head": Vector3(0.1, 0.0, 0.95), "neck": Vector3(0, 0, 0.3), "chest": Vector3(0, 0, -0.08), "arm_l": Vector3(0.05, 0, -0.1), "arm_r": Vector3(-0.05, 0, 0.04)},
}
const WRONG := {
	"neck_snap": {"neck": Vector3(0.2, 0, 1.25), "head": Vector3(0.4, 0.3, 1.15), "chest": Vector3(0, 0.25, -0.15), "arm_l": Vector3(0.1, 0, -0.05), "arm_r": Vector3(0.1, 0, 0.05)},
	"arms_up": {"arm_l": Vector3(2.9, 0, -0.25), "arm_r": Vector3(2.8, 0, 0.3), "fore_l": Vector3(0.5, 0, 0), "fore_r": Vector3(0.7, 0, 0), "head": Vector3(-0.5, 0, 0.2), "jaw": Vector3(-0.5, 0, 0), "spine": Vector3(0.12, 0, 0)},
	"backbend": {"drop": 0.25, "spine": Vector3(0.85, 0, 0), "chest": Vector3(0.75, 0, 0), "neck": Vector3(0.6, 0, 0), "head": Vector3(0.2, 0, 3.0),
			"arm_l": Vector3(-0.4, 0, -0.6), "arm_r": Vector3(-0.4, 0, 0.6), "thigh_l": Vector3(-0.3, 0, 0), "thigh_r": Vector3(-0.3, 0, 0), "shin_l": Vector3(0.6, 0, 0), "shin_r": Vector3(0.6, 0, 0)},
	"twisted": {"spine": Vector3(0, 1.3, 0), "chest": Vector3(0, 1.2, 0), "head": Vector3(0, -2.4, 0.3), "arm_l": Vector3(0.2, 0, -0.4), "arm_r": Vector3(1.0, 0, 0.3)},
	"crawl": {"drop": 1.0, "spine": Vector3(-1.3, 0, 0), "chest": Vector3(-0.3, 0, 0), "neck": Vector3(1.2, 0, 0), "head": Vector3(0.5, 0, 0.4),
			"arm_l": Vector3(1.6, 0, -0.2), "arm_r": Vector3(1.6, 0, 0.2), "thigh_l": Vector3(1.6, 0, -0.2), "thigh_r": Vector3(1.6, 0, 0.2), "shin_l": Vector3(-1.9, 0, 0), "shin_r": Vector3(-1.9, 0, 0)},
	"lean": {"spine": Vector3(0, 0, 0.75), "chest": Vector3(0, 0, 0.55), "neck": Vector3(0, 0, -0.6), "head": Vector3(0, 0, -1.25), "arm_l": Vector3(0, 0, -0.2),
			"arm_r": Vector3(0.1, 0, 1.2), "fore_r": Vector3(0.9, 0, 0)},
}

var cam: Camera3D
var figure: Node3D
var film: ShaderMaterial
var t := 0.0
var dist := FAR
var side := 0.0
var pose := "stand"
var pose_bones := {}
var phase := "idle"
var flash := false
var hold_wrong := 0.0
var glitch_wait := 3.0
var static_left := 0.0
var twitch_wait := 1.2
var twitch := 0.0
var gone := false
var base_pos := Vector3.ZERO
var forward := Vector3.FORWARD
var right := Vector3.RIGHT
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	rng.randomize()
	var p := Terrain.track_point(CAMERA_AT)
	var q := Terrain.track_point(CAMERA_AT + LOOK_AHEAD)
	forward = Vector3(q.x - p.x, 0.0, q.z - p.z).normalized()
	right = forward.cross(Vector3.UP).normalized()
	base_pos = p + Vector3(0, 1.75, 0) - right * 1.2
	cam = Camera3D.new()
	cam.fov = 48.0
	cam.near = 0.15
	cam.far = 3200.0
	add_child(cam)
	cam.global_position = base_pos
	cam.look_at(base_pos + forward * 40.0 + Vector3(0, -1.0, 0), Vector3.UP)
	cam.make_current()
	figure = Node3D.new()
	figure.set_script(Creature)
	add_child(figure)
	if not figure.setup(BODY):
		figure.queue_free()
		figure = null
		return
	var s := TALL / 2.6
	figure.scale = Vector3(s, s, s)
	figure.set_param("own_light", 0.2)
	figure.set_param("rim", 1.2)
	figure.set_param("eye_shine", 1.0)
	figure.set_param("pattern", 1.0)
	_set_pose("stand")
	_stand_at(FAR, 0.6)
	if Game.main:
		film = Game.main.film_mat


func _exit_tree() -> void:
	if film:
		film.set_shader_parameter("snow", 0.0)
		film.set_shader_parameter("jitter", 0.0)


func _set_pose(key: String) -> void:
	pose = key
	pose_bones = CALM.get(key, WRONG.get(key, {}))
	_apply(0.0)


func _apply(head_extra: float) -> void:
	if figure == null:
		return
	figure.at_rest()
	figure.shift("hips", Vector3(0, -float(pose_bones.get("drop", 0.0)), 0))
	for k: String in pose_bones:
		if k == "drop":
			continue
		var v: Vector3 = pose_bones[k]
		if k == "head":
			v += Vector3(0.0, 0.0, head_extra)
		figure.turn(k, v.x, v.y, v.z)
	figure.push()


func _stand_at(d: float, lateral: float) -> void:
	if figure == null:
		return
	dist = d
	side = lateral
	var flat := Vector3(base_pos.x, 0.0, base_pos.z) + forward * d + right * lateral
	flat.y = Terrain.height(flat.x, flat.z)
	figure.global_position = flat
	var to := base_pos - flat
	figure.rotation.y = atan2(-to.x, -to.z)


func _process(delta: float) -> void:
	if figure == null:
		return
	t += delta
	cam.global_position = base_pos + right * sin(t * 0.37) * 0.05 + Vector3(0, sin(t * 0.53) * 0.03, 0)
	cam.rotation.z = sin(t * 0.29) * 0.008
	var snow := 0.06 + 0.03 * absf(sin(t * 7.3)) * float(rng.randf() < 0.3)
	var jitter := 0.0
	match phase:
		"idle":
			glitch_wait -= delta
			if glitch_wait <= 0.0:
				_glitch()
		"glitch", "flick":
			static_left -= delta
			snow = 0.55 + rng.randf() * 0.35 if phase == "glitch" else 0.35
			jitter = 1.0
			if static_left <= 0.0:
				if phase == "glitch":
					_after_glitch()
				else:
					phase = "idle"
		"hold":
			hold_wrong -= delta
			if hold_wrong <= 0.0:
				_set_pose("stand" if rng.randf() < 0.6 else "askew")
				phase = "flick"
				static_left = 0.06
	twitch_wait -= delta
	if twitch_wait <= 0.0:
		twitch_wait = rng.randf_range(0.6, 2.4)
		twitch = rng.randf_range(-0.6, 0.6)
	elif twitch != 0.0:
		twitch = move_toward(twitch, 0.0, delta * 6.0)
	_apply(twitch + 0.12 * sin(t * 0.8))
	if film:
		film.set_shader_parameter("snow", snow)
		film.set_shader_parameter("jitter", jitter)


func _glitch() -> void:
	glitch_wait = rng.randf_range(1.8, 4.6)
	phase = "glitch"
	static_left = rng.randf_range(0.1, 0.3)
	if Game.world and Game.world.get("sfx"):
		Game.world.sfx.play("static_hit", rng.randf_range(-14.0, -8.0), rng.randf_range(0.8, 1.2))
	var keys := WRONG.keys()
	_set_pose(keys[rng.randi() % keys.size()])
	flash = rng.randf() < 0.12
	if flash:
		figure.visible = true
		_stand_at(rng.randf_range(4.5, 6.0), rng.randf_range(-0.8, 0.8))


func _after_glitch() -> void:
	if flash:
		flash = false
		_set_pose("stand")
		_stand_at(FAR, rng.randf_range(-3.0, 3.0))
		phase = "idle"
		return
	if gone:
		gone = false
		figure.visible = true
	elif rng.randf() < 0.15:
		gone = true
		figure.visible = false
		phase = "idle"
		return
	var d := dist - rng.randf_range(1.0, 7.0)
	if d < NEAR or rng.randf() < 0.15:
		d = rng.randf_range(FAR - 8.0, FAR + 6.0)
	_stand_at(d, clampf(side + rng.randf_range(-4.0, 4.0), -7.0, 7.0))
	phase = "hold"
	hold_wrong = rng.randf_range(0.5, 1.6)

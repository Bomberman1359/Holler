extends Node3D

const Terrain := preload("res://scripts/terrain.gd")
const Creature := preload("res://scripts/creature.gd")

enum Face { SMILE, FROWN, OPEN, NONE }
enum Part { STAND, STALK, AMBUSH }

const BODIES := ["watcher_smile", "watcher_frown", "watcher_open", "watcher_none"]
const BUILT_TALL := 2.6
const EFFECT_RANGE := 70.0
const SEEN_TO := 95.0
const STANCES := {
	"stand": {"head": Vector3(0.0, 0.0, 0.2), "arm_l": Vector3(0.03, 0, -0.05), "arm_r": Vector3(0.03, 0, 0.05), "fore_l": Vector3(0.08, 0, 0), "fore_r": Vector3(0.08, 0, 0)},
	"askew": {"head": Vector3(0.1, 0.0, 0.95), "neck": Vector3(0, 0, 0.3), "chest": Vector3(0, 0, -0.08), "arm_l": Vector3(0.05, 0, -0.1), "arm_r": Vector3(-0.05, 0, 0.04)},
	"bent": {"drop": 0.34, "spine": Vector3(-0.75, 0, 0), "chest": Vector3(-0.6, 0, 0), "neck": Vector3(0.75, 0, 0), "head": Vector3(0.5, 0, 0.12),
			"arm_l": Vector3(1.3, 0, -0.05), "arm_r": Vector3(1.3, 0, 0.05), "thigh_l": Vector3(0.28, 0, 0), "thigh_r": Vector3(0.28, 0, 0), "shin_l": Vector3(-0.5, 0, 0), "shin_r": Vector3(-0.5, 0, 0),
			"foot_l": Vector3(0.22, 0, 0), "foot_r": Vector3(0.22, 0, 0)},
	"stride": {"drop": 0.05, "spine": Vector3(-0.12, 0.1, 0), "thigh_l": Vector3(0.5, 0, 0), "shin_l": Vector3(-0.55, 0, 0), "thigh_r": Vector3(-0.38, 0, 0), "shin_r": Vector3(-0.2, 0, 0),
			"foot_r": Vector3(-0.35, 0, 0), "arm_l": Vector3(-0.3, 0, -0.04), "arm_r": Vector3(0.4, 0, 0.04), "fore_r": Vector3(0.3, 0, 0), "head": Vector3(0.05, 0, 0.15)},
	"squat": {"drop": 0.62, "thigh_l": Vector3(1.75, 0, -0.25), "thigh_r": Vector3(1.75, 0, 0.25), "shin_l": Vector3(-2.45, 0, 0), "shin_r": Vector3(-2.45, 0, 0), "foot_l": Vector3(0.7, 0, 0), "foot_r": Vector3(0.7, 0, 0),
			"spine": Vector3(-0.5, 0, 0), "chest": Vector3(-0.25, 0, 0), "neck": Vector3(0.6, 0, 0), "arm_l": Vector3(0.75, 0, -0.1), "arm_r": Vector3(0.75, 0, 0.1), "head": Vector3(0.15, 0, -0.3)},
	"behind": {"spine": Vector3(0, 0, 0.05), "head": Vector3(0, 0, -0.1), "arm_r": Vector3(0.9, 0, 0.25), "fore_r": Vector3(1.2, 0, 0)},
	"lean_out": {"drop": 0.06, "spine": Vector3(-0.1, 0, -0.42), "chest": Vector3(-0.08, 0, -0.3), "neck": Vector3(0.0, 0, 0.25), "head": Vector3(-0.1, -0.2, -0.75), "jaw": Vector3(-0.3, 0, 0),
			"arm_r": Vector3(1.45, 0, 0.5), "fore_r": Vector3(0.5, 0, 0), "arm_l": Vector3(0.1, 0, -0.1), "thigh_r": Vector3(0.1, 0, 0.2)},
	"reach": {"spine": Vector3(-0.22, 0, 0), "chest": Vector3(-0.2, 0, 0), "neck": Vector3(0.25, 0, 0), "head": Vector3(0.1, 0, 0.3), "jaw": Vector3(-0.45, 0, 0),
			"arm_l": Vector3(1.5, 0, -0.12), "arm_r": Vector3(1.35, 0, 0.2), "fore_l": Vector3(0.25, 0, 0), "fore_r": Vector3(0.4, 0, 0), "thigh_l": Vector3(0.35, 0, 0), "shin_l": Vector3(-0.3, 0, 0)},
}

var face: int = Face.SMILE
var tall := 2.6
var part: int = Part.STAND
var stance := "stand"
var build := 0
var home := Vector3.ZERO
var stop_distance := 16.0
var unseen_time := 0.0
var hop_wait := 2.5
var active_range := 150.0
var in_frame := false
var held := false
var body: Node3D
var side := 1.0
var sprung := false
var _spring := 0.0
var _spring_time := 0.0
var _hide_from := Vector3.ZERO
var _scope := false
var _shown := true


func _ready() -> void:
	body = Node3D.new()
	body.set_script(Creature)
	add_child(body)
	body.setup(BODIES[face])
	var s := tall / BUILT_TALL
	body.scale = Vector3(s, s, s)
	body.set_param("own_light", 0.03)
	body.set_param("pattern", 1.0)
	if stance == "stand":
		stance = ["stand", "askew", "bent", "askew", "stand"][build % 5]
	set_stance(stance)
	home = global_position
	add_to_group("watchers")
	_face_point(Game.player.global_position if Game.player else global_position + Vector3.FORWARD)


func set_stance(key: String, other := "", blend := 0.0) -> void:
	stance = key
	var a: Dictionary = STANCES.get(key, {})
	var b: Dictionary = STANCES.get(other, {}) if other != "" else {}
	body.at_rest()
	var bones := {}
	for k: String in a:
		bones[k] = true
	for k: String in b:
		bones[k] = true
	var drop := lerpf(a.get("drop", 0.0), b.get("drop", a.get("drop", 0.0)) if other != "" else a.get("drop", 0.0), blend)
	body.shift("hips", Vector3(0, -drop, 0))
	for k: String in bones:
		if k == "drop":
			continue
		var va: Vector3 = a.get(k, Vector3.ZERO)
		var v: Vector3 = va.lerp(b.get(k, Vector3.ZERO), blend) if other != "" else va
		var bone_name := k
		if side < 0.0:
			if k.ends_with("_l"):
				bone_name = k.trim_suffix("_l") + "_r"
			elif k.ends_with("_r"):
				bone_name = k.trim_suffix("_r") + "_l"
			v = Vector3(v.x, -v.y, -v.z)
		body.turn(bone_name, v.x, v.y, v.z)
	body.push()


func _face_point(p: Vector3) -> void:
	var d := p - global_position
	if Vector2(d.x, d.z).length() > 0.5:
		rotation.y = atan2(-d.x, -d.z)


func _scope_look() -> void:
	if Game.scope_on != _scope:
		_scope = Game.scope_on
		body.set_param("scope_glow", 0.12 if _scope else 0.0)


func head_point() -> Vector3:
	return global_position + Vector3(0, tall * 0.88, 0)


func seen_by(cam: Camera3D) -> bool:
	if not visible:
		return false
	if cam.global_position.distance_to(global_position) > SEEN_TO:
		return false
	return cam.is_position_in_frustum(head_point()) or cam.is_position_in_frustum(global_position + Vector3(0, tall * 0.3, 0))


func lie_in_wait(trunk: Vector3, way_point: Vector3) -> void:
	part = Part.AMBUSH
	sprung = false
	_spring = 0.0
	var t := Vector3(trunk.x, Terrain.height(trunk.x, trunk.y), trunk.y)
	var from_way := (t - way_point)
	from_way.y = 0.0
	from_way = from_way.normalized()
	global_position = t + from_way * (trunk.z + 0.42 * tall / BUILT_TALL)
	_hide_from = way_point
	_face_point(way_point)
	side = 1.0 if randf() < 0.5 else -1.0
	set_stance("behind")
	home = global_position


func _process(delta: float) -> void:
	var player := Game.player
	if player == null or held:
		return
	var cam: Camera3D = get_viewport().get_camera_3d()
	if cam == null:
		return
	var to_player := player.global_position - global_position
	var dist := to_player.length()
	var show := dist < 170.0
	if show != _shown:
		_shown = show
		body.visible = show
	if not show or Game.busy:
		return
	_scope_look()
	if part == Part.AMBUSH:
		_ambush(delta, player, cam, dist)
		return
	in_frame = seen_by(cam)
	if in_frame:
		unseen_time = 0.0
		if dist < EFFECT_RANGE:
			match face:
				Face.SMILE:
					Game.drain_mult = maxf(Game.drain_mult, 3.0)
				Face.FROWN:
					Game.jitter = maxf(Game.jitter, clampf(1.1 - dist / EFFECT_RANGE, 0.2, 1.0))
				Face.OPEN:
					Game.hum = maxf(Game.hum, clampf(1.2 - dist / EFFECT_RANGE, 0.2, 1.0))
		return
	unseen_time += delta
	var world := Game.world
	var target: Vector3 = player.global_position
	if world and world.get("reacher") and world.reacher.is_hunting():
		target = world.reacher.global_position
	elif world and world.get("colossus") and world.colossus.is_stepping():
		target = world.colossus.body_point()
	_face_point(target)
	if unseen_time < hop_wait:
		return
	unseen_time = 0.0
	hop_wait = randf_range(1.8, 4.5)
	if part == Part.STALK:
		_stalk(player, cam, dist)
	elif dist < 11.0:
		_go(home + Vector3(randf_range(-30, 30), 0, randf_range(-30, 30)).limit_length(34.0), cam)
	elif global_position.distance_to(home) > 40.0 and dist > active_range:
		_go(home, cam)


func _stalk(player: Node3D, cam: Camera3D, dist: float) -> void:
	if dist > active_range + 60.0:
		part = Part.STAND
		_go(home, cam)
		return
	var want := clampf(dist - randf_range(4.0, 11.0), stop_distance, 46.0)
	var back: Vector3 = player.global_basis.z
	var around := back.rotated(Vector3.UP, randf_range(-1.9, 1.9))
	var spot: Vector3 = player.global_position + around * want
	var forest: Node = Game.world.forest if Game.world else null
	var trunk := Vector3.ZERO
	if forest:
		trunk = forest.nearest_trunk(spot)
	if trunk != Vector3.ZERO:
		var t := Vector3(trunk.x, 0.0, trunk.y)
		var away := (t - Vector3(player.global_position.x, 0.0, player.global_position.z)).normalized()
		spot = t + away * (trunk.z + 0.4 * tall / BUILT_TALL) + away.cross(Vector3.UP) * 0.22 * side
		side = 1.0 if randf() < 0.5 else -1.0
		if _go(spot, cam):
			set_stance("behind", "lean_out", 0.55)
	elif _go(spot, cam):
		set_stance(["stand", "askew", "stride", "bent"][randi() % 4])


func _go(spot: Vector3, cam: Camera3D) -> bool:
	spot.y = Terrain.height(spot.x, spot.z)
	var head := spot + Vector3(0, tall * 0.88, 0)
	var far := cam.global_position.distance_to(spot) > SEEN_TO
	if not far and (cam.is_position_in_frustum(head) or cam.is_position_in_frustum(spot + Vector3(0, 0.4, 0))):
		return false
	if Terrain.track_distance(spot.x, spot.z) < 2.5:
		return false
	global_position = spot
	if Game.player:
		_face_point(Game.player.global_position)
	return true


func _ambush(delta: float, player: Node3D, cam: Camera3D, dist: float) -> void:
	if not sprung:
		if dist < 8.5 and dist > 2.0:
			sprung = true
			_spring_time = 0.0
			_face_point(player.global_position)
			var sfx: Node = Game.world.sfx if Game.world else null
			if sfx:
				sfx.play_at("watcher_sting", head_point(), 2.0, 40.0, randf_range(0.9, 1.1))
			Rig.note("scare", "watcher leans out", "%.1f m" % dist)
		return
	_spring_time += delta
	if _spring < 1.0:
		_spring = minf(_spring + delta / 0.16, 1.0)
		var e := 1.0 - pow(1.0 - _spring, 3.0)
		set_stance("behind", "lean_out", e)
		if _spring >= 1.0 and player.get("shake") != null:
			player.shake = maxf(player.shake, 0.25)
		return
	if _spring_time > 1.2 and not seen_by(cam):
		part = Part.STAND
		side = 1.0
		set_stance("stand")
		_go(home + Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized() * randf_range(45.0, 70.0), cam)
		home = global_position

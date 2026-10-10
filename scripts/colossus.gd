extends Node3D

signal about_to_step
signal footfall(pos: Vector3, left: bool)
signal arrived

const Terrain := preload("res://scripts/terrain.gd")
const Creature := preload("res://scripts/creature.gd")

const HIP := 172.0
const HIP_HALF := 14.5
const STEP_LENGTH := 96.0
const STEP_PERIOD := 15.0
const SWING_TIME := 6.5
const WARNING_TIME := 4.0
const LIFT := 30.0
const ANKLE := 9.0

var body: Node3D
var foot_pos: Array[Vector3] = [Vector3.ZERO, Vector3.ZERO]
var heading := 0.0
var pelvis := Vector3.ZERO
var route := PackedVector2Array()
var route_len := 0.0
var arc := 0.0
var walking := false
var timer := 0.0
var swing_foot := -1
var swing_t := 0.0
var swing_from := Vector3.ZERO
var swing_to := Vector3.ZERO
var next_foot := 0
var warned := false
var hurry := false
var mouth := 0.0
var bend := 0.0
var crouch := 0.0
var look_at_point := Vector3.INF
var reach_point := Vector3.INF
var reach_blend := 0.0
var _time := 0.0
var _skip := 0
var _last_step_left := false


func _ready() -> void:
	body = Node3D.new()
	body.set_script(Creature)
	add_child(body)
	body.setup("colossus")
	body.set_param("pattern", 0.012)
	body.set_param("veins", 1.0)
	body.set_param("vein_color", Vector3(0.75, 0.16, 0.12))
	body.set_param("vein_stretch", 0.25)
	body.set_param("wet", 0.25)
	body.set_param("rim", 0.5)
	body.set_param("tint", Vector3(0.5, 0.5, 0.56))
	body.mesh.custom_aabb = AABB(Vector3(-260, -80, -260), Vector3(520, 520, 520))
	visible = false


func is_stepping() -> bool:
	return swing_foot >= 0 or warned


func body_point() -> Vector3:
	return pelvis


func head_point() -> Vector3:
	return body.where("head") + Vector3(0, 14, 0)


func _ground(p: Vector2) -> Vector3:
	return Vector3(p.x, Terrain.height(p.x, p.y), p.y)


func _side(yaw: float) -> Vector3:
	return Vector3(cos(yaw), 0, -sin(yaw))


func _forward(yaw: float) -> Vector3:
	return Vector3(-sin(yaw), 0, -cos(yaw))


func place(at: Vector2, yaw: float) -> void:
	heading = yaw
	var mid := Vector3(at.x, 0, at.y)
	var side := _side(yaw)
	for i in 2:
		var p := mid + side * (HIP_HALF * (-1.0 if i == 0 else 1.0))
		foot_pos[i] = _ground(Vector2(p.x, p.z))
	walking = false
	swing_foot = -1
	warned = false
	visible = true
	pelvis = _pelvis_target()
	_pose(0.0)


func _route_point(s: float) -> Array:
	var left := clampf(s, 0.0, route_len)
	for i in route.size() - 1:
		var seg := route[i + 1] - route[i]
		var L := seg.length()
		if left <= L or i == route.size() - 2:
			var p := route[i] + seg * clampf(left / maxf(L, 0.001), 0.0, 1.0)
			return [p, atan2(-seg.x, -seg.y)]
		left -= L
	return [route[route.size() - 1], heading]


func walk_route(points: Array) -> void:
	route = PackedVector2Array()
	var mid := (foot_pos[0] + foot_pos[1]) * 0.5
	route.append(Vector2(mid.x, mid.z))
	for p: Vector2 in points:
		route.append(p)
	route_len = 0.0
	for i in route.size() - 1:
		route_len += route[i].distance_to(route[i + 1])
	arc = 0.0
	walking = true
	visible = true
	timer = STEP_PERIOD - SWING_TIME - WARNING_TIME - 0.5
	warned = false


func _pelvis_target() -> Vector3:
	var mid := (foot_pos[0] + foot_pos[1]) * 0.5
	var low := minf(foot_pos[0].y, foot_pos[1].y)
	var apart := Vector2(foot_pos[0].x - foot_pos[1].x, foot_pos[0].z - foot_pos[1].z).length()
	var sag := maxf(apart - HIP_HALF * 2.0, 0.0) * 0.16 + crouch * 86.0
	return Vector3(mid.x, low + HIP + ANKLE - 6.0 - sag, mid.z)


func _start_step() -> void:
	swing_foot = next_foot
	swing_t = 0.0
	swing_from = foot_pos[swing_foot]
	arc = minf(arc + STEP_LENGTH * (0.5 if arc <= 0.0 else 1.0), route_len)
	var at: Array = _route_point(arc)
	var side := _side(at[1])
	var p: Vector2 = at[0]
	var to := Vector3(p.x, 0, p.y) + side * (HIP_HALF * (-1.0 if swing_foot == 0 else 1.0))
	swing_to = _ground(Vector2(to.x, to.z))


func _process(delta: float) -> void:
	if not visible:
		return
	_time += delta
	if walking:
		timer += delta
		var period := STEP_PERIOD * (0.62 if hurry else 1.0)
		if swing_foot < 0:
			if not warned and timer >= period - SWING_TIME - WARNING_TIME:
				warned = true
				about_to_step.emit()
			if timer >= period - SWING_TIME:
				_start_step()
		else:
			swing_t += delta / SWING_TIME
			var s := clampf(swing_t, 0.0, 1.0)
			var e := s * s * (3.0 - 2.0 * s)
			var p := swing_from.lerp(swing_to, e)
			p.y += sin(s * PI) * LIFT * (1.0 - 0.35 * s)
			foot_pos[swing_foot] = p
			var want_yaw: float = _route_point(arc)[1]
			heading = lerp_angle(heading, want_yaw, minf(delta * 0.25, 1.0))
			if swing_t >= 1.0:
				foot_pos[swing_foot] = swing_to
				_last_step_left = swing_foot == 0
				footfall.emit(swing_to, swing_foot == 0)
				next_foot = 1 - swing_foot
				swing_foot = -1
				warned = false
				timer = 0.0
				if arc >= route_len - 0.5:
					var a := Vector2(foot_pos[0].x, foot_pos[0].z)
					var b := Vector2(foot_pos[1].x, foot_pos[1].z)
					if a.distance_to(b) < HIP_HALF * 2.6:
						walking = false
						arrived.emit()
	var want := _pelvis_target()
	if swing_foot >= 0:
		want += _forward(heading) * 9.0 * sin(clampf(swing_t, 0.0, 1.0) * PI)
	pelvis = pelvis.lerp(want, minf(delta * 0.55, 1.0)) if pelvis != Vector3.ZERO else want
	var busy := walking or bend > 0.001 or mouth > 0.001 or reach_blend > 0.001 or look_at_point != Vector3.INF
	_skip += 1
	if busy or _skip % 4 == 0:
		_pose(delta)


func _pose(_delta: float) -> void:
	global_position = Vector3(pelvis.x, 0.0, pelvis.z)
	rotation.y = heading
	var lowest := minf(foot_pos[0].y, foot_pos[1].y)
	global_position.y = lowest
	body.at_rest()
	var rest_hips: Vector3 = body.rest["hips"]
	var sway := 0.0
	if swing_foot >= 0:
		sway = (1.0 if swing_foot == 0 else -1.0) * sin(clampf(swing_t, 0.0, 1.0) * PI) * 5.0
	var breath := sin(_time * 0.5) * 0.6
	body.shift("hips", Vector3(sway, (pelvis.y - lowest) - rest_hips.y + breath, 0.0))
	body.turn("hips", 0.0, 0.0, -sway * 0.006)
	var stoop := 0.07 + bend * 0.95
	body.turn("spine", -stoop * 0.55, 0.0, sway * 0.004)
	body.turn("chest", -stoop * 0.6 + sin(_time * 0.5) * 0.012, 0.0, 0.0)
	var nod := -0.12 - bend * 0.25
	var twist := sin(_time * 0.11) * 0.25
	if look_at_point != Vector3.INF:
		var head_at: Vector3 = body.where("head")
		var to := look_at_point - head_at
		var want_yaw := atan2(-to.x, -to.z)
		twist = clampf(wrapf(want_yaw - heading, -PI, PI), -1.2, 1.2)
		nod = clampf(atan2(to.y, Vector2(to.x, to.z).length()) + stoop * 1.1, -1.0, 0.9)
	body.turn("neck", nod * 0.5, twist * 0.5, 0.0)
	body.turn("head", nod * 0.5, twist * 0.5, sin(_time * 0.07) * 0.06)
	body.turn("mouth_l", 0.0, mouth * 0.95, -mouth * 0.25)
	body.turn("mouth_r", 0.0, -mouth * 0.95, mouth * 0.25)
	var stride := 0.0
	if swing_foot >= 0:
		stride = (1.0 if swing_foot == 0 else -1.0) * sin(clampf(swing_t, 0.0, 1.0) * PI)
	body.turn("arm_l", stoop * 0.9 - stride * 0.16 + sin(_time * 0.23) * 0.02, 0.0, -0.05)
	body.turn("fore_l", 0.12 + sin(_time * 0.31 + 1.0) * 0.03, 0.0, 0.0)
	body.turn("hand_l", 0.1, 0.0, 0.0)
	body.turn("arm_r", stoop * 0.9 + stride * 0.2, 0.0, 0.07)
	body.turn("arm3", 0.2 + sin(_time * 0.41 + 2.0) * 0.16, sin(_time * 0.29) * 0.1, -0.1 + sin(_time * 0.37) * 0.08)
	body.turn("fore3", -0.25 + sin(_time * 0.53) * 0.2, 0.0, 0.0)
	if reach_blend > 0.001 and reach_point != Vector3.INF:
		var inv: Transform3D = body.global_transform.affine_inverse()
		var shoulder: Vector3 = body.head_of("arm_l")
		var hang: Vector3 = body.head_of("hand_l")
		var goal: Vector3 = hang.lerp(inv * reach_point, reach_blend)
		body.reach("arm_l", "fore_l", "hand_l", goal, Vector3(-1.0, 0.2, 0.8))
		var _unused := shoulder
	var inv2: Transform3D = body.global_transform.affine_inverse()
	for i in 2:
		var side := "l" if i == 0 else "r"
		var ankle: Vector3 = inv2 * (foot_pos[i] + Vector3(0, ANKLE, 0)) + Vector3(0, 0, 2.0)
		body.reach("thigh_" + side, "shin_" + side, "foot_" + side, ankle, Vector3((-0.2 if i == 0 else 0.2), 0.1, -1.0))
		var tip := 0.0
		if swing_foot == i:
			tip = -sin(clampf(swing_t, 0.0, 1.0) * PI) * 0.5
		body.level("foot_" + side, Basis(Vector3.RIGHT, tip))
	body.push()

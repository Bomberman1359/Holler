extends CharacterBody3D

signal hand_step
signal click
signal screech
signal alerted
signal sniffed

const Terrain := preload("res://scripts/terrain.gd")
const Creature := preload("res://scripts/creature.gd")

enum State { DORMANT, PATROL, LISTEN, SEARCH, CHARGE, CHASE }

const HEAR_RANGE := 46.0
const PATROL_SPEED := 1.7
const SEARCH_SPEED := 4.2
const CHARGE_SPEED := 7.4
const CHASE_SPEED := 5.1
const KILL_RANGE := 1.8
const GIVE_UP := 10.0
const REACT := 1.1
const LEASH := 190.0
const GRAVITY := 18.0
const LIMBS := ["arm_l", "arm_r", "leg_l", "leg_r"]

var state: int = State.DORMANT
var home := Vector3.ZERO
var patrol_points: Array[Vector3] = []
var patrol_index := 0
var target := Vector3.ZERO
var heard_for := 0.0
var state_time := 0.0
var chase_left := 0.0
var click_wait := 2.0
var warned_once := false
var rounds_reached := 0
var rounds_blocked := 0
var deaf_time := 0.0
var body: Node3D
var posed := false
var plant := {}
var swing_from := {}
var swing_to := {}
var swing_t := {}
var rest_at := {}
var jaw_open := 0.0
var jaw_want := 0.0
var sniff_left := 0.0
var sniff_wait := 9.0
var lifted := ""
var _time := 0.0
var _head_turn := Vector3.ZERO


func _ready() -> void:
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.45
	capsule.height = 1.5
	shape.shape = capsule
	shape.position.y = 0.8
	add_child(shape)
	collision_layer = 2
	collision_mask = 1
	floor_max_angle = deg_to_rad(55.0)
	floor_snap_length = 0.6
	body = Node3D.new()
	body.set_script(Creature)
	add_child(body)
	body.setup("reacher")
	body.set_param("wet", 0.5)
	body.set_param("rim", 0.5)
	body.set_param("veins", 0.9)
	body.set_param("vein_color", Vector3(0.45, 0.2, 0.3))
	body.set_param("pattern", 0.7)
	rest_at = {"arm_l": body.rest["hand_l"], "arm_r": body.rest["hand_r"], "leg_l": body.rest["foot_l"], "leg_r": body.rest["foot_r"]}
	for l: String in LIMBS:
		swing_t[l] = -1.0
	visible = false


func is_hunting() -> bool:
	return state == State.SEARCH or state == State.CHARGE or state == State.CHASE


func is_coming() -> bool:
	return state == State.CHARGE or state == State.CHASE


func is_listening() -> bool:
	return state == State.LISTEN


func is_asleep() -> bool:
	return state == State.DORMANT


func set_home(center: Vector3, radius := 22.0, also: Variant = null) -> void:
	home = center
	patrol_points.clear()
	for k in 5:
		var a := TAU * k / 5.0 + 0.4
		var p := center + Vector3(cos(a), 0, sin(a)) * radius * (0.6 + 0.4 * fmod(k * 0.37, 1.0))
		p.y = Terrain.height(p.x, p.z)
		patrol_points.append(p)
		if k == 2 and also != null:
			patrol_points.append(also as Vector3)
	_stand_at(patrol_points[0] + Vector3(0, 0.3, 0))
	patrol_index = 1
	_set_state(State.PATROL)


func set_route(points: Array) -> void:
	patrol_points.clear()
	var sum := Vector3.ZERO
	for p: Vector3 in points:
		patrol_points.append(p)
		sum += p
	home = sum / float(points.size())
	restart()


func restart() -> void:
	if patrol_points.is_empty():
		return
	var start := 0
	if Game.player:
		var far := -1.0
		for k in patrol_points.size():
			var d := patrol_points[k].distance_to(Game.player.global_position)
			if d > far:
				far = d
				start = k
	_stand_at(patrol_points[start] + Vector3(0, 0.3, 0))
	patrol_index = (start + 1) % patrol_points.size()
	heard_for = 0.0
	chase_left = 0.0
	_set_state(State.PATROL)


func sleep() -> void:
	visible = false
	_set_state(State.DORMANT)


func start_chase(from: Vector3, seconds := 28.0) -> void:
	_stand_at(from)
	chase_left = seconds
	_set_state(State.CHASE)
	_open_jaw(0.9)
	screech.emit()


func calm(seconds := 8.0) -> void:
	if state == State.DORMANT:
		return
	deaf_time = maxf(deaf_time, seconds)
	heard_for = 0.0
	chase_left = 0.0
	target = global_position
	_set_state(State.LISTEN)


func _stand_at(at: Vector3) -> void:
	global_position = at
	velocity = Vector3.ZERO
	visible = true
	posed = false
	body.set_param("own_light", 0.0)
	_plant_all()


func _plant_all() -> void:
	for l: String in LIMBS:
		plant[l] = _floor_at(body.global_transform * (rest_at[l] as Vector3))
		swing_t[l] = -1.0


func _alert() -> void:
	heard_for = 0.0
	_set_state(State.SEARCH)
	alerted.emit()
	if not warned_once:
		warned_once = true
		Game.say("Something heard you. Stop moving. It is blind.", 6.0)


func _set_state(s: int) -> void:
	state = s
	state_time = 0.0
	lifted = ""
	if s == State.CHARGE:
		_open_jaw(1.0)
		screech.emit()
	elif s == State.LISTEN:
		lifted = "arm_l" if randf() < 0.5 else "arm_r"


func _open_jaw(amount: float) -> void:
	jaw_want = amount


func _physics_process(delta: float) -> void:
	if state == State.DORMANT or Game.busy or Game.player == null:
		return
	state_time += delta
	var player := Game.player
	var to_player := player.global_position - global_position
	var dist := to_player.length()
	deaf_time = maxf(deaf_time - delta, 0.0)
	var heard := deaf_time <= 0.0 and not Game.hidden and Game.noise > 0.02 and dist < HEAR_RANGE * Game.noise

	if (state == State.SEARCH or state == State.CHARGE) and Vector2(global_position.x - home.x, global_position.z - home.z).length() > LEASH:
		deaf_time = 20.0
		heard_for = 0.0
		_set_state(State.PATROL)
		return

	var speed := 0.0
	match state:
		State.PATROL:
			target = patrol_points[patrol_index]
			speed = PATROL_SPEED
			if sniff_left > 0.0:
				sniff_left -= delta
				speed = 0.0
			else:
				sniff_wait -= delta
				if sniff_wait <= 0.0:
					sniff_wait = randf_range(9.0, 18.0)
					sniff_left = 2.4
					sniffed.emit()
			var there := Vector2(target.x - global_position.x, target.z - global_position.z).length() < 1.5
			if there or state_time > 35.0:
				if there:
					rounds_reached += 1
				else:
					rounds_blocked += 1
				patrol_index = (patrol_index + 1) % patrol_points.size()
				_set_state(State.LISTEN)
			if heard:
				target = player.global_position
				_alert()
		State.LISTEN:
			if heard:
				target = player.global_position
				_alert()
			elif state_time > 3.5:
				_set_state(State.PATROL)
		State.SEARCH:
			speed = SEARCH_SPEED
			if heard:
				target = player.global_position
				heard_for += delta
				if (dist < 9.0 and heard_for > REACT) or heard_for > 2.8:
					_set_state(State.CHARGE)
			else:
				heard_for = maxf(heard_for - delta, 0.0)
				if Vector2(target.x - global_position.x, target.z - global_position.z).length() < 1.6:
					deaf_time = GIVE_UP
					_set_state(State.LISTEN)
				elif state_time > 25.0:
					deaf_time = GIVE_UP
					_set_state(State.PATROL)
		State.CHARGE:
			speed = CHARGE_SPEED if state_time > 0.45 else 0.0
			if heard:
				target = player.global_position
				state_time = minf(state_time, 1.0)
			elif Vector2(target.x - global_position.x, target.z - global_position.z).length() < 1.6 or state_time > 6.0:
				heard_for = 0.0
				deaf_time = GIVE_UP
				_set_state(State.LISTEN)
		State.CHASE:
			speed = CHASE_SPEED if state_time > 0.6 else 0.0
			target = player.global_position
			chase_left -= delta
			if Game.hidden:
				chase_left = minf(chase_left, 2.5)
			if chase_left <= 0.0 or dist > 55.0:
				deaf_time = 9.0
				heard_for = 0.0
				target = global_position
				_set_state(State.LISTEN)
				Game.say("It lost you. Stand still. It is blind.", 5.0)
	if state_time > 1.3 and jaw_want > 0.5 and state != State.DORMANT:
		jaw_want = 0.25 if is_hunting() else 0.0

	var flat := Vector3(target.x - global_position.x, 0, target.z - global_position.z)
	if speed > 0.0 and flat.length() > 0.3:
		var dir := flat.normalized()
		velocity.x = move_toward(velocity.x, dir.x * speed, 20.0 * delta)
		velocity.z = move_toward(velocity.z, dir.z * speed, 20.0 * delta)
		rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), minf(delta * 5.0, 1.0))
	else:
		velocity.x = move_toward(velocity.x, 0.0, 20.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, 20.0 * delta)
	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	var ground := Terrain.height(global_position.x, global_position.z)
	if global_position.y < ground - 0.5:
		global_position.y = ground + 0.2

	if dist < KILL_RANGE and not Game.hidden and _nothing_between(player) and (state == State.CHARGE or state == State.CHASE or (state == State.SEARCH and Game.noise > 0.05 and heard_for > REACT)):
		Game.kill_player("reacher")

	if state == State.LISTEN or state == State.SEARCH or state == State.PATROL:
		click_wait -= delta
		if click_wait <= 0.0:
			click_wait = randf_range(0.8, 2.6) if state != State.PATROL else randf_range(3.0, 6.0)
			click.emit()


func _nothing_between(player: CharacterBody3D) -> bool:
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3(0, 0.9, 0), player.global_position + Vector3(0, 0.9, 0), 1, [get_rid(), player.get_rid()])
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _floor_at(p: Vector3) -> Vector3:
	var top := global_position.y + 1.2
	var q := PhysicsRayQueryParameters3D.create(Vector3(p.x, top, p.z), Vector3(p.x, global_position.y - 2.5, p.z), 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		return hit.position
	return Vector3(p.x, global_position.y, p.z)


func _process(delta: float) -> void:
	if not visible or body == null or posed:
		return
	_time += delta
	var speed := Vector2(velocity.x, velocity.z).length()
	var moving := speed > 0.25
	var lead := Vector3(velocity.x, 0, velocity.z) * 0.22
	var pairs := {"arm_l": "leg_r", "arm_r": "leg_l", "leg_l": "arm_r", "leg_r": "arm_l"}
	var others := {"arm_l": "arm_r", "arm_r": "arm_l", "leg_l": "leg_r", "leg_r": "leg_l"}
	var swing_time := clampf(0.46 - speed * 0.045, 0.13, 0.46)
	for l: String in LIMBS:
		var want: Vector3 = body.global_transform * (rest_at[l] as Vector3) + lead
		if swing_t[l] < 0.0:
			var reach_limit := (0.75 if l.begins_with("arm") else 0.4) * (1.0 if moving else 0.45)
			var off := Vector2(want.x - plant[l].x, want.z - plant[l].z).length()
			if off > reach_limit and swing_t[others[l]] < 0.0 and (swing_t[pairs[l]] < 0.0 or swing_t[pairs[l]] > 0.5):
				swing_t[l] = 0.0
				swing_from[l] = plant[l]
				var over := Vector3(velocity.x, 0, velocity.z).normalized() * (reach_limit * 0.75) if moving else Vector3.ZERO
				swing_to[l] = _floor_at(want + over)
		else:
			swing_t[l] += delta / swing_time
			var s: float = swing_t[l]
			if s >= 1.0:
				swing_t[l] = -1.0
				plant[l] = swing_to[l]
				if l.begins_with("arm"):
					hand_step.emit()
			else:
				var e := s * s * (3.0 - 2.0 * s)
				var lift := (0.42 if l.begins_with("arm") else 0.14) * sin(s * PI)
				plant[l] = (swing_from[l] as Vector3).lerp(swing_to[l], e) + Vector3(0, lift, 0)
	var low := clampf(speed / CHARGE_SPEED, 0.0, 1.0)
	var breathe := sin(_time * (2.2 + low * 5.0)) * 0.012
	var rock := 0.0
	if swing_t["arm_l"] >= 0.0:
		rock -= sin(float(swing_t["arm_l"]) * PI) * 0.07
	if swing_t["arm_r"] >= 0.0:
		rock += sin(float(swing_t["arm_r"]) * PI) * 0.07
	body.at_rest()
	body.shift("hips", Vector3(0, -0.08 * low + breathe, 0))
	body.turn("spine", -0.1 * low, 0.0, rock * 0.5)
	body.turn("chest", -0.12 * low + breathe * 2.0, 0.0, rock)
	jaw_open = move_toward(jaw_open, jaw_want, delta * 7.0)
	var want_turn := Vector3.ZERO
	match state:
		State.PATROL:
			if sniff_left > 0.0:
				want_turn = Vector3(0.55 + sin(_time * 19.0) * 0.07, sin(_time * 1.3) * 0.5, 0.0)
			else:
				want_turn = Vector3(-0.25, sin(_time * 0.9) * 0.55, sin(_time * 0.6) * 0.15)
		State.LISTEN:
			want_turn = Vector3(0.15, sin(_time * 0.5) * 0.3, 0.6 if lifted == "arm_l" else -0.6)
		State.SEARCH:
			want_turn = Vector3(0.1, sin(_time * 3.1) * 0.25, sin(_time * 2.3) * 0.2)
		State.CHARGE, State.CHASE:
			want_turn = Vector3(0.3, 0.0, sin(_time * 9.0) * 0.08)
	_head_turn = _head_turn.lerp(want_turn, minf(delta * (9.0 if is_hunting() else 3.0), 1.0))
	body.turn("neck", _head_turn.x * 0.5, _head_turn.y * 0.5, _head_turn.z * 0.4)
	body.turn("head", _head_turn.x * 0.5, _head_turn.y * 0.5, _head_turn.z * 0.6)
	body.turn("jaw", -jaw_open * 0.95, 0, 0)
	var inv: Transform3D = body.global_transform.affine_inverse()
	for side: String in ["l", "r"]:
		var sx := -1.0 if side == "l" else 1.0
		var hand: Vector3 = inv * (plant["arm_" + side] as Vector3)
		if lifted == "arm_" + side:
			hand += Vector3(sx * 0.1, 0.55 + sin(_time * 2.1) * 0.04, 0.25)
		hand += Vector3(0, 0.06, 0.1)
		body.reach("arm_" + side, "fore_" + side, "hand_" + side, hand, Vector3(sx * 0.55, 1.0, 0.75))
		body.level("hand_" + side)
		var foot: Vector3 = inv * (plant["leg_" + side] as Vector3) + Vector3(0, 0.17, 0.28)
		body.reach("thigh_" + side, "shin_" + side, "foot_" + side, foot, Vector3(sx * 0.3, 0.2, -1.0))
		body.level("foot_" + side)
	body.push()


func face_the_lens(eye: Vector3, forward: Vector3) -> void:
	visible = true
	var flat := Vector3(forward.x, 0, forward.z).normalized()
	global_position = eye + flat * 1.62 + Vector3(0, -1.3, 0)
	look_at(Vector3(eye.x, global_position.y, eye.z), Vector3.UP)
	jaw_open = 1.0
	jaw_want = 1.0
	_plant_all()
	_process(0.016)
	body.turn("neck", 0.16, 0, 0)
	body.turn("head", 0.02, 0, 0.14)
	body.turn("jaw", -1.0, 0, 0)
	body.push()
	body.set_param("own_light", 0.3)
	posed = true

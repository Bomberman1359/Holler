extends CharacterBody3D

signal footstep(loudness: float)
signal jumped
signal landed(strength: float)
signal winded(on: bool)

const WALK := 3.0
const RUN := 5.6
const CREEP := 1.4
const ACCEL := 26.0
const GRAVITY := 18.0
const JUMP := 5.2
const SENS := 0.0022
const EDGE := 1360.0
const STRIDE_WALK := 1.5
const STRIDE_RUN := 2.0
const STRIDE_CREEP := 1.0
const ZOOM_MAX := 8.0
const SCOPE_DRAIN := 0.42
const BASE_FOV := 60.0
const EYE := 1.65
const EYE_CROUCHED := 0.95
const RUN_SECONDS := 9.0
const REST_SECONDS := 13.0

var cam: Camera3D
var capsule: CapsuleShape3D
var shape: CollisionShape3D
var pitch := 0.0
var step_dist := 0.0
var zoom_target := 1.0
var zoom_noise := 0.0
var frozen := false
var shake := 0.0
var crouched := false
var running := false
var spent := false
var eye := EYE
var bob := 0.0
var dip := 0.0
var _air_time := 0.0
var _rest_wait := 0.0
var _fall_speed := 0.0


func _ready() -> void:
	shape = CollisionShape3D.new()
	capsule = CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.8
	shape.shape = capsule
	shape.position.y = 0.9
	add_child(shape)

	cam = Camera3D.new()
	cam.position.y = EYE
	cam.fov = 60.0
	cam.near = 0.12
	cam.far = 3200.0
	add_child(cam)
	cam.make_current()

	floor_max_angle = deg_to_rad(56.0)
	floor_snap_length = 0.4
	if not Shots.active and not Autotest.active and not Rig.active and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func look(relative: Vector2) -> void:
	var s := SENS * Game.sensitivity / maxf(Game.zoom * 0.7, 1.0)
	rotate_y(-relative.x * s)
	pitch = clampf(pitch - relative.y * s, -1.4, 1.4)
	cam.rotation.x = pitch


func zoom_step(amount: float) -> void:
	zoom_target = clampf(zoom_target * pow(1.25, amount), 1.0, ZOOM_MAX)


func toggle_scope() -> void:
	if Game.scope_on:
		Game.scope_on = false
	elif Game.battery > 0.0:
		Game.scope_on = true
	else:
		Game.say("The scope battery is dead.")


func toggle_lamp() -> void:
	Game.lamp_on = not Game.lamp_on
	Rig.note("lamp", "on" if Game.lamp_on else "off")


func _unhandled_input(event: InputEvent) -> void:
	if Game.busy or frozen:
		return
	if event.is_action_pressed("lamp"):
		toggle_lamp()


func _process(delta: float) -> void:
	var whole := minf(delta, 0.25)
	var steps := ceili(whole / 0.034)
	for i in steps:
		_move(whole / steps, 1.0 / steps * whole / maxf(delta, 0.0001))
	delta = whole
	if Game.busy:
		return
	if Input.is_action_pressed("zoom_in"):
		zoom_target = minf(zoom_target * (1.0 + 1.6 * delta), ZOOM_MAX)
	if Input.is_action_pressed("zoom_out"):
		zoom_target = maxf(zoom_target / (1.0 + 1.6 * delta), 1.0)
	var before := Game.zoom
	Game.zoom = lerpf(Game.zoom, zoom_target, minf(delta * 6.0, 1.0))
	if absf(Game.zoom - before) > 0.002:
		zoom_noise = 0.5
	zoom_noise = maxf(zoom_noise - delta, 0.0)
	cam.fov = rad_to_deg(2.0 * atan(tan(deg_to_rad(BASE_FOV * 0.5)) / Game.zoom))
	Game.footage += delta * 0.6
	shake = maxf(shake - delta * 0.55, 0.0)
	cam.h_offset = randf_range(-1.0, 1.0) * shake * 0.12
	cam.v_offset = randf_range(-1.0, 1.0) * shake * 0.16
	if Game.scope_on:
		Game.battery = maxf(Game.battery - SCOPE_DRAIN * Game.drain_mult * delta, 0.0)
		if Game.battery <= 0.0:
			Game.scope_on = false
			Game.say("The scope battery is dead.")
	var speed := Vector2(velocity.x, velocity.z).length()
	var n := 0.0
	if not is_on_floor():
		n = 0.2
	elif crouched:
		n = 0.06 if speed > 0.4 else 0.0
	elif speed > WALK + 0.5:
		n = 1.0
	elif speed > 0.5:
		n = 0.3
	if zoom_noise > 0.0:
		n = maxf(n, 0.6)
	if Game.scope_on:
		n = maxf(n, 0.4)
	Game.noise = n


func _move(delta: float, share: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var held := not (Game.busy or frozen)
	if not held:
		input = Vector2.ZERO
	var on_floor := is_on_floor()
	crouched = held and Input.is_action_pressed("crouch")

	var wants_run := held and Input.is_action_pressed("run") and input.y < -0.1 and not crouched
	running = wants_run and not spent and Game.stamina > 0.0
	if running and on_floor:
		Game.stamina = maxf(Game.stamina - delta / RUN_SECONDS, 0.0)
		_rest_wait = 0.9
		if Game.stamina <= 0.0:
			spent = true
			winded.emit(true)
	else:
		_rest_wait = maxf(_rest_wait - delta, 0.0)
		if _rest_wait <= 0.0:
			var rate := 1.0 if input == Vector2.ZERO else 0.55
			Game.stamina = minf(Game.stamina + delta * rate / REST_SECONDS, 1.0)
		if spent and Game.stamina > 0.3:
			spent = false
			winded.emit(false)

	var speed := WALK
	if crouched:
		speed = CREEP
	elif running:
		speed = RUN
	elif spent:
		speed = WALK * 0.85
	var dir := (transform.basis * Vector3(input.x, 0.0, input.y)).normalized()
	var grip := ACCEL if on_floor else ACCEL * 0.25
	velocity.x = move_toward(velocity.x, dir.x * speed, grip * delta)
	velocity.z = move_toward(velocity.z, dir.z * speed, grip * delta)
	if on_floor:
		velocity.y = 0.0
		if held and Input.is_action_just_pressed("jump") and not crouched and Game.stamina > 0.06:
			velocity.y = JUMP
			Game.stamina = maxf(Game.stamina - 0.07, 0.0)
			_rest_wait = 0.9
			jumped.emit()
	else:
		velocity.y -= GRAVITY * delta
		_fall_speed = maxf(_fall_speed, -velocity.y)
	velocity *= share
	move_and_slide()
	velocity /= share
	if Game.world and Game.world.get("forest"):
		global_position = Game.world.forest.push_out(global_position)
	global_position.x = clampf(global_position.x, -EDGE, EDGE)
	global_position.z = clampf(global_position.z, -EDGE, EDGE)

	if is_on_floor():
		if _air_time > 0.25:
			var hard := clampf((_fall_speed - 3.0) / 9.0, 0.15, 1.0)
			dip = maxf(dip, 0.05 + 0.2 * hard)
			landed.emit(hard)
		_air_time = 0.0
		_fall_speed = 0.0
		var flat := Vector2(velocity.x, velocity.z).length()
		var stride := STRIDE_WALK
		if crouched:
			stride = STRIDE_CREEP
		elif flat > WALK + 0.6:
			stride = STRIDE_RUN
		step_dist += flat * delta
		bob += flat * delta / stride * PI
		if step_dist >= stride:
			step_dist = 0.0
			footstep.emit(0.3 if crouched else (1.0 if flat > WALK + 0.6 else 0.6))
		if flat < 0.3:
			step_dist = minf(step_dist, stride * 0.6)
	else:
		_air_time += delta

	eye = move_toward(eye, EYE_CROUCHED if crouched else EYE, delta * 3.2)
	capsule.height = eye + 0.15
	shape.position.y = capsule.height * 0.5
	dip = move_toward(dip, 0.0, delta * 0.7)
	var flat_speed := Vector2(velocity.x, velocity.z).length()
	var swing := clampf(flat_speed / WALK, 0.0, 1.6) * (0.5 if crouched else 1.0)
	cam.position.y = eye - dip + absf(sin(bob)) * 0.035 * swing - 0.02 * swing
	cam.position.x = sin(bob) * 0.022 * swing
	cam.rotation.z = sin(bob) * 0.004 * swing

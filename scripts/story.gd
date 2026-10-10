extends Node

const Terrain := preload("res://scripts/terrain.gd")
const MeshLib := preload("res://scripts/meshlib.gd")
const Site := preload("res://scripts/site.gd")

const STOPS := ["gasthaus", "church", "bomber", "sanatorium", "radar", "tunnel", "lookout"]
const STOP_NAMES := ["the Gasthaus", "the church", "the bomber", "the sanatorium", "the radar station", "the tunnel site", "the fire lookout"]
const FILM_LIGHT := ["grey", "dusk", "moon", "grey", "moon", "dusk"]
const FILM_DATES := ["5 OCT 1947    16:40", "5 OCT 1947    19:05", "6 OCT 1947    02:30", "6 OCT 1947    11:15", "6 OCT 1947    21:40", "7 OCT 1947    04:12"]
const PAPER_AT := {
	"paper_notice": "notice", "paper_journal1": "journal1", "paper_flightlog": "flightlog", "paper_journal2": "journal2",
	"paper_journal3": "journal3", "cell_scratch": "cellwall", "paper_survey_note": "teamnote", "paper_army_order": "armyorder",
	"paper_staff_memo": "memo", "paper_measuring_log": "measlog", "paper_doctor": "doctor", "paper_lookout_note": "lookoutnote",
}
const FILM_SHOTS := [
	[[0.0, [[42.0, 2.6, "stand"]]], [3.2, [[30.0, 3.2, "stand"]]], [5.6, [[18.0, 2.4, "askew"], [46.0, -6.5, "stand"]]], [7.6, [[9.0, 1.6, "stand"]]]],
	[[0.0, []], [2.5, [[14.0, 0.0, "stand"]]], [5.0, [[11.0, -1.5, "askew"], [8.0, 3.5, "bent"]]], [7.4, [[6.0, -2.0, "stand"], [5.0, 2.5, "bent"], [13.0, 0.0, "askew"], [3.5, 2.2, "lean_out"]]]],
	[[0.0, [[19.0, 3.0, "stand"]]], [3.0, [[15.0, -4.0, "askew"], [21.0, 4.5, "stand"]]], [6.0, [[13.0, -3.0, "stand"], [18.0, 4.0, "stand"], [24.0, -1.0, "bent"]]]],
	[[0.0, [[11.5, -2.5, "stand"], [12.0, -0.8, "stand"], [11.5, 0.9, "stand"], [12.0, 2.6, "stand"]]], [3.6, [[8.5, -2.5, "askew"], [9.0, -0.8, "stand"], [8.5, 0.9, "askew"], [9.0, 2.6, "stand"]]], [5.6, []]],
	[[0.0, []], [3.0, [[16.0, 0.0, "stand"]]], [5.5, [[14.0, 0.5, "askew"], [13.0, -5.0, "stand"], [35.0, 6.0, "stand"]]], [8.0, [[5.0, -0.5, "stand"]]]],
	[[0.0, [[11.5, 1.9, "stand"]]], [3.5, [[9.0, 0.0, "stand"], [10.0, 4.0, "askew"]]], [6.4, [[6.0, -1.0, "stand"], [7.5, 2.5, "bent"], [11.5, 1.9, "stand"]]], [8.2, [[3.5, 0.3, "stand"]]]],
]
const FILM_SECONDS := [9.4, 9.4, 10.5, 8.4, 9.4, 9.6]
const FILM_SCARE := [8.7, -1.0, -1.0, 7.1, 8.8, 9.0]
const FILM_SCARE_AT := [Vector2(2.4, 0.6), Vector2.ZERO, Vector2.ZERO, Vector2(2.3, 0.0), Vector2(2.4, -0.3), Vector2(2.4, 0.2)]
const FILM_DRIFT := 0.4
const FILM_TILT := [-0.04, -0.04, 0.16, -0.04, -0.04, -0.04]

const HOLD_START := Vector2(-980, -150)
const WALK_TO_BOMBER := [Vector2(-860, 120), Vector2(-700, 300)]
const WALK_PAST_BOMBER := [Vector2(-625, 395), Vector2(-470, 400), Vector2(-330, 100), Vector2(-250, -150), Vector2(-160, -520), Vector2(-60, -700)]
const WALK_PAST_RADAR := [Vector2(30, -575), Vector2(190, -640), Vector2(260, -760), Vector2(150, -900)]
const WALK_OVER_HALL := [Vector2(345, -915), Vector2(520, -960), Vector2(690, -1010)]
const ROAD := [
	[150.0, "crack", 0], [470.0, "ambush", 1], [760.0, "ahead", 0], [1010.0, "ambush", -1], [1120.0, "crack", 1],
	[1400.0, "ambush", 1], [1560.0, "crack", 0], [1850.0, "ambush", -1], [2250.0, "ambush", 1], [2380.0, "ahead", 0],
	[2700.0, "ambush", -1], [3040.0, "crack", 1], [3260.0, "line", 0], [3440.0, "turn", 0], [3600.0, "release", 0],
]

var world: Node3D
var road_done := 0
var colossus_leg := 0
var line: Array = []
var stalk_wait := 12.0
var ending_step := 0
var items: Array = []
var current: Dictionary = {}
var films: Array = [{}, {}, {}, {}, {}, {}]
var film_items := {}
var film_cam: Camera3D
var film_index := -1
var film_t := 0.0
var film_shot := -1
var film_scared := false
var film_landed := false
var film_snow := 0.0
var film_shake := 0.0
var film_cast: Array = []
var film_before: Array = []
var film_crank: AudioStreamPlayer
var film_fill: Dictionary
var reading := false
var playing := false
var hides: Array[Vector3] = []
var _in_locker := false
var _roared := false
var approach_saved := 0
var reacher_site := -1
var intro_done := false
var glints: MultiMeshInstance3D
var _glint_count := 0
var _battery_mesh: ArrayMesh
var _scare_left := 0.0
var _ending_time := 0.0
var _roof_gone := false


func _ready() -> void:
	world = get_parent()
	film_cam = Camera3D.new()
	film_cam.near = 0.15
	film_cam.far = 3200.0
	film_cam.fov = 46.0
	world.add_child.call_deferred(film_cam)
	_build_glints()
	_place_things()
	Game.film_taken.connect(_on_film)
	Game.player_died.connect(_on_death)
	Game.player_back.connect(_on_back)
	_update_objective()


func site(place: String) -> Node3D:
	return world.sites.get(place)


func spot(place: String, mark: String) -> Vector3:
	var s := site(place)
	return s.mark(mark) if s else Vector3.ZERO


func _place_things() -> void:
	for place: String in world.sites:
		var s: Node3D = world.sites[place]
		var marks: Dictionary = s.info.get("marks", {})
		for mark: String in marks:
			var p: Vector3 = s.mark(mark)
			if PAPER_AT.has(mark):
				var key: String = PAPER_AT[mark]
				add_item(p, "Read", func() -> void: read(key, p), 2.6, false, 0.75)
			elif mark.begins_with("hide"):
				hides.append(p + Vector3(0, 1.0, 0))
			elif mark.begins_with("battery"):
				_add_battery(p, s.mark_yaw(mark))
			elif mark == "radio":
				add_item(p, "Key the radio", radio_call, 2.4, false, 1.0)
	for i in Game.FILM_COUNT:
		var s := site(STOPS[i])
		if s == null or not s.has_mark("camera"):
			continue
		var at: Vector3 = s.mark("camera")
		var yaw: float = s.mark_yaw("camera")
		films[i] = {"cam": at, "look": at + Vector3(sin(yaw), FILM_TILT[i], cos(yaw)) * 12.0, "site": STOPS[i]}
		var index := i
		film_items[i] = add_item(at, "Take the film", func() -> void: Game.take_film(index), 2.5, true, 1.0)


func add_item(pos: Vector3, label: String, action: Callable, radius := 2.3, once := true, shine := 1.0) -> Dictionary:
	var item := {"pos": pos, "prompt": label, "action": action, "radius": radius, "once": once, "used": false, "glint": -1}
	if shine > 0.0:
		item.glint = _add_glint(pos, shine)
	items.append(item)
	return item


func _add_battery(pos: Vector3, yaw: float) -> void:
	if _battery_mesh == null:
		_battery_mesh = MeshLib.load_mesh(Site.DIR + "prop_battery.hmesh").mesh
	var b := MeshInstance3D.new()
	b.mesh = _battery_mesh
	b.material_override = Site.material()
	b.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	b.visibility_range_end = 60.0
	world.add_child(b)
	b.global_position = pos
	b.rotation.y = yaw
	add_item(pos + Vector3(0, 0.08, 0), "Take the battery", func() -> void:
		Game.battery = minf(Game.battery + 55.0, Game.BATTERY_MAX)
		Game.say("A battery for the scope. Good for a couple more minutes.")
		world.sfx.play("pickup", -6.0)
		b.queue_free(), 2.2, true, 0.8)


func _build_glints() -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2(2, 2)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.use_custom_data = true
	mm.mesh = quad
	mm.instance_count = 96
	mm.visible_instance_count = 0
	glints = MultiMeshInstance3D.new()
	glints.name = "Glints"
	glints.multimesh = mm
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/glint.gdshader")
	m.render_priority = 10
	glints.material_override = m
	glints.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	glints.custom_aabb = AABB(Vector3(-Terrain.HALF, -50, -Terrain.HALF), Vector3(Terrain.SIZE, 600, Terrain.SIZE))
	world.add_child.call_deferred(glints)


func _add_glint(pos: Vector3, shine: float) -> int:
	var i := _glint_count
	if i >= glints.multimesh.instance_count:
		return -1
	_glint_count += 1
	glints.multimesh.visible_instance_count = _glint_count
	glints.multimesh.set_instance_transform(i, Transform3D(Basis(), pos))
	glints.multimesh.set_instance_color(i, Color(1, 1, 1, 1))
	glints.multimesh.set_instance_custom_data(i, Color(shine, randf(), 0, 0))
	return i


func _set_glint(i: int, shine: float) -> void:
	if i >= 0:
		var c := glints.multimesh.get_instance_custom_data(i)
		glints.multimesh.set_instance_custom_data(i, Color(shine, c.g, 0, 0))


func _process(delta: float) -> void:
	if not intro_done and Game.player and not Shots.active and not Game.busy:
		intro_done = true
		Game.say("Six cameras. Take the films, then radio from the lookout.", 7.0)
	_find_item()
	_update_hidden()
	_reacher_ground()
	_colossus_triggers()
	_road(delta)
	_ending(delta)
	if playing and film_index >= 0:
		_film_frame(delta)
	_update_objective()
	if _scare_left > 0.0:
		_scare_left -= delta
		if _scare_left <= 0.0:
			_death_card()


func _find_item() -> void:
	current = {}
	if Game.busy or Game.player == null:
		return
	var cam: Camera3D = Game.player.cam
	var eye := cam.global_position
	var fwd := -cam.global_basis.z
	var best := 0.5
	for item: Dictionary in items:
		if item.used:
			continue
		var to: Vector3 = (item.pos as Vector3) - eye
		var d := to.length()
		if d > item.radius:
			continue
		var facing := fwd.dot(to / maxf(d, 0.01))
		if facing > best:
			best = facing
			current = item


func prompt() -> String:
	if reading:
		return "E    put it down"
	return ("E    " + current.prompt) if not current.is_empty() else ""


func interact() -> void:
	if reading:
		_close_paper()
		return
	if Game.busy or current.is_empty():
		return
	var item := current
	if item.once:
		item.used = true
		_set_glint(item.glint, 0.0)
	(item.action as Callable).call()


func _update_hidden() -> void:
	var was := Game.hidden
	Game.hidden = false
	if Game.player == null:
		return
	var p: Vector3 = Game.player.global_position + Vector3(0, 1.0, 0)
	var still: bool = Vector2(Game.player.velocity.x, Game.player.velocity.z).length() < 0.4
	var inside := false
	for h in hides:
		if Vector2(h.x - p.x, h.z - p.z).length() < 0.75 and absf(h.y - p.y) < 1.5:
			inside = true
			if still and not Game.scope_on:
				Game.hidden = true
			Game.hint("locker", "A locker. Stand in it, keep still, scope off, and it cannot find you.", 6.0)
	if inside != _in_locker:
		_in_locker = inside
		world.sfx.play("locker", -10.0 if inside else -14.0, randf_range(0.95, 1.05))
	if Game.hidden and not was and world.reacher and world.reacher.is_hunting():
		Game.say("Hidden.", 2.0)


func read(key: String, where: Vector3) -> void:
	reading = true
	Game.busy = true
	world.sfx.play("paper", -6.0)
	var from := Vector2(640, 700)
	if Game.player:
		var cam: Camera3D = Game.player.cam
		if not cam.is_position_behind(where):
			var v := cam.unproject_position(where)
			var size := Vector2(Game.main.view.size)
			from = Vector2(v.x / size.x * 1280.0, v.y / size.y * 960.0)
	Game.main.hud.show_paper(key, from)
	for item: Dictionary in items:
		if (item.pos as Vector3).is_equal_approx(where):
			_set_glint(item.glint, 0.3)


func _close_paper() -> void:
	reading = false
	Game.busy = false
	world.sfx.play("paper", -10.0, 0.8)
	Game.main.hud.hide_paper()


func _on_film(index: int) -> void:
	world.sfx.play("film_click", -3.0)
	Game.hint("films", "The film is from nine days ago. It shows this spot as the camera saw it.", 5.0)
	_play_film(index)


func _play_film(index: int) -> void:
	var data: Dictionary = films[index]
	if data.is_empty():
		return
	playing = true
	Game.busy = true
	Game.scope_on = false
	var mat: ShaderMaterial = Game.main.film_mat
	film_crank = world.sfx._bed("crank", -10.0)
	var aim: Vector3 = ((data.look as Vector3) - (data.cam as Vector3)).normalized()
	film_cam.global_position = (data.cam as Vector3) + aim * 0.35
	film_cam.look_at(data.look, Vector3.UP)
	film_cam.h_offset = 0.0
	film_cam.v_offset = 0.0
	film_cam.make_current()
	world.forest.warm(data.cam, 300.0)
	mat.set_shader_parameter("worn", 1.0)
	world.air.set_look(FILM_LIGHT[index])
	film_fill = world.air.add_glow((data.cam as Vector3) + aim * 5.0 + Vector3(0, 1.2, 0), 26.0, Color(0.8, 0.82, 0.86), 0.55 if FILM_LIGHT[index] == "grey" else 0.25)
	Game.main.hud.show_caption("FILM %d        %s" % [index + 1, FILM_DATES[index]])
	film_index = index
	film_t = 0.0
	film_shot = -1
	film_scared = false
	film_snow = 0.3
	film_shake = 0.0
	film_cast = world.watchers.slice(0, 4)
	film_before = []
	for w: Node3D in film_cast:
		film_before.append([w.global_position, w.rotation.y, w.visible, w.stance, w.side])
		w.set("held", true)
		w.visible = false
	var flat := Vector3(aim.x, 0.0, aim.z).normalized()
	var across := flat.cross(Vector3.UP).normalized()
	if index == 2 and world.colossus:
		var at: Vector3 = (data.cam as Vector3) + flat * 135.0 + across * 45.0
		var to: Vector3 = (data.cam as Vector3) + flat * 115.0 - across * 70.0
		world.colossus.place(Vector2(at.x, at.z), atan2(across.x, across.z))
		world.colossus.walk_route([Vector2(to.x, to.z)])
		world.colossus.step_now()
		world.air.density_scale = 0.5
		film_landed = false
	if index == 3 and world.reacher:
		world.reacher.sleep()


func _film_frame(delta: float) -> void:
	film_t += delta
	var data: Dictionary = films[film_index]
	var mat: ShaderMaterial = Game.main.film_mat
	var cuts: Array = FILM_SHOTS[film_index]
	var length: float = FILM_SECONDS[film_index]
	var shot := 0
	for k in cuts.size():
		if film_t >= float(cuts[k][0]):
			shot = k
	if shot != film_shot:
		film_shot = shot
		if shot > 0:
			mat.set_shader_parameter("frame", Vector4(randf_range(-0.02, 0.02), randf_range(-0.03, 0.03), 1.25, 1.0))
			world.sfx.play("static_hit", -18.0, randf_range(0.9, 1.2))
			film_snow = 0.45
	var cam_y: float = (data.cam as Vector3).y
	var places: Array = cuts[shot][1]
	var after: Array = cuts[shot + 1][1] if shot + 1 < cuts.size() else []
	var t0: float = cuts[shot][0]
	var t1: float = cuts[shot + 1][0] if shot + 1 < cuts.size() else length
	var u := clampf((film_t - t0) / maxf(t1 - t0, 0.01), 0.0, 1.0)
	var eye := film_cam.global_position
	var ahead := Vector3(-film_cam.global_basis.z.x, 0.0, -film_cam.global_basis.z.z).normalized()
	var right := ahead.cross(Vector3.UP).normalized()
	var watch := eye
	if film_index == 2 and world.colossus:
		watch = world.colossus.body_point()
	for k in film_cast.size():
		var w: Node3D = film_cast[k]
		if film_scared and k == 0:
			continue
		if k >= places.size():
			w.visible = false
			continue
		var a := Vector2(places[k][0], places[k][1])
		var b := Vector2(after[k][0], after[k][1]) if k < after.size() else a
		var p := a.lerp(b, u * FILM_DRIFT)
		var at := eye + ahead * p.x + right * p.y
		at.y = _floor_under(at, cam_y)
		w.global_position = at
		w.visible = true
		w.body.visible = true
		w.set("_shown", true)
		var d := watch - at
		w.rotation.y = atan2(-d.x, -d.z)
		if a.distance_to(b) > 1.0:
			w.side = 1.0 if int(film_t / 0.42 + k) % 2 == 0 else -1.0
			w.set_stance("stride")
		else:
			w.set_stance(places[k][2])
	var flat := Vector3(film_cam.global_basis.z.x, 0.0, film_cam.global_basis.z.z).normalized() * -1.0
	var scare_at: float = FILM_SCARE[film_index]
	if film_index == 3 and world.reacher:
		if film_t >= 5.6 and not world.reacher.visible and not film_scared:
			var from: Vector3 = eye + flat * 13.0 + right * 1.0
			from.y = _floor_under(from, cam_y) + 0.3
			var goal := eye + flat * 1.0
			goal.y = from.y
			world.reacher.film_run(from, goal, 7.5)
			world.sfx.play("reacher_alert", -2.0)
	if scare_at > 0.0 and film_t >= scare_at and not film_scared:
		film_scared = true
		film_snow = 0.25
		if film_index == 3 and world.reacher:
			world.reacher.film_stop()
			world.reacher.face_the_lens(eye, -film_cam.global_basis.z, FILM_SCARE_AT[3].x)
			world.sfx.play("reacher_screech", 2.0, 1.05)
		elif not film_cast.is_empty():
			var w: Node3D = film_cast[0]
			var spot: Vector2 = FILM_SCARE_AT[film_index]
			var at := eye + flat * spot.x + right * spot.y
			at.y = _floor_under(at, cam_y)
			w.global_position = at
			var d := eye - at
			w.rotation.y = atan2(-d.x, -d.z)
			w.visible = true
			w.body.visible = true
			w.set("_shown", true)
			w.set_stance("bent")
			w.body.set_param("own_light", 0.3)
			world.sfx.play("watcher_sting", 0.0, 1.0)
		world.sfx.play("static_hit", -6.0, 0.8)
		film_shake = 0.5
	if film_index == 2 and world.colossus and not film_landed and world.colossus.swing_foot < 0 and film_t > 1.0:
		film_landed = true
		film_shake = 0.8
	if scare_at > 0.0 and film_t > scare_at + 0.35:
		film_snow = 0.9
	film_snow = move_toward(film_snow, 0.04, delta * 3.0) if film_snow < 0.85 else film_snow
	mat.set_shader_parameter("snow", film_snow)
	film_shake = move_toward(film_shake, 0.0, delta * 0.9)
	film_cam.h_offset = randf_range(-1.0, 1.0) * film_shake * 0.05
	film_cam.v_offset = randf_range(-1.0, 1.0) * film_shake * 0.07
	if film_t >= length:
		_end_film()


func _end_film() -> void:
	var index := film_index
	var mat: ShaderMaterial = Game.main.film_mat
	for k in film_cast.size():
		var w: Node3D = film_cast[k]
		w.global_position = film_before[k][0]
		w.rotation.y = film_before[k][1]
		w.visible = film_before[k][2]
		w.side = film_before[k][4]
		w.set_stance(film_before[k][3])
		w.body.set_param("own_light", 0.03)
		w.set("held", false)
	if index == 3 and world.reacher:
		world.reacher.film_stop()
		world.reacher.sleep()
	mat.set_shader_parameter("worn", 0.0)
	mat.set_shader_parameter("snow", 0.0)
	film_cam.h_offset = 0.0
	film_cam.v_offset = 0.0
	world.air.set_look("")
	world.air.clear_glow(film_fill)
	Game.main.hud.show_caption("")
	if film_crank:
		film_crank.queue_free()
		film_crank = null
	film_index = -1
	Game.player.cam.make_current()
	playing = false
	Game.busy = false
	if world.reacher and world.reacher.state != 0:
		world.reacher.calm(8.0)
	_after_film(index)


func _floor_under(at: Vector3, cam_y: float) -> float:
	var ground := Terrain.height(at.x, at.z)
	var q := PhysicsRayQueryParameters3D.create(Vector3(at.x, cam_y + 0.5, at.z), Vector3(at.x, ground - 1.0, at.z), 1)
	var hit := world.get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position.y if not hit.is_empty() else ground


func _after_film(index: int) -> void:
	match index:
		0:
			Game.hint("scope", "F switches the night scope on. Its battery runs down, and it hums.", 7.0)
			if world.colossus and colossus_leg == 0:
				colossus_leg = 1
				world.colossus.place(HOLD_START, 2.6)
				world.colossus.walk_route(WALK_TO_BOMBER)
		2:
			if world.colossus and colossus_leg <= 1:
				colossus_leg = 2
				if not world.colossus.visible or world.colossus.walking:
					world.colossus.place(WALK_TO_BOMBER[1], -1.2)
				world.colossus.walk_route(WALK_PAST_BOMBER)
				world.air.density_scale = 0.62
		3:
			if world.reacher and site("sanatorium"):
				Game.say("Something is coming down the ward. Run, or get in a locker.", 5.0)
				world.reacher.start_chase(spot("sanatorium", "reacher_ward") + Vector3(0, 0.3, 0))
		5:
			if world.reacher and site("tunnel"):
				Game.say("It heard the camera. The lockers, or the hall.", 5.0)
				world.reacher.start_chase(spot("tunnel", "chase_start") + Vector3(0, 0.3, 0))
	if Game.film_total() == Game.FILM_COUNT:
		var later := create_tween()
		later.tween_interval(12.0 if index == 5 or index == 3 else 1.0)
		later.tween_callback(func() -> void: Game.say("Six films. Get to the fire lookout and call it in.", 7.0))


func resume() -> void:
	intro_done = true
	for i: int in film_items:
		if Game.films[i]:
			var item: Dictionary = film_items[i]
			item.used = true
			_set_glint(item.glint, 0.0)
	var leg := 0
	if Game.films[0]:
		leg = 1
	if Game.films[2]:
		leg = 2
	if Game.films[4]:
		leg = 3
	if Game.films[5]:
		leg = 4
	colossus_leg = leg
	if world.colossus and leg > 0:
		var route: Array = [WALK_TO_BOMBER, WALK_PAST_BOMBER, WALK_PAST_RADAR, WALK_OVER_HALL][leg - 1]
		world.colossus.place(route[route.size() - 1], -1.2)
	var here := Game.checkpoint
	var i := Terrain.track_index(here.x, here.z)
	var along: float = Terrain.track_at[i] if i >= 0 else 0.0
	road_done = 0
	while road_done < ROAD.size() and along >= float(ROAD[road_done][0]) - 28.0:
		road_done += 1
	approach_saved = 0
	for k in range(1, STOPS.size()):
		var c := stop_point(k)
		if Vector2(c.x - here.x, c.z - here.z).length() < 110.0:
			approach_saved = k
	_update_objective()
	Rig.note("story", "resumed at film %d" % Game.film_total())


func next_stop() -> int:
	for i in Game.FILM_COUNT:
		if not Game.films[i]:
			return i
	return 6


func stop_point(i: int) -> Vector3:
	var s := site(STOPS[i])
	return s.global_position if s else Vector3.ZERO


func _update_objective() -> void:
	if Game.player == null or Game.ended:
		return
	var stop := next_stop()
	var to := stop_point(stop) - Game.player.global_position
	var d := Vector2(to.x, to.z)
	var names := ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
	var bearing: String = names[int(round(atan2(d.x, -d.y) / (PI / 4.0))) & 7]
	var text := "%s    %d m %s" % [STOP_NAMES[stop].capitalize(), int(round(d.length() / 10.0) * 10), bearing]
	if d.length() < 60.0:
		text = STOP_NAMES[stop].capitalize()
	if text != Game.objective:
		Game.set_objective(text)


func _reacher_ground() -> void:
	var reacher: Node3D = world.reacher
	if Game.player == null or reacher == null or Game.dead:
		return
	var here: Vector3 = Game.player.global_position
	var pp := Vector2(here.x, here.z)
	for i in range(approach_saved + 1, STOPS.size()):
		var c := stop_point(i)
		if pp.distance_to(Vector2(c.x, c.z)) < 110.0 and not reacher.is_hunting() and Game.player.is_on_floor():
			approach_saved = i
			Game.save_here()
			Game.save_game()
	var top := stop_point(6)
	if pp.distance_to(Vector2(top.x, top.z)) < 150.0:
		if reacher.state != 0:
			reacher_site = -1
			reacher.sleep()
		return
	if reacher.is_hunting():
		return
	for i in range(1, 6):
		var c := stop_point(i)
		if pp.distance_to(Vector2(c.x, c.z)) < 130.0:
			if reacher_site != i:
				reacher_site = i
				_settle_reacher(i, pp)
			return
	if reacher_site != -1 and reacher.global_position.distance_to(here) > 200.0:
		reacher_site = -1
		reacher.sleep()


func _settle_reacher(i: int, pp: Vector2) -> void:
	var reacher: Node3D = world.reacher
	var place: String = STOPS[i]
	var c := stop_point(i)
	var away := (Vector2(c.x, c.z) - pp).normalized()
	match place:
		"church":
			if not Game.films[i]:
				reacher.set_route([spot(place, "reacher_home"), spot(place, "nave"), spot(place, "door") + Vector3(-9, 0, 5), spot(place, "door") + Vector3(-9, 0, -6)])
			else:
				reacher.set_home(Terrain.on_ground(Vector2(c.x, c.z) + away * 34.0), 18.0)
		"sanatorium", "tunnel":
			reacher.set_home(Terrain.on_ground(Vector2(c.x, c.z) + away * 62.0), 16.0)
		_:
			var tripod: Variant = null
			if not Game.films[i] and not films[i].is_empty():
				var t: Vector3 = films[i].cam
				tripod = Vector3(t.x, Terrain.height(t.x, t.z), t.z)
			reacher.set_home(Terrain.on_ground(Vector2(c.x, c.z) + away * 20.0), 26.0, tripod)


func _colossus_triggers() -> void:
	var colossus: Node3D = world.colossus
	if colossus == null or Game.player == null or Game.ended:
		return
	var here: Vector3 = Game.player.global_position
	if world.air.density_scale < 1.0 and colossus.visible and colossus.body_point().distance_to(here) > 330.0 and colossus_leg != 3:
		world.air.density_scale = 1.0
	if colossus_leg == 2 and Game.films[3] and site("radar") and here.distance_to(spot("radar", "hut_door")) < 42.0:
		colossus_leg = 3
		colossus.place(WALK_PAST_BOMBER[WALK_PAST_BOMBER.size() - 1], -1.0)
		colossus.walk_route(WALK_PAST_RADAR)
		world.air.density_scale = 0.5
		Rig.note("colossus", "past the radar mast")
	if colossus_leg == 3 and Game.films[4] and site("tunnel") and here.distance_to(spot("tunnel", "hall_center")) < 13.0:
		colossus_leg = 4
		if colossus.walking or colossus.body_point().distance_to(Vector3(150, colossus.body_point().y, -900)) > 60.0:
			colossus.place(WALK_PAST_RADAR[WALK_PAST_RADAR.size() - 1], -1.4)
		colossus.hurry = true
		colossus.walk_route(WALK_OVER_HALL)
		world.air.density_scale = 0.45
		Game.hint("hall", "Look up.", 4.0)
		Rig.note("colossus", "over the hall")
	if world.water and world.water.material_override:
		var shake: float = world.water.material_override.get_shader_parameter("shake") if world.water.material_override.get_shader_parameter("shake") != null else 0.0
		if shake > 0.001:
			world.water.material_override.set_shader_parameter("shake", maxf(shake - get_process_delta_time() * 0.25, 0.0))


func on_footfall(pos: Vector3, _left: bool) -> void:
	if world.water and world.water.material_override and Game.player:
		var d: float = Game.player.global_position.distance_to(pos)
		world.water.material_override.set_shader_parameter("shake", clampf(700.0 / maxf(d, 80.0), 0.0, 1.0))


func _progress() -> float:
	var p: Vector3 = Game.player.global_position
	var i := Terrain.track_index(p.x, p.z)
	return Terrain.track_at[i] if i >= 0 else -1.0


func _spare_watcher(min_distance := 110.0) -> Node3D:
	var here: Vector3 = Game.player.global_position
	var best: Node3D = null
	var best_d := 0.0
	for w: Node3D in world.watchers:
		if w.part != 0 or w.held or line.has(w):
			continue
		var d := w.global_position.distance_to(here)
		if d > min_distance and d > best_d:
			best_d = d
			best = w
	return best


func _road(delta: float) -> void:
	if Game.player == null or Game.busy or Game.ended or world.watchers.is_empty():
		return
	var along := _progress()
	if along < 0.0:
		return
	stalk_wait -= delta
	if stalk_wait <= 0.0:
		stalk_wait = 18.0
		var allowed := 0
		if Game.films[0]:
			allowed = 1
		if Game.films[2]:
			allowed = 2
		var here: Vector3 = Game.player.global_position
		var count := 0
		for w: Node3D in world.watchers:
			if w.part == 1:
				count += 1
		if count < allowed:
			var cam: Camera3D = Game.player.cam
			var nearest: Node3D = null
			var nd := 170.0
			for w: Node3D in world.watchers:
				var d := w.global_position.distance_to(here)
				if w.part == 0 and not w.held and not line.has(w) and d < nd and d > 35.0 and not w.seen_by(cam):
					nd = d
					nearest = w
			if nearest == null:
				nearest = _spare_watcher(60.0)
			if nearest:
				nearest.part = 1
				Rig.note("watcher", "one starts to follow")
	while road_done < ROAD.size() and along >= float(ROAD[road_done][0]) - 28.0:
		var ev: Array = ROAD[road_done]
		road_done += 1
		_road_event(float(ev[0]), ev[1], int(ev[2]))


func _road_event(at_m: float, what: String, n: int) -> void:
	var p := Terrain.track_point(at_m)
	var ahead := (Terrain.track_point(at_m + 6.0) - p).normalized()
	var side := Vector3(-ahead.z, 0, ahead.x)
	Rig.note("road", what, "%d m" % int(at_m))
	match what:
		"crack":
			var from := p + side * (26.0 if n == 0 else -26.0) + ahead * 12.0
			world.sfx.play_at("branch_crack", from + Vector3(0, 1, 0), 0.0, 90.0, randf_range(0.85, 1.1))
		"ambush":
			var w := _spare_watcher()
			var forest: Node = world.forest
			if w == null or forest == null:
				return
			for tries in 6:
				var q: Vector3 = p + ahead * (tries * 3.0) + side * (5.0 * n)
				var trunk: Vector3 = forest.nearest_trunk(q)
				if trunk == Vector3.ZERO:
					continue
				var d := Terrain.track_distance(trunk.x, trunk.y)
				if d > 2.6 and d < 9.0:
					w.lie_in_wait(trunk, p + ahead * (tries * 3.0))
					return
		"ahead":
			var w := _spare_watcher()
			if w:
				var q := Terrain.track_point(at_m + 30.0)
				w.global_position = q
				w.set_stance("stand")
				w.rotation.y = atan2(ahead.x, ahead.z)
				w.unseen_time = 0.0
		"line":
			var top := stop_point(6)
			for k in 8:
				var w := _spare_watcher(60.0)
				if w == null:
					break
				var q := Terrain.track_point(at_m + 16.0 + k * 13.0) + side * (4.2 if k % 2 == 0 else -4.6)
				q.y = Terrain.height(q.x, q.z)
				w.global_position = q
				w.held = true
				w.side = 1.0
				w.set_stance(["stand", "askew", "stand", "bent"][k % 4])
				var d := top - q
				w.rotation.y = atan2(-d.x, -d.z)
				line.append(w)
		"turn":
			for w: Node3D in line:
				var d: Vector3 = Game.player.global_position - w.global_position
				if not w.seen_by(Game.player.cam):
					w.rotation.y = atan2(-d.x, -d.z)
					w.set_stance("reach" if randf() < 0.4 else "askew")
		"release":
			for w: Node3D in line:
				w.held = false
			line.clear()


func _on_death(how: String) -> void:
	var mat: ShaderMaterial = Game.main.film_mat
	if how == "reacher" and world.reacher:
		var cam: Camera3D = Game.player.cam
		world.reacher.face_the_lens(cam.global_position, -cam.global_basis.z)
		Game.player.zoom_target = 1.0
		cam.fov = 60.0
		Game.player.shake = 1.4
		world.sfx.play("death_hit", 2.0)
		world.sfx.play("reacher_screech", 6.0, 1.1)
	_scare_left = 0.7
	mat.set_shader_parameter("jitter", 1.0)


func _death_card() -> void:
	var mat: ShaderMaterial = Game.main.film_mat
	world.sfx.play("film_burn", -2.0)
	var tw := create_tween().set_parallel(true)
	tw.tween_method(func(v: float) -> void: mat.set_shader_parameter("snow", v), 0.0, 1.0, 0.25)
	tw.tween_method(func(v: float) -> void: mat.set_shader_parameter("dark", v), 0.0, 0.82, 0.5)
	var lines := ["It heard you.", "It is blind. It hears you run.", "Walk near the ruins. Crouch. Stand still when it clicks.", "The lockers hide you, if you keep still."]
	Game.main.hud.show_death(lines[mini(Game.deaths - 1, lines.size() - 1)] if Game.deaths <= 3 else lines[randi() % lines.size()])


func _on_back() -> void:
	var mat: ShaderMaterial = Game.main.film_mat
	mat.set_shader_parameter("snow", 0.0)
	mat.set_shader_parameter("dark", 0.0)
	mat.set_shader_parameter("jitter", 0.0)
	if world.reacher and world.reacher.state != 0:
		world.reacher.restart()
		world.reacher.calm(6.0)
	Game.say("FILM %d. Again." % Game.film_total(), 3.0)


func radio_call() -> void:
	if Game.ended:
		return
	if Game.film_total() < Game.FILM_COUNT:
		Game.say("%d films still out there. Take all six first." % (Game.FILM_COUNT - Game.film_total()))
		return
	Game.ended = true
	Game.scope_on = false
	ending_step = 1
	if world.reacher:
		world.reacher.sleep()
	world.air.density_scale = 1.0
	var colossus: Node3D = world.colossus
	var top := stop_point(6)
	var stand := Vector2(top.x - 250.0, top.z + 170.0)
	if colossus:
		var to := Vector2(top.x, top.z) - stand
		colossus.place(stand, atan2(-to.x, -to.y) + 1.9)
		colossus.hurry = true
	var static_bed: AudioStreamPlayer = world.sfx._bed("radio_static", -8.0)
	var tw := create_tween()
	tw.tween_callback(func() -> void: Game.say("\"Hochwald to Regensburg. Six films recovered. Team not found. Over.\"", 6.0))
	tw.tween_interval(7.5)
	tw.tween_callback(func() -> void:
		static_bed.queue_free()
		world.sfx.on_about_to_step())
	tw.tween_interval(3.5)
	tw.tween_callback(func() -> void:
		world.sfx.play("colossus_voice", 4.0)
		Game.player.shake = 0.5
		if colossus:
			colossus.look_at_point = top + Vector3(0, 13, 0))
	tw.tween_interval(3.0)
	tw.tween_callback(func() -> void: Game.say("Something is answering.", 5.0))
	tw.tween_interval(4.0)
	tw.tween_callback(func() -> void:
		ending_step = 2
		if colossus:
			var near := Vector2(top.x - 58.0, top.z + 34.0)
			colossus.walk_route([near])
		else:
			ending_step = 3)


func _ending(delta: float) -> void:
	if ending_step < 2 or ending_step >= 4:
		return
	var colossus: Node3D = world.colossus
	var player: Node3D = Game.player
	var top := stop_point(6)
	if colossus == null:
		ending_step = 4
		_end_card()
		return
	if ending_step == 2:
		colossus.look_at_point = player.global_position + Vector3(0, 1.6, 0)
		if not colossus.walking:
			ending_step = 3
			_ending_time = 0.0
			world.sfx.play("colossus_voice", 6.0, 0.9)
			player.shake = 0.8
		return
	_ending_time += delta
	var t := _ending_time
	colossus.look_at_point = player.global_position + Vector3(0, 1.6, 0)
	colossus.crouch = smoothstep(0.0, 9.0, t)
	colossus.bend = smoothstep(1.0, 10.0, t) * 0.85
	colossus.mouth = smoothstep(7.0, 12.0, t)
	if t > 7.2 and not _roared:
		_roared = true
		world.sfx.play("colossus_roar", 2.0, 0.92)
		player.shake = maxf(player.shake, 0.9)
	var roof: Node3D = site("lookout_roof")
	var in_cabin: bool = player.global_position.distance_to(top + Vector3(0, 12.3, 0)) < 5.5
	if roof and t > 6.0 and not _roof_gone and in_cabin:
		_roof_gone = true
		world.sfx.play("cable_sing", 2.0, 0.6)
		player.shake = 1.0
		var rt := create_tween()
		rt.tween_property(roof, "position", roof.position + Vector3(-70, 190, 50), 7.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		rt.parallel().tween_property(roof, "rotation", Vector3(0.6, 0.9, -0.4), 7.0)
	if t > 9.0:
		colossus.reach_point = player.global_position + Vector3(0, 6.0, 0)
		colossus.reach_blend = smoothstep(9.0, 15.5, t)
		player.shake = maxf(player.shake, 0.25 + 0.5 * colossus.reach_blend)
	if t > 15.5:
		ending_step = 4
		Game.clear_save()
		Rig.note("ending", "taken")
		Rig.shoot("taken")
		world.sfx.play("colossus_roar", 8.0, 1.08)
		world.sfx.play("death_hit", 0.0, 0.8)
		world.sfx.play("film_burn", 3.0)
		player.shake = 2.0
		var film: ShaderMaterial = Game.main.film_mat
		var tw := create_tween()
		tw.tween_method(func(v: float) -> void: film.set_shader_parameter("snow", v), 0.0, 1.0, 0.35)
		tw.parallel().tween_method(func(v: float) -> void: film.set_shader_parameter("dark", v), 0.0, 1.0, 0.9)
		tw.tween_interval(1.2)
		tw.tween_callback(_end_card)


func _end_card() -> void:
	Game.busy = true
	Game.main.hud.show_end()

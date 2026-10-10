extends Node

var active := false
var day := false
var only := ""
var ats: Array[PackedFloat64Array] = []
var site := ""
var looks: Array[PackedFloat64Array] = []
var site_only := false
var creature := ""
var stances := false
var scare := false


func _enter_tree() -> void:
	var args := OS.get_cmdline_user_args()
	active = "--shots" in args
	day = "--day" in args
	for a in args:
		if a.begins_with("--only="):
			only = a.substr(7)
		if a.begins_with("--at="):
			ats.append(a.substr(5).split_floats(","))
			only = "at_"
		if a.begins_with("--look="):
			var lv := PackedFloat64Array()
			for part in a.trim_prefix("--look=").split(","):
				lv.append(part.to_float())
			looks.append(lv)
		if a == "--looks-only":
			site_only = true
		if a.begins_with("--site="):
			site = a.substr(7)
			only = "at_"
		if a.begins_with("--creature="):
			creature = a.substr(11)
			only = "at_"
		if a == "--stances":
			stances = true
			only = "at_"
		if a == "--scare":
			scare = true
			only = "at_"


func _ready() -> void:
	if active:
		_run.call_deferred()
	elif "--intro" in OS.get_cmdline_user_args():
		_intro_run.call_deferred()


func _intro_run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://screenshots"))
	var main: Control = Game.main
	while main.intro == null or not main.intro.world_ready:
		await get_tree().process_frame
	for i in 6:
		await get_tree().process_frame
	await _grab("90_intro_leader")
	main.intro.count = 2
	main.intro.sweep = 0.99
	for i in 6:
		await get_tree().process_frame
	main.intro.typed = 100000.0
	for i in 6:
		await get_tree().process_frame
	await _grab("91_intro_order")
	var ev := InputEventAction.new()
	ev.action = "interact"
	ev.pressed = true
	main.intro._input(ev)
	main.intro.hold = 3.0
	for i in 8:
		await get_tree().process_frame
	await _grab("92_intro_title")
	Game.main.pause.open()
	Game.main.pause.process_mode = Node.PROCESS_MODE_ALWAYS
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in 4:
		await get_tree().process_frame
	await _grab("93_pause")
	get_tree().quit()


func _grab(shot: String) -> void:
	await RenderingServer.frame_post_draw
	get_tree().root.get_texture().get_image().save_png("res://screenshots/%s.png" % shot)
	print("shot ", shot)


func _run() -> void:
	for i in 3:
		await get_tree().process_frame
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://screenshots"))
	Rig._keep_out_of_godot("res://screenshots")
	var cam := Camera3D.new()
	cam.near = 0.15
	cam.far = 3200.0
	cam.fov = 60.0
	var root := get_tree().get_first_node_in_group("world_root")
	for i in 40:
		await get_tree().physics_frame
	if Game.player:
		var pp: Vector3 = Game.player.global_position
		print("player y %.2f, ground %.2f, on floor %s" % [pp.y, preload("res://scripts/terrain.gd").height(pp.x, pp.z), Game.player.is_on_floor()])
	root.add_child(cam)
	var terrain := preload("res://scripts/terrain.gd")
	for i in ats.size():
		var v := ats[i]
		if v.size() < 6:
			continue
		var m := Marker3D.new()
		m.name = "at_%02d" % i
		root.add_child(m)
		m.global_position = Vector3(v[0], terrain.height(v[0], v[2]) + v[1], v[2])
		m.look_at(Vector3(v[3], terrain.height(v[3], v[5]) + v[4], v[5]))
		m.add_to_group("shot_cam")
	if site != "":
		_site_shots(root, terrain)
	if creature != "":
		_creature_shots(root, terrain)
	if stances:
		_stance_shots(root, terrain)
	if scare:
		var at: Vector3 = terrain.track_point(60.0) + Vector3(0, 1.65, 0)
		var ahead: Vector3 = (terrain.track_point(70.0) - terrain.track_point(60.0)).normalized()
		_add("at_00_scare", root, at, at + ahead * 4.0)
		_add("at_01_scare_from_side", root, at + ahead * 1.2 + ahead.cross(Vector3.UP) * 3.2 + Vector3(0, -0.4, 0), at + ahead * 1.2 + Vector3(0, -0.5, 0))
		var r: Node = root.get("reacher")
		if r == null:
			r = CharacterBody3D.new()
			r.set_script(load("res://scripts/reacher.gd"))
			root.add_child(r)
		r.face_the_lens(at, ahead)
	for m: Node3D in get_tree().get_nodes_in_group("shot_cam"):
		if only != "" and not only in String(m.name):
			continue
		if m.has_meta("setup"):
			(m.get_meta("setup") as Callable).call()
		cam.global_transform = m.global_transform
		var world := get_tree().get_first_node_in_group("world_root")
		if world.get("forest"):
			world.forest.warm(m.global_position, 760.0)
		cam.make_current()
		Game.scope_on = "scope" in String(m.name)
		cam.fov = 60.0 / (6.0 if "zoom" in String(m.name) else 1.0)
		Game.zoom = 6.0 if "zoom" in String(m.name) else 1.0
		for i in 12:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_tree().root.get_texture().get_image().save_png("res://screenshots/%s%s.png" % [m.name, "_day" if day else ""])
		print("shot %-28s objects %5d  draw calls %5d  triangles %8d" % [m.name, Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)])
	get_tree().quit()


func _site_shots(root: Node, terrain: GDScript) -> void:
	var text := FileAccess.get_file_as_string("res://assets/gen/sites/%s.json" % site)
	if text == "":
		push_warning("no such place: " + site)
		return
	var info: Dictionary = JSON.parse_string(text)
	var o: Array = info.origin
	var lo: Array = info.box[0]
	var hi: Array = info.box[1]
	var yaw: float = info.yaw
	var turn := Basis(Vector3.UP, yaw)
	var mid_local := Vector3((lo[0] + hi[0]) * 0.5, clampf((lo[1] + hi[1]) * 0.5, 1.0, 6.0), (lo[2] + hi[2]) * 0.5)
	var mid: Vector3 = Vector3(o[0], o[1], o[2]) + turn * mid_local
	var reach := minf(maxf(hi[0] - lo[0], hi[2] - lo[2]) * 0.62 + 7.0, 60.0)
	var n := 0
	for v in looks:
		if v.size() < 6:
			continue
		var from: Vector3 = Vector3(o[0], 0, o[2]) + turn * Vector3(v[0], 0, v[2])
		var toward: Vector3 = Vector3(o[0], 0, o[2]) + turn * Vector3(v[3], 0, v[5])
		from.y = terrain.height(from.x, from.z) + v[1]
		toward.y = terrain.height(toward.x, toward.z) + v[4]
		_add("at_%02d_look" % n, root, from, toward)
		n += 1
	if site_only:
		return
	for a in [0.6, 2.2, 3.8, 5.4]:
		var at := mid + Vector3(cos(a), 0, sin(a)) * reach
		at.y = terrain.height(at.x, at.z) + 1.7
		_add("at_%02d_outside" % n, root, at, mid)
		n += 1
	var marks: Dictionary = info.marks
	for key: String in marks:
		var p: Array = marks[key].pos
		var at := Vector3(p[0], p[1] + (1.3 if "paper" not in key and "camera" not in key else 0.35), p[2])
		var to := mid
		if at.distance_to(mid) < 2.5:
			to = at + Basis(Vector3.UP, marks[key].yaw) * Vector3(0, 0, -4)
		if marks[key].has("eye"):
			at = Vector3(p[0], p[1] + float(marks[key].eye), p[2])
			to = at + Basis(Vector3.UP, marks[key].yaw) * Vector3(0, 0, -4)
		if "paper" in key:
			at += (mid - at).normalized() * -0.9 + Vector3(0, 0.5, 0)
			to = Vector3(p[0], p[1], p[2])
		_add("at_%02d_%s" % [n, key], root, at, to)
		n += 1


func _add(shot: String, root: Node, at: Vector3, to: Vector3) -> void:
	var m := Marker3D.new()
	m.name = shot
	root.add_child(m)
	m.global_position = at
	if at.distance_to(to) > 0.05:
		m.look_at(to)
	m.add_to_group("shot_cam")


func _creature_shots(root: Node, terrain: GDScript) -> void:
	var parts := creature.split(",")
	var size := parts[1].to_float() if parts.size() > 1 else 1.0
	var c := Node3D.new()
	c.set_script(load("res://scripts/creature.gd"))
	root.add_child(c)
	if not c.setup(parts[0]):
		push_warning("no such body: " + parts[0])
		return
	var at: Vector3 = terrain.track_point(60.0)
	c.global_position = at
	c.scale = Vector3.ONE * size
	if parts[0].begins_with("watcher"):
		c.set_param("own_light", 0.05)
	if parts[0] == "colossus":
		c.set_param("pattern", 0.012)
		c.set_param("veins", 1.0)
		c.set_param("vein_color", Vector3(0.75, 0.16, 0.12))
	var box: Array = c._info.get("box", [[-1, 0, -1], [1, 2, 1]])
	var tall: float = float(box[1][1]) * size
	var mid := at + Vector3(0, tall * 0.55, 0)
	var back := tall * 1.25 + 0.8
	var n := 0
	for a in [0.0, 0.8, 1.57, 3.14, 4.4]:
		_add("at_%02d_side" % n, root, mid + Vector3(sin(a), 0.05, -cos(a)) * back, mid)
		n += 1
	var head: Vector3 = c.where("head") + Vector3(0, 0.1 * size, 0)
	var far := maxf(tall / 2.6, 1.0)
	_add("at_%02d_zoom_head" % n, root, head + Vector3(0.3, -0.25, -3.0) * far, head + Vector3(0, -0.03, 0) * size * far)
	_add("at_%02d_zoom_head_side" % (n + 1), root, head + Vector3(2.2, -0.2, -2.1) * far, head + Vector3(0, -0.03, 0) * size * far)
	if tall > 50.0:
		var chest: Vector3 = c.where("chest") + Vector3(0, tall * 0.04, 0)
		_add("at_%02d_zoom_chest" % (n + 3), root, chest + Vector3(0.5, -0.1, -3.2) * far, chest)
		_add("at_%02d_from_below" % (n + 4), root, at + Vector3(40, 1.7, -70), head)
	if c.has("hand_l"):
		var hand: Vector3 = c.where("hand_l")
		_add("at_%02d_hand" % (n + 2), root, hand + Vector3(-0.45, 0.1, -0.5) * size, hand + Vector3(0, -0.1, 0) * size)


func _stance_shots(root: Node, terrain: GDScript) -> void:
	var Watcher := load("res://scripts/watcher.gd")
	var keys: Array = Watcher.STANCES.keys()
	var at: Vector3 = terrain.track_point(60.0)
	var along := Vector3(1, 0, 0)
	for i in keys.size():
		var w := Node3D.new()
		w.set_script(Watcher)
		w.face = i % 4
		w.tall = 2.6
		w.held = true
		w.stance = keys[i]
		var p := at + along * (i * 2.2)
		p.y = terrain.height(p.x, p.z)
		w.position = p
		root.add_child(w)
		w.set_stance(keys[i])
		w.rotation.y = PI
	var n := 0
	for i in range(0, keys.size(), 3):
		var mid := at + along * ((i + 1) * 2.2) + Vector3(0, 1.35, 0)
		_add("at_%02d_%s" % [n, "_".join(keys.slice(i, i + 3))], root, mid + Vector3(0, 0.1, 6.2), mid)
		n += 1

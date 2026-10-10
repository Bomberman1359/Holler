extends Node3D

const PlayerScript := preload("res://scripts/player.gd")
const Terrain := preload("res://scripts/terrain.gd")
const Sites := preload("res://scripts/sites.gd")
const Forest := preload("res://scripts/forest.gd")
const Cover := preload("res://scripts/cover.gd")
const Air := preload("res://scripts/air.gd")
const Watcher := preload("res://scripts/watcher.gd")
const Reacher := preload("res://scripts/reacher.gd")
const Colossus := preload("res://scripts/colossus.gd")
const Dust := preload("res://scripts/dust.gd")
const Sfx := preload("res://scripts/sfx.gd")
const Story := preload("res://scripts/story.gd")
const Site := preload("res://scripts/site.gd")
const MeshLib := preload("res://scripts/meshlib.gd")

var air: Node3D
var terrain: Node3D
var player: CharacterBody3D
var forest: Node3D
var cover: Node3D
var colossus: Node3D
var reacher: CharacterBody3D
var watchers: Array[Node3D] = []
var sfx: Node
var story: Node
var bare := false
var sites := {}
var water: MeshInstance3D


func _ready() -> void:
	var t0 := Time.get_ticks_msec()
	bare = "--bare" in OS.get_cmdline_user_args()
	Terrain.load_data()
	air = Node3D.new()
	air.name = "Air"
	air.set_script(Air)
	add_child(air)
	terrain = Node3D.new()
	terrain.name = "Terrain"
	terrain.set_script(Terrain)
	add_child(terrain)
	forest = Node3D.new()
	forest.name = "Forest"
	forest.set_script(Forest)
	add_child(forest)
	cover = Node3D.new()
	cover.name = "Cover"
	cover.set_script(Cover)
	add_child(cover)
	_build_water()
	print("ground and forest in ", Time.get_ticks_msec() - t0, " ms")

	player = CharacterBody3D.new()
	player.set_script(PlayerScript)
	player.name = "Player"
	player.position = Terrain.track_point(4.0) + Vector3(0, 0.5, 0)
	var ahead := Terrain.track_point(30.0) - Terrain.track_point(4.0)
	player.rotation.y = atan2(-ahead.x, -ahead.z)
	add_child(player)
	player.process_priority = 1
	Game.player = player
	Game.save_here()

	if not bare:
		_build_sites()
		_build_life()
	forest.warm(player.position)
	_add_shots()
	_test_switches()
	print("world built in ", Time.get_ticks_msec() - t0, " ms")


func _test_switches() -> void:
	var hide := String(Rig.opt("hide", ""))
	if hide == "":
		return
	for part in hide.split(","):
		match part:
			"near":
				forest.get_node("TreesNear").visible = false
			"far":
				forest.get_node("TreesFar").visible = false
			"ground":
				terrain.hide_all = true
				terrain.near_mesh.visible = false
			"sky":
				air.get_node("Sky").visible = false
			"lamp":
				Game.lamp_on = false


func _build_life() -> void:
	colossus = Node3D.new()
	colossus.name = "Colossus"
	colossus.set_script(Colossus)
	add_child(colossus)
	reacher = CharacterBody3D.new()
	reacher.name = "Reacher"
	reacher.set_script(Reacher)
	add_child(reacher)
	_add_watchers()
	sfx = Node.new()
	sfx.name = "Sfx"
	sfx.set_script(Sfx)
	add_child(sfx)
	colossus.about_to_step.connect(sfx.on_about_to_step)
	colossus.footfall.connect(sfx.on_footfall)
	colossus.footfall.connect(func(pos: Vector3, _left: bool) -> void: Dust.spawn(self, pos))
	reacher.hand_step.connect(func() -> void: sfx.play_at("reacher_step%d" % (randi() % 3), reacher.global_position, 2.0, 60.0, randf_range(0.85, 1.15)))
	reacher.click.connect(func() -> void: sfx.play_at("reacher_click", reacher.global_position + Vector3(0, 1.2, 0), 0.0, 55.0, randf_range(0.9, 1.2)))
	reacher.alerted.connect(func() -> void: sfx.play_at("reacher_alert", reacher.global_position + Vector3(0, 1.2, 0), 4.0, 80.0, randf_range(0.95, 1.05)))
	reacher.sniffed.connect(func() -> void: sfx.play_at("reacher_sniff", reacher.global_position + Vector3(0, 1.4, 0), -2.0, 40.0, randf_range(0.9, 1.1)))
	reacher.screech.connect(func() -> void: sfx.play_at("reacher_screech", reacher.global_position + Vector3(0, 1.2, 0), 6.0, 140.0))
	player.footstep.connect(sfx.on_step)
	player.landed.connect(sfx.on_land)
	player.jumped.connect(func() -> void: sfx.on_step(0.45))
	story = Node.new()
	story.name = "Story"
	story.set_script(Story)
	add_child(story)
	colossus.footfall.connect(story.on_footfall)


func add_watcher(at: Vector2, face: int, tall: float, stop := 16.0) -> Node3D:
	var w := Node3D.new()
	w.set_script(Watcher)
	w.face = face
	w.tall = tall
	w.stop_distance = stop
	w.build = watchers.size() % 5
	w.position = Terrain.on_ground(at)
	add_child(w)
	watchers.append(w)
	return w


func _add_watchers() -> void:
	var spots := [
		[Sites.GASTHAUS, Vector2(46, -70), 3, 2.4], [Sites.GASTHAUS, Vector2(-110, 30), 1, 2.9],
		[Sites.CHURCH, Vector2(-60, -40), 0, 2.6], [Sites.CHURCH, Vector2(50, -55), 2, 3.4], [Sites.CHURCH, Vector2(45, 60), 3, 2.2],
		[Sites.CHURCH_ROOF, Vector2(24, 10), 1, 3.0], [Sites.CHURCH_ROOF, Vector2(-20, -22), 0, 2.3],
		[Sites.BOMBER, Vector2(120, 30), 2, 2.8], [Sites.BOMBER, Vector2(110, -90), 3, 3.8], [Sites.BOMBER, Vector2(-30, 125), 0, 2.5],
		[Sites.SANATORIUM, Vector2(70, 40), 0, 3.2], [Sites.SANATORIUM, Vector2(-60, 70), 1, 2.4], [Sites.SANATORIUM, Vector2(55, -80), 2, 2.7], [Sites.SANATORIUM, Vector2(-80, -45), 3, 3.9],
		[Sites.RADAR, Vector2(50, 60), 1, 2.5], [Sites.RADAR, Vector2(-70, -25), 0, 3.0], [Sites.RADAR, Vector2(15, -80), 3, 2.6],
		[Sites.TUNNEL, Vector2(-70, 40), 2, 3.6], [Sites.TUNNEL, Vector2(-60, -70), 0, 2.4], [Sites.TUNNEL, Vector2(-40, 90), 1, 3.1], [Sites.TUNNEL, Vector2(10, -110), 3, 2.8],
		[Sites.LOOKOUT, Vector2(-45, 40), 0, 3.4], [Sites.LOOKOUT, Vector2(40, 50), 1, 2.6], [Sites.LOOKOUT, Vector2(-30, -45), 2, 3.0],
		[Sites.FORD, Vector2(60, 40), 3, 2.9], [Sites.FORD, Vector2(-70, -30), 0, 2.5],
	]
	for s: Array in spots:
		add_watcher((s[0] as Vector2) + (s[1] as Vector2), s[2], s[3], 12.0 + fmod((s[3] as float) * 7.3, 12.0))


func _build_water() -> void:
	if not FileAccess.file_exists("res://assets/gen/mesh/water.hmesh"):
		return
	water = MeshInstance3D.new()
	water.name = "Water"
	water.mesh = MeshLib.load_mesh("res://assets/gen/mesh/water.hmesh").mesh
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/water.gdshader")
	m.set_shader_parameter("ripple", load("res://assets/gen/tex/film_grain.png"))
	m.render_priority = -1
	water.material_override = m
	water.custom_aabb = AABB(Vector3(-Terrain.HALF, -20, -Terrain.HALF), Vector3(Terrain.SIZE, 400, Terrain.SIZE))
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(water)


func _build_sites() -> void:
	var text := FileAccess.get_file_as_string(Site.DIR + "index.json")
	if text == "":
		return
	for site_name: String in JSON.parse_string(text):
		var site := Node3D.new()
		site.set_script(Site)
		add_child(site)
		if site.setup(site_name, air):
			sites[site_name] = site
		else:
			site.queue_free()
	if sites.has("spawn") and sites["spawn"].has_mark("start"):
		player.position = sites["spawn"].mark("start")
		player.rotation.y = sites["spawn"].mark_yaw("start")
		Game.save_here()


func add_shot(shot_name: String, pos: Vector3, look_at_point: Vector3, setup := Callable()) -> void:
	var m := Marker3D.new()
	m.name = shot_name
	if setup.is_valid():
		m.set_meta("setup", setup)
	add_child(m)
	m.global_position = pos
	m.look_at(look_at_point, Vector3.UP)
	m.add_to_group("shot_cam")


func _add_shots() -> void:
	var eye := Vector3(0, 1.65, 0)
	var total := Terrain.track_length()
	var k := 0
	var along := 6.0
	while along < total - 10.0:
		var p := Terrain.track_point(along)
		var q := Terrain.track_point(along + 22.0)
		add_shot("t%02d_track_%04dm" % [k, int(along)], p + eye, q + eye + Vector3(0, -0.35, 0))
		along += 200.0
		k += 1
	var woods := Terrain.track_point(520.0) + Vector3(22, 0, 14)
	woods.y = Terrain.height(woods.x, woods.z)
	add_shot("w01_in_the_trees", woods + eye, woods + eye + Vector3(-10, -0.4, -14))
	add_shot("w02_ground_at_feet", woods + eye, woods + Vector3(-1.2, 0.0, -1.6))
	add_shot("w03_up_the_trunks", woods + eye, woods + Vector3(-4, 14, -6))
	var top := Terrain.on_ground(Sites.LOOKOUT)
	add_shot("v01_from_the_summit", top + Vector3(0, 13, 0), Terrain.on_ground(Sites.FORD) + Vector3(0, 60, 0))
	add_shot("v02_summit_ground", top + Vector3(14, 1.65, 10), top + Vector3(0, 4, 0))
	add_shot("v03_high_over_the_valley", Vector3(120, 330, 700), Vector3(-200, 40, -350))
	if not bare:
		_add_site_shots()


func _add_site_shots() -> void:
	var eye := Vector3(0, 1.65, 0)
	var spots := {
		"spawn": ["start"], "gasthaus": ["inn_room", "street_south"], "church": ["nave"], "bomber": ["inside", "tail_view"],
		"sanatorium": ["corridor", "ward_south"], "radar": ["hut", "knee_view"], "ford": ["battle"],
		"tunnel": ["hall_center", "yard", "gallery"], "lookout": ["cabin", "stair_foot"],
	}
	for site_name: String in spots:
		if not sites.has(site_name):
			continue
		var s: Node3D = sites[site_name]
		var mid: Vector3 = s.global_transform * (s.shown.custom_aabb.get_center() as Vector3)
		mid.y = Terrain.height(mid.x, mid.z) + 3.0
		var at := Terrain.track_point(maxf(Terrain.track_meters_near(mid.x, mid.z) - 40.0, 2.0))
		add_shot("s_%s_from_track" % site_name, at + eye, mid)
		for spot: String in spots[site_name]:
			if not s.has_mark(spot):
				continue
			var p: Vector3 = s.mark(spot)
			var m: Dictionary = s.info.marks[spot]
			var h: float = m.get("eye", 1.5)
			var from := p + Vector3(0, h, 0)
			var to := mid
			if m.has("eye") or from.distance_to(mid) < 4.0:
				to = from + Basis(Vector3.UP, s.mark_yaw(spot)) * Vector3(0, 0, -4)
			add_shot("s_%s_%s" % [site_name, spot], from, to)


func _process(_delta: float) -> void:
	Game.drain_mult = 1.0
	Game.jitter = 0.0
	Game.hum = 0.0

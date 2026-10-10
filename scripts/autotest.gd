extends Node

var active := false
var only := ""
var passed := 0
var failed := 0


func _enter_tree() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--autotest":
			active = true
		elif a.begins_with("--autotest="):
			active = true
			only = a.substr(11)


func _ready() -> void:
	if active:
		_run.call_deferred()


func check(what: String, ok: bool) -> void:
	if ok:
		passed += 1
		print("  ok    ", what)
	else:
		failed += 1
		print("  FAIL  ", what)
		Rig.note("test_failed", what)


func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func wait_until(cond: Callable, max_frames := 2400) -> bool:
	for i in max_frames:
		if cond.call():
			return true
		await get_tree().process_frame
	return false


func stand_at(item: Dictionary, back := 1.2) -> void:
	var player: CharacterBody3D = Game.player
	var p: Vector3 = item.pos
	var from := p + Vector3(back, 0, 0)
	var space := player.get_world_3d().direct_space_state
	for a in 8:
		var dir := Vector3(cos(a * TAU / 8.0), 0, sin(a * TAU / 8.0))
		var q := PhysicsRayQueryParameters3D.create(p + dir * back + Vector3(0, 0.3, 0), p + dir * back + Vector3(0, -3.0, 0), 1)
		var hit := space.intersect_ray(q)
		if not hit.is_empty():
			from = hit.position
			break
	var up := PhysicsRayQueryParameters3D.create(from + Vector3(0, 0.3, 0), from + Vector3(0, 1.9, 0), 1)
	var low := not space.intersect_ray(up).is_empty()
	if low:
		Input.action_press("crouch")
		player.set("eye", 0.95)
		player.capsule.height = 1.1
		player.shape.position.y = 0.55
	else:
		Input.action_release("crouch")
	player.global_position = from + Vector3(0, 0.1, 0)
	player.velocity = Vector3.ZERO
	var to := p - (from + Vector3(0, 0.95 if low else 1.65, 0))
	player.rotation.y = atan2(-to.x, -to.z)
	player.cam.rotation.x = atan2(to.y, Vector2(to.x, to.z).length())
	player.set("pitch", player.cam.rotation.x)
	await settle()
	to = p - player.cam.global_position
	player.rotation.y = atan2(-to.x, -to.z)
	player.cam.rotation.x = atan2(to.y, Vector2(to.x, to.z).length())
	player.set("pitch", player.cam.rotation.x)
	await frames(3)


func settle() -> void:
	var player: CharacterBody3D = Game.player
	var last := player.global_position
	var calm := 0
	for i in 240:
		await get_tree().physics_frame
		await get_tree().process_frame
		if player.is_on_floor() and player.global_position.distance_to(last) < 0.004 and absf(player.cam.position.y - (0.95 if Input.is_action_pressed("crouch") else 1.65)) < 0.12:
			calm += 1
			if calm >= 3:
				return
		else:
			calm = 0
		last = player.global_position


func _item(story: Node, label: String, near: Vector3 = Vector3.INF) -> Dictionary:
	var best := {}
	var best_d := 1e12
	for it: Dictionary in story.items:
		if it.prompt != label or it.used:
			continue
		var d := 0.0 if near == Vector3.INF else (it.pos as Vector3).distance_to(near)
		if d < best_d:
			best_d = d
			best = it
	return best


func _wanted(test: String) -> bool:
	return only == "" or only in test


func _run() -> void:
	await frames(30)
	Engine.time_scale = Rig.speed(6.0)
	print("AUTOTEST")
	if only == "gait":
		await _gait()
	if only == "stride":
		await _stride()
	if only == "gait" or only == "stride":
		pass
	elif _wanted("start"):
		await _start()
	if _wanted("papers"):
		await _papers()
	if _wanted("films"):
		await _films()
	if _wanted("death"):
		await _death()
	if _wanted("ending"):
		await _ending()
	Engine.time_scale = 1.0
	print("AUTOTEST %s: %d passed, %d failed" % ["PASSED" if failed == 0 else "FAILED", passed, failed])
	if Rig.active:
		Rig.finish(0 if failed == 0 else 1)
	else:
		get_tree().quit(0 if failed == 0 else 1)


func _gait() -> void:
	Game.invulnerable = true
	Engine.time_scale = 1.0
	var player: CharacterBody3D = Game.player
	var reacher: CharacterBody3D = Game.world.reacher
	var Terrain := preload("res://scripts/terrain.gd")
	var at := player.global_position
	var fwd := -player.global_basis.z
	var right := player.global_basis.x
	var a := at + fwd * 10.0 - right * 4.5
	var b := at + fwd * 5.0 + right * 3.5
	a.y = Terrain.height(a.x, a.z)
	b.y = Terrain.height(b.x, b.z)
	reacher.set_route([a, b])
	reacher.global_position = a + Vector3(0, 0.3, 0)
	reacher._plant_all()
	reacher.patrol_index = 1
	reacher.sniff_wait = 3.5
	await seconds(11.0)
	reacher._set_state(reacher.State.LISTEN)
	await seconds(3.0)
	reacher.start_chase(reacher.global_position, 6.0)
	await seconds(2.2)
	Game.busy = true
	reacher.face_the_lens(player.cam.global_position, -player.cam.global_basis.z)
	await seconds(1.5)
	Game.busy = false
	reacher.set_route([a, b])
	print("  cost: Reacher walking, watchers on:   %s" % await _frame_cost(3.0))
	reacher.set_process(false)
	print("  cost: Reacher shown but not posed:    %s" % await _frame_cost(3.0))
	reacher.sleep()
	print("  cost: Reacher asleep, watchers on:    %s" % await _frame_cost(3.0))
	for w: Node in Game.world.watchers:
		w.set_process(false)
	print("  cost: watchers not thinking:          %s" % await _frame_cost(3.0))
	for w: Node3D in Game.world.watchers:
		w.visible = false
	print("  cost: watchers hidden:                %s" % await _frame_cost(3.0))


func _stride() -> void:
	Game.invulnerable = true
	Engine.time_scale = 1.0
	var world: Node3D = Game.world
	var player: CharacterBody3D = Game.player
	var colossus: Node3D = world.colossus
	var Terrain := preload("res://scripts/terrain.gd")
	var where := String(Rig.opt("where", "lookout"))
	var from := Vector2(430, -820)
	var to := Vector2(700, -1100)
	if where == "lookout":
		var deck: Vector3 = world.sites["lookout"].mark("deck")
		player.global_position = deck + Vector3(0, 0.2, 0)
	else:
		var at: Vector3 = Terrain.track_point(2300.0)
		player.global_position = at + Vector3(0, 0.3, 0)
		from = Vector2(at.x - 150.0, at.z - 60.0)
		to = Vector2(at.x + 170.0, at.z + 40.0)
	colossus.place(from, 0.0)
	var mid := (from + to) * 0.5
	var look := Vector3(mid.x, Terrain.height(mid.x, mid.y) + (150.0 if where == "lookout" else 40.0), mid.y)
	var d: Vector3 = look - (player.global_position + Vector3(0, 1.65, 0))
	player.rotation.y = atan2(-d.x, -d.z)
	player.cam.rotation.x = atan2(d.y, Vector2(d.x, d.z).length())
	player.set("pitch", player.cam.rotation.x)
	await seconds(1.0)
	colossus.walk_route([to])
	await seconds(float(Rig.opt("stride_seconds", 34.0)))


func _frame_cost(t: float) -> String:
	var frames_n := 0
	var process := 0.0
	var t0 := Time.get_ticks_usec()
	while Time.get_ticks_usec() - t0 < int(t * 1e6):
		await get_tree().process_frame
		frames_n += 1
		process += Performance.get_monitor(Performance.TIME_PROCESS)
	var total := (Time.get_ticks_usec() - t0) / 1000.0
	return "%.1f ms a frame, %.1f ms of it in scripts, %d draw calls" % [total / frames_n, process / frames_n * 1000.0, Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)]


func _start() -> void:
	var world: Node3D = Game.world
	var player: CharacterBody3D = Game.player
	check("the world has all its places", world.sites.size() >= 10)
	check("the player stands on the ground at the start", await wait_until(func() -> bool: return player.is_on_floor(), 300))
	check("the story is running", world.story != null and world.story.items.size() > 10)
	var story: Node = world.story
	var count := {"Read": 0, "Take the film": 0, "Take the battery": 0, "Key the radio": 0}
	for it: Dictionary in story.items:
		count[it.prompt] = count.get(it.prompt, 0) + 1
	check("twelve papers to read (found %d)" % count["Read"], count["Read"] == 12)
	check("six films to take (found %d)" % count["Take the film"], count["Take the film"] == 6)
	check("batteries lie about (found %d)" % count["Take the battery"], count["Take the battery"] >= 5)
	check("one radio", count["Key the radio"] == 1)
	check("lockers to hide in (found %d)" % story.hides.size(), story.hides.size() >= 6)


func _papers() -> void:
	var story: Node = Game.world.story
	Game.invulnerable = true
	var read := 0
	for it: Dictionary in story.items:
		if it.prompt != "Read":
			continue
		await stand_at(it, 1.0)
		await frames(4)
		if story.current == it:
			story.interact()
			await frames(3)
			if story.reading and Game.main.hud.paper.visible:
				read += 1
			else:
				print("    the paper at ", it.pos, " did not come up: reading ", story.reading, ", busy ", Game.busy, ", dead ", Game.dead)
			story.interact()
			await frames(3)
		else:
			var cam: Camera3D = Game.player.cam
			var to: Vector3 = (it.pos as Vector3) - cam.global_position
			print("    cannot reach the paper at ", it.pos, ": eye at ", cam.global_position, ", ", snappedf(to.length(), 0.01), " m away, facing ", snappedf((-cam.global_basis.z).dot(to.normalized()), 0.01), ", on floor ", Game.player.is_on_floor(), ", current ", story.current.get("prompt", "none"))
	check("every paper can be picked up and read (%d of 12)" % read, read == 12)
	check("putting a paper down gives the night back", not Game.busy and not story.reading)
	var taken := 0
	var total := 0
	for it: Dictionary in story.items:
		if it.prompt != "Take the battery":
			continue
		total += 1
		Game.battery = 20.0
		await stand_at(it, 0.9)
		await frames(4)
		if story.current == it:
			story.interact()
			await frames(3)
			if Game.battery > 60.0:
				taken += 1
		else:
			var cam: Camera3D = Game.player.cam
			var to: Vector3 = (it.pos as Vector3) - cam.global_position
			print("    cannot reach the battery at ", it.pos, ": eye at ", cam.global_position, ", ", snappedf(to.length(), 0.01), " m away, facing ", snappedf((-cam.global_basis.z).dot(to.normalized()), 0.01), ", on floor ", Game.player.is_on_floor())
	check("every battery can be taken and tops up the scope (%d of %d)" % [taken, total], taken == total)


func _films() -> void:
	var story: Node = Game.world.story
	Game.invulnerable = true
	for i in Game.FILM_COUNT:
		var data: Dictionary = story.films[i]
		if data.is_empty():
			check("film %d has a camera" % (i + 1), false)
			continue
		var it := _item(story, "Take the film", data.cam)
		await stand_at(it, 1.3)
		await frames(4)
		var found: bool = story.current == it
		if found:
			story.interact()
		await frames(4)
		check("film %d: taken, and it plays" % (i + 1), found and Game.films[i] and story.playing)
		await seconds(3.4)
		Rig.shoot("film_%d" % (i + 1))
		await wait_until(func() -> bool: return not story.playing, 3000)
		check("film %d: the night comes back after it" % (i + 1), not Game.busy)
		if Game.world.reacher:
			Game.world.reacher.sleep()
	check("all six films are in", Game.film_total() == 6)
	Game.invulnerable = false


func _death() -> void:
	var world: Node3D = Game.world
	var hud: CanvasLayer = Game.main.hud
	Game.invulnerable = false
	Game.save_here()
	var before: Vector3 = Game.player.global_position
	Game.kill_player("reacher")
	check("dying stops the night", Game.dead and Game.busy)
	await wait_until(func() -> bool: return hud.death.visible and hud.death.modulate.a > 0.9, 900)
	check("the card comes up: you died", hud.death.visible)
	Rig.shoot("death_card")
	hud._leave_death(false)
	await frames(10)
	check("going back to the last film puts you on your feet there", not Game.dead and not Game.busy and Game.player.global_position.distance_to(before) < 3.0)
	check("the card is gone and the picture is clear", not hud.death.visible and float(Game.main.film_mat.get_shader_parameter("dark")) < 0.01)
	check("deaths are counted", Game.deaths == 1)
	if world.reacher:
		world.reacher.sleep()


func _ending() -> void:
	var world: Node3D = Game.world
	var story: Node = world.story
	var radio := _item(story, "Key the radio")
	check("the lookout has its radio", not radio.is_empty())
	if radio.is_empty():
		return
	var had: Array = Game.films.duplicate()
	Game.films = [true, true, true, false, true, true]
	await stand_at(radio, 0.9)
	await frames(4)
	if story.current == radio:
		story.interact()
	await frames(3)
	check("the radio is refused while a film is still out there", not Game.ended)
	Game.films = [true, true, true, true, true, true]
	await frames(3)
	if story.current == radio:
		story.interact()
	await frames(3)
	check("with six films the call goes out", Game.ended)
	check("you can still move during the end", not Game.busy)
	Rig.shoot("ending")
	var hud: CanvasLayer = Game.main.hud
	var came := await wait_until(func() -> bool:
		var c: Node3D = world.colossus
		if c and c.visible and story.ending_step >= 1 and story.ending_step < 4:
			var d: Vector3 = c.head_point() - Game.player.cam.global_position
			Game.player.rotation.y = atan2(-d.x, -d.z)
			Game.player.cam.rotation.x = clampf(atan2(d.y, Vector2(d.x, d.z).length()), -1.3, 1.3)
			Game.player.set("pitch", Game.player.cam.rotation.x)
		return hud.end_screen != null, 9000)
	check("the end card comes", came)
	check("it took you", story.ending_step == 4)
	Game.films.assign(had)

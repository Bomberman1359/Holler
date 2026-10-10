extends Node

const SHOT_WIDTH := 1280

var active := false
var plan := ""
var opts := {}
var out := ""
var t0 := 0
var tag := ""
var finished := false

var _frames: FileAccess
var _events: FileAccess
var _shots: FileAccess
var _spans: FileAccess
var _errors: FileAccess
var _logger: RefCounted
var _last_tick := 0
var _sec_frames := 0
var _sec_time := 0.0
var _sec_worst := 0.0
var _armed := false
var _ignore := 0
var _all := PackedFloat32Array()
var _shot_n := 0
var _next_shot := 0.0
var _tasks: Array[int] = []
var _rec: AudioEffectRecord
var _rec_bus := -1
var _audio_n := 0
var _audio_cut := 0.0
var _audio_len := 60.0
var _span_name := ""
var _span_from := 0
var _span_t := 0.0
var _span_calls := 0.0
var _span_prims := 0.0
var _span_rows := 0
var _error_count := 0
var _warning_count := 0
var _notes := 0
var _hidden := 0
var _span_hidden := 0
var _script_from := 0
var _script_usec := 0
var _script_frames := 0


func _enter_tree() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--rig="):
			active = true
			plan = a.substr(6)
		elif a.begins_with("--rig-"):
			var eq := a.find("=")
			if eq > 0:
				opts[a.substr(6, eq - 6)] = a.substr(eq + 1)
			else:
				opts[a.substr(6)] = "1"
	if "--rig" in OS.get_cmdline_user_args():
		active = true
		plan = "record"


func direct() -> bool:
	return active and (plan == "tour" or plan == "walk" or plan == "parts")


func opt(key: String, fallback: Variant) -> Variant:
	if not opts.has(key):
		return fallback
	var v: String = opts[key]
	if fallback is float:
		return v.to_float()
	if fallback is int:
		return v.to_int()
	if fallback is bool:
		return v != "0" and v != "false"
	return v


func speed(usual: float) -> float:
	if not active:
		return usual
	return opt("speed", 1.0)


func now() -> float:
	return (Time.get_ticks_usec() - t0) / 1000000.0


func _ready() -> void:
	if not active:
		set_process(false)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	t0 = Time.get_ticks_usec()
	_last_tick = t0
	out = ProjectSettings.globalize_path("res://").path_join(opt("out", "test_out/runs/manual"))
	DirAccess.make_dir_recursive_absolute(out.path_join("shots"))
	_keep_out_of_godot("res://test_out")
	_frames = FileAccess.open(out.path_join("frames.csv"), FileAccess.WRITE)
	_frames.store_line("t,fps,frame_ms,worst_ms,process_ms,physics_ms,draw_calls,primitives,objects,video_mb,static_mb,nodes,x,y,z,tag")
	_events = FileAccess.open(out.path_join("events.csv"), FileAccess.WRITE)
	_events.store_line("t,kind,what,extra")
	_shots = FileAccess.open(out.path_join("shots.csv"), FileAccess.WRITE)
	_shots.store_line("t,file,label,x,y,z")
	_spans = FileAccess.open(out.path_join("spans.csv"), FileAccess.WRITE)
	_spans.store_line("name,seconds,frames,fps,median_ms,worst_ms,draw_calls,primitives,hidden_frames,script_ms")
	_errors = FileAccess.open(out.path_join("errors.log"), FileAccess.WRITE)
	if ClassDB.class_exists("Logger"):
		_logger = (load("res://scripts/rig_logger.gd") as GDScript).new()
		OS.call("add_logger", _logger)
	_write_system()
	_audio_len = opt("audio", 60.0)
	if _audio_len > 0.0:
		_rec = AudioEffectRecord.new()
		_rec.format = AudioStreamWAV.FORMAT_16_BITS
		_rec_bus = 0
		AudioServer.add_bus_effect(_rec_bus, _rec)
		_rec.set_recording_active(true)
		_audio_cut = now()
		note("audio", "audio_%03d.wav" % _audio_n, "start")
	_next_shot = opt("every", 5.0)
	process_priority = -1000
	var tail := Node.new()
	tail.name = "RigTail"
	tail.process_priority = 1000
	tail.process_mode = Node.PROCESS_MODE_ALWAYS
	tail.set_script(preload("res://scripts/rig_tail.gd"))
	add_child(tail)
	if opt("ontop", true):
		var win := get_window()
		win.always_on_top = true
		var screen_at := DisplayServer.screen_get_position(win.current_screen)
		var screen_size := DisplayServer.screen_get_size(win.current_screen)
		win.position = screen_at + Vector2i(screen_size.x - win.size.x - 12, 38)
	print("RIG %s -> %s" % [plan, out])
	_run.call_deferred()


func _keep_out_of_godot(folder: String) -> void:
	var marker := ProjectSettings.globalize_path(folder).path_join(".gdignore")
	if not FileAccess.file_exists(marker):
		var f := FileAccess.open(marker, FileAccess.WRITE)
		if f:
			f.close()


func _write_system() -> void:
	var win := get_window()
	var screen := DisplayServer.window_get_current_screen()
	var info := {
		"plan": plan,
		"options": opts,
		"args": OS.get_cmdline_args(),
		"godot": Engine.get_version_info().string,
		"os": OS.get_name(),
		"os_version": OS.get_version(),
		"model": OS.get_model_name(),
		"cpu": OS.get_processor_name(),
		"cpu_threads": OS.get_processor_count(),
		"memory_mb": int(OS.get_memory_info().get("physical", 0) / 1048576.0),
		"gpu": RenderingServer.get_video_adapter_name(),
		"gpu_vendor": RenderingServer.get_video_adapter_vendor(),
		"gpu_api": RenderingServer.get_video_adapter_api_version(),
		"renderer": str(ProjectSettings.get_setting("rendering/renderer/rendering_method")),
		"display_driver": DisplayServer.get_name(),
		"window": [win.size.x, win.size.y],
		"window_mode": win.mode,
		"screen": [DisplayServer.screen_get_size(screen).x, DisplayServer.screen_get_size(screen).y],
		"screen_scale": DisplayServer.screen_get_scale(screen),
		"screen_hz": maxf(DisplayServer.screen_get_refresh_rate(screen), 0.0),
		"vsync": DisplayServer.window_get_vsync_mode(),
		"max_fps": Engine.max_fps,
		"audio_driver": AudioServer.get_driver_name(),
		"audio_mix_rate": AudioServer.get_mix_rate(),
		"audio_latency_ms": AudioServer.get_output_latency() * 1000.0,
		"audio_speaker_mode": AudioServer.get_speaker_mode(),
		"audio_device": AudioServer.output_device,
		"audio_devices": AudioServer.get_output_device_list(),
		"audio_buses": AudioServer.bus_count,
		"time": Time.get_datetime_string_from_system(),
		"machine": machine_state(),
		"busiest": busiest(),
	}
	var f := FileAccess.open(out.path_join("system.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(info, "  "))
	f.close()


func machine_state() -> Dictionary:
	var state := {"script_ms": _script_speed()}
	if OS.get_name() == "macOS":
		for item: Array in [["thermal", "pmset", ["-g", "therm"]], ["load", "sysctl", ["-n", "vm.loadavg"]], ["power", "pmset", ["-g", "batt"]]]:
			var lines: Array = []
			if OS.execute(item[1], item[2], lines, true) == 0 and not lines.is_empty():
				state[item[0]] = String(lines[0]).strip_edges().replace("\n", " | ")
	return state


func busiest() -> Array:
	var found: Array = []
	if OS.get_name() != "macOS":
		return found
	var lines: Array = []
	if OS.execute("top", ["-l", "2", "-n", "8", "-o", "cpu", "-stats", "command,cpu"], lines, true) != 0 or lines.is_empty():
		return found
	var text := String(lines[0])
	var at := text.rfind("COMMAND")
	if at < 0:
		return found
	for row in text.substr(at).split("\n").slice(1):
		row = row.strip_edges()
		if row != "":
			found.append(row)
	return found


func _script_speed() -> float:
	var t := Time.get_ticks_usec()
	var acc := 0.0
	for i in 200000:
		acc += sin(i * 0.001) * 0.5
	return (Time.get_ticks_usec() - t) / 1000.0 + acc * 0.0


func note(kind: String, what: String, extra: String = "") -> void:
	if not active or finished or _events == null:
		return
	_notes += 1
	_events.store_line("%.3f,%s,%s,%s" % [now(), kind, what.replace(",", ";").replace("\n", " "), extra.replace(",", ";").replace("\n", " ")])


func shoot(label: String) -> void:
	if not active or finished:
		return
	await RenderingServer.frame_post_draw
	if finished:
		return
	var img := get_viewport().get_texture().get_image()
	_ignore = maxi(_ignore, 3)
	if img == null or img.is_empty():
		return
	if img.get_width() > SHOT_WIDTH:
		img.resize(SHOT_WIDTH, int(round(img.get_height() * float(SHOT_WIDTH) / img.get_width())), Image.INTERPOLATE_BILINEAR)
	var file := "shots/%04d_%s.jpg" % [_shot_n, label.validate_filename().replace(" ", "_")]
	_shot_n += 1
	var path := out.path_join(file)
	_tasks.append(WorkerThreadPool.add_task(func() -> void: img.save_jpg(path, 0.86)))
	var p := _where()
	_shots.store_line("%.3f,%s,%s,%.1f,%.1f,%.1f" % [now(), file, label.replace(",", ";"), p.x, p.y, p.z])


func _where() -> Vector3:
	var cam := _camera()
	if cam:
		return cam.global_position
	return Vector3.ZERO


func _camera() -> Camera3D:
	if Game.main and Game.main.get("view"):
		return (Game.main.view as SubViewport).get_camera_3d()
	return get_viewport().get_camera_3d()


func scripts_done() -> void:
	if _span_name != "" and _script_from > 0:
		_script_usec += Time.get_ticks_usec() - _script_from
		_script_frames += 1


func _process(_delta: float) -> void:
	if finished:
		return
	var tick := Time.get_ticks_usec()
	_script_from = tick
	var dt := (tick - _last_tick) / 1000000.0
	_last_tick = tick
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if not DisplayServer.window_can_draw():
		_hidden += 1
	elif _ignore > 0:
		_ignore -= 1
	else:
		if _armed:
			_all.append(dt)
		_sec_frames += 1
		_sec_time += dt
		_sec_worst = maxf(_sec_worst, dt)
	if _sec_time >= 1.0:
		_row()
	var t := now()
	var every: float = opt("every", 5.0)
	if every > 0.0 and t >= _next_shot and plan != "tour":
		_next_shot = t + every
		shoot("t%04d" % int(t))
	if _rec and t - _audio_cut >= _audio_len:
		_cut_audio(true)
	_flush_log()
	if t > float(opt("timeout", 900.0)):
		note("rig", "timeout")
		finish(3)


func _row() -> void:
	var p := _where()
	var calls := Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
	var prims := Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
	_frames.store_line("%.2f,%.1f,%.2f,%.2f,%.2f,%.2f,%d,%d,%d,%.0f,%.0f,%d,%.1f,%.1f,%.1f,%s" % [now(), _sec_frames / _sec_time,
			_sec_time / _sec_frames * 1000.0, _sec_worst * 1000.0,
			Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
			calls, prims, Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0, Performance.get_monitor(Performance.MEMORY_STATIC) / 1048576.0,
			Performance.get_monitor(Performance.OBJECT_NODE_COUNT), p.x, p.y, p.z, tag])
	if _span_name != "":
		_span_calls += calls
		_span_prims += prims
		_span_rows += 1
	_sec_frames = 0
	_sec_time = 0.0
	_sec_worst = 0.0


func _flush_log() -> void:
	if _logger == null:
		return
	var got: PackedStringArray = _logger.call("take")
	for line in got:
		_errors.store_line("[%.2f] %s" % [now(), line])
	if not got.is_empty():
		_errors.flush()


func _cut_audio(again: bool) -> void:
	_rec.set_recording_active(false)
	var wav := _rec.get_recording()
	if wav:
		wav.save_to_wav(out.path_join("audio_%03d.wav" % _audio_n))
	_ignore = maxi(_ignore, 3)
	_audio_n += 1
	if again:
		_rec.set_recording_active(true)
		_audio_cut = now()
		note("audio", "audio_%03d.wav" % _audio_n, "start")


func span_begin(span_name: String) -> void:
	_armed = true
	_span_name = span_name
	_span_from = _all.size()
	_span_t = now()
	_span_calls = 0.0
	_span_prims = 0.0
	_span_rows = 0
	_span_hidden = _hidden
	_script_usec = 0
	_script_frames = 0
	tag = span_name


func span_end() -> void:
	if _span_name == "":
		return
	var part := _all.slice(_span_from)
	var s := _stats(part)
	var rows := maxf(_span_rows, 1.0)
	_spans.store_line("%s,%.1f,%d,%.1f,%.2f,%.2f,%d,%d,%d,%.2f" % [_span_name, now() - _span_t, part.size(), s.fps, s.median * 1000.0, s.worst * 1000.0,
			_span_calls / rows, _span_prims / rows, _hidden - _span_hidden, _script_usec / 1000.0 / maxf(_script_frames, 1.0)])
	_spans.flush()
	_span_name = ""


func _stats(times: PackedFloat32Array) -> Dictionary:
	if times.is_empty():
		return {"fps": 0.0, "median": 0.0, "p99": 0.0, "worst": 0.0, "over33": 0, "over50": 0}
	var sorted := times.duplicate()
	sorted.sort()
	var total := 0.0
	var over33 := 0
	var over50 := 0
	for v in times:
		total += v
		if v > 0.0334:
			over33 += 1
		if v > 0.050:
			over50 += 1
	return {"fps": times.size() / total, "median": sorted[sorted.size() / 2], "p99": sorted[mini(int(sorted.size() * 0.99), sorted.size() - 1)],
			"worst": sorted[sorted.size() - 1], "over33": over33, "over50": over50}


func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds, true, false, true).timeout


func _run() -> void:
	match plan:
		"tour":
			await _tour()
		"walk":
			await _walk()
		"parts":
			await _parts()
		_:
			await wait(2.0)
			_armed = true
			var seconds: float = opt("seconds", 0.0)
			if seconds <= 0.0:
				return
			tag = "record"
			await wait(seconds)
	finish(0)


func _world() -> Node3D:
	return get_tree().get_first_node_in_group("world_root") as Node3D


func _tour() -> void:
	while _world() == null:
		await get_tree().process_frame
	for i in 40:
		await get_tree().physics_frame
	var world := _world()
	var cam := Camera3D.new()
	cam.near = 0.15
	cam.far = 3200.0
	cam.fov = 60.0
	world.add_child(cam)
	var hold: float = opt("hold", 3.0)
	var only: String = opt("only", "")
	for m: Node3D in get_tree().get_nodes_in_group("shot_cam"):
		if only != "" and not only in String(m.name):
			continue
		if m.has_meta("setup"):
			(m.get_meta("setup") as Callable).call()
		cam.global_transform = m.global_transform
		if world.get("forest") and world.forest.has_method("warm"):
			world.forest.warm(m.global_position)
		cam.make_current()
		Game.scope_on = "scope" in String(m.name)
		var zoomed := "zoom" in String(m.name)
		cam.fov = 60.0 / (6.0 if zoomed else 1.0)
		Game.zoom = 6.0 if zoomed else 1.0
		tag = "settle"
		await wait(0.7)
		span_begin(String(m.name))
		await wait(hold)
		span_end()
		await shoot(String(m.name))
	Game.scope_on = false


func _parts() -> void:
	while _world() == null:
		await get_tree().process_frame
	for i in 40:
		await get_tree().physics_frame
	var world := _world()
	var main: Control = Game.main
	var cam := Camera3D.new()
	cam.near = 0.15
	cam.far = 3200.0
	cam.fov = 60.0
	world.add_child(cam)
	var parts := {
		"near": world.forest.get_node("TreesNear"),
		"far": world.forest.get_node("TreesFar"),
		"ground": world.terrain.near_mesh,
		"sky": world.air.get_node("Sky"),
	}
	var usual_size: int = Game.render_size
	var places: String = opt("only", "w01,t05,v03")
	for m: Node3D in get_tree().get_nodes_in_group("shot_cam"):
		var wanted := false
		for key in places.split(","):
			if String(m.name).begins_with(key):
				wanted = true
		if not wanted:
			continue
		cam.global_transform = m.global_transform
		world.forest.warm(m.global_position)
		cam.make_current()
		var short := String(m.name).substr(0, 3)
		var cases := ["all", "no_film", "no_near", "no_far", "no_ground", "no_sky", "no_lamp", "only_ground", "nothing", "size_640", "size_800", "size_1280"]
		for c: String in cases:
			for key: String in parts:
				(parts[key] as Node3D).visible = true
			world.terrain.hide_all = false
			main.set_film(true)
			Game.lamp_on = true
			main.set_render_size(usual_size)
			match c:
				"no_film":
					main.set_film(false)
				"no_near":
					parts["near"].visible = false
				"no_far":
					parts["far"].visible = false
				"no_ground":
					world.terrain.hide_all = true
					parts["ground"].visible = false
				"no_sky":
					parts["sky"].visible = false
				"no_lamp":
					Game.lamp_on = false
				"only_ground":
					parts["near"].visible = false
					parts["far"].visible = false
					parts["sky"].visible = false
				"nothing":
					world.terrain.hide_all = true
					for key: String in parts:
						(parts[key] as Node3D).visible = false
				"size_640":
					main.set_render_size(0)
				"size_800":
					main.set_render_size(1)
				"size_1280":
					main.set_render_size(3)
			tag = "settle"
			await wait(0.5)
			span_begin("%s_%s" % [short, c])
			await wait(opt("hold", 2.0))
			span_end()
	for key: String in parts:
		(parts[key] as Node3D).visible = true
	main.set_film(true)
	main.set_render_size(usual_size)


func _walk() -> void:
	while Game.player == null:
		await get_tree().process_frame
	for i in 40:
		await get_tree().physics_frame
	var terrain: GDScript = load("res://scripts/terrain.gd")
	var player: CharacterBody3D = Game.player
	var from: float = opt("from", 0.0)
	var seconds: float = opt("seconds", 60.0)
	Game.invulnerable = opt("safe", true)
	var start: Vector3 = terrain.call("track_point", from)
	player.global_position = start + Vector3(0, 0.6, 0)
	player.velocity = Vector3.ZERO
	var world := _world()
	if world.get("forest") and world.forest.has_method("warm"):
		world.forest.warm(player.global_position)
	await wait(0.5)
	span_begin("walk_from_%dm" % int(from))
	Input.action_press("move_forward")
	if opt("run", true):
		Input.action_press("run")
	var until := now() + seconds
	var total: float = terrain.call("track_length")
	while now() < until:
		var pp := player.global_position
		var i: int = terrain.call("track_index", pp.x, pp.z)
		var here: float = from if i < 0 else (terrain.get("track_at") as PackedFloat32Array)[i]
		if here > total - 6.0:
			break
		var target: Vector3 = terrain.call("track_point", here + 7.0)
		var dir := Vector2(target.x - pp.x, target.z - pp.z).normalized()
		player.rotation.y = lerp_angle(player.rotation.y, atan2(-dir.x, -dir.y), 0.12)
		await get_tree().physics_frame
	Input.action_release("move_forward")
	Input.action_release("run")
	span_end()


func _exit_tree() -> void:
	if active and not finished:
		_finalize(0)


func finish(code: int) -> void:
	if finished:
		return
	_finalize(code)
	get_tree().quit(code)


func _finalize(code: int) -> void:
	finished = true
	span_end()
	if _sec_frames > 0:
		_row()
	if _rec:
		_cut_audio(false)
		AudioServer.remove_bus_effect(_rec_bus, AudioServer.get_bus_effect_count(_rec_bus) - 1)
	for id in _tasks:
		WorkerThreadPool.wait_for_task_completion(id)
	_flush_log()
	if _logger:
		_error_count = _logger.get("errors")
		_warning_count = _logger.get("warnings")
		OS.call("remove_logger", _logger)
	var s := _stats(_all)
	var summary := {
		"plan": plan,
		"exit_code": code,
		"seconds": now(),
		"frames": _all.size(),
		"fps": snappedf(s.fps, 0.1),
		"median_ms": snappedf(s.median * 1000.0, 0.01),
		"p99_ms": snappedf(s.p99 * 1000.0, 0.01),
		"worst_ms": snappedf(s.worst * 1000.0, 0.01),
		"frames_over_33ms": s.over33,
		"frames_over_50ms": s.over50,
		"screenshots": _shot_n,
		"audio_files": _audio_n,
		"events": _notes,
		"errors": _error_count,
		"warnings": _warning_count,
		"deaths": Game.deaths,
		"films": Game.film_total(),
		"ended": Game.ended,
		"machine": machine_state(),
	}
	var f := FileAccess.open(out.path_join("summary.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(summary, "  "))
	f.close()
	for file: FileAccess in [_frames, _events, _shots, _spans, _errors]:
		if file:
			file.close()
	var done := FileAccess.open(out.path_join("done.txt"), FileAccess.WRITE)
	done.store_line("exit %d" % code)
	done.close()
	print("RIG DONE: %.1f fps over %d frames, %d errors, %d warnings" % [s.fps, _all.size(), _error_count, _warning_count])

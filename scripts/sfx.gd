extends Node

const Terrain := preload("res://scripts/terrain.gd")

const SPEED_OF_SOUND := 343.0
const VOICES := 16
const BED_BUS := "beds"
const MUSIC_DB := -14.0
const FLOORS := {"gasthaus": "wood", "lookout": "wood", "lookout_roof": "wood", "bomber": "metal", "radar": "metal"}
const STEP_COUNT := {"ground": 4, "wood": 3, "stone": 3, "metal": 3, "water": 2}
const ODD_INDOORS := ["door_creak", "knock", "door_creak"]
const ODD_METAL := ["metal_groan", "knock"]
const ODD_WOODS := ["branch_crack"]

var wind: AudioStreamPlayer
var night: AudioStreamPlayer
var music: AudioStreamPlayer
var tension: AudioStreamPlayer
var chase: AudioStreamPlayer
var whispers: AudioStreamPlayer
var hum: AudioStreamPlayer
var scope: AudioStreamPlayer
var motor: AudioStreamPlayer
var heart: AudioStreamPlayer
var breath: AudioStreamPlayer
var pending: Array = []
var night_quiet := 0.0
var night_cut := false
var was_scope := false
var was_zooming := false
var cache := {}
var call_wait := 200.0
var voices: Array = []
var voice_turn := 0
var feet: Array[AudioStreamPlayer] = []
var foot := 0
var last_step := -1
var danger := 0.0
var odd_wait := 30.0
var quiet := false
var giant: Dictionary
var throat: Dictionary


func _stream(sound: String) -> AudioStream:
	if cache.has(sound):
		return cache[sound]
	var s: AudioStream = null
	for ext: String in ["ogg", "wav"]:
		var path := "res://audio/%s.%s" % [sound, ext]
		if ResourceLoader.exists(path):
			s = load(path)
			break
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	if s == null:
		push_warning("no such sound: " + sound)
	cache[sound] = s
	return s


func _player(bus := "Master") -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	p.mix_target = AudioStreamPlayer.MIX_TARGET_SURROUND if Rig.active else AudioStreamPlayer.MIX_TARGET_STEREO
	return p


func _bed(sound: String, volume_db: float) -> AudioStreamPlayer:
	var p := _player(BED_BUS)
	p.stream = _stream(sound)
	p.volume_db = volume_db
	p.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(p)
	if p.stream:
		p.play()
	return p


func _ready() -> void:
	AudioServer.set_bus_volume_db(_bus(BED_BUS), 0.0)
	_make_voices()
	wind = _bed("wind_bed", -11.0)
	night = _bed("night_bed", -15.0)
	music = _bed("music", MUSIC_DB)
	tension = _bed("tension", -60.0)
	chase = _bed("chase", -60.0)
	whispers = _bed("whispers", -60.0)
	hum = _bed("watcher_hum", -60.0)
	scope = _bed("scope_hum", -60.0)
	motor = _bed("film_motor", -30.0)
	heart = _bed("heartbeat", -60.0)
	breath = _bed("breath", -60.0)
	for i in 2:
		var p := _player()
		add_child(p)
		feet.append(p)
	giant = _hold("colossus_breath", 620.0)
	throat = _hold("reacher_breath", 26.0)
	for sound: String in ["footfall", "cable_sing", "colossus_voice", "colossus_roar", "reacher_click", "reacher_alert", "reacher_sniff",
			"reacher_screech", "watcher_sting", "branch_crack", "death_hit", "knock", "metal_groan", "door_creak", "land", "paper",
			"film_click", "switch", "zoom_whirr", "film_burn", "static_hit", "pickup", "locker", "radio_static", "radio_tune", "crank"]:
		_stream(sound)
	for surface: String in STEP_COUNT:
		for i: int in STEP_COUNT[surface]:
			_stream("step_%s%d" % [surface, i])
	for i in 3:
		_stream("reacher_step%d" % i)


func _bus(bus_name: String) -> int:
	var bus := AudioServer.get_bus_index(bus_name)
	if bus < 0:
		AudioServer.add_bus()
		bus = AudioServer.bus_count - 1
		AudioServer.set_bus_name(bus, bus_name)
		AudioServer.set_bus_send(bus, "Master")
	return bus


func _make_voices() -> void:
	for i in VOICES:
		var bus_name := "voice%d" % i
		var bus := _bus(bus_name)
		if AudioServer.get_bus_effect_count(bus) == 0:
			AudioServer.add_bus_effect(bus, AudioEffectPanner.new())
			var lp := AudioEffectLowPassFilter.new()
			lp.cutoff_hz = 18000.0
			AudioServer.add_bus_effect(bus, lp)
		var p := _player(bus_name)
		add_child(p)
		voices.append({"player": p, "bus": bus_name, "pos": Vector3.ZERO, "base_db": 0.0, "reach": 80.0, "held": false})


func play(sound: String, volume_db := 0.0, pitch := 1.0) -> void:
	var s := _stream(sound)
	if s == null:
		return
	Rig.note("sound", sound, "%.1f dB" % volume_db)
	var p := _player()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = pitch
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()


func _free_voice() -> Dictionary:
	for k in VOICES:
		var v: Dictionary = voices[(voice_turn + k) % VOICES]
		if not v.held and not (v.player as AudioStreamPlayer).playing:
			voice_turn = (voice_turn + k + 1) % VOICES
			return v
	for k in VOICES:
		var v: Dictionary = voices[(voice_turn + k) % VOICES]
		if not v.held:
			voice_turn = (voice_turn + k + 1) % VOICES
			return v
	return voices[0]


func play_at(sound: String, where: Vector3, volume_db := 0.0, reach := 80.0, pitch := 1.0) -> void:
	var s := _stream(sound)
	if s == null:
		return
	var v := _free_voice()
	var p: AudioStreamPlayer = v.player
	v.pos = where
	v.base_db = volume_db
	v.reach = reach
	p.stream = s
	p.pitch_scale = pitch
	_place(v)
	Rig.note("sound3d", sound, "%.1f dB heard at %.1f dB" % [volume_db, p.volume_db])
	p.play()


func loop_at(sound: String, where: Vector3, volume_db := -6.0, reach := 45.0) -> AudioStreamPlayer:
	var v := _free_voice()
	var p: AudioStreamPlayer = v.player
	v.pos = where
	v.base_db = volume_db
	v.reach = reach
	v.held = true
	p.stream = _stream(sound)
	_place(v)
	if p.stream:
		p.play()
	return p


func _hold(sound: String, reach: float) -> Dictionary:
	var v := _free_voice()
	v.held = true
	v.reach = reach
	v.base_db = -80.0
	v.pos = Vector3(0, -9999, 0)
	(v.player as AudioStreamPlayer).stream = _stream(sound)
	(v.player as AudioStreamPlayer).volume_db = -80.0
	if (v.player as AudioStreamPlayer).stream:
		(v.player as AudioStreamPlayer).play()
	return v


func _listener() -> Camera3D:
	if Game.main and Game.main.get("view"):
		return (Game.main.view as SubViewport).get_camera_3d()
	return get_viewport().get_camera_3d()


func _place(v: Dictionary) -> void:
	var p: AudioStreamPlayer = v.player
	var cam := _listener()
	if cam == null:
		p.volume_db = v.base_db
		return
	var to: Vector3 = (v.pos as Vector3) - cam.global_position
	var dist := to.length()
	var reach: float = v.reach
	var near := reach * 0.12
	var db: float = v.base_db - 20.0 * log(maxf(dist, near) / near) / log(10.0)
	db -= 30.0 * smoothstep(reach * 0.6, reach, dist)
	if dist >= reach:
		db = -80.0
	var dir := to / maxf(dist, 0.001)
	var side := cam.global_basis.x.dot(dir)
	var front := -cam.global_basis.z.dot(dir)
	var bus := AudioServer.get_bus_index(v.bus)
	(AudioServer.get_bus_effect(bus, 0) as AudioEffectPanner).pan = clampf(side * 0.85, -0.85, 0.85)
	var cutoff := lerpf(16000.0, 1800.0, clampf(dist / reach, 0.0, 1.0))
	if front < 0.0:
		cutoff *= lerpf(1.0, 0.55, -front)
		db -= 2.0 * -front
	(AudioServer.get_bus_effect(bus, 1) as AudioEffectLowPassFilter).cutoff_hz = cutoff
	p.volume_db = db


func surface() -> String:
	var body: CharacterBody3D = Game.player
	if body == null:
		return "ground"
	var at := body.global_position
	if at.y < Terrain.water_level(at.x, at.z) + 0.04:
		return "water"
	var ray := PhysicsRayQueryParameters3D.create(at + Vector3(0, 0.4, 0), at - Vector3(0, 0.5, 0))
	ray.exclude = [body.get_rid()]
	var hit := body.get_world_3d().direct_space_state.intersect_ray(ray)
	if hit.is_empty():
		return "ground"
	var place: Node = (hit.collider as Node).get_parent()
	if place and place.get("key") != null:
		return FLOORS.get(place.key, "stone")
	return "ground"


func on_step(loud: float) -> void:
	var kind := surface()
	var count: int = STEP_COUNT[kind]
	var pick := randi() % count
	if pick == last_step:
		pick = (pick + 1) % count
	last_step = pick
	foot = 1 - foot
	var p := feet[foot]
	p.stream = _stream("step_%s%d" % [kind, pick])
	p.volume_db = lerpf(-21.0, -7.0, loud) + (2.0 if kind == "water" else 0.0)
	p.pitch_scale = randf_range(0.93, 1.07)
	Rig.note("sound", "step_" + kind, "%.1f dB" % p.volume_db)
	p.play()


func on_land(strength: float) -> void:
	play("land", lerpf(-16.0, -4.0, strength), randf_range(0.9, 1.05))
	if surface() == "water":
		play("step_water0", -6.0, 0.8)


func on_about_to_step() -> void:
	night_cut = true
	night_quiet = 999.0


func on_footfall(pos: Vector3, _left: bool) -> void:
	if Game.player == null:
		return
	var dist := Game.player.global_position.distance_to(pos)
	var delay := dist / SPEED_OF_SOUND
	var volume := clampf(6.0 - 16.0 * log(maxf(dist, 100.0) / 100.0) / log(10.0), -30.0, 6.0)
	var shake := clampf(450.0 / maxf(dist, 60.0), 0.0, 1.0)
	pending.append([delay, "footfall", volume, shake])
	pending.append([delay + 1.2, "cable_sing", volume - 14.0, 0.0])
	if dist < 700.0 and surface() != "ground":
		pending.append([delay + 0.5, "metal_groan" if surface() == "metal" else "door_creak", volume - 10.0, 0.0])


func _danger_now() -> float:
	var d := clampf(Game.hum, 0.0, 1.0) * 0.5
	var world: Node = Game.world
	if world == null or Game.player == null:
		return d
	var r: Node3D = world.get("reacher")
	if r and r.visible and not r.is_asleep():
		var away: float = r.global_position.distance_to(Game.player.global_position)
		if r.is_coming():
			d = 1.0
		elif r.is_hunting():
			d = maxf(d, 0.75)
		elif r.is_listening():
			d = maxf(d, 0.55)
		else:
			d = maxf(d, 0.4 * clampf(1.4 - away / 45.0, 0.0, 1.0))
	return d


func _process(delta: float) -> void:
	for v: Dictionary in voices:
		if (v.player as AudioStreamPlayer).playing:
			_place(v)
	for item: Array in pending.duplicate():
		item[0] -= delta
		if item[0] <= 0.0:
			play(item[1], item[2], randf_range(0.93, 1.05))
			if item[3] > 0.0 and Game.player:
				Game.player.shake = maxf(Game.player.shake, item[3])
			if item[1] == "footfall":
				night_quiet = 7.0
			pending.erase(item)
	var world: Node = Game.world
	var colossus: Node3D = world.get("colossus") if world else null
	var reacher: Node3D = world.get("reacher") if world else null
	var live := not quiet and not Game.ended and Game.player != null

	if colossus and colossus.visible and live and not Game.busy:
		call_wait -= delta
		if call_wait <= 0.0:
			call_wait = randf_range(170.0, 320.0)
			var away: float = Game.player.global_position.distance_to(colossus.body_point())
			pending.append([away / SPEED_OF_SOUND, "colossus_voice", clampf(-4.0 - away / 300.0, -22.0, -6.0), 0.0])
	if colossus and colossus.visible and live:
		giant.pos = colossus.head_point()
		giant.base_db = 4.0
	else:
		giant.base_db = -80.0
	if reacher and reacher.visible and live and not reacher.is_asleep():
		throat.pos = reacher.global_position + Vector3(0, 1.0, 0)
		throat.base_db = -2.0
	else:
		throat.base_db = -80.0

	if night_quiet < 900.0:
		night_quiet = maxf(night_quiet - delta, 0.0)
		if night_quiet <= 0.0:
			night_cut = false
	var night_db := -60.0 if (night_cut or quiet) else -15.0
	night.volume_db = move_toward(night.volume_db, night_db, delta * (90.0 if night_cut else 12.0))
	wind.volume_db = move_toward(wind.volume_db, -17.0 if quiet else -11.0, delta * 6.0)

	hum.volume_db = move_toward(hum.volume_db, lerpf(-60.0, -7.0, Game.hum) if live else -60.0, delta * 40.0)
	whispers.volume_db = move_toward(whispers.volume_db, lerpf(-34.0, -8.0, (Game.hum - 0.45) / 0.55) if (live and Game.hum > 0.45) else -60.0, delta * 30.0)
	scope.volume_db = move_toward(scope.volume_db, -20.0 if (Game.scope_on and live) else -60.0, delta * 160.0)
	if Game.scope_on != was_scope:
		was_scope = Game.scope_on
		play("switch", -6.0)
	if Game.player:
		var zooming: bool = Game.player.zoom_noise > 0.45
		if zooming and not was_zooming:
			play("zoom_whirr", -12.0)
		was_zooming = zooming
		var spent: float = clampf((0.34 - Game.stamina) / 0.3, 0.0, 1.0)
		breath.volume_db = move_toward(breath.volume_db, lerpf(-30.0, -9.0, spent) if (spent > 0.0 and live and not Game.busy) else -60.0, delta * 30.0)
		breath.pitch_scale = lerpf(1.0, 1.25, spent)

	var now := _danger_now() if (live and not Game.busy) else 0.0
	danger = move_toward(danger, now, delta * (1.6 if now > danger else 0.22))
	tension.volume_db = move_toward(tension.volume_db, lerpf(-34.0, -10.0, clampf((danger - 0.2) / 0.6, 0.0, 1.0)) if danger > 0.2 else -60.0, delta * 24.0)
	chase.volume_db = move_toward(chase.volume_db, lerpf(-22.0, -6.0, (danger - 0.85) / 0.15) if danger > 0.85 else -60.0, delta * (60.0 if danger > 0.85 else 10.0))
	heart.volume_db = move_toward(heart.volume_db, lerpf(-26.0, -7.0, clampf((danger - 0.35) / 0.5, 0.0, 1.0)) if danger > 0.35 else -60.0, delta * 30.0)
	heart.pitch_scale = lerpf(1.0, 1.7, clampf((danger - 0.35) / 0.65, 0.0, 1.0))

	var target := MUSIC_DB
	if colossus and colossus.visible and Game.player:
		var d: float = Game.player.global_position.distance_to(colossus.body_point() * Vector3(1, 0, 1) + Vector3(0, Game.player.global_position.y, 0))
		target = lerpf(-50.0, MUSIC_DB, clampf((d - 500.0) / 1200.0, 0.0, 1.0))
	if Game.ended or quiet:
		target = -60.0
	music.volume_db = move_toward(music.volume_db, target, delta * 4.0)

	_odd_noises(delta)


func _odd_noises(delta: float) -> void:
	if quiet or Game.busy or Game.ended or Game.player == null or danger > 0.3:
		return
	odd_wait -= delta
	if odd_wait > 0.0:
		return
	odd_wait = randf_range(22.0, 55.0)
	var kind := surface()
	var sounds: Array = ODD_WOODS
	var away := randf_range(28.0, 60.0)
	if kind == "metal":
		sounds = ODD_METAL
		away = randf_range(8.0, 18.0)
	elif kind == "wood" or kind == "stone":
		sounds = ODD_INDOORS
		away = randf_range(9.0, 22.0)
	var facing: float = Game.player.rotation.y
	var turn := facing + PI + randf_range(-1.3, 1.3) if randf() < 0.7 else randf() * TAU
	var where: Vector3 = Game.player.global_position + Vector3(-sin(turn), 0.0, -cos(turn)) * away + Vector3(0, randf_range(0.5, 3.0), 0)
	play_at(sounds[randi() % sounds.size()], where, -5.0, away * 2.6, randf_range(0.85, 1.1))

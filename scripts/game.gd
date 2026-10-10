extends Node

signal message(text: String, seconds: float)
signal objective_changed(text: String)
signal film_taken(index: int)
signal player_died(how: String)
signal player_back

const FILM_COUNT := 6
const BATTERY_MAX := 100.0
const SAVE_PATH := "user://night.json"

var films: Array[bool] = [false, false, false, false, false, false]
var battery := BATTERY_MAX
var scope_on := false
var zoom := 1.0
var footage := 0.0
var objective := ""
var checkpoint := Vector3.ZERO
var checkpoint_yaw := 0.0
var deaths := 0
var player: Node3D
var world: Node3D
var main: Control
var busy := false
var dead := false
var ended := false
var drain_mult := 1.0
var jitter := 0.0
var hum := 0.0
var noise := 0.0
var invulnerable := false
var hidden := false
var lamp_on := true
var stamina := 1.0
var render_size := 2
var show_fps := false
var fewer_trees := false
var sensitivity := 1.0
var seen_hints := {}
var in_title := false
var skip_title := false


func film_total() -> int:
	return films.count(true)


func say(text: String, seconds := 4.0) -> void:
	Rig.note("message", text)
	message.emit(text, seconds)


func hint(key: String, text: String, seconds := 6.0) -> void:
	if seen_hints.has(key):
		return
	seen_hints[key] = true
	say(text, seconds)


func set_objective(text: String) -> void:
	objective = text
	objective_changed.emit(text)


func save_here() -> void:
	if player:
		checkpoint = player.global_position
		checkpoint_yaw = player.rotation.y


func take_film(index: int) -> void:
	if films[index]:
		return
	films[index] = true
	Rig.note("film", str(index + 1))
	save_here()
	save_game()
	film_taken.emit(index)


func _save_path() -> String:
	return "user://night_test.json" if Autotest.active else SAVE_PATH


func save_game() -> void:
	if Shots.active or (Rig.active and not Autotest.active):
		return
	var f := FileAccess.open(_save_path(), FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"films": films, "at": [checkpoint.x, checkpoint.y, checkpoint.z], "yaw": checkpoint_yaw, "battery": battery}))


func _read_save() -> Dictionary:
	if not FileAccess.file_exists(_save_path()):
		return {}
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(_save_path()))
	return data if data is Dictionary else {}


func saved_films() -> int:
	var data := _read_save()
	if data.is_empty():
		return -1
	var n := 0
	for v: Variant in data.get("films", []):
		if v:
			n += 1
	return n


func load_game() -> bool:
	var data := _read_save()
	if data.is_empty():
		return false
	var taken: Array = data.get("films", [])
	for i in mini(taken.size(), FILM_COUNT):
		films[i] = bool(taken[i])
	var at: Array = data.get("at", [])
	if at.size() == 3:
		checkpoint = Vector3(at[0], at[1], at[2])
	checkpoint_yaw = float(data.get("yaw", 0.0))
	battery = clampf(float(data.get("battery", BATTERY_MAX)), 35.0, BATTERY_MAX)
	return true


func clear_save() -> void:
	if FileAccess.file_exists(_save_path()):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(_save_path()))


func restart_night() -> void:
	clear_save()
	reset()
	skip_title = true
	get_tree().reload_current_scene()


func kill_player(how := "reacher") -> void:
	if busy or ended or invulnerable or dead:
		return
	busy = true
	dead = true
	scope_on = false
	noise = 0.0
	zoom = 1.0
	deaths += 1
	Rig.note("death", how)
	Rig.shoot("death")
	player_died.emit(how)


func back_to_checkpoint() -> void:
	if player == null or not is_instance_valid(player):
		return
	noise = 0.0
	player.global_position = checkpoint + Vector3(0, 0.3, 0)
	player.rotation.y = checkpoint_yaw
	player.velocity = Vector3.ZERO
	battery = maxf(battery, 35.0)
	stamina = 1.0
	busy = false
	dead = false
	player_back.emit()


func reset() -> void:
	films = [false, false, false, false, false, false]
	battery = BATTERY_MAX
	scope_on = false
	zoom = 1.0
	footage = 0.0
	busy = false
	dead = false
	ended = false
	deaths = 0
	noise = 0.0
	stamina = 1.0
	lamp_on = true
	hidden = false
	seen_hints = {}

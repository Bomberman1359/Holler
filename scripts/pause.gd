extends CanvasLayer

const UI := preload("res://scripts/ui.gd")

const KEYS := [
	["W  A  S  D", "walk"],
	["Shift", "run, while your breath lasts"],
	["C  or  Ctrl", "crouch: slow and nearly silent"],
	["Space", "jump"],
	["Q", "hand lamp on or off"],
	["F", "night scope on or off (it hums, and its battery runs down)"],
	["Z  X  or scroll", "zoom the lens (the motor makes noise)"],
	["E", "read, take, use, put down"],
	["Esc", "this card"],
]

var panel: Control
var sens_label: Label
var fps_label: Label
var tree_label: Label


func _ready() -> void:
	layer = 25
	process_mode = Node.PROCESS_MODE_ALWAYS
	panel = Control.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.visible = false
	add_child(panel)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.84)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.add_child(dim)
	UI.label(panel, "Paused", "book", 72, Vector2(0, 80), 1280, HORIZONTAL_ALIGNMENT_CENTER, Color(1, 1, 1)).size.y = 110
	var y := 220.0
	for row: Array in KEYS:
		UI.label(panel, row[0], "typed", 22, Vector2(250, y), 240, HORIZONTAL_ALIGNMENT_RIGHT)
		UI.label(panel, row[1], "typed", 22, Vector2(530, y), 0.0, HORIZONTAL_ALIGNMENT_LEFT, UI.DIM)
		y += 36.0
	y += 26.0
	sens_label = _setting(y)
	fps_label = _setting(y + 36.0)
	tree_label = _setting(y + 72.0)
	UI.label(panel, "Enter", "typed", 22, Vector2(250, y + 108.0), 240, HORIZONTAL_ALIGNMENT_RIGHT)
	UI.label(panel, "full screen on or off", "typed", 22, Vector2(530, y + 108.0), 0.0, HORIZONTAL_ALIGNMENT_LEFT, UI.DIM)
	UI.button(panel, "Back to the valley", "typed", 26, Vector2(340, 742), 600, close)
	UI.button(panel, "Start the night again", "typed", 26, Vector2(340, 790), 600, _again)
	UI.button(panel, "Quit", "typed", 26, Vector2(340, 838), 600, func() -> void: get_tree().quit())
	UI.label(panel, "Hochwald      a game by Chunhwee Choi", "typed", 16, Vector2(0, 916), 1280, HORIZONTAL_ALIGNMENT_CENTER, Color(1, 1, 1, 0.3))
	_refresh()


func _setting(y: float) -> Label:
	var value := UI.label(panel, "", "typed", 22, Vector2(530, y), 0.0, HORIZONTAL_ALIGNMENT_LEFT, UI.DIM)
	return value


func _refresh() -> void:
	sens_label.text = "mouse speed  %d%%" % int(round(Game.sensitivity * 100.0))
	fps_label.text = "frame counter  %s" % ("on" if Game.show_fps else "off")
	tree_label.text = "trees  %s" % ("fewer (faster)" if Game.fewer_trees else "all of them")
	for pair: Array in [[sens_label, "-   +"], [fps_label, "P"], [tree_label, "T"]]:
		var l: Label = pair[0]
		if not l.has_meta("key"):
			l.set_meta("key", UI.label(panel, pair[1], "typed", 22, Vector2(250, l.position.y), 240, HORIZONTAL_ALIGNMENT_RIGHT))


func is_open() -> bool:
	return panel.visible


func open() -> void:
	panel.visible = true
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_duck(-10.0)


func close() -> void:
	panel.visible = false
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_duck(0.0)


func _duck(to_db: float) -> void:
	var bus := AudioServer.get_bus_index("beds")
	if bus < 0:
		return
	create_tween().tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(bus, v), AudioServer.get_bus_volume_db(bus), to_db, 0.3)


func _again() -> void:
	var bus := AudioServer.get_bus_index("beds")
	if bus >= 0:
		AudioServer.set_bus_volume_db(bus, 0.0)
	get_tree().paused = false
	Game.restart_night()


func _input(event: InputEvent) -> void:
	if not panel.visible or not (event is InputEventKey) or not event.pressed:
		return
	var key: int = (event as InputEventKey).physical_keycode
	if (event as InputEventKey).echo and not (key in [KEY_MINUS, KEY_EQUAL, KEY_KP_SUBTRACT, KEY_KP_ADD]):
		get_viewport().set_input_as_handled()
		return
	if key == KEY_ESCAPE:
		close()
	elif key == KEY_MINUS or key == KEY_KP_SUBTRACT:
		Game.sensitivity = maxf(Game.sensitivity - 0.1, 0.2)
		_refresh()
	elif key == KEY_EQUAL or key == KEY_KP_ADD:
		Game.sensitivity = minf(Game.sensitivity + 0.1, 3.0)
		_refresh()
	elif key == KEY_P:
		Game.show_fps = not Game.show_fps
		_refresh()
	elif key == KEY_T:
		Game.fewer_trees = not Game.fewer_trees
		_refresh()
	elif key == KEY_ENTER or key == KEY_KP_ENTER:
		var full := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if full else DisplayServer.WINDOW_MODE_FULLSCREEN)
	get_viewport().set_input_as_handled()

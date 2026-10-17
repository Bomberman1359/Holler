extends CanvasLayer

const UI := preload("res://scripts/ui.gd")

const W := 1280.0
const H := 960.0
const COMPASS_Y := 46.0
const COMPASS_LINE := 32.0
const COMPASS_H := 56.0
const COMPASS_HALF := 230.0
const COMPASS_PER := 2.9

var counter: Label
var films: Label
var state: Label
var msg: Label
var objective: Label
var prompt: Label
var caption: Label
var keys: Label
var fps: Label
var bars: Control
var compass: Control
var msg_left := 0.0
var keys_left := 14.0
var paper: Control
var paper_sheet: TextureRect
var paper_caption: Label
var paper_info := {}
var death: Control
var death_title: Label
var death_line: Label
var end_screen: Control
var _breath_shown := 0.0
var _paper_tween: Tween
var run_text: Label
var run_ghost: Label
var run_left := 0.0


func _ready() -> void:
	layer = 5
	counter = UI.label(self, "", "typed", 20, Vector2(44, 30))
	films = UI.label(self, "", "typed", 20, Vector2(44, 58))
	state = UI.label(self, "", "typed", 20, Vector2(0, 30), W - 44.0, HORIZONTAL_ALIGNMENT_RIGHT)
	fps = UI.label(self, "", "typed", 16, Vector2(0, 58), W - 44.0, HORIZONTAL_ALIGNMENT_RIGHT, UI.DIM)
	objective = UI.label(self, "", "typed", 18, Vector2(44, 906), 0.0, HORIZONTAL_ALIGNMENT_LEFT, UI.DIM)
	msg = UI.label(self, "", "book_it", 32, Vector2(140, 742), W - 280.0, HORIZONTAL_ALIGNMENT_CENTER)
	msg.size = Vector2(W - 280.0, 120)
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	msg.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	msg.position.y = 690
	prompt = UI.label(self, "", "typed", 24, Vector2(0, 566), W, HORIZONTAL_ALIGNMENT_CENTER)
	caption = UI.label(self, "", "typed", 26, Vector2(0, 44), W, HORIZONTAL_ALIGNMENT_CENTER)
	keys = UI.label(self, "W A S D  walk      Shift  run      C  crouch      Space  jump      Q  lamp      F  night scope      E  use      Esc  all keys",
			"typed", 16, Vector2(0, 932), W, HORIZONTAL_ALIGNMENT_CENTER, UI.DIM)
	bars = Control.new()
	bars.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bars.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bars.draw.connect(_draw_bars)
	add_child(bars)
	_build_compass()
	run_ghost = UI.label(self, "RUN", "scrawl", 200, Vector2(0, 250), W, HORIZONTAL_ALIGNMENT_CENTER, Color(0.85, 0.8, 0.76, 0.22))
	run_ghost.size.y = 330
	run_ghost.visible = false
	run_text = UI.label(self, "RUN", "scrawl", 200, Vector2(0, 250), W, HORIZONTAL_ALIGNMENT_CENTER, Color(0.72, 0.05, 0.04))
	run_text.size.y = 330
	run_text.pivot_offset = Vector2(W * 0.5, 165.0)
	run_text.add_theme_constant_override("shadow_offset_x", 5)
	run_text.add_theme_constant_override("shadow_offset_y", 5)
	run_text.visible = false
	_build_paper()
	_build_death()
	Game.message.connect(_on_message)
	Game.objective_changed.connect(func(t: String) -> void: objective.text = t)
	Game.player_back.connect(func() -> void: death.visible = false)
	objective.text = Game.objective
	var text := FileAccess.get_file_as_string("res://assets/gen/papers/papers.json")
	if text != "":
		paper_info = JSON.parse_string(text)


func _draw_bars() -> void:
	if not counter.visible:
		return
	var ink := UI.INK
	var x := 44.0
	var y := 872.0
	var font := UI.font("typed")
	bars.draw_string(font, Vector2(x, y + 15), "SCOPE", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, ink if Game.scope_on else UI.DIM)
	var cells := int(ceil(Game.battery / Game.BATTERY_MAX * 10.0))
	var low := Game.battery < 20.0
	for i in 10:
		var r := Rect2(x + 78.0 + i * 13.0, y + 2.0, 9.0, 15.0)
		if i < cells:
			bars.draw_rect(r, Color(1, 1, 1, 0.9 if not low else 0.55 + 0.4 * sin(Time.get_ticks_msec() * 0.012)))
		else:
			bars.draw_rect(r, Color(1, 1, 1, 0.22), false, 1.0)
	if _breath_shown > 0.01:
		var w := 260.0
		var bx := (W - w) * 0.5
		var by := 900.0
		var a := _breath_shown
		bars.draw_rect(Rect2(bx, by, w, 5.0), Color(1, 1, 1, 0.16 * a))
		var tired := Game.stamina < 0.2
		bars.draw_rect(Rect2(bx, by, w * Game.stamina, 5.0), Color(1, 1, 1, (0.5 if tired else 0.85) * a))
		bars.draw_string(font, Vector2(bx - 74.0, by + 9.0), "BREATH", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 1, 1, 0.6 * a))


func _build_compass() -> void:
	var strip := SubViewport.new()
	strip.size = Vector2i(int(720.0 * COMPASS_PER) + 2, int(COMPASS_H))
	strip.transparent_bg = true
	strip.disable_3d = true
	strip.render_target_update_mode = SubViewport.UPDATE_ONCE
	var ink := Control.new()
	ink.size = Vector2(strip.size)
	ink.draw.connect(_draw_strip.bind(ink))
	strip.add_child(ink)
	add_child(strip)
	var mat := ShaderMaterial.new()
	mat.shader = preload("res://shaders/compass.gdshader")
	mat.set_shader_parameter("strip", strip.get_texture())
	mat.set_shader_parameter("per", COMPASS_PER)
	mat.set_shader_parameter("strip_w", float(strip.size.x))
	mat.set_shader_parameter("half_w", COMPASS_HALF)
	mat.set_shader_parameter("rect_size", Vector2(COMPASS_HALF * 2.0 + 60.0, COMPASS_H))
	mat.set_shader_parameter("line_y", COMPASS_LINE)
	compass = ColorRect.new()
	compass.material = mat
	compass.mouse_filter = Control.MOUSE_FILTER_IGNORE
	compass.position = Vector2(W * 0.5 - COMPASS_HALF - 30.0, COMPASS_Y - COMPASS_LINE)
	compass.size = Vector2(COMPASS_HALF * 2.0 + 60.0, COMPASS_H)
	add_child(compass)


func _draw_strip(ink: Control) -> void:
	var font := UI.font("typed")
	var y := COMPASS_LINE
	var lines := PackedVector2Array([Vector2(0.0, y), Vector2(ink.size.x, y)])
	var colors := PackedColorArray([Color(1, 1, 1, 0.16)])
	for step in range(0, 49):
		var a := -180 + step * 15
		var x := (a + 180) * COMPASS_PER
		var deg := posmod(a, 360)
		var tick := 3.0
		var alpha := 0.32
		if deg % 90 == 0:
			tick = 7.0
			alpha = 0.75
			ink.draw_string(font, Vector2(x - 20.0, y - 12.0), ["N", "E", "S", "W"][deg / 90], HORIZONTAL_ALIGNMENT_CENTER, 40.0, 21, Color(1, 1, 1, 0.92))
		elif deg % 45 == 0:
			tick = 5.0
			alpha = 0.5
			ink.draw_string(font, Vector2(x - 20.0, y - 11.0), ["NE", "SE", "SW", "NW"][(deg - 45) / 90], HORIZONTAL_ALIGNMENT_CENTER, 40.0, 14, Color(1, 1, 1, 0.55))
		lines.append(Vector2(x, y - tick))
		lines.append(Vector2(x, y + tick))
		colors.append(Color(1, 1, 1, alpha))
	ink.draw_multiline_colors(lines, colors, 1.0)


func _update_compass() -> void:
	var on: bool = counter.visible and Game.player != null and Game.player.cam != null and Game.player.cam.is_inside_tree()
	compass.visible = on
	if not on:
		return
	var mat := compass.material as ShaderMaterial
	var fwd: Vector3 = -Game.player.cam.global_basis.z
	var heading := fposmod(rad_to_deg(atan2(fwd.x, -fwd.z)), 360.0)
	mat.set_shader_parameter("heading", heading)
	var story: Node = Game.world.get("story") if Game.world else null
	var mark_on := 0.0
	if story != null and not Game.ended:
		var to: Vector3 = story.stop_point(story.next_stop()) - Game.player.global_position
		if Vector2(to.x, to.z).length() >= 60.0:
			mark_on = 1.0
			var rel := wrapf(rad_to_deg(atan2(to.x, -to.z)) - heading, -180.0, 180.0)
			if absf(rel) * COMPASS_PER <= COMPASS_HALF:
				mat.set_shader_parameter("mark_x", rel * COMPASS_PER)
				mat.set_shader_parameter("mark_side", 0.0)
			else:
				mat.set_shader_parameter("mark_side", signf(rel))
	mat.set_shader_parameter("mark_on", mark_on)


func _build_paper() -> void:
	paper = Control.new()
	paper.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	paper.visible = false
	paper.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(paper)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.78)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	paper.add_child(dim)
	paper_sheet = TextureRect.new()
	paper_sheet.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	paper_sheet.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	paper_sheet.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	paper_sheet.size = Vector2(630, 840)
	paper_sheet.pivot_offset = paper_sheet.size * 0.5
	paper_sheet.mouse_filter = Control.MOUSE_FILTER_IGNORE
	paper.add_child(paper_sheet)
	paper_caption = UI.label(paper, "", "typed", 18, Vector2(0, 906), W, HORIZONTAL_ALIGNMENT_CENTER, UI.DIM)


func show_paper(key: String, from := Vector2(640, 700)) -> void:
	var tex: Texture2D = load("res://assets/gen/papers/%s.png" % key)
	paper_sheet.texture = tex
	var info: Dictionary = paper_info.get(key, {})
	paper_caption.text = info.get("caption", "")
	paper.visible = true
	paper.modulate.a = 0.0
	var rest := Vector2((W - paper_sheet.size.x) * 0.5, 44.0)
	paper_sheet.position = from - paper_sheet.size * 0.5
	paper_sheet.scale = Vector2(0.12, 0.12)
	paper_sheet.rotation = randf_range(-0.5, 0.5)
	if _paper_tween:
		_paper_tween.kill()
	var tw := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_paper_tween = tw
	tw.tween_property(paper, "modulate:a", 1.0, 0.25)
	tw.tween_property(paper_sheet, "position", rest, 0.42)
	tw.tween_property(paper_sheet, "scale", Vector2.ONE, 0.42)
	tw.tween_property(paper_sheet, "rotation", randf_range(-0.025, 0.025), 0.42)


func hide_paper() -> void:
	if _paper_tween:
		_paper_tween.kill()
	var tw := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	_paper_tween = tw
	tw.tween_property(paper_sheet, "position:y", H + 40.0, 0.25)
	tw.tween_property(paper, "modulate:a", 0.0, 0.25)
	tw.chain().tween_callback(func() -> void: paper.visible = false)


func _build_death() -> void:
	death = Control.new()
	death.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	death.visible = false
	add_child(death)
	var black := ColorRect.new()
	black.color = Color(0, 0, 0, 0.9)
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	death.add_child(black)
	death_title = UI.label(death, "Y O U   D I E D", "book", 96, Vector2(0, 300), W, HORIZONTAL_ALIGNMENT_CENTER, Color(1, 1, 1))
	death_title.size.y = 140
	death_line = UI.label(death, "", "book_it", 28, Vector2(0, 446), W, HORIZONTAL_ALIGNMENT_CENTER, UI.DIM)
	var from_film := UI.button(death, "Go back to the last film", "typed", 28, Vector2(340, 590), 600, func() -> void: _leave_death(false))
	from_film.name = "FromFilm"
	var again := UI.button(death, "Start the night again", "typed", 28, Vector2(340, 652), 600, func() -> void: _leave_death(true))
	again.name = "Again"
	UI.label(death, "Enter  the last film          R  the whole night", "typed", 15, Vector2(0, 900), W, HORIZONTAL_ALIGNMENT_CENTER, Color(1, 1, 1, 0.3))


func show_death(line: String) -> void:
	death_line.text = line
	death.visible = true
	death.modulate.a = 0.0
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	create_tween().tween_property(death, "modulate:a", 1.0, 0.9)


func _leave_death(whole_night: bool) -> void:
	if not death.visible or death.modulate.a < 0.5:
		return
	if whole_night:
		Game.restart_night()
		return
	death.visible = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	Game.back_to_checkpoint()


func show_end() -> void:
	end_screen = Control.new()
	end_screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(end_screen)
	var black := ColorRect.new()
	black.color = Color(0, 0, 0)
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	end_screen.add_child(black)
	UI.label(end_screen, "Hochwald", "black", 120, Vector2(0, 250), W, HORIZONTAL_ALIGNMENT_CENTER, Color(1, 1, 1)).size.y = 170
	UI.label(end_screen, "The seventh film was never recovered.", "book_it", 30, Vector2(0, 450), W, HORIZONTAL_ALIGNMENT_CENTER)
	UI.label(end_screen, "A game by Chunhwee Choi", "typed", 20, Vector2(0, 600), W, HORIZONTAL_ALIGNMENT_CENTER, UI.DIM)
	UI.button(end_screen, "Back to the title", "typed", 26, Vector2(340, 760), 600, func() -> void:
		Game.reset()
		get_tree().reload_current_scene())
	end_screen.modulate.a = 0.0
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	create_tween().tween_property(end_screen, "modulate:a", 1.0, 3.0)


func show_run(seconds := 3.5) -> void:
	run_left = seconds


func show_caption(text: String) -> void:
	caption.text = text


func _on_message(text: String, seconds: float) -> void:
	msg.text = text
	msg_left = seconds
	msg.modulate.a = 1.0


func _input(event: InputEvent) -> void:
	if death.visible and event is InputEventKey and event.pressed and not event.echo:
		var key: int = (event as InputEventKey).physical_keycode
		if key == KEY_ENTER or key == KEY_KP_ENTER or key == KEY_E:
			_leave_death(false)
			get_viewport().set_input_as_handled()
		elif key == KEY_R:
			_leave_death(true)
			get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	var story: Node = Game.world.get("story") if Game.world else null
	var in_film: bool = story != null and story.playing
	var plain: bool = not in_film and not Game.dead and end_screen == null
	counter.visible = plain
	films.visible = plain
	state.visible = plain
	objective.visible = plain
	fps.visible = plain and Game.show_fps
	counter.text = "16 mm    %04d ft    x %.1f" % [int(Game.footage), Game.zoom]
	films.text = "FILMS   %d / %d" % [Game.film_total(), Game.FILM_COUNT]
	var s := ""
	if Game.hidden:
		s = "HIDDEN"
	elif Game.player and Game.player.get("crouched"):
		s = "CROUCHED"
	if not Game.lamp_on and not Game.scope_on:
		s += ("      " if s != "" else "") + "LAMP OFF"
	state.text = s
	if Game.show_fps:
		fps.text = "%d frames a second" % Engine.get_frames_per_second()
	prompt.text = story.prompt() if story and not Game.dead else ""
	_breath_shown = move_toward(_breath_shown, 1.0 if (Game.stamina < 0.995 and plain) else 0.0, delta * (4.0 if Game.stamina < 0.995 else 0.8))
	bars.queue_redraw()
	_update_compass()
	if keys_left > 0.0:
		keys_left -= delta
		keys.modulate.a = clampf(keys_left / 2.0, 0.0, 1.0) if plain else 0.0
		keys.visible = keys_left > 0.0
	if msg_left > 0.0:
		msg_left -= delta
		if msg_left < 1.0:
			msg.modulate.a = maxf(msg_left, 0.0)
	if run_left > 0.0:
		run_left -= delta
		var live := run_left > 0.0 and not Game.dead
		var flick := randf() > (0.18 if run_left > 2.6 else 0.06)
		run_text.visible = live and flick
		run_text.position = Vector2(randf_range(-10.0, 10.0), 250.0 + randf_range(-7.0, 7.0))
		run_text.rotation = randf_range(-0.035, 0.035)
		run_text.scale = Vector2.ONE * (1.0 + maxf(run_left - 2.9, 0.0) * 0.5)
		run_text.modulate.a = clampf(run_left / 0.9, 0.0, 1.0)
		run_ghost.visible = live and randf() < 0.45
		run_ghost.position = Vector2(randf_range(-46.0, 46.0), 250.0 + randf_range(-20.0, 20.0))
	elif run_text.visible or run_ghost.visible:
		run_text.visible = false
		run_ghost.visible = false
	if death.visible:
		death_title.position = Vector2(randf_range(-1.2, 1.2), 300.0 + randf_range(-1.0, 1.0))
		death_title.modulate.a = 0.86 + 0.14 * randf()

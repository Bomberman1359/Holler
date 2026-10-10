extends Control

const WorldScript := preload("res://scripts/world.gd")
const HudScript := preload("res://scripts/hud.gd")
const IntroScript := preload("res://scripts/intro.gd")
const PauseScript := preload("res://scripts/pause.gd")
const FilmShader := preload("res://shaders/film.gdshader")

const RENDER_SIZES := [Vector2i(640, 480), Vector2i(800, 600), Vector2i(960, 720), Vector2i(1280, 960)]

var screen: TextureRect
var view: SubViewport
var film_view: SubViewport
var film_rect: TextureRect
var world: Node3D
var hud: CanvasLayer
var intro: CanvasLayer
var pause: CanvasLayer
var film_mat: ShaderMaterial
var film_on := true
var scope_mix := 0.0
var _film_frame := -1
var _scratch := Vector4(0.3, 0.7, 0.0, 0.0)
var _scratch_left := [0, 0]
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	Game.main = self
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	view = SubViewport.new()
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	view.handle_input_locally = false
	add_child(view)
	film_view = SubViewport.new()
	film_view.disable_3d = true
	film_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	film_view.handle_input_locally = false
	add_child(film_view)
	film_rect = TextureRect.new()
	film_rect.texture = view.get_texture()
	film_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	film_rect.stretch_mode = TextureRect.STRETCH_SCALE
	film_rect.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	film_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	film_mat = ShaderMaterial.new()
	film_mat.shader = FilmShader
	film_mat.set_shader_parameter("grain_tex", load("res://assets/gen/tex/film_grain.png"))
	film_mat.set_shader_parameter("dirt_tex", load("res://assets/gen/tex/film_dirt.png"))
	film_rect.material = film_mat
	film_view.add_child(film_rect)
	screen = TextureRect.new()
	screen.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	screen.stretch_mode = TextureRect.STRETCH_SCALE
	screen.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	screen.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(screen)
	set_film(not Shots.day and not Rig.opt("nofilm", false))
	set_render_size(Rig.opt("size", Game.render_size))

	var testing: bool = Shots.active or Autotest.active or Rig.direct()
	if testing:
		_build_world()
		return
	Game.busy = true
	intro = CanvasLayer.new()
	intro.set_script(IntroScript)
	add_child(intro)
	intro.finished.connect(_on_intro_finished)
	await get_tree().process_frame
	await get_tree().process_frame
	_build_world()
	hud.visible = false
	intro.world_ready = true


func set_render_size(index: int) -> void:
	Game.render_size = clampi(index, 0, RENDER_SIZES.size() - 1)
	view.size = RENDER_SIZES[Game.render_size]
	film_view.size = view.size
	film_mat.set_shader_parameter("res", Vector2(view.size))


func set_film(on: bool) -> void:
	film_on = on
	screen.texture = film_view.get_texture() if on else view.get_texture()
	film_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS if on else SubViewport.UPDATE_DISABLED


func _film_tick() -> void:
	var f := int(Time.get_ticks_msec() * 0.018)
	if f == _film_frame:
		return
	_film_frame = f
	var worn: float = film_mat.get_shader_parameter("worn") if film_mat.get_shader_parameter("worn") != null else 0.0
	var weave := 0.0016 * (1.0 + worn * 3.0 + Game.jitter * 6.0)
	var dust := 0.0
	var roll := _rng.randf()
	if roll > 0.80 - worn * 0.5:
		dust = _rng.randf_range(0.35, 1.0)
	film_mat.set_shader_parameter("frame", Vector4(_rng.randf_range(-weave, weave), _rng.randf_range(-weave, weave),
			0.965 + 0.035 * _rng.randf(), dust))
	film_mat.set_shader_parameter("offsets", Vector4(_rng.randf(), _rng.randf(), _rng.randf(), _rng.randf()))
	for i in 2:
		if _scratch_left[i] > 0:
			_scratch_left[i] -= 1
			if _scratch_left[i] == 0:
				_scratch[2 + i] = 0.0
		elif _rng.randf() < 0.012 + worn * 0.08:
			_scratch_left[i] = _rng.randi_range(2, 14)
			_scratch[i] = _rng.randf_range(0.06, 0.94)
			_scratch[2 + i] = _rng.randf_range(0.35, 1.0)
	film_mat.set_shader_parameter("scratch", _scratch)


func _build_world() -> void:
	world = Node3D.new()
	world.name = "World"
	world.set_script(WorldScript)
	world.add_to_group("world_root")
	Game.world = world
	view.add_child(world)

	hud = CanvasLayer.new()
	hud.set_script(HudScript)
	hud.visible = not Shots.active
	add_child(hud)

	pause = CanvasLayer.new()
	pause.set_script(PauseScript)
	add_child(pause)


func _on_intro_finished() -> void:
	Game.busy = false
	hud.visible = true
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _process(delta: float) -> void:
	if world == null:
		return
	scope_mix = move_toward(scope_mix, 1.0 if Game.scope_on else 0.0, delta * 5.0)
	film_mat.set_shader_parameter("scope", scope_mix)
	if not Game.dead:
		film_mat.set_shader_parameter("jitter", Game.jitter)
	if film_on:
		_film_tick()


func _input(event: InputEvent) -> void:
	if world == null:
		return
	var in_intro: bool = intro != null and is_instance_valid(intro) and intro.stage < 2
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if Game.player and (not Game.busy or Game.ended):
			var rel: Variant = event.get("screen_relative")
			Game.player.look(rel if rel != null else event.relative)
	elif in_intro:
		return
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
		if Game.player and not Game.busy:
			Game.player.zoom_step(1.0)
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
		if Game.player and not Game.busy:
			Game.player.zoom_step(-1.0)
	elif event is InputEventPanGesture:
		if Game.player and not Game.busy and absf(event.delta.y) > 0.1:
			Game.player.zoom_step(-event.delta.y * 0.25)
	elif event is InputEventMagnifyGesture:
		if Game.player and not Game.busy:
			Game.player.zoom_target = clampf(Game.player.zoom_target * event.factor, 1.0, Game.player.ZOOM_MAX)
	elif Game.dead:
		return
	elif event.is_action_pressed("restart") and Game.ended and hud and hud.end_screen != null:
		Game.reset()
		get_tree().reload_current_scene()
	elif event.is_action_pressed("interact"):
		if world.get("story"):
			world.story.interact()
	elif event.is_action_pressed("scope"):
		if Game.player and not Game.busy:
			Game.player.toggle_scope()
	elif event.is_action_pressed("pause"):
		if Game.ended:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		elif pause and not pause.is_open():
			pause.open()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		if not Shots.active and not (pause and pause.is_open()) and not (hud and hud.end_screen != null):
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

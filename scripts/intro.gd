extends CanvasLayer

signal finished(mode: String)

const UI := preload("res://scripts/ui.gd")
const TitleStage := preload("res://scripts/title_stage.gd")

const ORDER := """[b]HEADQUARTERS, TECHNICAL INTELLIGENCE BRANCH[/b]
Regensburg, U.S. Zone
[right]14 October 1947[/right]
SUBJECT:  Recovery of film, Hochwald valley
TO:          T/5, Signal Corps, attached

1.  Lt. Abbott's party of six entered the valley on 5 October to catalog [bgcolor=#111][color=#111]the tunnel site[/color][/bgcolor]. No radio contact since 6 October.

2.  The party set six automatic cameras. You will recover all six films.

3.  You will report by radio from the fire lookout on the summit.

4.  You will not [bgcolor=#111][color=#111]use the radio[/color][/bgcolor] before all six films are in hand.

5.  You go alone. No further men can be spared for this valley.


[right]By order of the Branch Chief[/right]"""

var leader: Control
var count := 8
var sweep := 0.0
var stage := 0
var order_sheet: Control
var order_text: RichTextLabel
var typed := 0.0
var hint: Label
var title_box: Control
var hold := 0.0
var world_ready := false
var stage_node: Node3D
var menu: Control
var items: Array[Label] = []
var choices: Array[String] = []
var picked := 0
var black: ColorRect
var theme: AudioStreamPlayer
var leaving := false


func _ready() -> void:
	layer = 20
	leader = Control.new()
	leader.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	leader.draw.connect(_draw_leader)
	add_child(leader)


func _draw_leader() -> void:
	var size := leader.size
	var c := size * 0.5
	var flick := 0.11 + randf() * 0.025
	leader.draw_rect(Rect2(Vector2.ZERO, size), Color(flick, flick, flick * 0.95))
	var ink := Color(0.78, 0.76, 0.68)
	leader.draw_arc(c, 330.0, 0.0, TAU, 72, ink, 5.0)
	leader.draw_arc(c, 285.0, 0.0, TAU, 72, ink, 3.0)
	leader.draw_line(Vector2(0, c.y), Vector2(size.x, c.y), ink, 3.0)
	leader.draw_line(Vector2(c.x, 0), Vector2(c.x, size.y), ink, 3.0)
	leader.draw_line(c, c + Vector2.from_angle(-PI * 0.5 + sweep * TAU) * 360.0, ink, 7.0)
	var font := UI.font("slab_bold")
	var label := str(count) if world_ready else "8"
	leader.draw_string(font, c + Vector2(-200, 130), label, HORIZONTAL_ALIGNMENT_CENTER, 400, 380, Color(0.9, 0.88, 0.8))
	for k in 3:
		if randf() < 0.5:
			var x := randf() * size.x
			leader.draw_line(Vector2(x, 0), Vector2(x + randf_range(-20, 20), size.y), Color(1, 1, 1, 0.12), 1.5)
	for k in 5:
		leader.draw_circle(Vector2(randf() * size.x, randf() * size.y), randf_range(1.5, 4.0), Color(0, 0, 0, 0.5))


func _build_order() -> void:
	order_sheet = Control.new()
	order_sheet.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(order_sheet)
	var desk := ColorRect.new()
	desk.color = Color(0.07, 0.06, 0.05)
	desk.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	order_sheet.add_child(desk)
	var shadow := ColorRect.new()
	shadow.color = Color(0, 0, 0, 0.5)
	shadow.position = Vector2(222, 62)
	shadow.size = Vector2(860, 850)
	shadow.rotation = 0.012
	order_sheet.add_child(shadow)
	var sheet := ColorRect.new()
	sheet.color = Color(0.83, 0.79, 0.66)
	sheet.position = Vector2(210, 50)
	sheet.size = Vector2(860, 850)
	sheet.rotation = 0.012
	order_sheet.add_child(sheet)
	var clip := ColorRect.new()
	clip.color = Color(0.45, 0.36, 0.22, 0.45)
	clip.position = Vector2(60, -6)
	clip.size = Vector2(22, 96)
	sheet.add_child(clip)
	var fold := ColorRect.new()
	fold.color = Color(0, 0, 0, 0.07)
	fold.position = Vector2(0, 424)
	fold.size = Vector2(860, 3)
	sheet.add_child(fold)
	var typewriter: Font = UI.font("slab")
	order_text = RichTextLabel.new()
	order_text.bbcode_enabled = true
	order_text.scroll_active = false
	order_text.position = Vector2(70, 80)
	order_text.size = Vector2(730, 720)
	order_text.add_theme_font_override("normal_font", typewriter)
	order_text.add_theme_font_override("bold_font", UI.font("slab_bold"))
	order_text.add_theme_font_size_override("normal_font_size", 21)
	order_text.add_theme_font_size_override("bold_font_size", 21)
	order_text.add_theme_color_override("default_color", Color(0.10, 0.09, 0.09))
	order_text.text = ORDER
	order_text.visible_characters = 0
	sheet.add_child(order_text)
	var stamp := Label.new()
	stamp.text = "RESTRICTED"
	stamp.position = Vector2(80, 655)
	stamp.rotation = -0.22
	stamp.add_theme_font_override("font", UI.font("slab_bold"))
	stamp.add_theme_font_size_override("font_size", 46)
	stamp.add_theme_color_override("font_color", Color(0.60, 0.10, 0.08, 0.75))
	sheet.add_child(stamp)
	hint = Label.new()
	hint.text = "E or click to go"
	hint.position = Vector2(0, 915)
	hint.size = Vector2(1280, 30)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_override("font", UI.font("typed"))
	hint.add_theme_font_size_override("font_size", 20)
	hint.add_theme_color_override("font_color", Color(0.8, 0.78, 0.7, 0.8))
	hint.visible = false
	order_sheet.add_child(hint)


func _build_title(mode: String) -> void:
	title_box = Control.new()
	title_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(title_box)
	var first := "Hochwald valley, 14 October 1947" if mode == "new" else "Film %d of 6" % Game.film_total()
	var lines := [[first, 44, 380.0, "book_it"], ["Running, zooming and the scope all make noise.", 19, 885.0, "typed"]]
	for l: Array in lines:
		var label := Label.new()
		label.add_theme_font_override("font", UI.font(l[3]))
		label.text = l[0]
		label.position = Vector2(0, l[2])
		label.size = Vector2(1280, 200)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", l[1])
		label.add_theme_color_override("font_color", Color(0.95, 0.94, 0.9))
		label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
		label.add_theme_constant_override("shadow_offset_x", 3)
		label.add_theme_constant_override("shadow_offset_y", 3)
		title_box.add_child(label)
	title_box.modulate.a = 0.0


func _process(delta: float) -> void:
	match stage:
		0:
			leader.queue_redraw()
			if not world_ready:
				return
			if stage_node == null and not Game.skip_title and Game.world:
				stage_node = Node3D.new()
				stage_node.set_script(TitleStage)
				Game.world.add_child(stage_node)
			sweep += delta / (0.04 if Rig.opt("fast", false) else 0.7)
			if sweep >= 1.0:
				sweep = 0.0
				count -= 1
				if count == 2:
					_beep()
				if count < 2:
					leader.queue_free()
					if Game.skip_title:
						Game.skip_title = false
						_start("new")
					else:
						stage = 1
						_build_menu()
		1:
			_point_at_mouse()
			hold += delta
			var auto := String(Rig.opt("choose", ""))
			if auto != "" and hold > 4.0 and not leaving:
				picked = maxi(choices.find(auto), 0)
				_show_pick()
				_choose(choices[picked])
		2:
			if order_text == null:
				return
			typed += delta * 70.0
			order_text.visible_characters = int(typed)
			if order_text.visible_characters >= order_text.get_total_character_count():
				hint.visible = true
				if String(Rig.opt("choose", "")) != "" and typed > order_text.get_total_character_count() + 140.0:
					order_sheet.queue_free()
					order_text = null
					_start("new")
		3:
			hold += delta
			if hold < 1.5:
				title_box.modulate.a = hold / 1.5
			elif hold <= 7.0:
				title_box.modulate.a = 1.0
			else:
				title_box.modulate.a = maxf(1.0 - (hold - 7.0) / 2.0, 0.0)
			if hold > 9.0:
				stage = 4
				queue_free()


func _beep() -> void:
	if Game.world and Game.world.get("sfx"):
		Game.world.sfx.play("film_click", -4.0, 1.6)


func _input(event: InputEvent) -> void:
	if leaving:
		return
	if stage == 1:
		_menu_input(event)
		return
	if stage != 2 or order_text == null:
		return
	var go: bool = event.is_action_pressed("interact") or (event is InputEventMouseButton and event.pressed) or event.is_action_pressed("ui_accept")
	if not go:
		return
	get_viewport().set_input_as_handled()
	if order_text.visible_characters < order_text.get_total_character_count():
		typed = 100000.0
		return
	order_sheet.queue_free()
	_start("new")


func _build_menu() -> void:
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(menu)
	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0, 0, 0, 0.0)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	menu.add_child(shade)
	UI.label(menu, "Hochwald", "black", 128, Vector2(92, 70)).size = Vector2(900, 190)
	UI.label(menu, "Bavarian Forest, October 1947", "book_it", 28, Vector2(100, 238), 0.0, HORIZONTAL_ALIGNMENT_LEFT, UI.DIM)
	choices = ["new"]
	var films := Game.saved_films()
	if films >= 0:
		choices.append("continue")
	choices.append("quit")
	var y := 600.0
	for c: String in choices:
		var text: String = {"new": "New night", "continue": "Continue        film %d of 6" % films, "quit": "Quit"}[c]
		var l := UI.label(menu, text, "typed", 34, Vector2(150, y), 900.0)
		l.set_meta("text", text)
		items.append(l)
		y += 64.0
	UI.label(menu, "Chunhwee Choi  2026", "typed", 15, Vector2(40, 920), 0.0, HORIZONTAL_ALIGNMENT_LEFT, Color(1, 1, 1, 0.28))
	black = ColorRect.new()
	black.color = Color(0, 0, 0, 1.0)
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(black)
	create_tween().tween_property(black, "color:a", 0.0, 1.6)
	picked = 0
	hold = 0.0
	_show_pick()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if Game.world and Game.world.get("sfx"):
		theme = Game.world.sfx._bed("theme", -60.0)
		create_tween().tween_property(theme, "volume_db", -7.0, 2.5)


func _show_pick() -> void:
	for i in items.size():
		var l := items[i]
		var on := i == picked
		l.text = (">>  " if on else "     ") + String(l.get_meta("text"))
		l.add_theme_color_override("font_color", UI.INK if on else Color(0.93, 0.92, 0.88, 0.5))


func _point_at_mouse() -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_VISIBLE:
		return
	var m := menu.get_local_mouse_position()
	for i in items.size():
		var r := Rect2(items[i].position - Vector2(20, 8), Vector2(700, 56))
		if r.has_point(m) and picked != i:
			picked = i
			_show_pick()
			if Game.world and Game.world.get("sfx"):
				Game.world.sfx.play("switch", -16.0, 1.4)


func _menu_input(event: InputEvent) -> void:
	var up: bool = event.is_action_pressed("move_forward") or event.is_action_pressed("ui_up")
	var down: bool = event.is_action_pressed("move_back") or event.is_action_pressed("ui_down")
	if up or down:
		picked = (picked + (-1 if up else 1) + items.size()) % items.size()
		_show_pick()
		if Game.world and Game.world.get("sfx"):
			Game.world.sfx.play("switch", -16.0, 1.4)
		get_viewport().set_input_as_handled()
		return
	var click: bool = event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT
	if click:
		_point_at_mouse()
		var m := menu.get_local_mouse_position()
		var r := Rect2(items[picked].position - Vector2(20, 8), Vector2(700, 56))
		if not r.has_point(m):
			return
	if click or event.is_action_pressed("interact") or event.is_action_pressed("ui_accept") or event.is_action_pressed("jump"):
		get_viewport().set_input_as_handled()
		_choose(choices[picked])


func _choose(choice: String) -> void:
	if choice == "quit":
		get_tree().quit()
		return
	leaving = true
	if Game.world and Game.world.get("sfx"):
		Game.world.sfx.play("film_click", -6.0, 0.8)
	if theme:
		var tw := create_tween()
		tw.tween_property(theme, "volume_db", -60.0, 1.4)
		tw.tween_callback(theme.queue_free)
		theme = null
	var tw2 := create_tween()
	tw2.tween_property(black, "color:a", 1.0, 0.7)
	tw2.tween_callback(func() -> void:
		menu.queue_free()
		if stage_node:
			stage_node.queue_free()
			stage_node = null
		if Game.player:
			Game.player.cam.make_current()
		leaving = false
		if choice == "continue":
			_start("continue")
		else:
			stage = 2
			_build_order()
		var tw3 := create_tween()
		tw3.tween_property(black, "color:a", 0.0, 0.6))


func _start(mode: String) -> void:
	stage = 3
	hold = 0.0
	if stage_node:
		stage_node.queue_free()
		stage_node = null
		if Game.player:
			Game.player.cam.make_current()
	finished.emit(mode)
	_build_title(mode)

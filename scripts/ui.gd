extends RefCounted

const INK := Color(0.93, 0.92, 0.88)
const DIM := Color(0.93, 0.92, 0.88, 0.55)

static var _fonts := {}


static func font(face: String) -> Font:
	if _fonts.has(face):
		return _fonts[face]
	var files := {
		"typed": "SpecialElite-Regular.ttf", "hand": "ReenieBeanie.ttf", "pencil": "HomemadeApple-Regular.ttf", "scrawl": "RockSalt-Regular.ttf",
		"book": "IMFePIrm28P.ttf", "book_it": "IMFePIit28P.ttf", "black": "UnifrakturCook-Bold.ttf", "slab": "CourierPrime-Regular.ttf",
		"slab_bold": "CourierPrime-Bold.ttf",
	}
	var f: Font = load("res://assets/fonts/" + files[face])
	_fonts[face] = f
	return f


static func label(parent: Node, text: String, face: String, size: int, pos: Vector2, width := 0.0, align := HORIZONTAL_ALIGNMENT_LEFT, color := INK) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	if width > 0.0:
		l.size = Vector2(width, size * 1.5)
	l.horizontal_alignment = align
	l.add_theme_font_override("font", font(face))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


static func button(parent: Node, text: String, face: String, size: int, pos: Vector2, width: float, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.flat = true
	b.position = pos
	b.size = Vector2(width, size * 1.7)
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", font(face))
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", Color(0.78, 0.77, 0.73))
	b.add_theme_color_override("font_hover_color", Color(1, 1, 1))
	b.add_theme_color_override("font_pressed_color", Color(0.6, 0.6, 0.58))
	for state in ["normal", "hover", "pressed", "focus"]:
		b.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	b.pressed.connect(action)
	parent.add_child(b)
	return b

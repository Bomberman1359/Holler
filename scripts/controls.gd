extends Node

const KEYS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"run": [KEY_SHIFT],
	"jump": [KEY_SPACE],
	"crouch": [KEY_C, KEY_CTRL],
	"lamp": [KEY_Q],
	"interact": [KEY_E],
	"scope": [KEY_F],
	"pause": [KEY_ESCAPE],
	"zoom_in": [KEY_Z],
	"zoom_out": [KEY_X],
	"restart": [KEY_R],
}


func _enter_tree() -> void:
	for action: String in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for code: int in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = code as Key
			InputMap.action_add_event(action, ev)

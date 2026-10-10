extends Logger

var lines := PackedStringArray()
var errors := 0
var warnings := 0
var lock := Mutex.new()


func _log_error(function: String, file: String, line: int, code: String, rationale: String, _editor_notify: bool, error_type: int, script_backtraces: Array[ScriptBacktrace]) -> void:
	var kind := "ERROR"
	match error_type:
		ERROR_TYPE_WARNING:
			kind = "WARNING"
		ERROR_TYPE_SCRIPT:
			kind = "SCRIPT ERROR"
		ERROR_TYPE_SHADER:
			kind = "SHADER ERROR"
	var text := "%s: %s" % [kind, rationale if rationale != "" else code]
	if rationale != "" and code != "":
		text += "  (%s)" % code
	text += "\n   at %s (%s:%d)" % [function, file, line]
	for bt in script_backtraces:
		if bt != null and not bt.is_empty():
			text += "\n" + bt.format(3)
	lock.lock()
	if error_type == ERROR_TYPE_WARNING:
		warnings += 1
	else:
		errors += 1
	lines.append(text)
	lock.unlock()


func _log_message(message: String, error: bool) -> void:
	if not error:
		return
	lock.lock()
	lines.append("STDERR: " + message.strip_edges())
	lock.unlock()


func take() -> PackedStringArray:
	lock.lock()
	var out := lines
	lines = PackedStringArray()
	lock.unlock()
	return out

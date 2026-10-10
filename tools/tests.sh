#!/usr/bin/env bash
# usage: GODOT=/path/to/godot tools/tests.sh [start|papers|films|death|ending]
GODOT="${GODOT:-godot}"
cd "$(dirname "$0")/.."
"$GODOT" --headless --path . --import >/dev/null 2>&1
arg="--autotest"
[ -n "$1" ] && arg="--autotest=$1"
"$GODOT" --headless --path . -- $arg > /tmp/holler_autotest.log 2>&1
grep -E "FAIL|cannot|AUTOTEST|SCRIPT ERROR" /tmp/holler_autotest.log

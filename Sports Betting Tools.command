#!/bin/bash
# Double-click launcher for the sports betting tools — opens a button window.
cd "$(dirname "$0")"

# Uses the modern python.org Python (Tcl/Tk 8.6+) instead of the ancient
# system one (/usr/bin/python3, Tcl/Tk 8.5.9 from 2009) which had real
# widget-rendering bugs on modern macOS. Falls back to system python3 if
# the modern one isn't installed for some reason.
PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

# Errors go to a log file (not /dev/null) so problems are visible/debuggable
# instead of silently vanishing.
nohup "$PYTHON" launcher_gui.py > /tmp/sports_betting_tools.log 2>&1 &
disown
sleep 1
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1

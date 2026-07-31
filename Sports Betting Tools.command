#!/bin/bash
# Double-click launcher for the sports betting tools — opens a button window.
cd "$(dirname "$0")"

# Errors go to a log file (not /dev/null) so problems are visible/debuggable
# instead of silently vanishing.
nohup python3 launcher_gui.py > /tmp/sports_betting_tools.log 2>&1 &
disown
sleep 1
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1

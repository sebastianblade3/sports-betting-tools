#!/bin/bash
# Double-click launcher for the sports betting tools — opens a button window.
cd "$(dirname "$0")"

nohup python3 launcher_gui.py > /dev/null 2>&1 &
disown
sleep 1
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1

#!/usr/bin/env python3
"""
Button-based launcher for the sports betting tools. Tools that have been
converted to a real GUI form open directly in this same app (no typing into
Terminal at all). Tools not yet converted still open in a new Terminal
window as before — being converted one at a time.
"""

import subprocess
import sys
import tkinter as tk
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
if str(FOLDER) not in sys.path:
    sys.path.insert(0, str(FOLDER))

# label -> ("gui", module_name) once converted, or ("terminal", script_filename) until then
TOOLS = [
    ("EV / Parlay Calculator", "gui", "ev_tool_gui"),
    ("NBA/WNBA Points Prop Model", "terminal", "nba_props_model.py"),
    ("MLB Props Model", "terminal", "mlb_props_model.py"),
    ("De-Vig Calculator", "gui", "devig_tool_gui"),
    ("Calibration Tracker", "gui", "calibration_tool_gui"),
    ("Kelly Stake Sizing", "gui", "kelly_tool_gui"),
    ("Bankroll / ROI Tracker", "gui", "bankroll_tool_gui"),
]


def launch_terminal(script_name):
    script_path = FOLDER / script_name
    apple_script = f'''
    tell application "Terminal"
        activate
        do script "cd '{FOLDER}' && python3 '{script_path.name}'"
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script])


def launch_gui(module_name):
    module = __import__(module_name)
    module.open_window()


def build_window():
    root = tk.Tk()
    root.title("Sports Betting Tools")
    root.geometry("340x460")
    root.resizable(False, False)

    title = tk.Label(root, text="Sports Betting Tools", font=("Helvetica", 16, "bold"))
    title.pack(pady=(20, 10))

    for label, kind, target in TOOLS:
        if kind == "gui":
            command = lambda t=target: launch_gui(t)
        else:
            command = lambda t=target: launch_terminal(t)
        btn = tk.Button(root, text=label, width=30, height=2, command=command)
        btn.pack(pady=5)

    quit_btn = tk.Button(root, text="Quit", width=30, command=root.destroy)
    quit_btn.pack(pady=(15, 10))

    root.mainloop()


if __name__ == "__main__":
    build_window()

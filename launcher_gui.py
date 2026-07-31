#!/usr/bin/env python3
"""
Button-based launcher for the sports betting tools. Each button opens the
corresponding tool in its own new Terminal window (the tools themselves still
need to ask questions like "how many legs?" or "enter a player's games" —
that still happens via typing in that window, but you no longer have to type
a number to choose WHICH tool first).
"""

import subprocess
import tkinter as tk
from pathlib import Path

FOLDER = Path(__file__).resolve().parent

TOOLS = [
    ("EV / Parlay Calculator", "ev_tool.py"),
    ("NBA/WNBA Points Prop Model", "nba_props_model.py"),
    ("MLB Props Model", "mlb_props_model.py"),
    ("De-Vig Calculator", "devig_tool.py"),
    ("Calibration Tracker", "calibration_tool.py"),
]


def launch(script_name):
    script_path = FOLDER / script_name
    # Opens a new Terminal window and runs the script in it (AppleScript,
    # since that's the standard way to open Terminal with a specific command
    # on macOS from a script).
    apple_script = f'''
    tell application "Terminal"
        activate
        do script "cd '{FOLDER}' && python3 '{script_path.name}'"
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script])


def build_window():
    root = tk.Tk()
    root.title("Sports Betting Tools")
    root.geometry("340x330")
    root.resizable(False, False)

    title = tk.Label(root, text="Sports Betting Tools", font=("Helvetica", 16, "bold"))
    title.pack(pady=(20, 10))

    for label, script in TOOLS:
        btn = tk.Button(
            root,
            text=label,
            width=30,
            height=2,
            command=lambda s=script: launch(s),
        )
        btn.pack(pady=5)

    quit_btn = tk.Button(root, text="Quit", width=30, command=root.destroy)
    quit_btn.pack(pady=(15, 10))

    root.mainloop()


if __name__ == "__main__":
    build_window()

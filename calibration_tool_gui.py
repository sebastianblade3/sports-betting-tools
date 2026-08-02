#!/usr/bin/env python3
"""
Button/form version of the calibration tracker — same tested math as
calibration_tool.py (load_log, brier_score, calibration_buckets,
append_entry imported directly, not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from calibration_tool import load_log, brier_score, calibration_buckets, append_entry, LOG_FILE


class CalibrationToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Calibration Tracker")
        self.root.geometry("560x640")

        self.outcome = tk.StringVar(value="1")

        form = tk.Frame(root, pady=10)
        form.pack(fill="x")

        tk.Label(form, text="Log a new calibration entry", font=("Helvetica", 13, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8)
        )

        tk.Label(form, text="Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.date_entry = tk.Entry(form, width=25)
        self.date_entry.grid(row=1, column=1, padx=10, pady=3)

        tk.Label(form, text="Description:").grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.description_entry = tk.Entry(form, width=25)
        self.description_entry.grid(row=2, column=1, padx=10, pady=3)

        tk.Label(form, text="Predicted probability (0-1 or %):").grid(row=3, column=0, sticky="w", padx=10, pady=3)
        self.prob_entry = tk.Entry(form, width=25)
        self.prob_entry.grid(row=3, column=1, padx=10, pady=3)

        tk.Label(form, text="Actual outcome:").grid(row=4, column=0, sticky="w", padx=10, pady=3)
        outcome_frame = tk.Frame(form)
        outcome_frame.grid(row=4, column=1, sticky="w", padx=10, pady=3)
        tk.Radiobutton(outcome_frame, text="Hit", variable=self.outcome, value="1").pack(side="left")
        tk.Radiobutton(outcome_frame, text="Miss", variable=self.outcome, value="0").pack(side="left")

        tk.Label(form, text="Notes (optional):").grid(row=5, column=0, sticky="w", padx=10, pady=3)
        self.notes_entry = tk.Entry(form, width=25)
        self.notes_entry.grid(row=5, column=1, padx=10, pady=3)

        btn_frame = tk.Frame(root, pady=8)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Log Entry", width=18, command=self.log_entry).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Refresh Report", width=18, command=self.show_report).pack(side="left", padx=10)

        self.output = tk.Text(root, height=22, width=68, wrap="word")
        self.output.pack(padx=10, pady=10, fill="both", expand=True)

        self.show_report()

    def parse_prob(self, raw):
        raw = raw.strip().rstrip("%")
        val = float(raw)
        if val > 1:
            val /= 100
        return val

    def log_entry(self):
        try:
            self._log_entry()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _log_entry(self):
        date = self.date_entry.get().strip()
        description = self.description_entry.get().strip()
        if not date or not description:
            messagebox.showerror("Missing info", "Enter a date and description.")
            return
        try:
            predicted_prob = self.parse_prob(self.prob_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Enter a valid probability (e.g. 0.65 or 65).")
            return

        actual_outcome = int(self.outcome.get())
        notes = self.notes_entry.get().strip()
        append_entry(date, description, predicted_prob, actual_outcome, notes)
        messagebox.showinfo("Logged", f"Logged to {LOG_FILE.name}")

        self.date_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.prob_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

        self.show_report()

    def show_report(self):
        try:
            self._show_report()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _show_report(self):
        entries = load_log()
        lines = []
        if not entries:
            lines.append("No calibration entries logged yet.")
        else:
            lines.append(f"=== Calibration Report ({len(entries)} entries) ===")
            lines.append("")

            score = brier_score(entries)
            lines.append(f"Brier score: {score:.3f}")
            lines.append("  (0 = perfect, 0.25 = always guessing 50%, 1.0 = confidently wrong)")
            lines.append("")

            lines.append("Calibration by predicted-probability bucket:")
            lines.append(f"{'Range':<12}{'n':<5}{'Avg predicted':<16}{'Actual hit rate':<16}")
            for b in calibration_buckets(entries):
                lines.append(f"{b['range']:<12}{b['n']:<5}{b['avg_predicted']:<16.1%}{b['actual_hit_rate']:<16.1%}")

            if len(entries) < 20:
                lines.append("")
                lines.append(f"NOTE: only {len(entries)} entries logged — way too small a sample to draw")
                lines.append("real conclusions yet. This report will get more meaningful as more")
                lines.append("predictions get logged and checked against results over time.")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))


def open_window():
    win = tk.Toplevel()
    CalibrationToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    CalibrationToolWindow(root)
    root.mainloop()

#!/usr/bin/env python3
"""
Button/form version of the calibration tracker — same tested math as
calibration_tool.py (load_log, brier_score, calibration_buckets,
append_entry, settle_entry, pending_entries, settled_entries imported
directly, not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from calibration_tool import (
    load_log,
    brier_score,
    calibration_buckets,
    append_entry,
    settle_entry,
    pending_entries,
    settled_entries,
    LOG_FILE,
)


class CalibrationToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Calibration Tracker")

        self.outcome = tk.StringVar(value="1")
        self.is_pending = tk.BooleanVar(value=False)
        self.settle_index_var = tk.StringVar(value="")
        self.settle_outcome = tk.StringVar(value="1")

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
        self.outcome_frame = tk.Frame(form)
        self.outcome_frame.grid(row=4, column=1, sticky="w", padx=10, pady=3)
        self.hit_radio = tk.Radiobutton(self.outcome_frame, text="Hit", variable=self.outcome, value="1")
        self.hit_radio.pack(side="left")
        self.miss_radio = tk.Radiobutton(self.outcome_frame, text="Miss", variable=self.outcome, value="0")
        self.miss_radio.pack(side="left")

        tk.Checkbutton(
            form, text="Outcome not known yet (log as pending, settle later)",
            variable=self.is_pending, command=self.toggle_pending
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=3)

        tk.Label(form, text="Notes (optional):").grid(row=6, column=0, sticky="w", padx=10, pady=3)
        self.notes_entry = tk.Entry(form, width=25)
        self.notes_entry.grid(row=6, column=1, padx=10, pady=3)

        btn_frame = tk.Frame(root, pady=8)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Log Entry", width=18, command=self.log_entry).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Refresh Report", width=18, command=self.show_report).pack(side="left", padx=10)

        settle_frame = tk.LabelFrame(root, text="Settle a pending prediction", padx=10, pady=8)
        settle_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(settle_frame, text="Pending entry:").grid(row=0, column=0, sticky="w", padx=5)
        self.settle_menu = tk.OptionMenu(settle_frame, self.settle_index_var, "")
        self.settle_menu.grid(row=0, column=1, sticky="w", padx=5)

        settle_outcome_frame = tk.Frame(settle_frame)
        settle_outcome_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=3)
        tk.Radiobutton(settle_outcome_frame, text="Hit", variable=self.settle_outcome, value="1").pack(side="left")
        tk.Radiobutton(settle_outcome_frame, text="Miss", variable=self.settle_outcome, value="0").pack(side="left")

        tk.Button(settle_frame, text="Settle", command=self.settle_pending).grid(
            row=2, column=0, columnspan=2, pady=6
        )

        output_frame = tk.Frame(root)
        output_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        scrollbar = tk.Scrollbar(output_frame)
        scrollbar.pack(side="right", fill="y")
        self.output = tk.Text(output_frame, height=18, width=68, wrap="word", yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.output.yview)

        self._pending_indices = []
        self.show_report()

        self.root.update_idletasks()
        self.root.geometry("580x760")

    def toggle_pending(self):
        state = "disabled" if self.is_pending.get() else "normal"
        self.hit_radio.config(state=state)
        self.miss_radio.config(state=state)

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

        actual_outcome = None if self.is_pending.get() else int(self.outcome.get())
        notes = self.notes_entry.get().strip()
        append_entry(date, description, predicted_prob, actual_outcome, notes)
        status = "pending (no outcome yet)" if actual_outcome is None else ("hit" if actual_outcome else "miss")
        messagebox.showinfo("Logged", f"Logged to {LOG_FILE.name} as {status}")

        self.date_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.prob_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

        self.show_report()

    def settle_pending(self):
        try:
            self._settle_pending()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _settle_pending(self):
        selected = self.settle_index_var.get()
        if not selected:
            messagebox.showerror("No entry selected", "Choose a pending entry to settle.")
            return
        index = int(selected)
        outcome = int(self.settle_outcome.get())
        settle_entry(index, outcome)
        messagebox.showinfo("Settled", "Prediction settled.")
        self.show_report()

    def show_report(self):
        try:
            self._show_report()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _show_report(self):
        entries = load_log()
        lines = []
        pending = pending_entries(entries)
        settled = settled_entries(entries)

        if not entries:
            lines.append("No calibration entries logged yet.")
        else:
            lines.append(f"=== Calibration Report ({len(entries)} entries: {len(settled)} settled, {len(pending)} pending) ===")
            lines.append("")

            score = brier_score(entries)
            if score is None:
                lines.append("No settled entries yet — nothing to score.")
            else:
                lines.append(f"Brier score: {score:.3f}")
                lines.append("  (0 = perfect, 0.25 = always guessing 50%, 1.0 = confidently wrong)")
                lines.append("")

                lines.append("Calibration by predicted-probability bucket:")
                lines.append(f"{'Range':<12}{'n':<5}{'Avg predicted':<16}{'Actual hit rate':<16}")
                for b in calibration_buckets(entries):
                    lines.append(f"{b['range']:<12}{b['n']:<5}{b['avg_predicted']:<16.1%}{b['actual_hit_rate']:<16.1%}")

            if pending:
                lines.append("")
                lines.append("Pending predictions (no outcome yet):")
                for i, e in enumerate(entries):
                    if e["actual_outcome"] is None:
                        lines.append(f"  [{i}] {e['date']}  {e['description']}  (predicted {e['predicted_prob']:.1%})")

            if len(settled) < 20:
                lines.append("")
                lines.append(f"NOTE: only {len(settled)} settled entries logged — way too small a sample to draw")
                lines.append("real conclusions yet. This report will get more meaningful as more")
                lines.append("predictions get logged and checked against results over time.")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))

        # rebuild the "settle a pending prediction" dropdown
        menu = self.settle_menu["menu"]
        menu.delete(0, "end")
        self._pending_indices = []
        for i, e in enumerate(entries):
            if e["actual_outcome"] is None:
                label = f"[{i}] {e['date']} {e['description']}"
                menu.add_command(label=label, command=lambda idx=i: self.settle_index_var.set(str(idx)))
                self._pending_indices.append(i)
        if self._pending_indices:
            self.settle_index_var.set(str(self._pending_indices[0]))
        else:
            self.settle_index_var.set("")


def open_window():
    win = tk.Toplevel()
    CalibrationToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    CalibrationToolWindow(root)
    root.mainloop()

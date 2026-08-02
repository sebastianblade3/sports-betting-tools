#!/usr/bin/env python3
"""
Button/form version of the EV calculator — same tested math as ev_tool.py
(evaluate_power, evaluate_flex, POWER_MULTIPLIERS, FLEX_MULTIPLIERS imported
directly, not reimplemented), just a real GUI instead of typing into Terminal.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from ev_tool import (
    POWER_MULTIPLIERS,
    FLEX_MULTIPLIERS,
    evaluate_power,
    evaluate_flex,
    append_to_vault,
)


class EVToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("EV / Parlay Calculator")
        self.root.geometry("520x600")

        self.mode = tk.StringVar(value="power")
        self.num_legs = tk.IntVar(value=3)
        self.leg_rows = []  # list of (label_entry, prob_entry)
        self.last_result = None  # (mode, n, legs, probs, multiplier) for logging

        top = tk.Frame(root, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Mode:").grid(row=0, column=0, sticky="w", padx=10)
        tk.Radiobutton(top, text="Power Play", variable=self.mode, value="power").grid(row=0, column=1)
        tk.Radiobutton(top, text="Flex Play", variable=self.mode, value="flex").grid(row=0, column=2)

        tk.Label(top, text="Number of legs:").grid(row=1, column=0, sticky="w", padx=10, pady=(10, 0))
        tk.Spinbox(top, from_=2, to=6, textvariable=self.num_legs, width=5).grid(row=1, column=1, pady=(10, 0), sticky="w")
        tk.Button(top, text="Set Up Legs", command=self.build_leg_rows).grid(row=1, column=2, pady=(10, 0))

        self.legs_frame = tk.Frame(root, pady=10)
        self.legs_frame.pack(fill="x")

        action_frame = tk.Frame(root, pady=10)
        action_frame.pack(fill="x")
        tk.Button(action_frame, text="Calculate", width=20, command=self.calculate).pack(side="left", padx=10)
        self.log_button = tk.Button(action_frame, text="Log to Match-Notes.md", width=20, command=self.log_result, state="disabled")
        self.log_button.pack(side="left")

        self.output = tk.Text(root, height=20, width=62, wrap="word")
        self.output.pack(padx=10, pady=10, fill="both", expand=True)

        self.build_leg_rows()

    def build_leg_rows(self):
        try:
            self._build_leg_rows()
        except Exception as e:
            # Final safety net: no error should ever disappear silently.
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _build_leg_rows(self):
        try:
            n = self.num_legs.get()
        except tk.TclError:
            messagebox.showerror(
                "Invalid number of legs",
                "The 'Number of legs' box doesn't have a valid whole number in it "
                "right now (e.g. it might be empty or mid-edit). Click into it, "
                "make sure it shows a number like 3, then try 'Set Up Legs' again.",
            )
            return

        if not (2 <= n <= 6):
            messagebox.showerror("Out of range", "Number of legs must be between 2 and 6.")
            return

        for widget in self.legs_frame.winfo_children():
            widget.destroy()
        self.leg_rows = []

        tk.Label(self.legs_frame, text="Leg label", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=10)
        tk.Label(self.legs_frame, text="Probability (0-1 or %)", font=("Helvetica", 10, "bold")).grid(row=0, column=1, padx=10)

        for i in range(n):
            label_entry = tk.Entry(self.legs_frame, width=35)
            label_entry.grid(row=i + 1, column=0, padx=10, pady=2)
            label_entry.insert(0, f"Leg {i + 1}")

            prob_entry = tk.Entry(self.legs_frame, width=12)
            prob_entry.grid(row=i + 1, column=1, padx=10, pady=2)

            self.leg_rows.append((label_entry, prob_entry))

        # Force an immediate redraw. In some environments (sandboxed launch,
        # missing Accessibility/Screen Recording permission for the Python
        # process) Tk's normal automatic repaint after adding widgets can lag
        # significantly — this forces it to happen right away instead of
        # waiting on the next natural event loop pass.
        self.legs_frame.update_idletasks()

    def parse_prob(self, raw):
        raw = raw.strip().rstrip("%")
        val = float(raw)
        if val > 1:
            val /= 100.0
        return val

    def calculate(self):
        try:
            self._calculate()
        except Exception as e:
            # Final safety net: no error should ever disappear silently.
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _calculate(self):
        if not self.leg_rows:
            messagebox.showerror("No legs set up", "Click 'Set Up Legs' first.")
            return

        try:
            legs = [le.get().strip() for le, pe in self.leg_rows]
            probs = [self.parse_prob(pe.get()) for le, pe in self.leg_rows]
        except ValueError:
            messagebox.showerror("Invalid input", "Enter each probability as a number (e.g. 0.62 or 62).")
            return

        n = len(probs)
        mode = self.mode.get()
        self.output.delete("1.0", tk.END)

        lines = ["--- Per-leg summary ---"]
        for label, p in zip(legs, probs):
            lines.append(f"  {label}: {p:.0%}")
        lines.append("")

        multiplier = None
        if mode == "power":
            multiplier = POWER_MULTIPLIERS.get(n)
            if multiplier is None:
                messagebox.showerror("No multiplier", f"No standard Power multiplier on file for {n} picks.")
                return
            combined, breakeven, ev = evaluate_power(probs, multiplier)
            lines.append(f"Multiplier: {multiplier}x")
            lines.append(f"Combined hit probability (all legs): {combined:.2%}")
            lines.append(f"Breakeven probability needed: {breakeven:.2%}")
            lines.append(f"EV per $1 staked: {ev:+.3f}  ({'+EV' if ev > 0 else '-EV'})")
            if ev > 0:
                margin = combined / breakeven - 1
                lines.append(f"Margin above breakeven: {margin:+.1%} (thin if under ~20%)")
        else:
            payout_table = FLEX_MULTIPLIERS.get(n)
            if payout_table is None:
                messagebox.showerror("No table", f"No standard Flex table on file for {n} picks.")
                return
            breakdown, ev = evaluate_flex(probs, payout_table)
            lines.append("Correct legs -> probability -> payout contribution:")
            for k, dp_k, mult in breakdown:
                lines.append(f"  {k}/{n} correct: {dp_k:.2%} chance, pays {mult}x")
            lines.append(f"Expected return per $1 staked: {ev + 1:.3f}")
            lines.append(f"EV per $1 staked: {ev:+.3f}  ({'+EV' if ev > 0 else '-EV'})")

        self.output.insert(tk.END, "\n".join(lines))
        self.last_result = (mode, n, legs, probs, multiplier)
        self.log_button.config(state="normal")

    def log_result(self):
        if not self.last_result:
            return
        mode, n, legs, probs, multiplier = self.last_result
        append_to_vault(mode, n, legs, probs, multiplier if mode == "power" else None)
        messagebox.showinfo("Logged", "Entry logged to Match-Notes.md")


def open_window():
    win = tk.Toplevel()
    EVToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    EVToolWindow(root)
    root.mainloop()

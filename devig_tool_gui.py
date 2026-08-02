#!/usr/bin/env python3
"""
Button/form version of the de-vig calculator — same tested math as
devig_tool.py (devig_two_way, edge, american_to_implied_prob,
implied_prob_to_american imported directly, not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from devig_tool import (
    devig_two_way,
    american_to_implied_prob,
    implied_prob_to_american,
    edge,
)


class DevigToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("De-Vig Calculator")
        self.root.geometry("480x520")

        self.has_model_prob = tk.BooleanVar(value=False)

        form = tk.Frame(root, pady=10)
        form.pack(fill="x")

        tk.Label(form, text="Side A name:").grid(row=0, column=0, sticky="w", padx=10, pady=3)
        self.label_a_entry = tk.Entry(form, width=20)
        self.label_a_entry.grid(row=0, column=1, padx=10, pady=3)
        self.label_a_entry.insert(0, "Over")

        tk.Label(form, text="Side A odds:").grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.odds_a_entry = tk.Entry(form, width=20)
        self.odds_a_entry.grid(row=1, column=1, padx=10, pady=3)

        tk.Label(form, text="Side B name:").grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.label_b_entry = tk.Entry(form, width=20)
        self.label_b_entry.grid(row=2, column=1, padx=10, pady=3)
        self.label_b_entry.insert(0, "Under")

        tk.Label(form, text="Side B odds:").grid(row=3, column=0, sticky="w", padx=10, pady=3)
        self.odds_b_entry = tk.Entry(form, width=20)
        self.odds_b_entry.grid(row=3, column=1, padx=10, pady=3)

        tk.Checkbutton(
            form, text="I have my own model probability for Side A",
            variable=self.has_model_prob, command=self.toggle_model_prob
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 3))

        tk.Label(form, text="Model probability for A (0-1 or %):").grid(row=5, column=0, sticky="w", padx=10, pady=3)
        self.model_prob_entry = tk.Entry(form, width=20, state="disabled")
        self.model_prob_entry.grid(row=5, column=1, padx=10, pady=3)

        tk.Button(root, text="Calculate", width=20, command=self.calculate).pack(pady=10)

        self.output = tk.Text(root, height=18, width=58, wrap="word")
        self.output.pack(padx=10, pady=10, fill="both", expand=True)

    def toggle_model_prob(self):
        self.model_prob_entry.config(state="normal" if self.has_model_prob.get() else "disabled")

    def parse_prob(self, raw):
        raw = raw.strip().rstrip("%")
        val = float(raw)
        if val > 1:
            val /= 100
        return val

    def calculate(self):
        try:
            self._calculate()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _calculate(self):
        label_a = self.label_a_entry.get().strip() or "Side A"
        label_b = self.label_b_entry.get().strip() or "Side B"
        try:
            odds_a = int(self.odds_a_entry.get().strip())
            odds_b = int(self.odds_b_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid odds", "Enter American odds as whole numbers, e.g. -140 or 120.")
            return

        our_prob_a = None
        if self.has_model_prob.get():
            try:
                our_prob_a = self.parse_prob(self.model_prob_entry.get())
            except ValueError:
                messagebox.showerror("Invalid probability", "Enter a number (e.g. 0.62 or 62).")
                return

        true_a, true_b, vig_pct = devig_two_way(odds_a, odds_b)
        raw_a = american_to_implied_prob(odds_a)
        raw_b = american_to_implied_prob(odds_b)

        lines = [
            f"=== {label_a} ({odds_a:+d}) vs {label_b} ({odds_b:+d}) ===",
            f"Raw implied probabilities: {label_a} {raw_a:.1%}  |  {label_b} {raw_b:.1%}  (sum: {raw_a+raw_b:.1%})",
            f"Vig/overround: {vig_pct:.2f} percentage points",
            f"De-vigged (TRUE market) probabilities: {label_a} {true_a:.1%}  |  {label_b} {true_b:.1%}",
            f"Fair odds equivalent: {label_a} {implied_prob_to_american(true_a):+d}  |  {label_b} {implied_prob_to_american(true_b):+d}",
        ]

        if our_prob_a is not None:
            e = edge(our_prob_a, true_a)
            lines.append("")
            lines.append(f"Your model's probability for {label_a}: {our_prob_a:.1%}")
            lines.append(f"Edge vs true market probability: {e:+.1f} percentage points")
            if e > 3:
                lines.append(f"-> Your model thinks {label_a} is UNDERVALUED by the market (potential edge, IF your model is right)")
            elif e < -3:
                lines.append(f"-> Your model thinks {label_a} is OVERVALUED by the market (potential edge on {label_b}, IF your model is right)")
            else:
                lines.append("-> Your model roughly agrees with the market — no meaningful edge either way")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))


def open_window():
    win = tk.Toplevel()
    DevigToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    DevigToolWindow(root)
    root.mainloop()
